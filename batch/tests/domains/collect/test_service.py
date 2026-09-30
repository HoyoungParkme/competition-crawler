from __future__ import annotations

import threading
from datetime import date

import httpx

from collector.domains.collect.models import Collected, FailureKind, SourceName
from collector.domains.collect.service import CollectService
from collector.infra.http import FormatError, HttpFailure, SourceHttp
from tests.conftest import SOURCE_SETTINGS, FakeClock, comp


class FakeSource:
    origin = "https://src.test"
    robots_paths = ("/list",)

    def __init__(self, name: SourceName, behaviour, *, missing: bool = False) -> None:
        self.name = name
        self._behaviour = behaviour
        self._missing = missing

    def missing_config(self) -> bool:
        return self._missing

    def collect(self, http: SourceHttp, base_date: date, page_cap: int) -> Collected:
        return self._behaviour()


def http_factory(robots: str = "User-agent: *\nAllow: /\n"):
    def factory(settings, deadline, stop):
        clock = FakeClock()
        client = httpx.Client(
            transport=httpx.MockTransport(lambda r: httpx.Response(200, text=robots))
        )
        return SourceHttp(
            settings,
            deadline=clock() + 100,
            stop=stop,
            client=client,
            sleep=clock.sleep,
            clock=clock,
        )

    return factory


def run(sources, robots: str = "User-agent: *\nAllow: /\n"):
    service = CollectService(SOURCE_SETTINGS, sources, threading.Event(), http_factory(robots))
    return service.collect_all(date(2026, 9, 27))


def raise_(exc):
    def behaviour():
        raise exc

    return behaviour


def test_failures_become_empty_results_with_a_kind() -> None:
    ok = FakeSource(
        SourceName.DACON, lambda: Collected([comp("대회", source=SourceName.DACON)], collected=1)
    )
    results = run(
        [
            ok,
            FakeSource(SourceName.KAGGLE, None, missing=True),
            FakeSource(SourceName.WEVITY, raise_(HttpFailure("connection", "timeout"))),
            FakeSource(SourceName.EVENTUS, raise_(HttpFailure("status", "응답 404", 404))),
            FakeSource(SourceName.AIFACTORY, raise_(FormatError("틀"))),
            FakeSource(SourceName.CONTESTKOREA, raise_(KeyError("x"))),
        ]
    )
    kinds = {str(r.source): r.failure for r in results}
    assert kinds == {
        "DACON": None,
        "Kaggle": FailureKind.MISSING_CONFIG,
        "wevity": FailureKind.CONNECTION,
        "event-us": FailureKind.HTTP_STATUS,
        "AI팩토리": FailureKind.FORMAT,
        "콘테스트코리아": FailureKind.FORMAT,
    }
    assert results[0].normalized == 1
    assert all(r.competitions == [] for r in results[1:])


def test_budget_is_a_connection_failure() -> None:
    results = run([FakeSource(SourceName.DACON, raise_(HttpFailure("budget", "예산")))])
    assert results[0].failure is FailureKind.CONNECTION


def test_robots_disallow_is_its_own_kind() -> None:
    results = run(
        [FakeSource(SourceName.DACON, lambda: Collected([], 0))],
        robots="User-agent: *\nDisallow: /\n",
    )
    assert results[0].failure is FailureKind.ROBOTS
