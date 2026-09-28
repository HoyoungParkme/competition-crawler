"""같은 대회 판정. 예는 CCR-PRD-001 5.2와 CCR-UC-001 UC-S4에 적힌 실측이다."""

from __future__ import annotations

from datetime import date
from difflib import SequenceMatcher

import pytest

from collector.domains.collect.models import SourceName
from collector.domains.notion.models import NotionRow
from collector.domains.record.models import HistoryRecord, Result
from collector.domains.screen.matching import (
    extract_marks,
    group,
    judge_pair,
    key_of_competition,
    key_of_history,
    key_of_notion,
    normalize_link,
    normalize_title,
    similarity,
)
from collector.domains.screen.models import Verdict
from tests.conftest import comp


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("2026년 Big Data 활용 대회 참가자 모집", "2026bigdata활용대회"),
        ("[부산광역시] Big Data 활용 대회", "bigdata활용대회"),
        ("2026 AI 해커톤 (~9/20)", "2026ai해커톤"),
        ("2026 AI 해커톤 참가팀 모집 공고", "2026ai해커톤"),
        ("데이터 분석 경진대회(9월 20일(금)까지)", "데이터분석경진대회"),
        ("[제5회] 알고리즘 대회 안내", "알고리즘대회"),
        ("[2026 AI 공모전]", "2026ai공모전"),
        ("AI 대회 (제2회)", "ai대회제2회"),
    ],
)
def test_normalize_title(title: str, expected: str) -> None:
    assert normalize_title(title) == expected


def test_marks() -> None:
    assert extract_marks("2026 데이터 경진대회") == (frozenset({2026}), frozenset())
    assert extract_marks("제5회 AI 대회")[1] == frozenset({5})
    assert extract_marks("The 2nd Global Quantum AI Competition - 2026") == (frozenset({2026}), frozenset({2}))
    assert extract_marks("SW마에스트로 16기 모집")[1] == frozenset({16})
    assert extract_marks("[제5차] 제조혁신 경진대회")[1] == frozenset({5})
    assert extract_marks("20251 기업")[0] == frozenset()


def test_tracking_parameters_are_removed_but_ids_are_kept() -> None:
    assert (
        normalize_link("https://www.wevity.com/?c=find&s=1&gbn=view&ix=110675&utm_source=x&fbclid=y")
        == "https://www.wevity.com/?c=find&s=1&gbn=view&ix=110675"
    )
    assert normalize_link("http://Event-Us.kr/a/event/1/") == "https://event-us.kr/a/event/1"
    assert normalize_link(None) is None


def test_similarity_matches_prd_examples() -> None:
    a = key_of_competition(comp("2026 한국관광 데이터랩 활용 경진대회"))
    b = key_of_competition(comp("2025 한국관광 데이터랩 활용 경진대회"))
    assert similarity(a, b) == pytest.approx(0.94, abs=0.01)
    # 정규화는 PRD의 0.85를 재현한다. 0.90에 닿을 수 없는 짝이라 similarity는 계산하지 않고 0을 돌려준다
    c = key_of_competition(comp("2026년 Big Data 활용 대회 참가자 모집"))
    d = key_of_competition(comp("[부산광역시] Big Data 활용 대회"))
    ratio = SequenceMatcher(None, c.title_norm, d.title_norm, autojunk=False).ratio()
    assert ratio == pytest.approx(0.85, abs=0.01)
    assert similarity(c, d) == 0.0


def test_step2_years_split_similar_names() -> None:
    a = key_of_competition(comp("2026 한국관광 데이터랩 활용 경진대회"))
    b = key_of_competition(comp("2025 한국관광 데이터랩 활용 경진대회"))
    result = judge_pair(a, b)
    assert (result.verdict, result.step) == (Verdict.DIFFERENT, 2)


