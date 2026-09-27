from __future__ import annotations

import threading
from types import SimpleNamespace

import httpx2
import openai
import pytest
from pydantic import ValidationError

from collector.domains.collect.models import SourceName
from collector.domains.screen.adapters.openai_judge import CRITERIA, OpenAiJudge, Relevance, build_input
from collector.domains.screen.ports import JudgeError
from tests.conftest import JUDGE_SETTINGS, comp


def status_error(status: int, code: str | None = None, type_: str | None = None) -> openai.APIStatusError:
    request = httpx2.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx2.Response(status, request=request)
    body = {"code": code, "type": type_, "message": "x"}
    classes = {400: openai.BadRequestError, 401: openai.AuthenticationError, 404: openai.NotFoundError, 429: openai.RateLimitError}
    cls = classes.get(status, openai.InternalServerError if status >= 500 else openai.APIStatusError)
    return cls("x", response=response, body=body)


def completed(decision: str = "keep", reason: str = "AI 대회") -> SimpleNamespace:
    return SimpleNamespace(status="completed", output_parsed=Relevance(decision=decision, reason=reason), incomplete_details=None)


class FakeResponses:
    def __init__(self, *results: object) -> None:
        self.results = list(results)
        self.calls: list[dict] = []

    def parse(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def judge_with(*results: object) -> tuple[OpenAiJudge, FakeResponses]:
    responses = FakeResponses(*results)
    client = SimpleNamespace(responses=responses)
    return OpenAiJudge(JUDGE_SETTINGS, "k", threading.Event(), client=client, sleep=lambda s: None), responses


def test_request_shape() -> None:
    judge, responses = judge_with(completed())
    answer = judge.judge(comp("2026 AI 챌린지", source=SourceName.AIFACTORY, extras=("주제 1",)))
    assert answer.keep and answer.reason == "AI 대회"
    call = responses.calls[0]
    assert call["model"] == "gpt-6-luna"
    assert call["instructions"] == CRITERIA
    assert call["reasoning"] == {"effort": "none"}
    assert call["store"] is False
    assert call["max_output_tokens"] == 300
    assert call["text_format"] is Relevance
    assert call["input"] == "대회명: 2026 AI 챌린지\n출처: AI팩토리\n부가 정보: 주제 1"


def test_discard() -> None:
    judge, _ = judge_with(completed("discard", "사진 공모전"))
    assert judge.judge(comp("사진 공모전")).keep is False


@pytest.mark.parametrize(
    "error",
    [
        status_error(401),
        status_error(404),
        status_error(429, code="project_spend_limit_exceeded"),
        status_error(429, type_="insufficient_quota"),
    ],
)
def test_same_answer_errors_are_fatal_and_not_retried(error: Exception) -> None:
    judge, responses = judge_with(error, completed())
    with pytest.raises(JudgeError) as err:
        judge.judge(comp("대회"))
    assert err.value.fatal
    assert len(responses.calls) == 1


def test_bad_request_fails_only_that_bundle() -> None:
    judge, responses = judge_with(status_error(400), completed())
    with pytest.raises(JudgeError) as err:
        judge.judge(comp("대회"))
    assert not err.value.fatal
    assert len(responses.calls) == 1


def test_rate_limit_and_server_errors_are_retried() -> None:
    judge, responses = judge_with(status_error(429, code="rate_limit_exceeded"), status_error(503), completed())
    assert judge.judge(comp("대회")).keep
    assert len(responses.calls) == 3


def test_connection_errors_exhaust_retries() -> None:
    request = httpx2.Request("POST", "https://api.openai.com/v1/responses")
    errors = [openai.APITimeoutError(request=request) for _ in range(3)]
    judge, responses = judge_with(*errors)
    with pytest.raises(JudgeError):
        judge.judge(comp("대회"))
    assert len(responses.calls) == 3


def test_incomplete_refusal_and_schema_errors_are_bundle_failures() -> None:
    incomplete = SimpleNamespace(status="incomplete", output_parsed=None, incomplete_details=SimpleNamespace(reason="max_output_tokens"))
    refusal = SimpleNamespace(status="completed", output_parsed=None, incomplete_details=None)
    try:
        Relevance.model_validate_json('{"decision": "maybe", "reason": ""}')
    except ValidationError as exc:
        invalid = exc
    for result in (incomplete, refusal, invalid):
        judge, responses = judge_with(result, completed())
        with pytest.raises(JudgeError) as err:
            judge.judge(comp("대회"))
        assert not err.value.fatal
        assert len(responses.calls) == 1


def test_long_extras_are_cut() -> None:
    text = build_input(comp("대회", extras=tuple("과제" * 50 for _ in range(20))))
    assert len(text) < 1000
