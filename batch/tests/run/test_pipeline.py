"""하루치 실행(CCR-UC-001 UC-A1)을 가짜 소스 · 판별과 실제 파일 경계로 끝까지 돌려 본다."""

from __future__ import annotations

import json
import threading
from datetime import date
from pathlib import Path

import pytest

from collector.core.settings import RunContext, Settings
from collector.domains.collect.models import FailureKind, SourceName, SourceResult
from collector.domains.list.crud import ListCrud
from collector.domains.list.service import ListService
from collector.domains.record.crud import RecordCrud
from collector.domains.record.service import RecordService
from collector.domains.screen.ports import Answer
from collector.domains.screen.service import ScreenService
from collector.infra.http import Stopped
from collector.run.pipeline import Pipeline, Services
from tests.conftest import comp
from tests.domains.screen.test_service import FakeJudge

BASE = date(2026, 9, 27)


def context(tmp_path: Path, *, write: bool = True) -> RunContext:
    env = {
        "BATCH_RUNNER": "laptop",
        "DRY_RUN": "false" if write else "true",
        "RUN_STARTED_AT": "2026-09-26T23:50:00Z",
        "RUN_ID": "77-1",
        "RUN_KIND": "schedule",
        "STATE_DIR": str(tmp_path / "data"),
        "APPEND_DIR": str(tmp_path / "append"),
    }
    return RunContext.from_env(env)


def results(*items, failed: tuple[SourceName, ...] = ()) -> list[SourceResult]:
    out = [
        SourceResult(
            source=SourceName.EVENTUS, competitions=list(items), collected=len(items) + 1, dropped=1
        )
    ]
    out += [SourceResult.failed(name, FailureKind.CONNECTION, "timeout") for name in failed]
    return out


def entry_line(source: str, source_id: str, title: str, link: str) -> dict:
    return {
        "id": f"{source}:{source_id}",
        "source": source,
        "source_id": source_id,
        "title": title,
        "link": link,
        "start_date": None,
        "deadline": "2026-10-20",
        "collected_on": "2026-09-20",
        "reason": "AI",
    }


def write_lines(path: Path, lines: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in lines), encoding="utf-8"
    )


def services_for(ctx: RunContext, collected, judge, stop: threading.Event) -> Services:
    listing = ListService(ListCrud(ctx.state_dir, ctx.append_dir), write=ctx.write)
    record = RecordService(
        RecordCrud(ctx.state_dir, ctx.append_dir),
        write=ctx.write,
        run_id=ctx.run_id,
        base_date=ctx.base_date,
    )
    screen = ScreenService(
        record,
        base_date=ctx.base_date,
        ignore_discards=False,
        judge=judge,
        concurrency=2,
        stop=stop,
    )
    collect = collected if callable(collected) else (lambda base: collected)
    return Services(collect=collect, list=listing, record=record, screen=screen)


def read_appends(tmp_path: Path, name: str) -> list[dict]:
    path = tmp_path / "append" / name
    return (
        [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]
        if path.exists()
        else []
    )


def run(
    tmp_path: Path,
    collected,
    judge=None,
    *,
    write: bool = True,
    listed: list[dict] | None = None,
    history: list[dict] | None = None,
    runs: list[dict] | None = None,
):
    (tmp_path / "data").mkdir(exist_ok=True)
    if listed is not None:
        write_lines(tmp_path / "data" / "competitions.jsonl", listed)
    if history is not None:
        write_lines(tmp_path / "data" / "processed.jsonl", history)
    if runs is not None:
        write_lines(tmp_path / "data" / "runs.jsonl", runs)
    ctx = context(tmp_path, write=write)
    stop = threading.Event()
    line = Pipeline(ctx, Settings.load({}), services_for(ctx, collected, judge, stop), stop).run()
    return (
        line,
        read_appends(tmp_path, "competitions.jsonl"),
        read_appends(tmp_path, "processed.jsonl"),
        read_appends(tmp_path, "runs.jsonl"),
    )


def test_happy_path_loads_keeps_and_records_discards(tmp_path: Path) -> None:
    listed = [entry_line("DACON", "k", "이미 있는 해커톤", "https://example.com/known")]
    judge = FakeJudge(
        {"사진 공모전": Answer(False, "사진"), "2026 AI 해커톤": Answer(True, "AI 해커톤")}
    )
    collected = results(
        comp("2026 AI 해커톤", source_id="1", start=date(2026, 9, 1), deadline=date(2026, 10, 1)),
        comp("사진 공모전", source_id="2", deadline=date(2026, 10, 2)),
        comp("이미 있는 해커톤", source_id="3", link="https://example.com/known"),
        comp("어제 마감한 대회", source_id="4", deadline=date(2026, 9, 26)),
    )
    line, added, history, run_lines = run(tmp_path, collected, judge, listed=listed)
    assert line.result.value == "success"
    assert [(a["id"], a["title"], a["collected_on"], a["reason"]) for a in added] == [
        ("event-us:1", "2026 AI 해커톤", "2026-09-27", "AI 해커톤")
    ]
    assert line.dropped == {"normalize": 1, "expired": 1, "known": 1, "discarded": 1}
    assert line.loaded == 1
    assert {(h["source_id"], h["result"]) for h in history} == {
        ("1", "keep"),
        ("2", "discard"),
        ("3", "keep"),
    }
    assert run_lines[0]["run_id"] == "77-1" and run_lines[0]["base_date"] == "2026-09-27"
    assert run_lines[0]["sources"]["event-us"] == {"collected": 5, "normalized": 4, "failure": None}
    assert "create_failed" not in run_lines[0]


