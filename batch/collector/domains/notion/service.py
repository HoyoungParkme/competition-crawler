"""노션 행 읽기 · 컬럼 확인 · 행 만들기(CCR-UC-001 UC-S4 1 · UC-S6 1 · 2 · 3).

값은 모두 묶음의 대표에서 온다(CCR-API-001 4.2). 노션에 쓰지 않는 실행은 컬럼을 확인만 하고
만들지 않으며, 행 만들기는 부르지 않는다(CCR-UC-001 UC-A1 1b).
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from collector.domains.collect.models import Competition
from collector.domains.notion.crud import NotionCrud
from collector.domains.notion.models import (
    COLLECTED,
    CREATABLE,
    DEADLINE,
    EXPECTED_TYPES,
    LINK,
    SOURCE,
    START,
    STATUS,
    STATUS_NEW,
    TITLE,
    CreateOutcome,
    NotionReadFailed,
    NotionRow,
    SchemaCheck,
)
from collector.infra.notion import NotionFailure
from collector.shared.dates import parse_to_kst_date

log = logging.getLogger(__name__)

TEXT_LIMIT = 2000


def _date_of(prop: Any) -> date | None:
    if not isinstance(prop, dict):
        return None
    value = prop.get("date")
    return parse_to_kst_date(value.get("start")) if isinstance(value, dict) else None


def row_of(page: dict[str, Any]) -> NotionRow:
    """행 하나를 이름으로 읽는다. 컬럼이 없으면 빈 값으로 본다(CCR-API-001 행 읽기)."""
    props = page.get("properties") or {}
    title_prop = props.get(TITLE) or {}
    parts = title_prop.get("title") if isinstance(title_prop, dict) else None
    title = "".join(str(p.get("plain_text") or "") for p in parts or [] if isinstance(p, dict)).strip()
    link_prop = props.get(LINK) or {}
    link = link_prop.get("url") if isinstance(link_prop, dict) else None
    return NotionRow(
        page_id=str(page.get("id") or ""),
        title=title,
        link=str(link).strip() if link else None,
        start_date=_date_of(props.get(START)),
        deadline=_date_of(props.get(DEADLINE)),
    )


def _date_value(value: date | None) -> dict[str, Any]:
    return {"date": {"start": value.isoformat()} if value else None}


def properties_of(competition: Competition, base_date: date) -> dict[str, Any]:
    """노션 행의 값(CCR-API-001 4.2). `결과날`은 보내지 않는다."""
    return {
        TITLE: {"title": [{"text": {"content": competition.title[:TEXT_LIMIT]}}]},
        LINK: {"url": competition.link},
        START: _date_value(competition.start_date),
        DEADLINE: _date_value(competition.deadline),
        STATUS: {"status": {"name": STATUS_NEW}},
        SOURCE: {"select": {"name": str(competition.source)}},
        COLLECTED: _date_value(base_date),
    }


def check_schema(properties: dict[str, Any]) -> tuple[list[str], str | None]:
    """(만들 컬럼, 문제). 문제가 있으면 행을 만들지 않는다(CCR-API-001 1.4)."""
    missing: list[str] = []
    for name, expected in EXPECTED_TYPES.items():
        prop = properties.get(name)
        if not isinstance(prop, dict):
            if name in CREATABLE:
                missing.append(name)
                continue
            return missing, f"컬럼 `{name}`이 없다"
        if prop.get("type") != expected:
            return missing, f"컬럼 `{name}`의 종류가 {prop.get('type')}다(기대 {expected})"
    options = ((properties.get(STATUS) or {}).get("status") or {}).get("options") or []
    if not any(isinstance(o, dict) and o.get("name") == STATUS_NEW for o in options):
        return missing, f"`{STATUS}`에 `{STATUS_NEW}` 선택지가 없다"
    return missing, None


class NotionService:
    def __init__(self, crud: NotionCrud, *, write: bool) -> None:
        self._crud = crud
        self._write = write

    def read_rows(self) -> list[NotionRow]:
        try:
            pages = self._crud.query_pages()
        except NotionFailure as exc:
            raise NotionReadFailed(exc.detail) from exc
        rows = [row_of(page) for page in pages]
        log.info("노션 행 %d개를 읽었다", len(rows))
        return rows

    def check_columns(self) -> SchemaCheck:
        """첫 행을 만들기 전에 한 번. 스키마를 끝내 읽지 못해도 컬럼을 만들지 못한 때와 같다."""
        try:
            data = self._crud.get_data_source()
        except NotionFailure as exc:
            return SchemaCheck(ok=False, problem=f"스키마를 읽지 못했다: {exc.detail}")
        properties = data.get("properties")
        if not isinstance(properties, dict):
            return SchemaCheck(ok=False, problem="스키마에 properties가 없다")
        missing, problem = check_schema(properties)
        if problem:
            return SchemaCheck(ok=False, problem=problem)
        if not missing:
            return SchemaCheck(ok=True)
        if not self._write:
            log.info("노션에 쓰지 않는 실행이라 컬럼 %s를 만들지 않는다", ", ".join(missing))
            return SchemaCheck(ok=True)
        shapes = {SOURCE: {"select": {}}, COLLECTED: {"date": {}}}
        try:
            self._crud.add_properties({name: shapes[name] for name in missing})
        except NotionFailure as exc:
            return SchemaCheck(ok=False, problem=f"컬럼 {', '.join(missing)}을 만들지 못했다: {exc.detail}")
        log.info("컬럼 %s를 만들었다", ", ".join(missing))
        return SchemaCheck(ok=True, created=missing)

    def create_row(self, competition: Competition, base_date: date) -> CreateOutcome:
        try:
            response = self._crud.create_page(properties_of(competition, base_date))
        except NotionFailure as exc:
            return CreateOutcome(created=False, error=exc.detail)
        if response.committed_id:
            return CreateOutcome(created=True, page_id=response.committed_id, via_committed=True)
        return CreateOutcome(created=True, page_id=str(response.data.get("id") or "") or None)