def test_step3_last_years_notice_is_a_different_competition() -> None:
    # 2026년 Big Data(9/10~9/18)와 작년 공고(2025-04-24~05-02). 유사도 0.85지만 3단계에서 갈린다
    new = comp("2026년 Big Data 활용 대회 참가자 모집", start=date(2026, 9, 10), deadline=date(2026, 9, 18))
    old = HistoryRecord(
        source="event-us",
        source_id="1",
        link=None,
        title="[부산광역시] Big Data 활용 대회",
        start_date=date(2025, 4, 24),
        deadline=date(2025, 5, 2),
        result=Result.KEEP,
        base_date=date(2025, 4, 25),
        run_id="r",
    )
    result = judge_pair(key_of_competition(new), key_of_history(old))
    assert (result.verdict, result.step) == (Verdict.DIFFERENT, 3)


def test_step3_deadlines_far_apart() -> None:
    a = key_of_competition(comp("AI 창업 경진대회", source_id="1", deadline=date(2026, 9, 30)))
    b = key_of_competition(comp("AI 창업 경진대회", source_id="2", deadline=date(2026, 1, 10)))
    assert judge_pair(a, b).verdict is Verdict.DIFFERENT


def test_extended_deadline_stays_the_same_competition() -> None:
    before = comp("2026 AI 챌린지", source_id="1", start=date(2026, 8, 1), deadline=date(2026, 9, 10))
    after = comp("2026 AI 챌린지", source_id="2", start=date(2026, 8, 1), deadline=date(2026, 9, 30))
    result = judge_pair(key_of_competition(before), key_of_competition(after))
    assert (result.verdict, result.step, result.certain) == (Verdict.SAME, 4, True)


def test_step1_same_source_and_id_ignores_changed_dates() -> None:
    a = comp("대회", source=SourceName.DACON, source_id="7", start=date(2026, 9, 1), deadline=date(2026, 9, 30))
    b = comp("대회 이름 바뀜", source=SourceName.DACON, source_id="7", start=date(2027, 1, 1))
    result = judge_pair(key_of_competition(a), key_of_competition(b))
    assert (result.verdict, result.step, result.certain) == (Verdict.SAME, 1, True)


def test_notion_link_match_still_checks_years() -> None:
    link = "https://event-us.kr/big/event/1?utm_source=notion"
    candidate = comp("2026 Big Data 활용 대회", link="https://event-us.kr/big/event/1")
    same_year = NotionRow("p1", "Big Data 대회 2026", link, None, None)
    other_year = NotionRow("p2", "2025 Big Data 활용 대회", link, None, None)
    assert judge_pair(key_of_competition(candidate), key_of_notion(same_year)).step == 1
    assert judge_pair(key_of_competition(candidate), key_of_notion(other_year)).verdict is Verdict.DIFFERENT


def test_name_only_match_is_not_certain() -> None:
    a = key_of_competition(comp("알고리즘 경진대회", deadline=date(2026, 10, 1)))
    b = key_of_history(
        HistoryRecord("wevity", "9", None, "알고리즘 경진대회", None, None, Result.DISCARD, None, "r")
    )
    result = judge_pair(a, b)
    assert (result.verdict, result.certain) == (Verdict.SAME, False)


def test_below_threshold_is_undecided_not_different() -> None:
    a = key_of_competition(comp("2026 AI 창업 경진대회"))
    b = key_of_competition(comp("2026 데이터 시각화 공모전"))
    assert judge_pair(a, b).verdict is Verdict.UNDECIDED


def test_prd_pair_at_082_is_undecided() -> None:
    # 노션 행과 event-us의 부문 모집 공고는 같은 대회지만 0.82라 판단하지 않는다(PRD 5.2)
    row = NotionRow("p1", "2026 데이터·AI 혁신 챌린지 통합경진대회", "https://dxchallenge.co.kr", None, None)
    notice = comp("2026 데이터·AI 혁신 챌린지 통합경진대회 데이터 문제해결 부문 모집")
    assert judge_pair(key_of_competition(notice), key_of_notion(row)).verdict is Verdict.UNDECIDED


