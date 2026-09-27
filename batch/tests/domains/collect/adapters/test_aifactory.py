from __future__ import annotations

from datetime import date

import httpx
import pytest

from collector.domains.collect.adapters import aifactory
from collector.infra.http import FormatError
from tests.conftest import FakeClock, fixture_bytes, make_http, response_of


@pytest.fixture(scope="module")
def competitions() -> dict[str, object]:
    tasks = aifactory.parse_page(response_of("aifactory_competition.html"))
    assert len(tasks) == 112
    groups = aifactory.group_tasks(tasks)
    assert len(groups) == 88
    out = {}
    for group in groups:
        c = aifactory.to_competition(group)
        assert c is not None
        out[c.source_id] = c
    return out


@pytest.mark.parametrize(
    ("source_id", "title", "start", "deadline"),
    [
        ("9304", "2026 국립공원 위성 모니터링 AI 챌린지", date(2026, 7, 31), date(2026, 10, 6)),
        ("9235", "2026 AI Co-Scientist Challenge Korea (AI 연구동료 경진대회)", date(2025, 12, 10), date(2026, 1, 31)),
        ("9159", "2025 네트워크 AI 해커톤 참가자 접수", date(2025, 7, 14), date(2025, 8, 15)),
        ("6684", "[제5차] USG AI·데이터 제조혁신 경진대회", date(2024, 10, 21), date(2024, 11, 5)),
        ("2367", "[연습용] 추론자동화 제출", date(2023, 7, 17), date(2025, 12, 30)),
    ],
)
def test_competition_names_and_dates(competitions, source_id, title, start, deadline) -> None:
    c = competitions[source_id]
    assert c.title == title
    assert (c.start_date, c.deadline) == (start, deadline)
    assert c.link == f"https://aifactory.space/competitions/{source_id}"


def test_name_rules() -> None:
    task = lambda i, name: aifactory.Task(i, name, "과학기술정보통신부", date(2026, 7, 1), date(2026, 8, 1))  # noqa: E731
    # 연도가 없는 페이지 이름(기관명)은 대회명이 되지 않는다
    assert aifactory.competition_name("과학기술정보통신부", [task(1, "2026 데이터 경진대회")], date(2026, 7, 1)) == "2026 데이터 경진대회"
    # 공통 앞부분에서 끝의 구분 기호를 뗀다
    tasks = [task(2, "2026 AI 챌린지 - 이미지 부문"), task(3, "2026 AI 챌린지 - 텍스트 부문")]
    assert aifactory.competition_name("과학기술정보통신부", tasks, date(2026, 7, 1)) == "2026 AI 챌린지"
    # 머리 꼬리표가 과제마다 다르면 떼고 다시 본다
    tagged = [task(6, "[Track 1] 2026 데이터 분석 대회"), task(7, "[Track 2] 2026 데이터 분석 대회")]
    assert aifactory.competition_name("과학기술정보통신부", tagged, date(2026, 7, 1)) == "2026 데이터 분석 대회"
    # 주제 번호로 시작하면 페이지 이름을 쓴다
    topics = [task(4, "주제 1: 탐지"), task(5, "주제 2: 분류")]
    assert aifactory.competition_name("국립공원 챌린지", topics, date(2026, 7, 1)) == "국립공원 챌린지"


def test_sentinel_date_is_empty() -> None:
    payload = '5:{"id":"7","name":"과제","page":{"name":"p"},"endDate":"1970-01-01T00:00:00.000Z"}\n'
    tasks = aifactory.parse_tasks(payload)
    assert tasks[0].deadline is None


def test_page_without_payload_is_a_format_error() -> None:
    with pytest.raises(FormatError):
        aifactory.parse_page(httpx.Response(200, text="<html></html>"))


def test_collect_counts_tasks(clock: FakeClock) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=fixture_bytes("aifactory_competition.html"))

    collected = aifactory.AiFactorySource().collect(make_http(handler, clock=clock), date(2026, 9, 27), page_cap=20)
    # 수집 건수는 합치기 전 과제의 수다
    assert collected.collected == 112
    assert len(collected.competitions) == 88
