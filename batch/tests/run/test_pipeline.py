"""하루치 실행(CCR-UC-001 UC-A1)을 가짜 소스 · 노션 · 판별로 끝까지 돌려 본다."""

from __future__ import annotations

import json
import threading
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from collector.core.settings import RunContext, Settings
from collector.domains.collect.models import FailureKind, SourceName, SourceResult
from collector.domains.notion.models import CreateOutcome, NotionReadFailed, NotionRow, SchemaCheck
from collector.domains.record.crud import RecordCrud
from collector.domains.record.service import RecordService
from collector.domains.screen.ports import Answer
from collector.domains.screen.service import ScreenService
from collector.infra.http import Stopped
from collector.run.pipeline import Pipeline, Services
from tests.conftest import comp
from tests.domains.screen.test_service import FakeJudge

BASE = date(2026, 9, 27)


class FakeNotion:
    def __init__(self, rows=None, *, read_error: bool = False, schema_ok: bool = True, fail_titles=()) -> None:
        self.rows = rows or []
        self.read_error = read_error
        self.schema_ok = schema_ok
        self.fail_titles = set(fail_titles)
        self.created: list[str] = []

    def read_rows(self) -> list[NotionRow]:
        if self.read_error:
            raise NotionReadFailed("503")
        return self.rows

    def check_columns(self) -> SchemaCheck:
        return SchemaCheck(ok=self.schema_ok, problem=None if self.schema_ok else "컬럼 `링크`이 없다")

    def create_row(self, competition, base_date) -> CreateOutcome:
        if competition.title in self.fail_titles:
            return CreateOutcome(created=False, error="400 validation_error")
        self.created.append(competition.title)
        return CreateOutcome(created=True, page_id="p")


def context(tmp_path: Path, *, write: bool = True) -> RunContext:
    env = {
        "GITHUB_ACTIONS": "true",
        "DRY_RUN": "false" if write else "true",
        "RUN_STARTED_AT": "2026-09-26T23:50:00Z",
        "RUN_ID": "77-1",
        "GITHUB_EVENT_NAME": "schedule",
        "GITHUB_REF": "refs/heads/main",
        "STATE_DIR": str(tmp_path / "data"),
        "APPEND_DIR": str(tmp_path / "append"),
    }
    return RunContext.from_env(env)


def results(*items, failed: tuple[SourceName, ...] = ()) -> list[SourceResult]:
    out = [SourceResult(source=SourceName.EVENTUS, competitions=list(items), collected=len(items) + 1, dropped=1)]
    out += [SourceResult.failed(name, FailureKind.CONNECTION, "timeout") for name in failed]
    return out


def run(tmp_path: Path, collected, notion, judge=None, *, write: bool = True, history: list[dict] | None = None, runs: list[dict] | None = None):
    (tmp_path / "data").mkdir(exist_ok=True)
    if history is not None:
        (tmp_path / "data" / "processed.jsonl").write_text("".join(json.dumps(h) + "\n" for h in history), encoding="utf-8")
    if runs is not None:
        (tmp_path / "data" / "runs.jsonl").write_text("".join(json.dumps(r) + "\n" for r in runs), encoding="utf-8")
    ctx = context(tmp_path, write=write)
    stop = threading.Event()
    record = RecordService(RecordCrud(ctx.state_dir, ctx.append_dir), write=ctx.write, run_id=ctx.run_id, base_date=ctx.base_date)
    screen = ScreenService(record, base_date=ctx.base_date, ignore_discards=False, judge=judge, concurrency=2, stop=stop)
    collect = collected if callable(collected) else (lambda base: collected)
    services = Services(collect=collect, notion=notion, record=record, screen=screen)
    line = Pipeline(ctx, Settings.load({}), services, stop).run()
    appended = tmp_path / "append" / "processed.jsonl"
    history_lines = [json.loads(x) for x in appended.read_text(encoding="utf-8").splitlines()] if appended.exists() else []
    run_file = tmp_path / "append" / "runs.jsonl"
    run_lines = [json.loads(x) for x in run_file.read_text(encoding="utf-8").splitlines()] if run_file.exists() else []
    return line, history_lines, run_lines


def test_happy_path_loads_keeps_and_records_discards(tmp_path: Path) -> None:
    notion = FakeNotion(rows=[NotionRow("p", "이미 있는 해커톤", "https://example.com/known", None, None)])
    judge = FakeJudge({"사진 공모전": Answer(False, "사진")})
    collected = results(
        comp("2026 AI 해커톤", source_id="1", start=date(2026, 9, 1), deadline=date(2026, 10, 1)),
        comp("사진 공모전", source_id="2", deadline=date(2026, 10, 2)),
        comp("이미 있는 해커톤", source_id="3", link="https://example.com/known"),
        comp("어제 마감한 대회", source_id="4", deadline=date(2026, 9, 26)),
    )
    line, history, run_lines = run(tmp_path, collected, notion, judge)
    assert line.result.value == "success"
    assert notion.created == ["2026 AI 해커톤"]
    assert line.dropped == {"normalize": 1, "expired": 1, "known": 1, "discarded": 1}
    assert line.loaded == 1
    assert {(h["source_id"], h["result"]) for h in history} == {("1", "keep"), ("2", "discard"), ("3", "keep")}
    assert run_lines[0]["run_id"] == "77-1" and run_lines[0]["base_date"] == "2026-09-27"
    assert run_lines[0]["sources"]["event-us"] == {"collected": 5, "normalized": 4, "failure": None}


