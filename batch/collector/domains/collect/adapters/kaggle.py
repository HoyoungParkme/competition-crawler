"""Kaggle 대회 목록(CCR-API-001 POST/api.kaggle.com/v1/…/ListCompetitions).

실측 전이다. 필드 이름은 공식 클라이언트(kagglesdk) 코드를 따른다(CCR-API-001 5장).
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
PAGE_SIZE = 100
PRACTICE = {"gettingstarted", "playground"}


def parse_page(response: httpx.Response) -> tuple[list[dict[str, Any]], str]:
    try:
        data = response.json()
    except ValueError as exc:
        raise FormatError("JSON이 아니다") from exc
    if not isinstance(data, dict):
        raise FormatError("최상위가 객체가 아니다")
    competitions = data.get("competitions", [])
    if not isinstance(competitions, list):
        raise FormatError("competitions가 배열이 아니다")
    return competitions, str(data.get("nextPageToken") or "")


def is_practice(category: Any) -> bool:
    # 상위 문서의 두 표기(Getting Started · gettingStarted)를 모두 맞게 견준다
    return isinstance(category, str) and re.sub(r"\s+", "", category).lower() in PRACTICE


def normalize(item: dict[str, Any]) -> Competition | None:
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
    deadline = parse_to_kst_date(item.get("newEntrantDeadline")) or parse_to_kst_date(item.get("deadline"))
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
        return not self._token

    def collect(self, http: SourceHttp, base_date: date, page_cap: int) -> Collected:
        competitions: list[Competition] = []
        collected = dropped = 0
        page_token = ""
        for _ in range(page_cap):
            body = {
                "group": "COMPETITION_LIST_TAB_GENERAL",
                "category": "HOST_SEGMENT_UNSPECIFIED",
                "sortBy": "COMPETITION_SORT_BY_LATEST_DEADLINE",
                "search": "",
                "pageSize": PAGE_SIZE,
                "pageToken": page_token,
            }
            items, page_token = http.fetch(
                "POST",
                URL,
                json=body,
                headers={"Authorization": f"Bearer {self._token}"},
                parse=parse_page,
            )
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
            if not page_token or not items or not page_open:
                return Collected(competitions, collected, dropped)
        return Collected(competitions, collected, dropped, page_cap_hit=True)
