"""마무리 단계(CCR-INFRA-001 8.2)를 로컬 bare 저장소를 원격으로 삼아 돌려 본다."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import finish


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout


@pytest.fixture
def origin(tmp_path: Path) -> Path:
    remote = tmp_path / "origin.git"
    git(tmp_path, "init", "--bare", "-b", "main", str(remote))
    seed = tmp_path / "seed"
    git(tmp_path, "clone", str(remote), str(seed))
    (seed / "data").mkdir()
    (seed / "data" / "competitions.jsonl").write_text(entry("DACON", "1") + "\n", encoding="utf-8")
    (seed / "data" / "status.json").write_text(
        '{"DACON:1": {"status": "done"}}\n', encoding="utf-8"
    )
    (seed / "data" / "processed.jsonl").write_text(
        json.dumps({"source": "DACON", "source_id": "1", "result": "keep", "run_id": "0-1"}) + "\n",
        encoding="utf-8",
    )
    (seed / "README.md").write_text("x\n", encoding="utf-8")
    git(seed, "add", ".")
    git(seed, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-m", "seed")
    git(seed, "push", "origin", "HEAD:main")
    return remote


def entry(source: str, source_id: str, **extra: object) -> str:
    line = {
        "id": f"{source}:{source_id}",
        "source": source,
        "source_id": source_id,
        "title": f"대회 {source_id}",
        "link": f"https://example.com/{source}/{source_id}",
        "start_date": None,
        "deadline": "2026-10-20",
        "collected_on": "2026-09-27",
        "reason": "AI",
    }
    line.update(extra)
    return json.dumps(line, ensure_ascii=False)


def env_for(tmp_path: Path, run_id: str = "9-1") -> dict[str, str]:
    append = tmp_path / "append"
    append.mkdir(exist_ok=True)
    return {
        "RUN_ID": run_id,
        "RUN_STARTED_AT": "2026-09-26T23:50:00Z",
        "RUN_KIND": "schedule",
        "APPEND_DIR": str(append),
    }


def main_file(origin: Path, tmp_path: Path, name: str) -> list[dict]:
    check = tmp_path / f"check-{len(list(tmp_path.iterdir()))}"
    git(tmp_path, "clone", "--quiet", str(origin), str(check))
    path = check / "data" / name
    return (
        [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]
        if path.exists()
        else []
    )


def test_appends_list_history_and_run_line_with_keep_count(tmp_path: Path, origin: Path) -> None:
    env = env_for(tmp_path)
    append = Path(env["APPEND_DIR"])
    (append / "competitions.jsonl").write_text(
        entry("wevity", "2") + "\n" + entry("DACON", "1", title="이미 있는 식별자") + "\n",
        encoding="utf-8",
    )
    (append / "processed.jsonl").write_text(
        json.dumps(
            {
                "source": "wevity",
                "source_id": "2",
                "result": "keep",
                "run_id": "9-1",
                "title": "대회",
            },
            ensure_ascii=False,
        )
        + "\n"
        + json.dumps({"source": "wevity", "source_id": "3", "result": "discard", "run_id": "9-1"})
        + "\n",
        encoding="utf-8",
    )
    (append / "runs.jsonl").write_text(
        json.dumps(
            {
                "run_id": "9-1",
                "base_date": "2026-09-27",
                "kind": "schedule",
                "result": "success",
                "keep_count": None,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    outcome = finish.finish(env, finish.Git(tmp_path / "work", str(origin), None))
    assert outcome.code == 0
    listed = main_file(origin, tmp_path, "competitions.jsonl")
    assert [(e["id"], e["title"]) for e in listed] == [
        ("DACON:1", "대회 1"),
        ("wevity:2", "대회 2"),
    ]  # 있는 식별자는 건너뜀
    history = main_file(origin, tmp_path, "processed.jsonl")
    assert [h["source_id"] for h in history] == ["1", "2", "3"]
    runs = main_file(origin, tmp_path, "runs.jsonl")
    assert runs == [
        {
            "run_id": "9-1",
            "base_date": "2026-09-27",
            "kind": "schedule",
            "result": "success",
            "keep_count": 2,
        }
    ]
    log = git(origin, "log", "-1", "--format=%an <%ae>|%cn|%s", "main")
    assert log.startswith("ccr-batch <ccr-batch@localhost>|ccr-batch|실행 기록 2026-09-27 · 9-1")
    changed = git(origin, "show", "--name-only", "--format=", "main").split()
    assert changed == [
        "data/competitions.jsonl",
        "data/processed.jsonl",
        "data/runs.jsonl",
    ]  # 상태 파일은 건드리지 않는다
    assert main_file(origin, tmp_path, "status.json") == [{"DACON:1": {"status": "done"}}]


def test_missing_run_line_writes_an_aborted_line(tmp_path: Path, origin: Path) -> None:
    env = env_for(tmp_path)
    outcome = finish.finish(env, finish.Git(tmp_path / "work", str(origin), None))
    assert outcome.code == 1
    runs = main_file(origin, tmp_path, "runs.jsonl")
    assert runs == [
        {
            "run_id": "9-1",
            "base_date": "2026-09-27",
            "kind": "schedule",
            "result": "aborted",
            "keep_count": 1,
        }
    ]


def test_invalid_lines_are_dropped_and_the_step_fails(tmp_path: Path, origin: Path) -> None:
    env = env_for(tmp_path)
    append = Path(env["APPEND_DIR"])
    (append / "competitions.jsonl").write_text('{"id": "x:1", "source": "x"}\n', encoding="utf-8")
    (append / "processed.jsonl").write_text('{"source": "wevity"}\nnot json\n', encoding="utf-8")
    (append / "runs.jsonl").write_text(
        json.dumps(
            {"run_id": "9-1", "base_date": "2026-09-27", "kind": "schedule", "result": "success"}
        )
        + "\n",
        encoding="utf-8",
    )
    outcome = finish.finish(env, finish.Git(tmp_path / "work", str(origin), None))
    assert outcome.code == 1
    assert [h["source_id"] for h in main_file(origin, tmp_path, "processed.jsonl")] == ["1"]
    assert [e["id"] for e in main_file(origin, tmp_path, "competitions.jsonl")] == ["DACON:1"]


def test_already_pushed_run_is_not_added_twice(tmp_path: Path, origin: Path) -> None:
    env = env_for(tmp_path)
    (Path(env["APPEND_DIR"]) / "runs.jsonl").write_text(
        json.dumps(
            {"run_id": "9-1", "base_date": "2026-09-27", "kind": "schedule", "result": "success"}
        )
        + "\n",
        encoding="utf-8",
    )
    assert finish.finish(env, finish.Git(tmp_path / "work", str(origin), None)).code == 0
    again = finish.finish(env, finish.Git(tmp_path / "work2", str(origin), None))
    assert again.code == 0
    assert len(main_file(origin, tmp_path, "runs.jsonl")) == 1


def test_rebases_on_top_of_concurrent_commits(tmp_path: Path, origin: Path) -> None:
    env = env_for(tmp_path)
    (Path(env["APPEND_DIR"]) / "runs.jsonl").write_text(
        json.dumps(
            {"run_id": "9-1", "base_date": "2026-09-27", "kind": "schedule", "result": "success"}
        )
        + "\n",
        encoding="utf-8",
    )
    git_ops = finish.Git(tmp_path / "work", str(origin), None)
    real_push = git_ops.commit_and_push
    calls = {"n": 0}

    def racing_push(message: str) -> None:
        calls["n"] += 1
        if calls["n"] == 1:
            # 그사이 관리자가 버림 기록을 비우는 커밋을 올렸다
            other = tmp_path / "other"
            git(tmp_path, "clone", "--quiet", str(origin), str(other))
            (other / "data" / "processed.jsonl").write_text(
                json.dumps({"source": "DACON", "source_id": "1", "result": "keep", "run_id": "0-1"})
                + "\n"
                + json.dumps(
                    {"source": "DACON", "source_id": "5", "result": "keep", "run_id": "manual"}
                )
                + "\n",
                encoding="utf-8",
            )
            git(other, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-am", "manual")
            git(other, "push", "origin", "HEAD:main")
        real_push(message)

    git_ops.commit_and_push = racing_push  # type: ignore[method-assign]
    outcome = finish.finish(env, git_ops)
    assert outcome.code == 0 and calls["n"] == 2
    history = main_file(origin, tmp_path, "processed.jsonl")
    assert [h["source_id"] for h in history] == ["1", "5"]  # 관리자의 수정이 남는다
    assert main_file(origin, tmp_path, "runs.jsonl")[0]["keep_count"] == 2


def test_base_date_is_kst() -> None:
    assert finish.base_date_of("2026-09-26T23:50:00Z") == "2026-09-27"


def test_append_lines_adds_missing_newline(tmp_path: Path) -> None:
    path = tmp_path / "f.jsonl"
    path.write_text('{"a": 1}', encoding="utf-8")
    finish.append_lines(path, ['{"b": 2}'])
    assert path.read_text(encoding="utf-8") == '{"a": 1}\n{"b": 2}\n'


def test_first_run_on_an_empty_repository(tmp_path: Path) -> None:
    remote = tmp_path / "empty.git"
    git(tmp_path, "init", "--bare", "-b", "main", str(remote))
    seed = tmp_path / "seed-empty"
    git(tmp_path, "clone", str(remote), str(seed))
    (seed / "README.md").write_text("x\n", encoding="utf-8")
    git(seed, "add", ".")
    git(seed, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-m", "seed")
    git(seed, "push", "origin", "HEAD:main")
    env = env_for(tmp_path)
    (Path(env["APPEND_DIR"]) / "competitions.jsonl").write_text(
        entry("event-us", "7") + "\n", encoding="utf-8"
    )
    (Path(env["APPEND_DIR"]) / "runs.jsonl").write_text(
        json.dumps(
            {
                "run_id": "9-1",
                "base_date": "2026-09-27",
                "kind": "manual",
                "result": "failure",
                "failure_reason": "all_sources_failed",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    outcome = finish.finish(env, finish.Git(tmp_path / "work", str(remote), None))
    assert outcome.code == 0
    runs = main_file(remote, tmp_path, "runs.jsonl")
    assert runs[0]["keep_count"] == 0 and runs[0]["failure_reason"] == "all_sources_failed"
    assert [e["id"] for e in main_file(remote, tmp_path, "competitions.jsonl")] == ["event-us:7"]


def test_existing_ids_skips_broken_lines_and_missing_file(tmp_path: Path) -> None:
    assert finish.existing_ids(tmp_path / "none.jsonl") == set()
    path = tmp_path / "competitions.jsonl"
    path.write_text(entry("DACON", "1") + '\n{broken\n{"source": "x"}\n', encoding="utf-8")
    assert finish.existing_ids(path) == {"DACON:1"}


@pytest.mark.parametrize("missing", ["RUN_ID", "APPEND_DIR", "WORK_DIR", "REMOTE_URL"])
def test_main_needs_the_runner_variables(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    missing: str,
) -> None:
    env = {
        "RUN_ID": "local-20260926T235000",
        "APPEND_DIR": str(tmp_path / "append"),
        "WORK_DIR": str(tmp_path / "work"),
        "REMOTE_URL": str(tmp_path / "origin.git"),
    }
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv(missing)
    assert finish.main() == 1
    assert f"환경 변수 {missing}이 없다" in capsys.readouterr().out


def test_main_pushes_to_the_remote_from_the_runner(
    tmp_path: Path,
    origin: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """원격·작업 폴더·실행 종류는 실행기가 넘긴 이름에서 읽는다. 토큰은 어디에도 찍지 않는다."""
    env = env_for(tmp_path, run_id="local-20260926T235000")
    run = {
        "run_id": "local-20260926T235000",
        "base_date": "2026-09-27",
        "kind": "manual",
        "result": "success",
    }
    (Path(env["APPEND_DIR"]) / "runs.jsonl").write_text(json.dumps(run) + "\n", encoding="utf-8")
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("RUN_KIND", "manual")
    monkeypatch.setenv("WORK_DIR", str(tmp_path / "work"))
    monkeypatch.setenv("REMOTE_URL", str(origin))
    monkeypatch.setenv("PUSH_TOKEN", "tok-secret-value")
    assert finish.main() == 0
    assert (tmp_path / "work" / "finish-main" / ".git").is_dir()
    runs = main_file(origin, tmp_path, "runs.jsonl")
    assert [(r["run_id"], r["kind"]) for r in runs] == [("local-20260926T235000", "manual")]
    assert "tok-secret-value" not in capsys.readouterr().out
