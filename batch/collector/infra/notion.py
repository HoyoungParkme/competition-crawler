"""노션 API에 거는 요청(CCR-API-001 1.4 · 2.3 · CCR-INFRA-001 8.5).

읽기는 같은 요청을 다시 보내도 결과가 같아 연결 오류 · 타임아웃 · 429 · 529 · 5xx에 다시 보낸다.
쓰기는 다시 보내면 같은 행이 둘 생길 수 있어, 노션이 속도 제한이나 과부하로 거절했거나 요청이
노션에 닿지 않았을 때만 다시 보낸다. 요청 헤더는 로그에 찍지 않는다.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

import httpx

from collector.core.settings import NotionSettings
from collector.infra.http import USER_AGENT, Stopped, parse_retry_after

NOTION_VERSION = "2025-09-03"
BASE_URL = "https://api.notion.com"
_BUSY = (429, 529)
# 연결을 맺기 전에 난 오류. 요청이 노션에 닿지 않았다
_NOT_SENT = (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout)


class NotionFailure(Exception):
    """끝내 받지 못했다. detail은 로그에만 남긴다."""

    def __init__(self, detail: str, *, status: int | None = None, maybe_written: bool = False) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status = status
        self.maybe_written = maybe_written  # 응답 없이 끊긴 쓰기. 행이 생겼을 수 있다


@dataclass(frozen=True)
class WriteResponse:
    data: dict[str, Any]
    committed_id: str | None = None  # 503이 알려 준 새 행의 id(CCR-UC-001 UC-S6 2d)


def _error_text(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return f"응답 {response.status_code}"
    if isinstance(body, dict):
        text = f"응답 {response.status_code} {body.get('code', '')}: {body.get('message', '')}".strip()
        extra = body.get("additional_data")
        guidance = extra.get("retry_guidance") if isinstance(extra, dict) else None
        if guidance:
            text += f" (retry_guidance: {guidance})"  # 503이 쓰기가 저장됐는지 알려 준다. 로그에만 남긴다
        return text
    return f"응답 {response.status_code}"


def _committed_id(response: httpx.Response) -> str | None:
    try:
        body = response.json()
    except ValueError:
        return None
    extra = body.get("additional_data") if isinstance(body, dict) else None
    value = extra.get("committed_resource_id") if isinstance(extra, dict) else None
    return str(value) if value else None


class NotionHttp:
    def __init__(
        self,
        settings: NotionSettings,
        token: str,
        stop: threading.Event,
        *,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._settings = settings
        self._stop = stop
        self._sleep = sleep
        self._clock = clock
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_VERSION,
            "User-Agent": USER_AGENT,
        }
        self._client = client or httpx.Client(base_url=BASE_URL)
        self._last: float | None = None
        self.requests = 0

    def close(self) -> None:
        self._client.close()

    def _wait(self, seconds: float) -> None:
        while seconds > 0:
            if self._stop.is_set():
                raise Stopped()
            chunk = min(seconds, 0.5)
            self._sleep(chunk)
            seconds -= chunk

    def _pace(self) -> None:
        # 읽기와 쓰기를 합쳐 평균 초당 3회를 넘지 않는다
        if self._last is not None:
            self._wait(1.0 / self._settings.requests_per_second - (self._clock() - self._last))
        if self._stop.is_set():
            raise Stopped()

    def _send(self, method: str, path: str, json: Any, timeout: float) -> httpx.Response:
        self._pace()
        try:
            return self._client.request(method, path, json=json, headers=self._headers, timeout=timeout)
        finally:
            self._last = self._clock()
            self.requests += 1

    def _busy_wait(self, response: httpx.Response, attempt: int) -> None:
        wait = parse_retry_after(response.headers.get("Retry-After"))
        if wait is None:
            self._backoff(attempt)
        elif wait > self._settings.retry_after_cap_seconds:
            raise NotionFailure(f"Retry-After {wait:.0f}초가 상한보다 길다", status=response.status_code)
        else:
            self._wait(wait)

    def _backoff(self, attempt: int) -> None:
        steps = self._settings.backoff_seconds or (1.0,)
        self._wait(steps[min(attempt, len(steps) - 1)])

    def read(self, method: str, path: str, json: Any = None) -> dict[str, Any]:
        attempts = 1 + max(0, self._settings.retries)
        last_error = "다시 보낼 횟수를 다 썼다"
        for attempt in range(attempts):
            final = attempt == attempts - 1
            try:
                response = self._send(method, path, json, self._settings.read_timeout_seconds)
            except httpx.HTTPError as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                if final:
                    break
                self._backoff(attempt)
                continue
            status = response.status_code
            if status == 200:
                try:
                    data = response.json()
                except ValueError:
                    data = None
                if isinstance(data, dict):
                    return data
                last_error = "응답이 JSON 객체가 아니다"
                if final:
                    break
                self._backoff(attempt)
                continue
            if status in _BUSY:
                last_error = _error_text(response)
                if final:
                    break
                self._busy_wait(response, attempt)
                continue
            if status >= 500:
                last_error = _error_text(response)
                if final:
                    break
                self._backoff(attempt)
                continue
            raise NotionFailure(_error_text(response), status=status)
        raise NotionFailure(last_error)

    def write(self, method: str, path: str, json: Any) -> WriteResponse:
        attempts = 1 + max(0, self._settings.retries)
        last_error = "다시 보낼 횟수를 다 썼다"
        for attempt in range(attempts):
            final = attempt == attempts - 1
            try:
                response = self._send(method, path, json, self._settings.write_timeout_seconds)
            except _NOT_SENT as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                if final:
                    break
                self._backoff(attempt)
                continue
            except httpx.HTTPError as exc:
                # 연결을 맺은 뒤 끊겼다. 행이 이미 생겼을 수 있어 다시 보내지 않는다
                raise NotionFailure(f"{type(exc).__name__}: {exc}", maybe_written=True) from exc
            status = response.status_code
            if status == 200:
                try:
                    data = response.json()
                except ValueError:
                    data = {}
                return WriteResponse(data if isinstance(data, dict) else {})
            if status in _BUSY:
                last_error = _error_text(response)
                if final:
                    break
                self._busy_wait(response, attempt)
                continue
            if status == 503:
                committed = _committed_id(response)
                if committed:
                    return WriteResponse({}, committed_id=committed)
            raise NotionFailure(_error_text(response), status=status, maybe_written=status >= 500)
        raise NotionFailure(last_error)
