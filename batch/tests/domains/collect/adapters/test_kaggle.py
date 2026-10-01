"""2026-10-01에 저장한 실제 응답으로 본다. 일반 탭 1쪽 20건 · 2쪽 1건이고 3쪽은 빈 객체였다."""

from __future__ import annotations

import json
from datetime import date

import httpx

from collector.domains.collect.adapters import kaggle
from tests.conftest import FakeClock, fixture_bytes, make_http, response_of

BASE = date(2026, 10, 1)
PAGES = {1: "kaggle_p1_1001.json", 2: "kaggle_p2_1001.json"}


def item(slug: str, deadline: str, category: str = "Featured", **extra: object) -> dict:
    return {
        "ref": f"https://www.kaggle.com/competitions/{slug}",
        "title": slug.replace("-", " ").title(),
        "category": category,
        "deadline": deadline,
        "enabledDate": "2026-08-01T00:00:00Z",
        "tags": [{"name": "tabular"}],
        **extra,
    }


def test_missing_token_means_missing_config() -> None:
    assert kaggle.KaggleSource(None).missing_config()
    assert not kaggle.KaggleSource("t").missing_config()


def test_parses_saved_page() -> None:
    items = kaggle.parse_page(response_of("kaggle_p1_1001.json", "application/json"))
    competitions = [kaggle.normalize(i) for i in items]
    assert len(competitions) == 20 and all(competitions)
    # Getting Started 11 · Playground 2가 연습용이다
    assert sum(1 for c in competitions if c and c.practice) == 13
    knee = next(c for c in competitions if c and c.source_id == "rsna-knee-abnormality-detection")
    assert knee.link == "https://www.kaggle.com/competitions/rsna-knee-abnormality-detection"
    # 새 참가 마감 2026-10-15T23:59:00Z는 KST로 다음 날이다
    assert (knee.start_date, knee.deadline) == (date(2026, 8, 6), date(2026, 10, 16))
    assert knee.extras[0] == "Research"


def test_empty_object_is_an_empty_page() -> None:
    response = httpx.Response(200, json={})
    assert kaggle.parse_page(response) == []


def test_deadline_with_milliseconds() -> None:
    c = kaggle.normalize(item("paper", "2026-11-12T23:59:00.807Z"))
    assert c is not None and c.deadline == date(2026, 11, 13)


def test_practice_categories_are_marked() -> None:
    for category in ("Getting Started", "gettingStarted", "Playground"):
        c = kaggle.normalize(item("titanic", "2030-01-01T00:00:00Z", category=category))
        assert c is not None and c.practice
    for category in ("Featured", "Research", "Community"):
        c = kaggle.normalize(item("cup", "2026-12-01T00:00:00Z", category=category))
        assert c is not None and not c.practice


def test_collect_turns_pages_until_an_empty_one(clock: FakeClock) -> None:
    bodies = []
    auths = set()

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        bodies.append(body)
        auths.add(request.headers.get("authorization"))
        name = PAGES.get(body["page"])
        if name is None:
            return httpx.Response(200, json={})
        return httpx.Response(
            200, content=fixture_bytes(name), headers={"content-type": "application/json"}
        )

    collected = kaggle.KaggleSource("secret-token").collect(
        make_http(handler, clock=clock), BASE, page_cap=20
    )
    assert [b["page"] for b in bodies] == [1, 2, 3]
    assert "pageSize" not in bodies[0] and "pageToken" not in bodies[0]
    assert auths == {"Bearer secret-token"}
    assert (collected.collected, collected.dropped) == (21, 0)
    assert len(collected.competitions) == 21
    assert not collected.page_cap_hit


def test_collect_stops_on_a_closed_page(clock: FakeClock) -> None:
    pages = []

    def handler(request: httpx.Request) -> httpx.Response:
        pages.append(json.loads(request.content)["page"])
        return httpx.Response(200, json={"competitions": [item("old", "2026-01-01T00:00:00Z")]})

    collected = kaggle.KaggleSource("t").collect(make_http(handler, clock=clock), BASE, page_cap=20)
    assert pages == [1]
    assert collected.collected == 1


def test_collect_reports_the_page_cap(clock: FakeClock) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"competitions": [item("open", "2026-12-01T00:00:00Z")]})

    collected = kaggle.KaggleSource("t").collect(make_http(handler, clock=clock), BASE, page_cap=2)
    assert collected.page_cap_hit
    assert collected.collected == 2
