from __future__ import annotations

import json
import subprocess
from datetime import date
from pathlib import Path

import pytest

from collector.domains.collect.models import FailureKind, SourceName, SourceResult
from collector.domains.record.crud import HistoryReadFailed, RecordCrud, export_main_state
from collector.domains.record.models import HistoryEntry, Result, RunLine, RunWarning, SourceLine, WarningKind
from collector.domains.record.service import RecordService
from tests.conftest import comp

BASE = date(2026, 9, 27)


def keep_line(source_id: str) -> str:
    return json.dumps({"source": "DACON", "source_id": source_id, "result": "keep", "run_id": "r0", "title": "t"})


def run_line(base: str, keep: int | None = None, **sources: int | None) -> str:
    line: dict = {"run_id": f"r-{base}", "base_date": base, "kind": "schedule", "result": "success"}
    if keep is not None:
        line["keep_count"] = keep
    line["sources"] = {
        name: {"collected": n or 0, "normalized": n or 0, "failure": None if n is not None else "connection"}
        for name, n in sources.items()
    }
    return json.dumps(line, ensure_ascii=False)


def make(tmp_path: Path, history: list[str] | None = None, runs: list[str] | None = None, *, write: bool = True):
    state = tmp_path / "data"
    state.mkdir()
    if history is not None:
        (state / "processed.jsonl").write_text("\n".join(history) + "\n", encoding="utf-8")
    if runs is not None:
        (state / "runs.jsonl").write_text("\n".join(runs) + "\n", encoding="utf-8")
    crud = RecordCrud(state, tmp_path / "append")
    return RecordService(crud, write=write, run_id="r1", base_date=BASE), tmp_path / "append"


def test_first_run_has_empty_history_and_no_comparison(tmp_path: Path) -> None:
    service, _ = make(tmp_path)
    state = service.load()
    assert state.history == [] and not state.history_exists and state.history_error is None
    assert service.history_shrank(state) is False


def test_unreadable_history_line_is_a_read_failure(tmp_path: Path) -> None:
    service, _ = make(tmp_path, history=[keep_line("1"), "{broken"])
    state = service.load()
    assert state.history_error is not None


def test_missing_required_field_is_a_read_failure(tmp_path: Path) -> None:
    service, _ = make(tmp_path, history=[json.dumps({"source": "DACON", "result": "keep", "run_id": "r"})])
    assert service.load().history_error is not None


def test_keep_count_shrink_is_detected(tmp_path: Path) -> None:
    service, _ = make(tmp_path, history=[keep_line("1")], runs=[run_line("2026-09-26", keep=2)])
    assert service.history_shrank(service.load())


def test_missing_history_with_recorded_count_counts_as_zero(tmp_path: Path) -> None:
    service, _ = make(tmp_path, runs=[run_line("2026-09-26", keep=1)])
    assert service.history_shrank(service.load())


def test_corrupt_run_lines_are_counted_and_skipped(tmp_path: Path) -> None:
    service, _ = make(tmp_path, runs=[run_line("2026-09-26", keep=0), "not json", '{"no": "id"}'])
    state = service.load()
    assert state.runs.corrupt == 2 and len(state.runs.lines) == 1


