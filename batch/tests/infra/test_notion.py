from __future__ import annotations

import threading

import httpx
import pytest

from collector.infra.notion import NOTION_VERSION, NotionFailure, NotionHttp
from tests.conftest import NOTION_SETTINGS, FakeClock


def make(handler, clock: FakeClock) -> NotionHttp:
    client = httpx.Client(base_url="https://api.notion.com", transport=httpx.MockTransport(handler))
    return NotionHttp(NOTION_SETTINGS, "secret", threading.Event(), client=client, sleep=clock.sleep, clock=clock)


def sequence(*responses):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        item = responses[min(len(calls) - 1, len(responses) - 1)]
        if isinstance(item, Exception):
            raise item
        return item

    return handler, calls


def test_headers(clock: FakeClock) -> None:
    handler, calls = sequence(httpx.Response(200, json={"ok": True}))
    make(handler, clock).read("GET", "/v1/data_sources/x")
    assert calls[0].headers["Notion-Version"] == NOTION_VERSION
    assert calls[0].headers["Authorization"] == "Bearer secret"


def test_read_retries_busy_and_server_errors(clock: FakeClock) -> None:
    handler, calls = sequence(
        httpx.Response(429, headers={"Retry-After": "2"}),
        httpx.Response(502),
        httpx.Response(200, json={"results": []}),
    )
    assert make(handler, clock).read("POST", "/q") == {"results": []}
    assert len(calls) == 3


def test_read_client_error_is_not_retried(clock: FakeClock) -> None:
    handler, calls = sequence(httpx.Response(404, json={"code": "object_not_found", "message": "없음"}))
    with pytest.raises(NotionFailure) as err:
        make(handler, clock).read("POST", "/q")
    assert err.value.status == 404 and len(calls) == 1
    assert "object_not_found" in err.value.detail


def test_retry_after_over_cap_is_not_awaited(clock: FakeClock) -> None:
    handler, calls = sequence(httpx.Response(429, headers={"Retry-After": "90"}))
    with pytest.raises(NotionFailure):
        make(handler, clock).read("POST", "/q")
    assert len(calls) == 1


def test_write_retries_only_busy_and_unsent(clock: FakeClock) -> None:
    request = httpx.Request("POST", "https://api.notion.com/v1/pages")
    handler, calls = sequence(
        httpx.ConnectError("refused", request=request),
        httpx.Response(529),
        httpx.Response(200, json={"id": "page-1"}),
    )
    response = make(handler, clock).write("POST", "/v1/pages", json={})
    assert response.data["id"] == "page-1" and len(calls) == 3


@pytest.mark.parametrize("status", [500, 502, 503, 409, 400])
def test_write_does_not_retry_errors_that_may_have_written(clock: FakeClock, status: int) -> None:
    handler, calls = sequence(httpx.Response(status, json={"code": "x", "message": "y"}))
    with pytest.raises(NotionFailure) as err:
        make(handler, clock).write("POST", "/v1/pages", json={})
    assert len(calls) == 1
    assert err.value.maybe_written is (status >= 500)


def test_write_read_timeout_is_not_retried(clock: FakeClock) -> None:
    request = httpx.Request("POST", "https://api.notion.com/v1/pages")
    handler, calls = sequence(httpx.ReadTimeout("slow", request=request))
    with pytest.raises(NotionFailure) as err:
        make(handler, clock).write("POST", "/v1/pages", json={})
    assert err.value.maybe_written and len(calls) == 1


def test_503_with_committed_id_counts_as_created(clock: FakeClock) -> None:
    body = {"code": "service_unavailable", "additional_data": {"committed_resource_id": "page-9"}}
    handler, calls = sequence(httpx.Response(503, json=body))
    response = make(handler, clock).write("POST", "/v1/pages", json={})
    assert response.committed_id == "page-9" and len(calls) == 1


def test_requests_are_paced_to_three_per_second(clock: FakeClock) -> None:
    handler, _ = sequence(httpx.Response(200, json={}))
    http = make(handler, clock)
    for _ in range(4):
        http.read("GET", "/x")
    assert sum(clock.slept) == pytest.approx(1.0, abs=0.01)