def test_threshold_is_090() -> None:
    # 연도가 없는 쪽 이름이 18자면 연도 네 글자가 붙어도 0.90으로 같고, 17자면 못 미친다
    a = key_of_competition(comp("2026 스마트 물류 데이터 분석 아이디어 경진대회"))
    b = key_of_competition(comp("스마트 물류 데이터 분석 아이디어 경진대회"))
    result = judge_pair(a, b)
    assert (result.verdict, result.step) == (Verdict.SAME, 5)
    assert result.similarity == pytest.approx(0.90)
    c = key_of_competition(comp("2026 스마트 물류 데이터 분석 아이디어 공모전"))
    d = key_of_competition(comp("스마트 물류 데이터 분석 아이디어 공모전"))
    assert judge_pair(c, d).verdict is Verdict.UNDECIDED


def test_group_does_not_chain_different_years() -> None:
    # 연도 없는 공고 하나가 2025년과 2026년 공고를 잇지 못한다(UC-S4 4b).
    # 연도 없는 이름이 18자 이상이라 연도가 붙은 두 공고와 각각 0.90을 넘는다
    items = [
        comp("2026 데이터 기반 도시 문제 해결 아이디어 경진대회", source_id="a"),
        comp("데이터 기반 도시 문제 해결 아이디어 경진대회", source_id="b"),
        comp("2025 데이터 기반 도시 문제 해결 아이디어 경진대회", source_id="c"),
    ]
    groups = group(items, [key_of_competition(c) for c in items])
    assert sorted(len(g) for g in groups) == [1, 2]
    joined = next(g for g in groups if len(g) == 2)
    assert {items[i].source_id for i in joined} in ({"a", "b"}, {"b", "c"})


def test_group_needs_every_pair_to_be_the_same() -> None:
    # 2026-09-27 wevity. a~b 0.94 · b~c 0.91이지만 a–c는 0.90에 못 미쳐 판단하지 않음이다.
    # 강한 a~b를 먼저 합치고, c는 a와 같다고 나오지 않아 따로 남는다(UC-S4 4b)
    items = [
        comp("[동작구시설관리공단] 2026 주민참여 혁신 아이디어 공모전", source=SourceName.WEVITY, source_id="a"),
        comp("[대전관광공사] 2026 주민참여 아이디어 공모전", source=SourceName.WEVITY, source_id="b"),
        comp("[포천도시공사] 2026년 주민참여예산제 아이디어 공모전", source=SourceName.WEVITY, source_id="c"),
    ]
    keys = [key_of_competition(c) for c in items]
    assert judge_pair(keys[0], keys[1]).verdict is Verdict.SAME
    assert judge_pair(keys[1], keys[2]).verdict is Verdict.SAME
    assert judge_pair(keys[0], keys[2]).verdict is Verdict.UNDECIDED
    assert group(items, keys) == [[0, 1], [2]]


def test_group_keeps_templated_idea_contests_apart() -> None:
    # 2026-09-27. 문턱 0.80 · 사슬 규칙에서는 0.87 · 0.84 짝으로 이어져 한 묶음이 됐다(PRD 5.2)
    items = [
        comp("2026 대구 관광 혁신 아이디어 공모전", source_id="a"),
        comp("[포천도시공사] 2026년 혁신 아이디어 공모전", source_id="b"),
        comp("2026년 성남시 규제혁신 아이디어 공모전", source_id="c"),
    ]
    assert group(items, [key_of_competition(c) for c in items]) == [[0], [1], [2]]


def test_group_merges_duplicate_notices_across_sources() -> None:
    items = [
        comp("2026 국립공원 위성 모니터링 AI 챌린지", source=SourceName.AIFACTORY, source_id="9304"),
        comp("2026 국립공원 위성 모니터링 AI 챌린지 참가자 모집", source=SourceName.EVENTUS, source_id="1"),
        comp("전혀 다른 사진 공모전", source=SourceName.WEVITY, source_id="2"),
    ]
    groups = group(items, [key_of_competition(c) for c in items])
    assert sorted(len(g) for g in groups) == [1, 2]
