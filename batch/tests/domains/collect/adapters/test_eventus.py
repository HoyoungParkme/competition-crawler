from __future__ import annotations

import json
from datetime import date

import httpx

from collector.domains.collect.adapters import eventus
from collector.domains.collect.models import SourceName
from tests.conftest import FakeClock, fixture_bytes, make_http, response_of

BASE = date(2026, 9, 23)


def test_query_filters_open_contests_from_kst_midnight() -> None:
    query = eventus.build_query(BASE, 2)
    assert query["page"] == {"current": 2, "size": 100}
    assert {"event_type": ["대회/공모전"]} in query["filters"]["all"]
    assert query["filters"]["any"][0] == {
        "register_due_date": {"from": "2026-09-22T15:00:00+00:00"}
    }
    assert query["sort"] == [{"register_due_date": "asc"}]


def test_parses_saved_page() -> None:
    items, total_pages = eventus.parse_page(response_of("eventus_final.json", "application/json"))
    assert total_pages == 1
    competitions = [eventus.normalize(i) for i in items]
    assert len(competitions) == 40 and all(competitions)
    found = next(c for c in competitions if c and c.source_id == "135608")
    assert found.source is SourceName.EVENTUS
    assert found.link == "https://event-us.kr/intween/event/135608"
    # UTC 값을 KST 날짜로 바꾼다
    assert (found.start_date, found.deadline) == (date(2026, 9, 17), date(2026, 9, 23))
    assert found.extras[0] == "창업"


def test_item_without_subdomain_is_dropped() -> None:
    assert eventus.normalize({"id": {"raw": "1"}, "title": {"raw": "대회"}}) is None


def test_collect_reads_every_page(clock: FakeClock) -> None:
    data = json.loads(fixture_bytes("eventus_final.json"))
    pages = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        pages.append(body["page"]["current"])
        page = dict(data, meta={"page": {"current": body["page"]["current"], "total_pages": 2}})
        page["results"] = (
            data["results"][:20] if body["page"]["current"] == 1 else data["results"][20:]
        )
        return httpx.Response(200, json=page)

    collected = eventus.EventUsSource().collect(make_http(handler, clock=clock), BASE, page_cap=20)
    assert pages == [1, 2]
    assert collected.collected == 40 and len(collected.competitions) == 40
    assert not collected.page_cap_hit


def test_page_cap_stops_collection(clock: FakeClock) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"meta": {"page": {"total_pages": 50}}, "results": []})

    collected = eventus.EventUsSource().collect(make_http(handler, clock=clock), BASE, page_cap=2)
    assert collected.page_cap_hit
