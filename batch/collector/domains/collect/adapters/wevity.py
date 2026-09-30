"""wevity 공모전 목록과 날수 맞춰 보기.

CCR-API-001 GET/www.wevity.com/?c=find · GET/www.wevity.com/?c=find&gbn=view.
목록에는 마감까지의 날수만 있고, 이 날수는 아침에 하루 많게 나온다. 실행마다 상세 페이지 하나로
보정값(0 또는 −1)을 재고 모든 항목에 적용한다. 재지 못하면 −1로 둔다.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date, timedelta

import httpx
from selectolax.parser import HTMLParser, Node

from collector.domains.collect.models import Collected, Competition, SourceName
from collector.infra.http import FormatError, HttpFailure, SourceHttp
from collector.shared.text import html_text

log = logging.getLogger(__name__)

LIST_URL = "https://www.wevity.com/"
CATEGORIES = (
    20,
    21,
    22,
    3,
    1,
)  # 웹/모바일/IT · 게임/소프트웨어 · 과학/공학 · 논문/리포트 · 기획/아이디어
OPEN_STATES = {"접수중", "마감임박"}
CLOSED_STATE = "마감"
_DAY = re.compile(r"D\s*([-+])\s*(\d+)")
_IX = re.compile(r"[?&]ix=(\d+)")
_PERIOD = re.compile(r"(\d{4}-\d{2}-\d{2})\s*~\s*(\d{4}-\d{2}-\d{2})")


@dataclass
class WevityItem:
    ix: str | None
    href: str | None
    title: str
    fields: list[str] = field(default_factory=list)
    organ: str = ""
    sign: str | None = None  # "-"면 마감까지, "+"면 마감 뒤
    days: int | None = None
    status: str = ""


def _title_without_badges(anchor: Node) -> str:
    parts: list[str] = []
    for node in anchor.iter(include_text=True):
        if node.tag == "-text":
            parts.append(node.text())
        elif "stat" in (node.attributes.get("class") or "").split():
            continue  # SPECIAL · IDEA 같은 배지
        else:
            parts.append(node.text())
    return html_text("".join(parts))


def parse_list(response: httpx.Response) -> list[WevityItem]:
    """CCR-MS-001#wevity.parse_list"""
    tree = HTMLParser(response.text)
    ul = tree.css_first("ul.list")
    if ul is None:
        raise FormatError("ul.list가 없다")
    items: list[WevityItem] = []
    for li in ul.iter():
        if li.tag != "li" or "top" in (li.attributes.get("class") or "").split():
            continue
        tit = li.css_first("div.tit")
        if tit is None:
            continue
        anchor = tit.css_first("a")
        href = anchor.attributes.get("href") if anchor is not None else None
        match = _IX.search(href or "")
        sub = li.css_first("div.sub-tit")
        fields = []
        if sub is not None:
            text = sub.text(strip=True)
            text = text.split(":", 1)[1] if ":" in text else text
            fields = [f.strip() for f in text.split(",") if f.strip()]
        organ_node = li.css_first("div.organ")
        day_node = li.css_first("div.day")
        state_node = li.css_first("span.dday")
        day_match = _DAY.search(day_node.text(deep=False)) if day_node is not None else None
        items.append(
            WevityItem(
                ix=match.group(1) if match else None,
                href=href,
                title=_title_without_badges(anchor) if anchor is not None else "",
                fields=fields,
                organ=organ_node.text(strip=True) if organ_node is not None else "",
                sign=day_match.group(1) if day_match else None,
                days=int(day_match.group(2)) if day_match else None,
                status=state_node.text(strip=True) if state_node is not None else "",
            )
        )
    return items


def parse_detail_end(response: httpx.Response) -> date:
    """CCR-MS-001#wevity.parse_detail_end"""
    text = HTMLParser(response.text).text(separator=" ")
    at = text.find("접수기간")
    match = _PERIOD.search(text, at) if at >= 0 else None
    if match is None:
        raise FormatError("접수기간을 찾지 못했다")
    return date.fromisoformat(match.group(2))


def deadline_of(item: WevityItem, base_date: date, offset: int) -> date | None:
    """CCR-MS-001#wevity.deadline_of"""
    if item.days is None or item.sign is None:
        return None
    if item.sign == "-":
        return base_date + timedelta(days=item.days + offset)
    return base_date - timedelta(days=item.days - offset)