def test_preview_writes_nothing(tmp_path: Path) -> None:
    line, added, history, run_lines = run(
        tmp_path, results(comp("2026 AI 해커톤")), FakeJudge({}), write=False
    )
    assert line.loaded == 1  # 넣었을 대회는 센다
    assert added == [] and history == [] and run_lines == []
    assert not (tmp_path / "append").exists()


def test_runs_without_any_secret(tmp_path: Path) -> None:
    # 반드시 있어야 하는 시크릿은 없다(UC-A1 1d1). 키가 없으면 판별만 미룬다
    collected = results(
        comp("오늘 마감 대회", source_id="1", deadline=BASE),
        comp("다른 대회", source_id="2", deadline=date(2026, 10, 9)),
    )
    line, added, history, _ = run(tmp_path, collected, judge=None)
    assert line.result.value == "success"
    assert [a["id"] for a in added] == ["event-us:1"] and added[0]["reason"] == ""
    assert line.deferred == 1 and line.judge_failed == 2
    assert [w.to_dict() for w in line.warnings] == [
        {"kind": "judge_deferred", "cause": "missing_key"}
    ]
    assert [h["source_id"] for h in history] == ["1"]


def test_all_sources_failed(tmp_path: Path) -> None:
    collected = [SourceResult.failed(name, FailureKind.CONNECTION, "x") for name in SourceName]
    line, _, _, _ = run(tmp_path, collected)
    assert line.failure_reason.value == "all_sources_failed"


def test_unreadable_list_file_stops_before_judging(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "competitions.jsonl").write_text("{broken\n", encoding="utf-8")
    judge = FakeJudge({})
    line, added, history, run_lines = run(tmp_path, results(comp("2026 AI 해커톤")), judge)
    assert line.failure_reason.value == "list_read_failed"
    assert judge.asked == [] and added == [] and history == []
    assert run_lines[0]["failure_reason"] == "list_read_failed"


def test_unreadable_history_stops_before_judging(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "processed.jsonl").write_text("{broken\n", encoding="utf-8")
    judge = FakeJudge({})
    line, _, _, _ = run(tmp_path, results(comp("2026 AI 해커톤")), judge)
    assert line.failure_reason.value == "history_read_failed"
    assert judge.asked == []


def test_list_read_failure_comes_before_history_failure(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "competitions.jsonl").write_text("{broken\n", encoding="utf-8")
    (tmp_path / "data" / "processed.jsonl").write_text("{broken\n", encoding="utf-8")
    line, _, _, _ = run(tmp_path, results(comp("2026 AI 해커톤")), FakeJudge({}))
    assert line.failure_reason.value == "list_read_failed"


def test_history_shrank(tmp_path: Path) -> None:
    runs = [
        {
            "run_id": "1-1",
            "base_date": "2026-09-26",
            "kind": "schedule",
            "result": "success",
            "keep_count": 3,
        }
    ]
    line, _, _, _ = run(tmp_path, results(comp("2026 AI 해커톤")), FakeJudge({}), runs=runs)
    assert line.failure_reason.value == "history_shrank"


def test_deleted_entry_is_still_known_and_not_readded(tmp_path: Path) -> None:
    # 참가자가 페이지에서 지운 대회도 목록 파일에 남아 있어 다시 들어오지 않는다(UC-A2 5a)
    listed = [entry_line("event-us", "9", "지운 대회", "https://example.com/event-us/9")]
    judge = FakeJudge({})
    line, added, history, _ = run(
        tmp_path,
        results(comp("지운 대회", source_id="9", deadline=date(2026, 10, 20))),
        judge,
        listed=listed,
    )
    assert judge.asked == [] and added == [] and line.dropped["known"] == 1
    assert [(h["source_id"], h["result"]) for h in history] == [("9", "keep")]


def test_existing_id_gets_history_only(tmp_path: Path) -> None:
    # 판정을 지나쳐 온 같은 식별자는 항목을 더하지 않고 처리 이력에만 적는다(UC-S6 2a)
    listed = [entry_line("event-us", "1", "다른 이름의 옛 항목", "https://other.example/1")]
    ctx = context(tmp_path)
    stop = threading.Event()
    (tmp_path / "data").mkdir()
    write_lines(tmp_path / "data" / "competitions.jsonl", listed)
    services = services_for(
        ctx,
        results(comp("2027 신규 대회", source_id="1", deadline=date(2027, 3, 1))),
        FakeJudge({}),
        stop,
    )
    services.screen.split_known = lambda bundles, known: (bundles, 0)  # type: ignore[method-assign]
    line = Pipeline(ctx, Settings.load({}), services, stop).run()
    assert line.loaded == 0 and read_appends(tmp_path, "competitions.jsonl") == []
    assert [(h["source_id"], h["result"]) for h in read_appends(tmp_path, "processed.jsonl")] == [
        ("1", "keep")
    ]


def test_failed_source_is_marked_and_run_continues(tmp_path: Path) -> None:
    line, _, _, _ = run(
        tmp_path, results(comp("AI 해커톤"), failed=(SourceName.WEVITY,)), FakeJudge({})
    )
    assert line.result.value == "success"
    assert line.sources["wevity"].failure == "connection"


def test_stop_signal_leaves_no_run_line(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    ctx = context(tmp_path)
    stop = threading.Event()

    def collect(base):
        stop.set()
        return results(comp("AI 해커톤"))

    with pytest.raises(Stopped):
        Pipeline(ctx, Settings.load({}), services_for(ctx, collect, None, stop), stop).run()
    assert (tmp_path / "append" / "runs.jsonl").read_text(encoding="utf-8") == ""
