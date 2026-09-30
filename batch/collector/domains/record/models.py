"""기록 경계의 값. 도메인 개념 HistoryRecord · Run · Warning(CCR-DOM-001).

두 기록 파일의 한 줄 형식은 ERD(CCR-DOM-003)가 정한다. 마무리 단계(`batch/finish.py`)는
이 모듈을 불러오지 않고 같은 형식을 따로 안다(CCR-INFRA-001 8.2).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import Any

HISTORY_REQUIRED = ("source", "source_id", "result", "run_id")


class Result(StrEnum):
    KEEP = "keep"  # 남김
    DISCARD = "discard"  # 버림


class RunResult(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    ABORTED = "aborted"  # 중단. 마무리 단계만 쓴다


class FailureReason(StrEnum):
    ALL_SOURCES_FAILED = "all_sources_failed"
    LIST_READ_FAILED = "list_read_failed"
    HISTORY_READ_FAILED = "history_read_failed"
    HISTORY_SHRANK = "history_shrank"


class WarningKind(StrEnum):
    ZERO_COUNT = "zero_count"
    JUDGE_DEFERRED = "judge_deferred"
    SUMMARY_CORRUPT = "summary_corrupt"


def _iso(value: date | None) -> str | None:
    return value.isoformat() if value else None


def _date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    return date.fromisoformat(str(value))


@dataclass(frozen=True)
class HistoryEntry:
    """선별이 정해 넘기는 한 줄의 값. 기준일과 실행 식별자는 기록 경계가 붙인다."""

    source: str
    source_id: str
    link: str | None
    title: str
    start_date: date | None
    deadline: date | None
    result: Result


@dataclass(frozen=True)
class HistoryRecord:
    """처리 이력 한 줄(`data/processed.jsonl`)."""

    source: str
    source_id: str
    link: str | None
    title: str
    start_date: date | None
    deadline: date | None
    result: Result
    base_date: date | None
    run_id: str

    @classmethod
    def of(cls, entry: HistoryEntry, base_date: date, run_id: str) -> HistoryRecord:
        """CCR-MS-001#HistoryRecord.of"""
        return cls(
            source=entry.source,
            source_id=entry.source_id,
            link=entry.link,
            title=entry.title,
            start_date=entry.start_date,
            deadline=entry.deadline,
            result=entry.result,
            base_date=base_date,
            run_id=run_id,
        )

    def to_dict(self) -> dict[str, Any]:
        """CCR-MS-001#HistoryRecord.to_dict"""
        return {
            "source": self.source,
            "source_id": self.source_id,
            "link": self.link,
            "title": self.title,
            "start_date": _iso(self.start_date),
            "deadline": _iso(self.deadline),
            "result": str(self.result),
            "base_date": _iso(self.base_date),
            "run_id": self.run_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HistoryRecord:
        """CCR-MS-001#HistoryRecord.from_dict"""
        missing = [k for k in HISTORY_REQUIRED if data.get(k) in (None, "")]
        if missing:
            raise ValueError(f"필수 필드가 없다: {missing}")
        return cls(
            source=str(data["source"]),
            source_id=str(data["source_id"]),
            link=data.get("link") or None,
            title=str(data.get("title") or ""),
            start_date=_date(data.get("start_date")),
            deadline=_date(data.get("deadline")),
            result=Result(data["result"]),
            base_date=_date(data.get("base_date")),
            run_id=str(data["run_id"]),
        )


@dataclass(frozen=True)
class RunWarning:
    kind: WarningKind
    source: str | None = None
    last_nonzero: date | None = None  # 소스 0건일 때 그 소스가 마지막으로 건수를 낸 기준일
    cause: str | None = None  # 판별 미룸일 때 missing_key · call_failed

    def to_dict(self) -> dict[str, Any]:
        """CCR-MS-001#RunWarning.to_dict"""
        out: dict[str, Any] = {"kind": str(self.kind)}
        if self.source is not None:
            out["source"] = self.source
        if self.last_nonzero is not None:
            out["last_nonzero"] = self.last_nonzero.isoformat()
        if self.cause is not None:
            out["cause"] = self.cause
        return out


@dataclass
class SourceLine:
    collected: int
    normalized: int
    failure: str | None

    def to_dict(self) -> dict[str, Any]:
        """CCR-MS-001#SourceLine.to_dict"""
        return {"collected": self.collected, "normalized": self.normalized, "failure": self.failure}


@dataclass
class RunLine:
    """실행 요약 한 줄(`data/runs.jsonl`). 남김 기록의 수는 마무리 단계가 채운다."""

    run_id: str
    base_date: date
    kind: str
    result: RunResult = RunResult.SUCCESS
    failure_reason: FailureReason | None = None
    keep_count: int | None = None  # 배치는 비워 두고 마무리 단계가 올린 뒤 세어 채운다
    sources: dict[str, SourceLine] = field(default_factory=dict)
    dropped: dict[str, int] = field(
        default_factory=lambda: {"normalize": 0, "expired": 0, "known": 0, "discarded": 0}
    )
    loaded: int = 0
    judge_failed: int = 0
    deferred: int = 0
    warnings: list[RunWarning] = field(default_factory=list)
    duration_s: float = 0.0

    def fail(self, reason: FailureReason) -> None:
        """CCR-MS-001#RunLine.fail"""
        self.result = RunResult.FAILURE
        self.failure_reason = reason

    def to_dict(self) -> dict[str, Any]:
        """CCR-MS-001#RunLine.to_dict"""
        return {
            "run_id": self.run_id,
            "base_date": self.base_date.isoformat(),
            "kind": self.kind,
            "result": str(self.result),
            "failure_reason": str(self.failure_reason) if self.failure_reason else None,
            "keep_count": self.keep_count,
            "sources": {name: line.to_dict() for name, line in self.sources.items()},
            "dropped": dict(self.dropped),
            "loaded": self.loaded,
            "judge_failed": self.judge_failed,
            "deferred": self.deferred,
            "warnings": [w.to_dict() for w in self.warnings],
            "duration_s": round(self.duration_s, 1),
        }
