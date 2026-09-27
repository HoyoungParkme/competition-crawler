"""수집 경계의 값. 도메인 개념 Source · Competition · SourceResult(CCR-DOM-001)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum


class SourceName(StrEnum):
    """소스 이름. 노션 `출처`에 이 이름이 들어간다(CCR-DOM-001 Source · CCR-API-001 4.2)."""

    EVENTUS = "event-us"
    DACON = "DACON"
    KAGGLE = "Kaggle"
    WEVITY = "wevity"
    AIFACTORY = "AI팩토리"
    CONTESTKOREA = "콘테스트코리아"


# 묶음의 대표를 고를 때와 합칠 짝의 차례를 가를 때 쓰는 우선순위(CCR-UC-001 UC-S4 4a2)
SOURCE_PRIORITY: dict[SourceName, int] = {
    SourceName.DACON: 1,
    SourceName.KAGGLE: 2,
    SourceName.AIFACTORY: 3,
    SourceName.EVENTUS: 4,
    SourceName.WEVITY: 5,
    SourceName.CONTESTKOREA: 6,
}


class FailureKind(StrEnum):
    """소스 실패의 종류. 실행 요약에는 이 값만 남는다(CCR-UC-001 UC-S7)."""

    CONNECTION = "connection"  # 연결 · 타임아웃 · 시간 예산 초과
    HTTP_STATUS = "http_status"  # 응답 코드
    FORMAT = "format"  # 응답이 예상과 다름
    ROBOTS = "robots"  # 수집 금지
    MISSING_CONFIG = "missing_config"  # 설정 누락


@dataclass(frozen=True)
class Competition:
    """한 소스에 올라온 공고 하나(CCR-DOM-001 Competition)."""

    source: SourceName
    source_id: str
    title: str
    link: str
    start_date: date | None = None
    deadline: date | None = None
    extras: tuple[str, ...] = ()
    practice: bool = False  # Kaggle 상시 연습용 대회. 마감 판정에서 버린다

    def dates_filled(self) -> int:
        return (self.start_date is not None) + (self.deadline is not None)


@dataclass
class Collected:
    """소스 어댑터가 돌려주는 것. 정규화까지 마친 대회와 셈."""

    competitions: list[Competition]
    collected: int  # 소스가 준 원본 레코드의 수
    dropped: int = 0  # 대회명이나 링크를 채우지 못해 버린 수
    page_cap_hit: bool = False
    notes: list[str] = field(default_factory=list)  # 로그에만 남길 것


@dataclass
class SourceResult:
    """한 실행에서 소스 하나를 돈 결과(CCR-DOM-001 SourceResult)."""

    source: SourceName
    competitions: list[Competition]
    collected: int
    dropped: int
    failure: FailureKind | None = None
    detail: str | None = None  # 원문 실패 사유. 로그에만 남긴다
    page_cap_hit: bool = False

    @property
    def normalized(self) -> int:
        return len(self.competitions)

    @classmethod
    def failed(cls, source: SourceName, kind: FailureKind, detail: str) -> "SourceResult":
        return cls(source=source, competitions=[], collected=0, dropped=0, failure=kind, detail=detail)
