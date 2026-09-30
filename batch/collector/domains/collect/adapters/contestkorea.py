"""콘테스트코리아 공모전 목록(CCR-API-001 GET/www.contestkorea.com/sub/list.php).

접수마감일은 목록에 찍힌 "접수 MM.DD~MM.DD"의 뒤 날짜다. 연도는 기준일 + N에 가장 가까운
날이 되는 해로 정한다. 날수만으로 세지 않는 것은 날수가 하루 어긋날 수 있어서다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta

import httpx
from selectolax.parser import HTMLParser

from collector.domains.collect.models import Collected, Competition, SourceName
from collector.infra.http import FormatError, SourceHttp
from collector.shared.text import html_text

URL = "https://www.contestkorea.com/sub/list.php"
CODES = ("030310001", "031410001")  # 학문·과학·IT · 아이디어·건축·창업
PAGE_SIZE = 12
_STR_NO = re.compile(r"str_no=(\d+)")
_PERIOD = re.compile(r"(\d{1,2})\.(\d{1,2})\s*~\s*(\d{1,2})\.(\d{1,2})")
_DAY = re.compile(r"D\s*-\s*(\d+)")


@dataclass
class CkItem:
    str_no: str | None
    href: str | None
    title: str
    categories: list[str] = field(default_factory=list)
    host: str = ""
    target: str = ""
    period: tuple[int, int, int, int] | None = None
    days: int | None = None


def parse_list(response: httpx.Response) -> list[CkItem]:
    """CCR-MS-001#contestkorea.parse_list"""
    tree = HTMLParser(response.text)
    box = tree.css_first("div.list_style_2")
    if box is None:
        raise FormatError("div.list_style_2가 없다")
    items: list[CkItem] = []
    for li in box.css("div.list_style_2 > ul > li"):
        anchor = li.css_first("div.title > a")
        if anchor is None:
            continue
        href = anchor.attributes.get("href")
        match = _STR_NO.search(href or "")
        title_node = li.css_first("span.txt")
        host = target = ""
        for row in li.css("ul.host > li"):
            label = row.css_first("strong")
            text = row.text(strip=True)
            value = text.split(".", 1)[1].strip() if "." in text else text
            if label is not None and "주최" in label.text():
                host = value
            elif label is not None and "대상" in label.text():
                target = value
        step1 = li.css_first("span.step-1")
        period = _PERIOD.search(step1.text()) if step1 is not None else None
        day_node = li.css_first("span.day")
        day = _DAY.search(day_node.text()) if day_node is not None else None
        items.append(
            CkItem(
                str_no=match.group(1) if match else None,
                href=href,
                title=html_text(title_node.text()) if title_node is not None else "",
                categories=[
                    n.text(strip=True) for n in li.css("span.category") if n.text(strip=True)
                ],
                host=host,
                target=target,
                period=tuple(int(x) for x in period.groups()) if period else None,  # type: ignore[arg-type]
                days=int(day.group(1)) if day else None,
            )
        )
    return items


def resolve_dates(
    base_date: date, period: tuple[int, int, int, int] | None, days: int | None
) -> tuple[date | None, date | None]:
    """CCR-MS-001#contestkorea.resolve_dates

    (접수시작일, 접수마감일). 날수를 읽지 못하면 연도를 정할 수 없어 둘 다 비운다.
    """
    if days is None:
        return None, None
    estimate = base_date + timedelta(days=days)
    if period is None:
        return None, estimate
    sm, sd, em, ed = period
    candidates = []
    for year in (estimate.year - 1, estimate.year, estimate.year + 1):
        try:
            candidates.append(date(year, em, ed))
        except ValueError:
            continue
    if not candidates:
        return None, estimate
    deadline = min(candidates, key=lambda d: abs((d - estimate).days))
    try:
        start = date(deadline.year, sm, sd)
    except ValueError:
        return None, deadline
    if start > deadline:
        try:
            start = date(deadline.year - 1, sm, sd)
        except ValueError:
            return None, deadline
    return start, deadline


class ContestKoreaSource:
    name = SourceName.CONTESTKOREA
    origin = "https://www.contestkorea.com"
    robots_paths = ("/sub/list.php",)

    def missing_config(self) -> bool:
        """CCR-MS-001#ContestKoreaSource.missing_config"""
        return False

    def collect(self, http: SourceHttp, base_date: date, page_cap: int) -> Collected:
        """CCR-MS-001#ContestKoreaSource.collect"""
        merged: dict[str, CkItem] = {}
        order: list[str] = []
        pages = 0
        cap_hit = False
        for code in CODES:
            page = 1
            while True:
                if pages >= page_cap:
                    cap_hit = True
                    break
                items = http.fetch(
                    "GET",
                    URL,
                    params={
                        "displayrow": str(PAGE_SIZE),
                        "int_gbn": "1",
                        "Txt_bcode": code,
                        "Txt_sortkey": "a.str_aedate",
                        "Txt_sortword": "asc",
                        "page": str(page),
                    },
                    parse=parse_list,
                )
                pages += 1
                for item in items:
                    key = item.str_no or (item.href or "")
                    if key in merged:
                        known = merged[key]
                        known.categories.extend(
                            c for c in item.categories if c not in known.categories
                        )
                        continue
                    merged[key] = item
                    order.append(key)
                if len(items) < PAGE_SIZE:
                    break
                page += 1
            if cap_hit:
                break

        competitions: list[Competition] = []
        collected = dropped = 0
        for key in order:
            item = merged[key]
            collected += 1
            if not item.title or (item.str_no is None and not item.href):
                dropped += 1
                continue
            if item.str_no is not None:
                source_id = item.str_no
                link = f"https://www.contestkorea.com/sub/view.php?int_gbn=1&str_no={item.str_no}"
            else:
                link = str(httpx.URL(URL).join(item.href or ""))
                source_id = link
            start, deadline = resolve_dates(base_date, item.period, item.days)
            extras = tuple(item.categories + [v for v in (item.host, item.target) if v])
            competitions.append(
                Competition(
                    source=SourceName.CONTESTKOREA,
                    source_id=source_id,
                    title=item.title,
                    link=link,
                    start_date=start,
                    deadline=deadline,
                    extras=extras,
                )
            )
        return Collected(competitions, collected, dropped, page_cap_hit=cap_hit)