def test_append_writes_whole_file_each_time(tmp_path: Path) -> None:
    service, append = make(tmp_path)
    service.start()
    entry = HistoryEntry("DACON", "1", "https://dacon.io/x", "대회", date(2026, 9, 1), None, Result.KEEP)
    service.append([entry])
    service.append([HistoryEntry("wevity", "2", None, "대회", None, None, Result.DISCARD)])
    lines = [json.loads(x) for x in (append / "processed.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [(x["source_id"], x["result"], x["run_id"], x["base_date"]) for x in lines] == [
        ("1", "keep", "r1", "2026-09-27"),
        ("2", "discard", "r1", "2026-09-27"),
    ]
    assert lines[0]["start_date"] == "2026-09-01" and lines[0]["deadline"] is None
    assert not list(append.glob(".processed.jsonl.*"))  # 임시 파일이 남지 않는다


def test_preview_writes_nothing(tmp_path: Path) -> None:
    service, append = make(tmp_path, write=False)
    service.start()
    service.append([HistoryEntry("DACON", "1", None, "t", None, None, Result.KEEP)])
    service.write_run(RunLine("r1", BASE, "manual"))
    assert not append.exists()


def test_run_line_shape(tmp_path: Path) -> None:
    service, append = make(tmp_path)
    line = RunLine("r1", BASE, "schedule", sources={"DACON": SourceLine(3, 2, None)})
    line.warnings.append(RunWarning(WarningKind.JUDGE_DEFERRED, cause="missing_key"))
    service.write_run(line)
    data = json.loads((append / "runs.jsonl").read_text(encoding="utf-8"))
    assert data["keep_count"] is None  # 마무리 단계가 채운다
    assert data["sources"] == {"DACON": {"collected": 3, "normalized": 2, "failure": None}}
    assert data["warnings"] == [{"kind": "judge_deferred", "cause": "missing_key"}]
    assert set(data) == {
        "run_id", "base_date", "kind", "result", "failure_reason", "keep_count", "sources", "dropped",
        "loaded", "judge_failed", "deferred", "create_failed", "warnings", "duration_s",
    }


def zero(source: SourceName = SourceName.DACON) -> list[SourceResult]:
    return [SourceResult(source=source, competitions=[], collected=0, dropped=0)]


def test_zero_count_after_three_days_of_counts(tmp_path: Path) -> None:
    runs = [run_line(f"2026-09-{d}", DACON=5) for d in (22, 23, 24)] + [run_line("2026-09-26", DACON=0)]
    service, _ = make(tmp_path, runs=runs)
    warnings = service.zero_count_warnings(zero(), service.load(), days=3)
    assert warnings == [RunWarning(WarningKind.ZERO_COUNT, source="DACON", last_nonzero=date(2026, 9, 24))]


def test_zero_count_needs_n_consecutive_days(tmp_path: Path) -> None:
    runs = [run_line("2026-09-23", DACON=0), run_line("2026-09-24", DACON=5), run_line("2026-09-25", DACON=5)]
    service, _ = make(tmp_path, runs=runs)
    assert service.zero_count_warnings(zero(), service.load(), days=3) == []


def test_zero_count_skips_failed_and_missing_days_and_merges_same_day(tmp_path: Path) -> None:
    runs = [
        run_line("2026-09-21", DACON=4),
        run_line("2026-09-22", DACON=0),
        run_line("2026-09-22", DACON=2),  # 같은 날 하나라도 건수를 냈으면 건수를 낸 날
        run_line("2026-09-24", DACON=None),  # 실패한 줄은 건너뛴다
        run_line("2026-09-25", DACON=6),
    ]
    service, _ = make(tmp_path, runs=runs)
    warnings = service.zero_count_warnings(zero(), service.load(), days=3)
    assert warnings[0].last_nonzero == date(2026, 9, 25)


def test_no_zero_warning_on_first_run_or_when_source_failed(tmp_path: Path) -> None:
    service, _ = make(tmp_path)
    assert service.zero_count_warnings(zero(), service.load(), days=3) == []
    failed = [SourceResult.failed(SourceName.DACON, FailureKind.CONNECTION, "x")]
    assert service.zero_count_warnings(failed, service.load(), days=3) == []


def test_state_dir_and_append_dir_must_differ(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        RecordCrud(tmp_path, tmp_path)


def git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def test_export_main_state_reads_origin_main(tmp_path: Path) -> None:
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "--bare", "-b", "main", str(origin))
    work = tmp_path / "work"
    git(tmp_path, "clone", str(origin), str(work))
    (work / "data").mkdir()
    (work / "data" / "processed.jsonl").write_text(keep_line("1") + "\n", encoding="utf-8")
    git(work, "add", ".")
    git(work, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-m", "state")
    git(work, "push", "origin", "HEAD:main")
    # 브랜치의 작업 트리에 오래된 사본이 있어도 main 최신 판을 읽는다
    (work / "data" / "processed.jsonl").write_text("", encoding="utf-8")
    dest = export_main_state(work, tmp_path / "exported")
    assert (dest / "processed.jsonl").read_text(encoding="utf-8").strip() == keep_line("1")
    assert not (dest / "runs.jsonl").exists()


def test_export_without_remote_is_a_read_failure(tmp_path: Path) -> None:
    git(tmp_path, "init", "-b", "main", str(tmp_path / "lonely"))
    with pytest.raises(HistoryReadFailed):
        export_main_state(tmp_path / "lonely", tmp_path / "out")
