"""판별 모델의 인터페이스(CCR-UC-001 UC-S5 · CCR-API-001 POST/api.openai.com/v1/responses)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from collector.domains.collect.models import Competition


class JudgeError(Exception):
    """판별하지 못했다.

    fatal이면 다시 물어도 같은 답이 오므로 남은 묶음도 묻지 않는다(CCR-API-001 2.2).
    """

    def __init__(self, detail: str, *, fatal: bool = False) -> None:
        super().__init__(detail)
        self.detail = detail
        self.fatal = fatal


@dataclass(frozen=True)
class Answer:
    keep: bool
    reason: str  # 한 줄 근거. 로그에만 남긴다


class Judge(Protocol):
    def judge(self, competition: Competition) -> Answer:
        """CCR-MS-001#Judge.judge

        묶음의 대표 하나가 관심 분야인지 묻는다. 실패하면 JudgeError.
        """
        ...