class WevitySource:
    name = SourceName.WEVITY
    origin = "https://www.wevity.com"
    robots_paths = ("/?c=find&s=1&gub=1", "/?c=find&s=1&gbn=view", "/?c=find&s=1&gbn=viewok")

    def missing_config(self) -> bool:
        """CCR-MS-001#WevitySource.missing_config"""
        return False

    def collect(self, http: SourceHttp, base_date: date, page_cap: int) -> Collected:
        """CCR-MS-001#WevitySource.collect"""
        merged: dict[str, WevityItem] = {}
        order: list[str] = []
        collected = dropped = 0
        pages = 0
        cap_hit = False
        for cidx in CATEGORIES:
            gp = 1
            while True:
                if pages >= page_cap:
                    cap_hit = True
                    break
                items = http.fetch(
                    "GET",
                    LIST_URL,
                    params={"c": "find", "s": "1", "gub": "1", "cidx": str(cidx), "gp": str(gp)},
                    parse=parse_list,
                )
                pages += 1
                for item in items:
                    key = item.ix or (item.href or "")
                    if key in merged:
                        known = merged[key]
                        known.fields.extend(f for f in item.fields if f not in known.fields)
                        continue
                    merged[key] = item
                    order.append(key)
                # 일반 목록은 접수 중 뒤에 마감이 이어지므로 쪽의 끝이 마감이면 뒤쪽도 마감이다.
                # 첫 쪽 위쪽 홍보 칸에 남은 마감 공고로는 멈추지 않는다(CCR-DOM-002 5장 결정 8)
                if not items or items[-1].status == CLOSED_STATE:
                    break
                gp += 1
            if cap_hit:
                break

        offset, note = self._calibrate(http, [merged[k] for k in order], base_date)
        competitions: list[Competition] = []
        for key in order:
            item = merged[key]
            collected += 1
            if not item.title or (item.ix is None and not item.href):
                dropped += 1
                continue
            if item.ix is not None:
                source_id = item.ix
                link = f"https://www.wevity.com/?c=find&s=1&gbn=view&ix={item.ix}"
            else:
                # 원천 ID를 읽지 못하면 목록의 링크를 절대 주소로 바꿔 쓴다(CCR-API-001 1.2)
                link = str(httpx.URL(LIST_URL).join(item.href or ""))
                source_id = link
            extras = tuple(item.fields + ([item.organ] if item.organ else []))
            competitions.append(
                Competition(
                    source=SourceName.WEVITY,
                    source_id=source_id,
                    title=item.title,
                    link=link,
                    start_date=None,
                    deadline=deadline_of(item, base_date, offset),
                    extras=extras,
                )
            )
        return Collected(competitions, collected, dropped, page_cap_hit=cap_hit, notes=[note])

    def _calibrate(
        self, http: SourceHttp, items: list[WevityItem], base_date: date
    ) -> tuple[int, str]:
        """CCR-MS-001#WevitySource._calibrate"""
        pick = next(
            (
                i
                for i in items
                if i.status in OPEN_STATES and i.sign == "-" and i.days is not None and i.ix
            ),
            None,
        )
        if pick is None:
            return -1, "날수 맞춰 보기: 고를 공고가 없어 보정값 −1"
        try:
            # 상세는 같은 사이트의 gbn=viewok로 302를 보낸다(2026-09-27 실측). 목록과 달리 따라간다
            end = http.fetch(
                "GET",
                LIST_URL,
                params={"c": "find", "s": "1", "gbn": "view", "ix": pick.ix},
                parse=parse_detail_end,
                follow_redirects=True,
            )
        except (HttpFailure, FormatError) as exc:
            return -1, f"날수 맞춰 보기 실패({exc}): 보정값 −1"
        offset = (end - base_date).days - (pick.days or 0)
        if offset not in (0, -1):
            return -1, f"날수 맞춰 보기: 차이 {offset}가 0 · −1이 아니라 보정값 −1"
        return (
            offset,
            f"날수 맞춰 보기: ix={pick.ix} 마감 {end} · 목록 D-{pick.days} → 보정값 {offset}",
        )
