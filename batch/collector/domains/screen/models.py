"""선별 경계의 값. 도메인 개념 Bundle(CCR-DOM-001)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum, StrEnum

from collector.domains.collect.models import Competition


class Verdict(Enum):
    SAME = "same"
    DIFFERENT = "different"
    UNDECIDED = "undecided"  # 5단계에서 문턱에 못 미쳤다. 다르다는 뜻이 아니다


@dataclass(frozen=True)
class PairResult:
    verdict: Verdict
    step: int | None = None
    similarity: float = 0.0
    certain: bool = False  # 1단계였거나, 연도 · 회차 · 접수 날짜를 실제로 맞대 보고 같았다


@dataclass(frozen=True)
class MatchKey:
    """판정에 쓰는 값. 대회 · 목록 항목 · 처리 이력 기록에서 같은 방법으로 뽑는다(CCR-DOM-001 4.2 규칙 6)."""

    source: str | None
    source_id: str | None
    link: str | None  # 추적용 매개변수를 뗀 링크. 목록 항목과 견줄 때만 쓴다
    from_list: bool
    title_norm: str
    years: frozenset[int]
    rounds: frozenset[int]
    start: date | None
    deadline: date | None
    chars: frozenset[str] = field(default=frozenset(), compare=False)  # 유사도 계산 전 거르기용


class KnownKind(StrEnum):
    LIST = "list"
    HISTORY = "history"


@dataclass(frozen=True)
class Known:
    """이미 아는 대회. 목록 항목이면 결과는 남김이다."""

    kind: KnownKind
    key: MatchKey
    result: str  # keep · discard
    label: str


class Outcome(StrEnum):
    KNOWN = "known"
    DISCARDED = "discarded"
    LOADED = "loaded"
    DEFERRED = "deferred"


@dataclass
class Bundle:
    members: list[Competition]
    representative: Competition
    judge_failed: bool = False
    outcome: Outcome | None = None
    matched: list[tuple[Known, PairResult]] = field(default_factory=list)
    reason: str = ""  # 판별 근거. 목록 항목에 들어간다(CCR-UC-001 UC-S6)
    keys: list[MatchKey] = field(default_factory=list, repr=False)  # 구성원의 판정 값. 구성원과 같은 차례

    @property
    def deadline(self) -> date | None:
        """CCR-MS-001#Bundle.deadline

        묶음의 접수마감일은 구성원 가운데 가장 늦은 값이다. 오늘 마감인지 가를 때 쓴다.
        """
        values = [m.deadline for m in self.members if m.deadline is not None]
        return max(values) if values else None