def test_preview_writes_nothing_and_creates_no_rows(tmp_path: Path) -> None:
    notion = FakeNotion()
    line, history, run_lines = run(tmp_path, results(comp("2026 AI 해커톤")), notion, FakeJudge({}), write=False)
    assert notion.created == [] and history == [] and run_lines == []
    assert not (tmp_path / "append").exists()


def test_missing_notion_config_fails_before_collecting(tmp_path: Path) -> None:
    def collect(base):
        raise AssertionError("수집하지 않는다")

    line, _, run_lines = run(tmp_path, collect, None)
    assert (line.result.value, line.failure_reason.value) == ("failure", "missing_config")
    assert run_lines[0]["sources"] == {}


def test_all_sources_failed(tmp_path: Path) -> None:
    collected = [SourceResult.failed(name, FailureKind.CONNECTION, "x") for name in SourceName]
    line, _, _ = run(tmp_path, collected, FakeNotion())
    assert line.failure_reason.value == "all_sources_failed"


def test_notion_read_failure_stops_before_judging(tmp_path: Path) -> None:
    judge = FakeJudge({})
    line, history, _ = run(tmp_path, results(comp("2026 AI 해커톤")), FakeNotion(read_error=True), judge)
    assert line.failure_reason.value == "notion_read_failed"
    assert judge.asked == [] and history == []


def test_unreadable_history_stops_before_judging(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "processed.jsonl").write_text("{broken\n", encoding="utf-8")
    judge = FakeJudge({})
    line, _, _ = run(tmp_path, results(comp("2026 AI 해커톤")), FakeNotion(), judge)
    assert line.failure_reason.value == "history_read_failed"
    assert judge.asked == []


def test_history_shrank(tmp_path: Path) -> None:
    runs = [{"run_id": "1-1", "base_date": "2026-09-26", "kind": "schedule", "result": "success", "keep_count": 3}]
    line, _, _ = run(tmp_path, results(comp("2026 AI 해커톤")), FakeNotion(), FakeJudge({}), runs=runs)
    assert line.failure_reason.value == "history_shrank"


def test_due_today_row_failure_fails_the_run(tmp_path: Path) -> None:
    notion = FakeNotion(fail_titles={"오늘 마감 해커톤"})
    collected = results(comp("오늘 마감 해커톤", source_id="1", deadline=BASE), comp("다음 달 AI 대회", source_id="2", deadline=date(2026, 10, 30)))
    line, history, _ = run(tmp_path, collected, notion, FakeJudge({}))
    assert line.failure_reason.value == "due_today_not_loaded"
    assert line.create_failed == 1 and line.loaded == 1
    kinds = [w.kind.value for w in line.warnings]
    assert "due_today_not_loaded" in kinds and "create_all_failed" not in kinds
    assert [h["source_id"] for h in history] == ["2"]


def test_schema_problem_counts_every_bundle_as_create_failure(tmp_path: Path) -> None:
    notion = FakeNotion(schema_ok=False)
    line, history, _ = run(tmp_path, results(comp("AI 해커톤", deadline=date(2026, 10, 3))), notion, FakeJudge({}))
    assert line.result.value == "success"
    assert line.create_failed == 1 and notion.created == []
    assert [w.kind.value for w in line.warnings] == ["create_all_failed"]
    assert history == []


def test_missing_openai_key_defers_and_warns(tmp_path: Path) -> None:
    collected = results(comp("오늘 마감 대회", source_id="1", deadline=BASE), comp("다른 대회", source_id="2", deadline=date(2026, 10, 9)))
    notion = FakeNotion()
    line, history, _ = run(tmp_path, collected, notion, judge=None)
    assert line.result.value == "success"
    assert notion.created == ["오늘 마감 대회"]
    assert line.deferred == 1 and line.judge_failed == 2
    assert [w.to_dict() for w in line.warnings] == [{"kind": "judge_deferred", "cause": "missing_key"}]
    assert [h["source_id"] for h in history] == ["1"]


def test_failed_source_is_marked_and_run_continues(tmp_path: Path) -> None:
    line, _, _ = run(tmp_path, results(comp("AI 해커톤"), failed=(SourceName.WEVITY,)), FakeNotion(), FakeJudge({}))
    assert line.result.value == "success"
    assert line.sources["wevity"].failure == "connection"


def test_stop_signal_leaves_no_run_line(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    ctx = context(tmp_path)
    stop = threading.Event()
    record = RecordService(RecordCrud(ctx.state_dir, ctx.append_dir), write=True, run_id=ctx.run_id, base_date=ctx.base_date)
    screen = ScreenService(record, base_date=BASE, ignore_discards=False, judge=None, concurrency=1, stop=stop)

    def collect(base):
        stop.set()
        return results(comp("AI 해커톤"))

    with pytest.raises(Stopped):
        Pipeline(ctx, Settings.load({}), Services(collect, FakeNotion(), record, screen), stop).run()
    assert (tmp_path / "append" / "runs.jsonl").read_text(encoding="utf-8") == ""
