"""대회 소스에 거는 요청.

모든 요청에 식별 가능한 User-Agent를 붙이고, 같은 소스 안에서 요청 사이 1초를 둔다.
연결 오류 · 타임아웃 · 429 · 5xx · 틀이 다른 응답은 정해진 횟수만큼 다시 보낸다. 그 밖의 4xx와
3xx는 다시 보내지 않는다. 소스마다 시간 예산이 있고, 기다림과 요청이 그 기한을 넘지 않는다.
httpx의 타임아웃은 단계마다 걸려 요청 전체를 묶지 못하므로, 본문을 받는 동안에도 기한을 본다
(CCR-API-001 1.1 · 1.2 · 2.1 · CCR-INFRA-001 8.5).
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Callable, Mapping, TypeVar

import httpx

from collector.core.settings import SourceSettings

USER_AGENT = "competition-crawler/0.1 (+https://github.com/HoyoungParkme/competition-crawler)"
# 본문을 풀어서 받으므로 다시 만드는 응답에서는 전송 방식을 뜻하는 머리말을 뺀다
_DECODED_HEADERS = {"content-encoding", "content-length", "transfer-encoding"}

T = TypeVar("T")


class FormatError(Exception):
    """응답의 틀이 예상과 다르다. 다시 보내 볼 만하다."""


class Stopped(Exception):
    """신호를 받아 새 요청을 멈췄다."""


class HttpFailure(Exception):
    """끝내 받지 못했다. category는 connection · status · format · budget 가운데 하나다."""

    def __init__(self, category: str, detail: str, status: int | None = None) -> None:
        super().__init__(detail)
        self.category = category
        self.detail = detail
        self.status = status


def parse_retry_after(value: str | None, now: datetime | None = None) -> float | None:
    """CCR-MS-001#http.parse_retry_after

    `Retry-After`를 초로 읽는다. 초 수와 HTTP 날짜를 모두 받는다. 읽지 못하면 None.
    """
    if not value:
        return None
    value = value.strip()
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        when = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return max(0.0, (when - (now or datetime.now(timezone.utc))).total_seconds())


class SourceHttp:
    """소스 하나가 한 실행에서 쓰는 요청 도구. 시간 예산의 기한은 만들 때 정한다."""

    def __init__(
        self,
        settings: SourceSettings,
        *,
        deadline: float,
        stop: threading.Event,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._settings = settings
        self._deadline = deadline
        self._stop = stop
        self._client = client or httpx.Client(headers={"User-Agent": USER_AGENT}, max_redirects=5)
        self._sleep = sleep
        self._clock = clock
        self._last_request: float | None = None
        self.requests = 0

    def close(self) -> None:
        """CCR-MS-001#SourceHttp.close"""
        self._client.close()

    def remaining(self) -> float:
        """CCR-MS-001#SourceHttp.remaining"""
        return self._deadline - self._clock()

    def _check(self) -> None:
        if self._stop.is_set():
            raise Stopped()
        if self.remaining() <= 0:
            raise HttpFailure("budget", "소스의 시간 예산을 넘겼다")

    def _wait(self, seconds: float) -> None:
        if seconds <= 0:
            return
        if seconds > self.remaining():
            raise HttpFailure("budget", "기다릴 시간이 남은 예산보다 길다")
        end = self._clock() + seconds
        while True:
            left = end - self._clock()
            if left <= 0:
                return
            if self._stop.is_set():
                raise Stopped()
            self._sleep(min(left, 0.5))

    def _pace(self) -> None:
        if self._last_request is None:
            return
        gap = self._settings.interval_seconds - (self._clock() - self._last_request)
        self._wait(gap)

    def _backoff(self, attempt: int) -> None:
        steps = self._settings.backoff_seconds or (1.0,)
        self._wait(steps[min(attempt, len(steps) - 1)])

    def _receive(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, Any] | None,
        json: Any,
        headers: Mapping[str, str] | None,
        timeout: float,
        follow_redirects: bool,
    ) -> httpx.Response:
        """요청하고 본문을 끝까지 받는다. 받는 동안에도 멈춤 표시와 시간 예산의 기한을 본다."""
        request = self._client.build_request(method, url, params=params, json=json, headers=headers, timeout=timeout)
        response = self._client.send(request, stream=True, follow_redirects=follow_redirects)
        body = bytearray()
        try:
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if self._stop.is_set():
                    raise Stopped()
                if self.remaining() <= 0:
                    raise HttpFailure("budget", "응답을 받는 중에 소스의 시간 예산을 넘겼다")
        finally:
            response.close()
        kept = [(k, v) for k, v in response.headers.multi_items() if k.lower() not in _DECODED_HEADERS]
        return httpx.Response(
            response.status_code,
            headers=kept,
            content=bytes(body),
            request=response.request,
            history=response.history,
        )

    def fetch(
        self,
        method: str,
        url: str,
        *,
        parse: Callable[[httpx.Response], T],
        params: Mapping[str, Any] | None = None,
        json: Any = None,
        headers: Mapping[str, str] | None = None,
        follow_redirects: bool = False,
        accept_client_errors: bool = False,
    ) -> T:
        """CCR-MS-001#SourceHttp.fetch

        요청하고 `parse`로 읽는다. `parse`가 FormatError를 내면 다시 보낸다.
        """
        attempts = 1 + max(0, self._settings.retries)
        for attempt in range(attempts):
            last = attempt == attempts - 1
            self._check()
            self._pace()
            self._check()
            timeout = min(self._settings.timeout_seconds, self.remaining())
            try:
                response = self._receive(
                    method,
                    url,
                    params=params,
                    json=json,
                    headers=headers,
                    timeout=timeout,
                    follow_redirects=follow_redirects,
                )
            except httpx.HTTPError as exc:  # 연결 오류 · 타임아웃
                self._last_request = self._clock()
                self.requests += 1
                if last:
                    raise HttpFailure("connection", f"{type(exc).__name__}: {exc}") from exc
                self._backoff(attempt)
                continue
            self._last_request = self._clock()
            self.requests += 1
            status = response.status_code
            if 300 <= status < 400:
                # 목록 주소가 바뀐 것이라 사람이 알아채야 한다(CCR-API-001 1.2)
                raise HttpFailure("status", f"리디렉션 {status}", status)
            if status == 429 or status >= 500:
                failure = HttpFailure("status", f"응답 {status}", status)
                if last:
                    raise failure
                wait = parse_retry_after(response.headers.get("Retry-After"))
                if wait is not None:
                    if wait > self._settings.retry_after_cap_seconds or wait > self.remaining():
                        raise failure
                    self._wait(wait)
                else:
                    self._backoff(attempt)
                continue
            if status >= 400 and not accept_client_errors:
                raise HttpFailure("status", f"응답 {status}", status)
            try:
                return parse(response)
            except FormatError as exc:
                if last:
                    raise HttpFailure("format", str(exc)) from exc
                self._backoff(attempt)
                continue
        raise HttpFailure("connection", "다시 보낼 횟수를 다 썼다")  # 도달하지 않는다
