"""처리 이력과 실행 요약(CCR-UC-001 UC-S4 2 · UC-S7 · CCR-DOM-001 HistoryRecord · Run · Warning).

기록 경계는 묶음을 모른다. 적을 값은 선별과 실행의 흐름이 정해 넘기고, 여기서는 받은 대로
덧붙인다. 스스로 판단하는 것은 남김 기록의 수 견주기 · 소스 0건 경고 · 요약 파일 손상 경고다
(CCR-DOM-001 4.2 규칙 4 · 5).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from collector.domains.collect.models import SourceResult
from collector.domains.record.crud import HistoryReadFailed, RecordCrud, RunsFile
from collector.domains.record.models import (
    HistoryEntry,
    HistoryRecord,
    Result,
    RunLine,
    RunWarning,
    WarningKind,
)

log = logging.getLogger(__name__)


@dataclass
class State:
    """실행을 시작할 때 읽은 두 파일."""

    history: list[HistoryRecord] = field(default_factory=list)
    history_exists: bool = False
    history_error: str | None = None  # 읽지 못했으면 그 사유. 로그에만 남긴다
    runs: RunsFile = field(default_factory=RunsFile)

    @property
    def keep_count(self) -> int:
        return sum(1 for r in self.history if r.result is Result.KEEP)

    def last_keep_count(self) -> int | None:
        """실행 요약에 마지막으로 적힌 남김 기록의 수. 적힌 줄이 없으면 None."""
        for line in reversed(self.runs.lines):
            value = line.get("keep_count")
            if isinstance(value, int) and not isinstance(value, bool):
                return value
        return None


class RecordService:
    def __init__(self, crud: RecordCrud, *, write: bool, run_id: str, base_date: date) -> None:
        self._crud = crud
        self._write = write
        self._run_id = run_id
        self._base_date = base_date
        self._appended: list[dict[str, Any]] = []

    def start(self) -> None:
        """노션에 쓰는 실행이면 추가분 파일을 비워 둔다."""
        if self._write:
            self._crud.reset_appends()

    def load(self) -> State:
        """두 파일을 읽는다. 처리 이력을 읽지 못하면 history_error에 사유를 담는다(UC-S4 2b)."""
        state = State()
        try:
            self._crud.prepare()
            history = self._crud.read_history()
            state.runs = self._crud.read_runs()
        except HistoryReadFailed as exc:
            state.history_error = str(exc)
            log.error("처리 이력을 읽지 못했다: %s", exc)
            return state
        state.history = history or []
        state.history_exists = history is not None
        if state.runs.corrupt:
            log.warning("실행 요약에 읽히지 않는 줄 %d개를 건너뛴다", state.runs.corrupt)
        return state

    def history_shrank(self, state: State) -> bool:
        """남김 기록이 실행 요약에 마지막으로 적힌 수보다 적은가(UC-S4 2c · 2a)."""
        last = state.last_keep_count()
        if last is None:
            return False  # 첫 실행이거나 적힌 줄이 없다(UC-S4 2a1)
        current = state.keep_count if state.history_exists else 0
        if current < last:
            log.error("처리 이력의 남김 기록 %d개가 실행 요약에 적힌 %d개보다 적다", current, last)
            return True
        return False

    def append(self, entries: list[HistoryEntry]) -> None:
        """처리 이력 추가분에 곧바로 적는다. 노션에 쓰지 않는 실행은 적지 않는다(UC-A1 1b2)."""
        if not self._write or not entries:
            return
        for entry in entries:
            self._appended.append(HistoryRecord.of(entry, self._base_date, self._run_id).to_dict())
        self._crud.write_history_appends(self._appended)

    @property
    def appended_count(self) -> int:
        return len(self._appended)

    def zero_count_warnings(self, results: list[SourceResult], state: State, days: int) -> list[RunWarning]:
        """꾸준히 건수를 내던 소스가 오류 없이 0건을 냈는가(UC-S7 2)."""
        warnings: list[RunWarning] = []
        for result in results:
            if result.failure is not None or result.normalized > 0:
                continue
            last = _nonzero_streak_before_zero(str(result.source), state.runs.lines, self._base_date, days)
            if last is not None:
                warnings.append(RunWarning(WarningKind.ZERO_COUNT, source=str(result.source), last_nonzero=last))
        return warnings

    def write_run(self, line: RunLine) -> None:
        """실행 요약 추가분에 이 실행의 한 줄을 쓴다. 노션에 쓰지 않는 실행은 쓰지 않는다(UC-S7 8a)."""
        if not self._write:
            return
        self._crud.write_run_append(line.to_dict())


def _day_counts(source: str, lines: list[dict[str, Any]]) -> dict[date, bool]:
    """기준일마다 그 소스가 1건 이상을 냈는가. 수집하지 않았거나 실패한 줄은 건너뛴다."""
    days: dict[date, bool] = {}
    for line in lines:
        sources = line.get("sources")
        entry = sources.get(source) if isinstance(sources, dict) else None
        if not isinstance(entry, dict) or entry.get("failure") is not None:
            continue
        normalized = entry.get("normalized")
        if not isinstance(normalized, int) or isinstance(normalized, bool):
            continue
        try:
            day = date.fromisoformat(str(line.get("base_date")))
        except ValueError:
            continue
        days[day] = days.get(day, False) or normalized > 0
    return days


def _nonzero_streak_before_zero(source: str, lines: list[dict[str, Any]], today: date, need: int) -> date | None:
    """0건이 시작되기 바로 앞까지 연속 `need`일 1건 이상이었으면 마지막으로 건수를 낸 기준일."""
    days = _day_counts(source, lines)
    if days.get(today):
        return None  # 같은 기준일의 다른 실행이 건수를 냈다
    ordered = sorted((d for d in days if d < today), reverse=True)
    index = 0
    while index < len(ordered) and not days[ordered[index]]:
        index += 1  # 오늘 앞으로 이어진 0건인 날
    streak = 0
    last_nonzero: date | None = None
    while index < len(ordered) and days[ordered[index]]:
        last_nonzero = last_nonzero or ordered[index]
        streak += 1
        index += 1
    return last_nonzero if streak >= need else None
