"""노션 경계의 값. 도메인 개념 NotionRow(CCR-DOM-001)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

# 컬럼은 이름으로 지정한다(CCR-API-001 1.4)
TITLE = "기타"
LINK = "링크"
START = "시작일"
DEADLINE = "마감일"
STATUS = "상태"
SOURCE = "출처"
COLLECTED = "수집일"
STATUS_NEW = "시작 전"

EXPECTED_TYPES = {
    TITLE: "title",
    LINK: "url",
    START: "date",
    DEADLINE: "date",
    STATUS: "status",
    SOURCE: "select",
    COLLECTED: "date",
}
CREATABLE = (SOURCE, COLLECTED)


class NotionReadFailed(Exception):
    """노션을 읽지 못했다. 판별도 적재도 하지 않는다(CCR-UC-001 UC-A1 5a)."""


@dataclass(frozen=True)
class NotionRow:
    page_id: str
    title: str
    link: str | None
    start_date: date | None
    deadline: date | None


@dataclass
class SchemaCheck:
    ok: bool
    created: list[str] = field(default_factory=list)
    problem: str | None = None


@dataclass
class CreateOutcome:
    created: bool
    page_id: str | None = None
    via_committed: bool = False  # 503이 새 행의 id를 알려 줬다(CCR-UC-001 UC-S6 2d)
    error: str | None = None
