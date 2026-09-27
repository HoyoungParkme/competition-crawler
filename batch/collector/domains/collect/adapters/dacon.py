"""DACON 대회 목록(CCR-API-001 GET/app.dacon.io/api/v1/competition/list)."""

from __future__ import annotations

from datetime import date
from typing import Any

import httpx

from collector.domains.collect.models import Collected, Competition, SourceName
from collector.infra.http import FormatError, SourceHttp
from collector.shared.dates import parse_to_kst_date
from collector.shared.text import clean_text

URL = "https://app.dacon.io/api/v1/competition/list"


def parse_page(response: httpx.Response) -> list[dict[str, Any]]:
    try:
        data = response.json()
    except ValueError as exc:
        raise FormatError("JSON이 아니다") from exc
    if not isinstance(data, dict) or not isinstance(data.get("data"), list):
        raise FormatError("data 배열이 없다")
    return data["data"]


def link_for(cpt_id: str, is_landing: Any) -> str:
    if str(is_landing) == "1":
        return f"https://dacon.io/competition/{cpt_id}/overview"
    return f"https://dacon.io/competitions/official/{cpt_id}/overview/description"


def normalize(item: dict[str, Any]) -> Competition | None:
    cpt_id = str(item.get("cpt_id") or "").strip()
    title = clean_text(item.get("name"))
    if not cpt_id or not title:
        return None
    keyword = item.get("keyword") or ""
    extras = tuple(word.strip() for word in str(keyword).split("|") if word.strip())
    return Competition(
        source=SourceName.DACON,
        source_id=cpt_id,
        title=title,
        link=link_for(cpt_id, item.get("is_landing_cpt")),
        # 시간대 표기가 없어 KST로 본다. 목록이 주는 날짜는 대회 기간뿐이라 접수 기간으로 쓴다
        start_date=parse_to_kst_date(item.get("period_start")),
        deadline=parse_to_kst_date(item.get("period_end")),
        extras=extras,
    )


class DaconSource:
    name = SourceName.DACON
    origin = "https://app.dacon.io"
    robots_paths = ("/api/v1/competition/list",)

    def missing_config(self) -> bool:
        return False

    def collect(self, http: SourceHttp, base_date: date, page_cap: int) -> Collected:
        competitions: list[Competition] = []
        collected = dropped = 0
        for offset in range(page_cap):
            items = http.fetch("GET", URL, params={"offset": offset, "range": ""}, parse=parse_page)
            if not items:
                return Collected(competitions, collected, dropped)
            any_open = False
            for item in items:
                collected += 1
                competition = normalize(item) if isinstance(item, dict) else None
                if competition is None:
                    dropped += 1
                    continue
                competitions.append(competition)
                if competition.deadline is not None and competition.deadline >= base_date:
                    any_open = True
            # 종료일이 늦은 차례라, 접수 중인 대회가 없는 쪽을 읽으면 멈춘다
            if not any_open:
                return Collected(competitions, collected, dropped)
        return Collected(competitions, collected, dropped, page_cap_hit=True)
