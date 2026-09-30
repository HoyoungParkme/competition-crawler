"""목록 파일을 읽고 새 대회를 더한다(CCR-UC-001 UC-S4 1 · UC-S6).

목록 경계는 읽기와 더하기만 연다. 항목을 고치거나 지우는 길이 없고, 상태 파일은 열지도 않는다
(CCR-DOM-001 4.2 규칙 3). 사람이 페이지에서 지운 항목도 파일에 남아 있어 그대로 아는 대회다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from collector.domains.collect.models import Competition
from collector.domains.list.crud import ListCrud, ListReadFailed
from collector.domains.list.models import ListEntry, entry_of

log = logging.getLogger(__name__)


@dataclass
class ListFile:
    """실행을 시작할 때 읽은 목록 파일."""

    entries: list[ListEntry] = field(default_factory=list)
    exists: bool = False
    error: str | None = None  # 읽지 못했으면 그 사유. 로그에만 남긴다

    def ids(self) -> set[str]:
        """CCR-MS-001#ListFile.ids"""
        return {entry.id for entry in self.entries}


class ListService:
    def __init__(self, crud: ListCrud, *, write: bool) -> None:
        self._crud = crud
        self._write = write
        self._known_ids: set[str] = set()
        self._appended: list[dict[str, Any]] = []

    def load(self) -> ListFile:
        """CCR-MS-001#ListService.load"""
        if self._write:
            self._crud.reset_appends()
        result = ListFile()
        try:
            entries = self._crud.read()
        except ListReadFailed as exc:
            result.error = str(exc)
            log.error("목록 파일을 읽지 못했다: %s", exc)
            return result
        result.entries = entries or []
        result.exists = entries is not None
        duplicates = len(result.entries) - len(result.ids())
        if duplicates:
            log.warning("목록 파일에 식별자가 겹친 줄이 %d개 있다", duplicates)
        self._known_ids = result.ids()
        return result

    def append(self, competition: Competition, base_date: date, reason: str) -> ListEntry | None:
        """CCR-MS-001#ListService.append"""
        entry = entry_of(competition, base_date, reason)
        if entry.id in self._known_ids:
            log.warning("이미 목록에 있는 식별자라 더하지 않는다: %s (%s)", entry.title, entry.id)
            return None
        self._known_ids.add(entry.id)
        if not self._write:
            return entry  # 미리보기. 항목만 만들고 쓰지 않는다(UC-A1 1b3)
        self._appended.append(entry.to_dict())
        self._crud.write_appends(self._appended)
        return entry

    @property
    def appended_count(self) -> int:
        """CCR-MS-001#ListService.appended_count"""
        return len(self._appended)
