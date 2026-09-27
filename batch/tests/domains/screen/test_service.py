from __future__ import annotations

import threading
from datetime import date
from pathlib import Path

import pytest

from collector.domains.collect.models import Competition, SourceName
from collector.domains.notion.models import NotionRow
from collector.domains.record.crud import RecordCrud
from collector.domains.record.models import HistoryRecord, Result
from collector.domains.record.service import RecordService
from collector.domains.screen.models import Outcome
from collector.domains.screen.ports import Answer, JudgeError
from collector.domains.screen.service import ScreenService
from tests.conftest import comp

BASE = date(2026, 9, 27)


class FakeJudge:
    def __init__(self, answers: dict[str, object]) -> None:
        self.answers = answers
        self.asked: list[str] = []
        self._lock = threading.Lock()

    def judge(self, competition: Competition) -> Answer:
        with self._lock:
            self.asked.append(competition.title)
        answer = self.answers.get(competition.title, Answer(True, "AI 대회"))
        if isinstance(answer, Exception):
            raise answer
        return answer  # type: ignore[return-value]


class MemoryRecord(RecordService):
    def __init__(self, tmp: Path, write: bool = True) -> None:
        super().__init__(RecordCrud(tmp / "state", tmp / "append"), write=write, run_id="r1", base_date=BASE)
        self.entries: list = []

    def append(self, entries) -> None:  # type: ignore[override]
        self.entries.extend(entries)
        super().append(entries)


def service(tmp_path: Path, judge=None, *, ignore_discards: bool = False, write: bool = True):
    record = MemoryRecord(tmp_path, write=write)
    return ScreenService(
        record,
        base_date=BASE,
        ignore_discards=ignore_discards,
        judge=judge,
        concurrency=4,
        stop=threading.Event(),
    ), record


def history(title: str, result: Result, *, source="event-us", source_id="h1", start=None, deadline=None) -> HistoryRecord:
    return HistoryRecord(source, source_id, None, title, start, deadline, result, date(2026, 9, 1), "old")


def test_drop_expired_keeps_today_and_unknown_deadlines(tmp_path: Path) -> None:
    screen, _ = service(tmp_path)
    kept, dropped = screen.drop_expired(
        [
            comp("어제 마감", deadline=date(2026, 9, 26)),
            comp("오늘 마감", deadline=BASE),
            comp("마감 모름"),
            comp("Titanic", source=SourceName.KAGGLE, deadline=date(2030, 1, 1), practice=True),
        ]
    )
    assert [c.title for c in kept] == ["오늘 마감", "마감 모름"]
    assert dropped == 2


def test_representative_prefers_more_dates_then_priority(tmp_path: Path) -> None:
    screen, _ = service(tmp_path)
    bundles = screen.bundle(
        [
            comp("2026 AI 챌린지", source=SourceName.WEVITY, source_id="1", deadline=date(2026, 10, 1)),
            comp("2026 AI 챌린지", source=SourceName.EVENTUS, source_id="2", start=date(2026, 9, 1), deadline=date(2026, 10, 1)),
            comp("2026 AI 챌린지", source=SourceName.DACON, source_id="3", deadline=date(2026, 10, 1)),
        ]
    )
    assert len(bundles) == 1
    assert bundles[0].representative.source is SourceName.EVENTUS


def test_known_by_source_id_and_member_records(tmp_path: Path) -> None:
    screen, record = service(tmp_path)
    member_a = comp("2026 AI 챌린지", source=SourceName.DACON, source_id="7", start=date(2026, 9, 1), deadline=date(2026, 10, 1))
    member_b = comp("2026 AI 챌린지 참가자 모집", source=SourceName.WEVITY, source_id="8", deadline=date(2026, 10, 1))
    bundles = screen.bundle([member_a, member_b])
    known = screen.build_known([], [history("2026 AI 챌린지", Result.DISCARD, source="DACON", source_id="7")])
    unknown, count = screen.split_known(bundles, known)
    assert unknown == [] and count == 1
    # 자기 기록이 없는 구성원만 견준 쪽의 결과(버림)로 적는다. 날짜는 대표의 것으로 채운다
    assert [(e.source, e.source_id, e.result, e.start_date) for e in record.entries] == [
        ("wevity", "8", Result.DISCARD, date(2026, 9, 1))
    ]


def test_notion_row_keeps_and_wins_over_discard(tmp_path: Path) -> None:
    screen, record = service(tmp_path)
    candidate = comp("2026 데이터 분석 경진대회", source_id="new", start=date(2026, 9, 1), deadline=date(2026, 10, 1))
    rows = [NotionRow("p", "2026 데이터 분석 경진대회", None, date(2026, 9, 1), date(2026, 10, 1))]
    known = screen.build_known(rows, [history("2026 데이터 분석 경진대회", Result.DISCARD, source_id="x", deadline=date(2026, 10, 1))])
    unknown, count = screen.split_known(screen.bundle([candidate]), known)
    assert count == 1
    assert [e.result for e in record.entries] == [Result.KEEP]


def test_name_only_match_is_known_but_not_recorded(tmp_path: Path) -> None:
    screen, record = service(tmp_path)
    candidate = comp("알고리즘 경진대회")  # 날짜 없음
    known = screen.build_known([], [history("알고리즘 경진대회", Result.KEEP, deadline=date(2026, 10, 1))])
    unknown, count = screen.split_known(screen.bundle([candidate]), known)
    assert count == 1 and record.entries == []


