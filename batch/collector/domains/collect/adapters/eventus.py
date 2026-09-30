"""event-us 공고 검색(CCR-API-001 POST/api.event-us.kr/api/v1/engine/search)."""

from __future__ import annotations

from datetime import date
from typing import Any

import httpx

from collector.domains.collect.models import Collected, Competition, SourceName
from collector.infra.http import FormatError, SourceHttp
from collector.shared.dates import kst_midnight_utc, parse_to_kst_date
from collector.shared.text import clean_text

URL = "https://api.event-us.kr/api/v1/engine/search"
PAGE_SIZE = 100
_EPOCH = "1900-01-01T00:00:00+00:00"


def build_query(base_date: date, page: int) -> dict[str, Any]:
    """CCR-MS-001#eventus.build_query"""
    day0 = kst_midnight_utc(base_date).isoformat()
    return {
        "query": "",
        "page": {"current": page, "size": PAGE_SIZE},
        "filters": {
            # 뒤의 셋은 사이트의 검색 화면이 늘 거는 조건과 같다
            "all": [
                {"event_type": ["대회/공모전"]},
                {"state": "Start"},
                {"disclosure_status": "open"},
                {"is_ignore": "false"},
            ],
            # 접수마감일이 기준일 이후이거나, 없으면서 행사가 끝나지 않은 것
            "any": [
                {"register_due_date": {"from": day0}},
                {
                    "all": [
                        {"none": {"register_due_date": {"from": _EPOCH}}},
                        {
                            "any": [
                                {"close_date": {"from": day0}},
                                {"none": {"close_date": {"from": _EPOCH}}},
                            ]
                        },
                    ]
                },
            ],
        },
        "sort": [{"register_due_date": "asc"}],
    }


def _raw(item: dict[str, Any], key: str) -> Any:
    value = item.get(key)
    return value.get("raw") if isinstance(value, dict) else None


def parse_page(response: httpx.Response) -> tuple[list[dict[str, Any]], int]:
    """CCR-MS-001#eventus.parse_page"""
    try:
        data = response.json()
    except ValueError as exc:
        raise FormatError("JSON이 아니다") from exc
    if not isinstance(data, dict):
        raise FormatError("최상위가 객체가 아니다")
    page = (data.get("meta") or {}).get("page") or {}
    results = data.get("results")
    if not isinstance(results, list) or not isinstance(page.get("total_pages"), int):
        raise FormatError("results나 meta.page.total_pages가 없다")
    return results, page["total_pages"]


def normalize(item: dict[str, Any]) -> Competition | None:
    """CCR-MS-001#eventus.normalize"""
    source_id = str(_raw(item, "id") or "").strip()
    title = clean_text(_raw(item, "title"))
    subdomain = str(_raw(item, "subdomain") or "").strip()
    if not source_id or not title or not subdomain:
        return None
    extras: list[str] = []
    for key in ("category", "category2"):
        value = _raw(item, key)
        if isinstance(value, str) and value.strip():
            extras.append(value.strip())
    tags = _raw(item, "tags")
    if isinstance(tags, list):
        extras.extend(str(t).strip() for t in tags if str(t).strip())
    return Competition(
        source=SourceName.EVENTUS,
        source_id=source_id,
        title=title,
        link=f"https://event-us.kr/{subdomain}/event/{source_id}",
        start_date=parse_to_kst_date(_raw(item, "register_start_date")),
        deadline=parse_to_kst_date(_raw(item, "register_due_date")),
        extras=tuple(extras),
    )


class EventUsSource:
    name = SourceName.EVENTUS
    origin = "https://api.event-us.kr"
    robots_paths = ("/api/v1/engine/search",)

    def missing_config(self) -> bool:
        """CCR-MS-001#EventUsSource.missing_config"""
        return False

    def collect(self, http: SourceHttp, base_date: date, page_cap: int) -> Collected:
        """CCR-MS-001#EventUsSource.collect"""
        competitions: list[Competition] = []
        collected = dropped = 0
        page = 1
        total_pages = 1
        while page <= total_pages:
            if page > page_cap:
                return Collected(competitions, collected, dropped, page_cap_hit=True)
            results, total_pages = http.fetch(
                "POST", URL, json=build_query(base_date, page), parse=parse_page
            )
            for item in results:
                collected += 1
                competition = normalize(item) if isinstance(item, dict) else None
                if competition is None:
                    dropped += 1
                else:
                    competitions.append(competition)
            page += 1
        return Collected(competitions, collected, dropped)
