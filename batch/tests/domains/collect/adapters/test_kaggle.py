"""Kaggle은 실측 전이다. 공식 클라이언트 코드의 필드 이름으로 만든 응답으로 본다(CCR-API-001 5장)."""

from __future__ import annotations

from datetime import date

import httpx

from collector.domains.collect.adapters import kaggle
from tests.conftest import FakeClock, make_http

BASE = date(2026, 9, 27)


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


def test_normalize_uses_slug_and_new_entrant_deadline() -> None:
    c = kaggle.normalize(
        item("ai-cup", "2026-12-01T23:59:00Z", newEntrantDeadline="2026-11-24T23:59:00Z")
    )
    assert c is not None
    assert c.source_id == "ai-cup"
    assert c.link == "https://www.kaggle.com/competitions/ai-cup"
    assert c.deadline == date(2026, 11, 25)  # UTC 23:59는 KST로 다음 날
    assert c.extras == ("Featured", "tabular")
    assert not c.practice


def test_practice_categories_are_marked() -> None:
    for category in ("Getting Started", "gettingStarted", "Playground"):
        c = kaggle.normalize(item("titanic", "2030-01-01T00:00:00Z", category=category))
        assert c is not None and c.practice


def test_collect_sends_bearer_and_stops_on_closed_page(clock: FakeClock) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(
            200,
            json={"competitions": [item("old", "2026-01-01T00:00:00Z")], "nextPageToken": "next"},
        )

    collected = kaggle.KaggleSource("secret-token").collect(
        make_http(handler, clock=clock), BASE, page_cap=20
    )
    assert seen["auth"] == "Bearer secret-token"
    assert collected.collected == 1