def test_last_year_record_does_not_block_this_year(tmp_path: Path) -> None:
    screen, _ = service(tmp_path)
    candidate = comp("Big Data 활용 대회", start=date(2026, 9, 10), deadline=date(2026, 9, 30))
    known = screen.build_known([], [history("Big Data 활용 대회", Result.KEEP, start=date(2025, 4, 24), deadline=date(2025, 5, 2))])
    unknown, count = screen.split_known(screen.bundle([candidate]), known)
    assert count == 0 and len(unknown) == 1


def test_ignore_discards_hides_discard_records(tmp_path: Path) -> None:
    screen, _ = service(tmp_path, ignore_discards=True, write=False)
    candidate = comp("사진 공모전", source=SourceName.WEVITY, source_id="5")
    known = screen.build_known([], [history("사진 공모전", Result.DISCARD, source="wevity", source_id="5")])
    unknown, count = screen.split_known(screen.bundle([candidate]), known)
    assert count == 0 and len(unknown) == 1


def test_judge_discards_are_recorded_and_keeps_returned(tmp_path: Path) -> None:
    judge = FakeJudge({"사진 공모전": Answer(False, "사진")})
    screen, record = service(tmp_path, judge)
    bundles = screen.bundle([comp("AI 해커톤", source_id="1"), comp("사진 공모전", source_id="2")])
    outcome = screen.judge(bundles)
    assert [b.representative.title for b in outcome.to_load] == ["AI 해커톤"]
    assert outcome.discarded == 1
    assert [(e.title, e.result) for e in record.entries] == [("사진 공모전", Result.DISCARD)]


def test_failures_at_most_half_are_kept(tmp_path: Path) -> None:
    judge = FakeJudge({"A": JudgeError("타임아웃")})
    screen, _ = service(tmp_path, judge)
    outcome = screen.judge(screen.bundle([comp("A", source_id="1"), comp("B 해커톤", source_id="2")]))
    assert outcome.judge_failed == 1 and outcome.deferred == 0
    assert len(outcome.to_load) == 2


def test_failures_over_half_are_deferred_except_due_today(tmp_path: Path) -> None:
    judge = FakeJudge({"A": JudgeError("x"), "B": JudgeError("x"), "C": JudgeError("x")})
    screen, record = service(tmp_path, judge)
    bundles = screen.bundle(
        [
            comp("A", source_id="1", deadline=BASE),
            comp("B", source_id="2", deadline=date(2026, 10, 1)),
            comp("C", source_id="3"),
            comp("D 해커톤", source_id="4"),
        ]
    )
    outcome = screen.judge(bundles)
    assert outcome.judge_failed == 3
    assert outcome.deferred == 2
    assert outcome.cause == "call_failed"
    assert sorted(b.representative.title for b in outcome.to_load) == ["A", "D 해커톤"]
    assert record.entries == []  # 미룬 묶음은 적지 않는다
    assert {b.outcome for b in bundles if b.representative.title in ("B", "C")} == {Outcome.DEFERRED}


def test_fatal_error_stops_asking(tmp_path: Path) -> None:
    judge = FakeJudge({f"대회 {i}": JudgeError("401", fatal=True) for i in range(10)})
    screen, _ = service(tmp_path, judge)
    screen._concurrency = 1
    outcome = screen.judge(screen.bundle([comp(f"대회 {i}", source_id=str(i), deadline=date(2026, 10, i + 1)) for i in range(10)]))
    assert len(judge.asked) == 1
    assert outcome.judge_failed == 10 and outcome.deferred == 10


def test_missing_key_defers_with_missing_key_cause(tmp_path: Path) -> None:
    screen, _ = service(tmp_path, judge=None)
    outcome = screen.judge(screen.bundle([comp("A", deadline=BASE, source_id="1"), comp("B", source_id="2")]))
    assert outcome.cause == "missing_key"
    assert [b.representative.title for b in outcome.to_load] == ["A"]


def test_bundle_deadline_is_the_latest_member_deadline(tmp_path: Path) -> None:
    # 오늘 마감인 구성원이 있어도 더 늦은 구성원이 있으면 오늘 마감으로 보지 않는다
    judge = FakeJudge({"2026 AI 챌린지": JudgeError("x")})
    screen, _ = service(tmp_path, judge)
    bundles = screen.bundle(
        [
            comp("2026 AI 챌린지", source=SourceName.WEVITY, source_id="1", deadline=BASE),
            comp("2026 AI 챌린지", source=SourceName.EVENTUS, source_id="2", start=date(2026, 9, 1), deadline=date(2026, 10, 3)),
        ]
    )
    assert bundles[0].deadline == date(2026, 10, 3)
    outcome = screen.judge(bundles)
    assert outcome.deferred == 1


@pytest.mark.parametrize("write", [False])
def test_preview_writes_nothing(tmp_path: Path, write: bool) -> None:
    judge = FakeJudge({"사진 공모전": Answer(False, "사진")})
    screen, record = service(tmp_path, judge, write=write)
    screen.judge(screen.bundle([comp("사진 공모전")]))
    assert record.appended_count == 0
    assert not (tmp_path / "append" / "processed.jsonl").exists()
