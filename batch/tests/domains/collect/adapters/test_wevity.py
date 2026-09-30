from __future__ import annotations

from datetime import date, timedelta

import httpx

from collector.domains.collect.adapters import wevity
from tests.conftest import FakeClock, fixture_bytes, make_http, response_of

BASE = date(2026, 9, 27)


def test_parses_list_without_badges() -> None:
    items = wevity.parse_list(response_of("wev_c1_0927.html"))
    assert len(items) == 15
    first = items[0]
    assert first.ix == "111148"
    assert first.title == "스파크업 : 모두의 에너지 (에너지 창업 경연대회)"
    assert (first.sign, first.days, first.status) == ("-", 5, "마감임박")


def test_detail_page_gives_the_end_date() -> None:
    assert wevity.parse_detail_end(response_of("wev_view_110675.html")) == date(2026, 10, 7)


def test_deadline_with_offset() -> None:
    item = wevity.WevityItem(ix="1", href=None, title="t", sign="-", days=10)
    assert wevity.deadline_of(item, BASE, 0) == date(2026, 10, 7)
    assert wevity.deadline_of(item, BASE, -1) == date(2026, 10, 6)
    closed = wevity.WevityItem(ix="2", href=None, title="t", sign="+", days=3)
    assert wevity.deadline_of(closed, BASE, 0) == date(2026, 9, 24)


def handler_for(detail_status: int = 200, shift: int = 0):
    """목록은 저장한 쪽을, 상세는 목록의 날수에 `shift`를 더한 마감일을 돌려준다."""
    days = {i.ix: i.days for i in wevity.parse_list(response_of("wev_c1_0927.html"))}
    pages = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.params.get("gbn") == "view":
            # 실제 사이트처럼 viewok로 보낸다
            ix = request.url.params["ix"]
            return httpx.Response(
                302, headers={"Location": f"/?c=find&s=1&gbn=viewok&gp=1&ix={ix}"}
            )
        if request.url.params.get("gbn") == "viewok":
            if detail_status != 200:
                return httpx.Response(detail_status)
            end = BASE + timedelta(days=days[request.url.params["ix"]] + shift)
            return httpx.Response(
                200, text=f"<table><tr><th>접수기간</th><td>2026-09-01 ~ {end}</td></tr></table>"
            )
        pages.append((request.url.params["cidx"], request.url.params["gp"]))
        if request.url.params["gp"] == "1":
            return httpx.Response(200, content=fixture_bytes("wev_c1_0927.html"))
        return httpx.Response(200, text="<ul class='list'></ul>")

    return handler, pages


def test_collect_merges_categories_and_calibrates_offset(clock: FakeClock) -> None:
    handler, pages = handler_for()
    collected = wevity.WevitySource().collect(make_http(handler, clock=clock), BASE, page_cap=20)
    # 다섯 분야가 같은 쪽을 돌려주므로 ix로 합쳐 15건이다
    assert [cidx for cidx, _ in pages if _ == "1"] == ["20", "21", "22", "3", "1"]
    assert collected.collected == 15
    by_id = {c.source_id: c for c in collected.competitions}
    # 110675의 상세 마감일(10/7)과 목록 D-10이 맞아 보정값은 0이다
    assert by_id["110675"].deadline == date(2026, 10, 7)
    assert by_id["110675"].link == "https://www.wevity.com/?c=find&s=1&gbn=view&ix=110675"
    assert "보정값 0" in collected.notes[0]


def test_morning_listing_one_day_ahead_is_corrected(clock: FakeClock) -> None:
    # 아침의 목록은 날수가 하루 많다. 상세의 마감일이 하루 이르면 보정값 −1을 모든 항목에 쓴다
    handler, _ = handler_for(shift=-1)
    collected = wevity.WevitySource().collect(make_http(handler, clock=clock), BASE, page_cap=20)
    by_id = {c.source_id: c for c in collected.competitions}
    assert by_id["110675"].deadline == date(2026, 10, 6)
    assert "보정값 -1" in collected.notes[0]


def test_calibration_failure_falls_back_to_minus_one(clock: FakeClock) -> None:
    handler, _ = handler_for(detail_status=404)
    collected = wevity.WevitySource().collect(make_http(handler, clock=clock), BASE, page_cap=20)
    by_id = {c.source_id: c for c in collected.competitions}
    assert by_id["110675"].deadline == date(2026, 10, 6)
    assert "−1" in collected.notes[0]


def test_page_cap_is_shared_across_categories(clock: FakeClock) -> None:
    handler, pages = handler_for()
    collected = wevity.WevitySource().collect(make_http(handler, clock=clock), BASE, page_cap=3)
    assert collected.page_cap_hit
    assert len(pages) == 3


def list_page(*rows: tuple[str, str, str]) -> str:
    """(ix, 날수, 상태)마다 목록 한 줄. 실제 쪽처럼 머리 줄을 둔다."""
    lis = "".join(
        f'<li><div class="tit"><a href="?c=find&s=1&gub=1&cidx=20&gbn=view&gp=1&ix={ix}">공모전 {ix}</a></div>'
        f'<div class="organ">주최</div><div class="day">{day}<span class="dday">{state}</span></div></li>'
        for ix, day, state in rows
    )
    return f'<ul class="list"><li class="top"><div class="tit">공모전명</div></li>{lis}</ul>'


def test_promoted_closed_notice_does_not_stop_the_category(clock: FakeClock) -> None:
    # 2026-09-28 아침처럼 첫 쪽 위쪽 홍보 칸에 전날 마감된 공고가 있다. 쪽의 끝이 마감인 2쪽까지 읽고,
    # 2쪽 앞머리의 접수 중 공고도 받는다. 모두 마감인 3쪽은 읽지 않는다(CCR-DOM-002 5장 결정 8)
    pages = {
        "1": list_page(
            ("1", "D-3", "접수중"),
            ("2", "D+0", "마감"),
            ("3", "D-5", "접수중"),
            ("4", "D-9", "마감임박"),
        ),
        "2": list_page(("5", "D-12", "접수중"), ("6", "D+1", "마감"), ("7", "D+2", "마감")),
        "3": list_page(("8", "D+3", "마감"), ("9", "D+4", "마감")),
    }
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.params.get("gbn") == "view":
            return httpx.Response(404)  # 날수 맞춰 보기는 이 테스트에서 보지 않는다
        cidx, gp = request.url.params["cidx"], request.url.params["gp"]
        seen.append((cidx, gp))
        return httpx.Response(200, text=pages[gp] if cidx == "20" else list_page())

    collected = wevity.WevitySource().collect(make_http(handler, clock=clock), BASE, page_cap=20)
    assert [gp for cidx, gp in seen if cidx == "20"] == ["1", "2"]
    assert [c.source_id for c in collected.competitions] == ["1", "2", "3", "4", "5", "6", "7"]
