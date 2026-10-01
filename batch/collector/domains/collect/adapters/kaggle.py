"""Kaggle 대회 목록(CCR-API-001 POST/api.kaggle.com/v1/…/ListCompetitions).

2026-10-01에 실측했다. 한 쪽은 20건으로 정해져 있고, 쪽은 `page`로만 넘어간다.
토큰이 설정에 없으면 요청하지 않고 설정 누락으로 끝난다(CCR-UC-001 UC-S1 1a).
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any

import httpx

from collector.domains.collect.models import Collected, Competition, SourceName
from collector.infra.http import FormatError, SourceHttp
from collector.shared.dates import parse_to_kst_date
from collector.shared.text import clean_text

URL = "https://api.kaggle.com/v1/competitions.CompetitionApiService/ListCompetitions"
PRACTICE = {"gettingstarted", "playground"}


def parse_page(response: httpx.Response) -> list[dict[str, Any]]:
    """CCR-MS-001#kaggle.parse_page"""
    try:
        data = response.json()
    except ValueError as exc:
        raise FormatError("JSON이 아니다") from exc
    if not isinstance(data, dict):
        raise FormatError("최상위가 객체가 아니다")
    # 마지막 쪽 다음은 빈 객체 {}로 온다
    competitions = data.get("competitions", [])
    if not isinstance(competitions, list):
        raise FormatError("competitions가 배열이 아니다")
    return competitions


def is_practice(category: Any) -> bool:
    # 실제 값은 Getting Started · Playground다. RFQ의 gettingStarted 표기도 맞게 견준다
    """CCR-MS-001#kaggle.is_practice"""
    return isinstance(category, str) and re.sub(r"\s+", "", category).lower() in PRACTICE


def normalize(item: dict[str, Any]) -> Competition | None:
    """CCR-MS-001#kaggle.normalize"""
    ref = str(item.get("ref") or "").strip().rstrip("/")
    slug = ref.split("/")[-1] if ref else ""
    title = clean_text(item.get("title"))
    if not slug or not title:
        return None
    category = item.get("category")
    extras: list[str] = []
    if isinstance(category, str) and category.strip():
        extras.append(category.strip())
    for tag in item.get("tags") or []:
        if isinstance(tag, dict) and str(tag.get("name") or "").strip():
            extras.append(str(tag["name"]).strip())
    deadline = parse_to_kst_date(item.get("newEntrantDeadline")) or parse_to_kst_date(
        item.get("deadline")
    )
    return Competition(
        source=SourceName.KAGGLE,
        source_id=slug,
        title=title,
        link=f"https://www.kaggle.com/competitions/{slug}",
        start_date=parse_to_kst_date(item.get("enabledDate")),
        deadline=deadline,
        extras=tuple(extras),
        practice=is_practice(category),
    )


class KaggleSource:
    name = SourceName.KAGGLE
    origin = "https://api.kaggle.com"
    robots_paths = ("/v1/competitions.CompetitionApiService/ListCompetitions",)

    def __init__(self, token: str | None) -> None:
        self._token = token

    def missing_config(self) -> bool:
        """CCR-MS-001#KaggleSource.missing_config"""
        return not self._token

    def collect(self, http: SourceHttp, base_date: date, page_cap: int) -> Collected:
        """CCR-MS-001#KaggleSource.collect"""
        competitions: list[Competition] = []
        collected = dropped = 0
        for page in range(1, page_cap + 1):
            # pageSize는 무시되고 nextPageToken은 오지 않아 page로 넘긴다
            body = {
                "group": "COMPETITION_LIST_TAB_GENERAL",
                "category": "HOST_SEGMENT_UNSPECIFIED",
                "sortBy": "COMPETITION_SORT_BY_LATEST_DEADLINE",
                "search": "",
                "page": page,
            }
            items = http.fetch(
                "POST",
                URL,
                json=body,
                headers={"Authorization": f"Bearer {self._token}"},
                parse=parse_page,
            )
            if not items:
                return Collected(competitions, collected, dropped)
            page_open = False
            for item in items:
                collected += 1
                competition = normalize(item) if isinstance(item, dict) else None
                if competition is None:
                    dropped += 1
                    continue
                competitions.append(competition)
                ends = parse_to_kst_date(item.get("deadline")) or competition.deadline
                if ends is None or ends >= base_date:
                    page_open = True
            # 마감이 늦은 차례라, 한 쪽이 모두 마감됐으면 뒤쪽도 마감된 것이다
            if not page_open:
                return Collected(competitions, collected, dropped)
        return Collected(competitions, collected, dropped, page_cap_hit=True)
