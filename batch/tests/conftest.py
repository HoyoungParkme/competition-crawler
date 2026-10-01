from __future__ import annotations

import threading
import zlib
from collections.abc import Callable
from datetime import date
from pathlib import Path

import httpx
import pytest

from collector.core.settings import JudgeSettings, SourceSettings
from collector.infra.http import SourceHttp, new_client

FIXTURES = Path(__file__).parent / "fixtures"


def fixture_bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def response_of(name: str, content_type: str = "text/html; charset=utf-8") -> httpx.Response:
    return httpx.Response(200, content=fixture_bytes(name), headers={"content-type": content_type})


class FakeClock:
    """가짜 시계. sleep이 시계를 앞으로 민다."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.slept: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


SOURCE_SETTINGS = SourceSettings(
    timeout_seconds=20,
    retries=2,
    backoff_seconds=(2.0, 4.0),
    retry_after_cap_seconds=30,
    interval_seconds=1.0,
    page_cap=20,
    budget_seconds=120,
)
JUDGE_SETTINGS = JudgeSettings(
    model="gpt-6-luna",
    timeout_seconds=30,
    retries=2,
    concurrency=4,
    max_output_tokens=300,
    backoff_seconds=(2.0, 4.0),
)


def make_http(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    settings: SourceSettings = SOURCE_SETTINGS,
    clock: FakeClock | None = None,
    stop: threading.Event | None = None,
) -> SourceHttp:
    clock = clock or FakeClock()
    return SourceHttp(
        settings,
        deadline=clock() + settings.budget_seconds,
        stop=stop or threading.Event(),
        client=new_client(httpx.MockTransport(handler)),
        sleep=clock.sleep,
        clock=clock,
    )


def comp(
    title: str,
    *,
    source=None,
    source_id: str | None = None,
    start: date | None = None,
    deadline: date | None = None,
    link: str | None = None,
    extras: tuple[str, ...] = (),
    practice: bool = False,
):
    """테스트용 대회. 수집 경계를 여기서 불러오면 기반 테스트가 수집 경계에 묶이므로 안에서 부른다."""
    from collector.domains.collect.models import Competition, SourceName

    source = source or SourceName.EVENTUS
    sid = source_id or str(zlib.crc32(f"{source}:{title}".encode()))
    return Competition(
        source=source,
        source_id=sid,
        title=title,
        link=link or f"https://example.com/{source}/{sid}",
        start_date=start,
        deadline=deadline,
        extras=extras,
        practice=practice,
    )


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()
