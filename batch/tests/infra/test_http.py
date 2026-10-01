from __future__ import annotations

import threading
from datetime import UTC

import httpx
import pytest

from collector.infra.http import FormatError, HttpFailure, Stopped, parse_retry_after
from tests.conftest import FakeClock, make_http


def text(response: httpx.Response) -> str:
    return response.text


def test_retries_5xx_with_backoff_then_succeeds(clock: FakeClock) -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(503) if len(calls) < 3 else httpx.Response(200, text="ok")

    http = make_http(handler, clock=clock)
    assert http.fetch("GET", "https://src.test/list", parse=text) == "ok"
    assert len(calls) == 3
    assert http.requests == 3
    # 2초, 4초로 늘려 가며 기다린다
    assert sum(clock.slept) == pytest.approx(6.0)


def test_gives_up_after_two_retries(clock: FakeClock) -> None:
    http = make_http(lambda r: httpx.Response(500), clock=clock)
    with pytest.raises(HttpFailure) as err:
        http.fetch("GET", "https://src.test/list", parse=text)
    assert err.value.category == "status"
    assert http.requests == 3


def test_client_error_is_not_retried(clock: FakeClock) -> None:
    http = make_http(lambda r: httpx.Response(404), clock=clock)
    with pytest.raises(HttpFailure) as err:
        http.fetch("GET", "https://src.test/list", parse=text)
    assert err.value.status == 404
    assert http.requests == 1


def test_redirect_is_a_status_failure_and_not_followed(clock: FakeClock) -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(301, headers={"Location": "https://src.test/moved"})

    http = make_http(handler, clock=clock)
    with pytest.raises(HttpFailure) as err:
        http.fetch("GET", "https://src.test/list", parse=text)
    assert err.value.category == "status"
    assert calls == ["https://src.test/list"]


def test_retry_after_longer_than_cap_fails_without_waiting(clock: FakeClock) -> None:
    http = make_http(lambda r: httpx.Response(429, headers={"Retry-After": "45"}), clock=clock)
    with pytest.raises(HttpFailure):
        http.fetch("GET", "https://src.test/list", parse=text)
    assert http.requests == 1
    assert clock.slept == []


def test_retry_after_within_cap_is_honoured(clock: FakeClock) -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return (
            httpx.Response(429, headers={"Retry-After": "7"})
            if len(calls) == 1
            else httpx.Response(200, text="ok")
        )

    http = make_http(handler, clock=clock)
    assert http.fetch("GET", "https://src.test/list", parse=text) == "ok"
    assert sum(clock.slept) == pytest.approx(7.0)


def test_format_error_is_retried_and_then_reported_as_format(clock: FakeClock) -> None:
    def parse(response: httpx.Response) -> str:
        raise FormatError("틀이 다르다")

    http = make_http(lambda r: httpx.Response(200, text="<html>"), clock=clock)
    with pytest.raises(HttpFailure) as err:
        http.fetch("GET", "https://src.test/list", parse=parse)
    assert err.value.category == "format"
    assert http.requests == 3


def test_connection_error_is_retried(clock: FakeClock) -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            raise httpx.ConnectError("refused", request=request)
        return httpx.Response(200, text="ok")

    http = make_http(handler, clock=clock)
    assert http.fetch("GET", "https://src.test/list", parse=text) == "ok"


def test_requests_are_spaced_one_second_apart(clock: FakeClock) -> None:
    http = make_http(lambda r: httpx.Response(200, text="ok"), clock=clock)
    http.fetch("GET", "https://src.test/a", parse=text)
    http.fetch("GET", "https://src.test/b", parse=text)
    assert sum(clock.slept) == pytest.approx(1.0)


def test_budget_exhaustion_is_a_budget_failure(clock: FakeClock) -> None:
    http = make_http(lambda r: httpx.Response(200, text="ok"), clock=clock)
    clock.now += 121
    with pytest.raises(HttpFailure) as err:
        http.fetch("GET", "https://src.test/list", parse=text)
    assert err.value.category == "budget"


def test_stop_flag_stops_new_requests(clock: FakeClock) -> None:
    stop = threading.Event()
    stop.set()
    http = make_http(lambda r: httpx.Response(200, text="ok"), clock=clock, stop=stop)
    with pytest.raises(Stopped):
        http.fetch("GET", "https://src.test/list", parse=text)


def test_user_agent_identifies_the_crawler(clock: FakeClock) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["ua"] = request.headers.get("user-agent")
        return httpx.Response(200, text="ok")

    make_http(handler, clock=clock).fetch("GET", "https://src.test/list", parse=text)
    assert seen["ua"].startswith("competition-crawler/")


def test_cookies_from_a_response_are_not_sent_back(clock: FakeClock) -> None:
    sent = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request.headers.get("cookie"))
        return httpx.Response(200, text="ok", headers={"set-cookie": "ka_sessionid=abc; Path=/"})

    http = make_http(handler, clock=clock)
    http.fetch("GET", "https://src.test/robots.txt", parse=text)
    http.fetch("POST", "https://src.test/list", parse=text)
    # Kaggle은 익명 세션 쿠키가 실린 요청을 토큰이 있어도 401로 거절한다(2026-10-01)
    assert sent == [None, None]


def test_parse_retry_after_reads_seconds_and_dates() -> None:
    from datetime import datetime

    assert parse_retry_after("12") == 12
    assert parse_retry_after(None) is None
    now = datetime(2026, 9, 27, 0, 0, 0, tzinfo=UTC)
    assert parse_retry_after("Sun, 27 Sep 2026 00:00:30 GMT", now=now) == pytest.approx(30)
    assert parse_retry_after("soon") is None


def test_budget_also_cuts_a_slow_body(clock: FakeClock) -> None:
    # httpx 타임아웃은 조각마다 다시 재므로, 조금씩 오는 본문은 기한을 넘겨도 끊기지 않는다(CCR-INFRA-001 8.5)
    def slow_body():
        for _ in range(10):
            clock.now += 50
            yield b"x" * 10

    http = make_http(lambda r: httpx.Response(200, content=slow_body()), clock=clock)
    with pytest.raises(HttpFailure) as err:
        http.fetch("GET", "https://src.test/list", parse=text)
    assert err.value.category == "budget"


def test_compressed_body_is_decoded_once(clock: FakeClock) -> None:
    import gzip

    body = gzip.compress("한글 목록".encode())
    http = make_http(
        lambda r: httpx.Response(
            200,
            content=body,
            headers={"content-encoding": "gzip", "content-type": "text/plain; charset=utf-8"},
        ),
        clock=clock,
    )
    assert http.fetch("GET", "https://src.test/list", parse=text) == "한글 목록"
