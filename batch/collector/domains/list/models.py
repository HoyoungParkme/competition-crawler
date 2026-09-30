"""목록 경계의 값. 도메인 개념 ListEntry(CCR-DOM-001).

목록 파일 한 줄의 형식은 ERD(CCR-DOM-003 competitions)가 정한다. 페이지와 마무리 단계는
이 모듈을 불러오지 않고 같은 형식을 따로 안다(CCR-DOM-001 4.2).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from collector.domains.collect.models import Competition
from collector.shared.text import clean_text

LIST_REQUIRED = ("source", "source_id", "title", "link", "collected_on")
REASON_MAX = 300


def _iso(value: date | None) -> str | None:
    return value.isoformat() if value else None


def _date(value: Any, name: str) -> date | None:
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError(f"{name}이 날짜가 아니다: {value!r}") from exc


@dataclass(frozen=True)
class ListEntry:
    """목록 파일 한 줄(`data/competitions.jsonl`). 배치는 더하기만 한다."""

    source: str
    source_id: str
    title: str
    link: str
    start_date: date | None
    deadline: date | None
    collected_on: date
    reason: str = ""

    @property
    def id(self) -> str:
        """CCR-MS-001#ListEntry.id"""
        return f"{self.source}:{self.source_id}"

    def to_dict(self) -> dict[str, Any]:
        """CCR-MS-001#ListEntry.to_dict"""
        return {
            "id": self.id,
            "source": self.source,
            "source_id": self.source_id,
            "title": self.title,
            "link": self.link,
            "start_date": _iso(self.start_date),
            "deadline": _iso(self.deadline),
            "collected_on": self.collected_on.isoformat(),
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ListEntry:
        """CCR-MS-001#ListEntry.from_dict"""
        missing = [k for k in LIST_REQUIRED if data.get(k) in (None, "")]
        if missing:
            raise ValueError(f"필수 필드가 없다: {missing}")
        collected_on = _date(data["collected_on"], "collected_on")
        assert collected_on is not None
        return cls(
            source=str(data["source"]),
            source_id=str(data["source_id"]),
            title=str(data["title"]),
            link=str(data["link"]),
            start_date=_date(data.get("start_date"), "start_date"),
            deadline=_date(data.get("deadline"), "deadline"),
            collected_on=collected_on,
            reason=str(data.get("reason") or ""),
        )


def entry_of(competition: Competition, base_date: date, reason: str) -> ListEntry:
    """CCR-MS-001#list.entry_of"""
    return ListEntry(
        source=str(competition.source),
        source_id=competition.source_id,
        title=competition.title,
        link=competition.link,
        start_date=competition.start_date,
        deadline=competition.deadline,
        collected_on=base_date,
        reason=clean_text(reason)[:REASON_MAX],
    )
