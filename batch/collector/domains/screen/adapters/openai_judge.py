"""OpenAI Responses API로 관련도를 판별한다(CCR-API-001 1.3 · 2.2 · 3.2 · 4.3).

SDK의 자동 재시도는 끄고 2.2의 표대로 직접 다시 묻는다. 판별 기준의 문구는 규칙이라 코드에 둔다
(CCR-DOM-001 4.3 · CCR-UC-001 UC-A4).
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Literal

import openai
from pydantic import BaseModel, ConfigDict, ValidationError

from collector.core.settings import JudgeSettings
from collector.domains.collect.models import Competition
from collector.domains.screen.ports import Answer, JudgeError
from collector.infra.http import Stopped

log = logging.getLogger(__name__)

CRITERIA = """\
너는 대회 공고를 거르는 분류기다. 공고가 AI·개발 분야 대회인지 가려 keep 또는 discard로 답한다.

keep: AI·머신러닝·데이터 분석 경진대회, 해커톤, 소프트웨어·개발 공모전, 데이터 활용 공모전,
알고리즘 대회, AI를 주제로 한 논문 경진대회.
discard: 창업·IR 경진대회, 사진·영상·디자인·문학 공모전, AI와 무관한 논문 공모,
교육과정·부트캠프 모집, 세미나·컨퍼런스.

분야가 섞여 있으면 참가자가 AI나 소프트웨어를 직접 만들거나 데이터를 분석해 겨루는지를 본다.
reason에는 판단 근거를 한국어 한 문장으로 적는다."""

FATAL_CODES = {
    "credit_balance_exhausted",
    "organization_spend_limit_exceeded",
    "project_spend_limit_exceeded",
    "organization_usage_limit_exceeded",
}
_EXTRAS_LIMIT = 800


class Relevance(BaseModel):
    """판별 스키마(CCR-API-001 4.3)."""

    model_config = ConfigDict(extra="forbid")

    decision: Literal["keep", "discard"]
    reason: str


def build_input(competition: Competition) -> str:
    """CCR-MS-001#openai_judge.build_input"""
    extras = ", ".join(competition.extras)
    if len(extras) > _EXTRAS_LIMIT:
        extras = extras[:_EXTRAS_LIMIT] + "…"
    lines = [f"대회명: {competition.title}", f"출처: {competition.source}"]
    if extras:
        lines.append(f"부가 정보: {extras}")
    return "\n".join(lines)


def _is_fatal(exc: openai.APIStatusError) -> bool:
    if exc.status_code in (401, 403, 404):
        return True
    if exc.status_code == 429:
        return exc.code in FATAL_CODES or exc.type == "insufficient_quota"
    return False


def _retryable(exc: Exception) -> bool:
    if isinstance(exc, openai.APIConnectionError):  # 타임아웃 포함
        return True
    if isinstance(exc, openai.APIStatusError):
        return exc.status_code in (408, 409, 429) or exc.status_code >= 500
    return False


class OpenAiJudge:
    def __init__(
        self,
        settings: JudgeSettings,
        api_key: str,
        stop: threading.Event,
        *,
        client: Any = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._settings = settings
        self._stop = stop
        self._sleep = sleep
        self._client = client or openai.OpenAI(api_key=api_key, max_retries=0, timeout=settings.timeout_seconds)

    def judge(self, competition: Competition) -> Answer:
        """CCR-MS-001#OpenAiJudge.judge"""
        attempts = 1 + max(0, self._settings.retries)
        for attempt in range(attempts):
            if self._stop.is_set():
                raise Stopped()
            try:
                response = self._client.responses.parse(
                    model=self._settings.model,
                    instructions=CRITERIA,
                    input=build_input(competition),
                    text_format=Relevance,
                    reasoning={"effort": "none"},
                    max_output_tokens=self._settings.max_output_tokens,
                    store=False,
                    timeout=self._settings.timeout_seconds,
                )
            except ValidationError as exc:
                raise JudgeError(f"답이 스키마에 맞지 않는다: {exc.error_count()}건") from exc
            except openai.APIStatusError as exc:
                if _is_fatal(exc):
                    raise JudgeError(f"응답 {exc.status_code} {exc.code or exc.type or ''}".strip(), fatal=True) from exc
                if not _retryable(exc) or attempt == attempts - 1:
                    raise JudgeError(f"응답 {exc.status_code} {exc.code or exc.type or ''}".strip()) from exc
                self._backoff(attempt)
                continue
            except openai.APIConnectionError as exc:
                if attempt == attempts - 1:
                    raise JudgeError(type(exc).__name__) from exc
                self._backoff(attempt)
                continue
            return self._read(response)
        raise JudgeError("다시 물을 횟수를 다 썼다")  # 도달하지 않는다

    def _read(self, response: Any) -> Answer:
        status = getattr(response, "status", None)
        if status != "completed":
            details = getattr(response, "incomplete_details", None)
            reason = getattr(details, "reason", None) if details is not None else None
            raise JudgeError(f"status {status}{f' ({reason})' if reason else ''}")
        parsed = response.output_parsed
        if parsed is None:
            raise JudgeError("답이 없다(거절이거나 최종 메시지 없음)")
        return Answer(keep=parsed.decision == "keep", reason=parsed.reason.strip())

    def _backoff(self, attempt: int) -> None:
        steps = self._settings.backoff_seconds or (1.0,)
        left = steps[min(attempt, len(steps) - 1)]
        while left > 0:
            if self._stop.is_set():
                raise Stopped()
            chunk = min(left, 0.5)
            self._sleep(chunk)
            left -= chunk
