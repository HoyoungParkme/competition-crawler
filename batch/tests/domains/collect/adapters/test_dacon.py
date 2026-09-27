from __future__ import annotations

from datetime import date

import httpx

from collector.domains.collect.adapters import dacon
from tests.conftest import FakeClock, fixture_bytes, make_http, response_of

BASE = date(2026, 9, 27)


def test_parses_saved_page_and_builds_links() -> None:
    items = dacon.parse_page(response_of("dacon_off0.json", "application/json"))
    competitions = [dacon.normalize(i) for i in items]
    assert len(competitions) == 15 and all(competitions)
    scpc = next(c for c in competitions if c and c.source_id == "236746")
    assert scpc.link == "https://dacon.io/competition/236746/overview"
    assert (scpc.start_date, scpc.deadline) == (date(2026, 7, 6), date(2026, 8, 28))
    assert "알고리즘" in scpc.extras


def test_official_link_when_not_a_landing_page() -> None:
    assert dacon.link_for("123", 0) == "https://dacon.io/competitions/official/123/overview/description"


def test_stops_after_a_page_with_nothing_open(clock: FakeClock) -> None:
    offsets = []

    def handler(request: httpx.Request) -> httpx.Response:
        offset = int(request.url.params["offset"])
        offsets.append(offset)
        name = "dacon_off0.json" if offset == 0 else "dacon_off1.json"
        return httpx.Response(200, content=fixture_bytes(name), headers={"content-type": "application/json"})

    collected = dacon.DaconSource().collect(make_http(handler, clock=clock), BASE, page_cap=20)
    # 둘째 쪽에는 접수 중인 대회가 없어 거기서 멈춘다
    assert offsets == [0, 1]
    assert collected.collected == 30
