from __future__ import annotations

from datetime import date

import httpx

from collector.domains.collect.adapters import contestkorea
from tests.conftest import FakeClock, fixture_bytes, make_http, response_of

BASE = date(2026, 9, 27)


def test_parses_saved_list() -> None:
    items = contestkorea.parse_list(response_of("ck_idea_0927.html"))
    assert len(items) == 12
    first = items[0]
    assert first.str_no == "202608190005"
    assert first.title == "2026 인천관광 혁신아이디어 공모전"
    assert (first.period, first.days) == ((8, 18, 9, 27), 0)


def test_dates_use_the_printed_period() -> None:
    assert contestkorea.resolve_dates(BASE, (8, 18, 9, 27), 0) == (
        date(2026, 8, 18),
        date(2026, 9, 27),
    )
    # 날수가 하루 어긋나도 찍힌 마감일을 쓴다
    assert contestkorea.resolve_dates(BASE, (9, 1, 10, 5), 9) == (
        date(2026, 9, 1),
        date(2026, 10, 5),
    )
    # 해를 넘기는 접수 기간
    assert contestkorea.resolve_dates(date(2026, 12, 20), (12, 1, 1, 15), 26) == (
        date(2026, 12, 1),
        date(2027, 1, 15),
    )
    # 날수를 읽지 못하면 연도를 정할 수 없다
    assert contestkorea.resolve_dates(BASE, (8, 18, 9, 27), None) == (None, None)


def test_collect_walks_both_categories(clock: FakeClock) -> None:
    requested = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append((request.url.params["Txt_bcode"], request.url.params["page"]))
        if request.url.params["page"] == "1":
            return httpx.Response(200, content=fixture_bytes("ck_idea_0927.html"))
        return httpx.Response(200, text="<div class='list_style_2'><ul></ul></div>")

    collected = contestkorea.ContestKoreaSource().collect(
        make_http(handler, clock=clock), BASE, page_cap=20
    )
    assert requested == [
        ("030310001", "1"),
        ("030310001", "2"),
        ("031410001", "1"),
        ("031410001", "2"),
    ]
    # 두 분야가 같은 쪽을 돌려주므로 str_no로 합쳐 12건이다
    assert collected.collected == 12
    first = next(c for c in collected.competitions if c.source_id == "202608190005")
    assert first.link == "https://www.contestkorea.com/sub/view.php?int_gbn=1&str_no=202608190005"
    assert first.deadline == date(2026, 9, 27)
