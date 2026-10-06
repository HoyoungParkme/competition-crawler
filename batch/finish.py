"""마무리 단계. 이번 실행의 추가분을 기본 브랜치 최신 판 위에 다시 얹어 한 커밋으로 올린다.

CCR-UC-001 UC-A1 9 · *a2 · CCR-INFRA-001 8.2. 노트북의 git과 파이썬 표준 라이브러리만 쓰고,
배치 패키지를 불러오지 않는다. 세 파일(목록 · 처리 이력 · 실행 요약)의 형식은 ERD(CCR-DOM-003)를
따라 여기서 따로 안다. 페이지가 쓰는 `data/status.json`은 읽지도 스테이징하지도 않는다.
토큰은 받기와 push 명령에만 명령 줄 설정으로 주고, 명령을 그대로 찍지 않는다.
"""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

LIST = "data/competitions.jsonl"
HISTORY = "data/processed.jsonl"
RUNS = "data/runs.jsonl"
LIST_REQUIRED = ("id", "source", "source_id", "title", "link", "collected_on")
HISTORY_REQUIRED = ("source", "source_id", "result", "run_id")
RUN_REQUIRED = ("run_id", "base_date", "kind", "result")
ATTEMPTS = 5
GIT_TIMEOUT = 60
KST = timezone(timedelta(hours=9))
BOT_NAME = "ccr-batch"
BOT_EMAIL = "ccr-batch@localhost"


class GitError(Exception):
    pass


@dataclass
class Additions:
    listed: list[str] = field(default_factory=list)  # 목록에 붙일 줄. 원문 그대로
    history: list[str] = field(default_factory=list)  # 붙일 줄. 원문 그대로
    run: dict | None = None  # 배치가 쓴 이 실행의 줄
    rejected: int = 0  # 형식이 맞지 않아 붙이지 않은 줄


def _valid(line: str, required: tuple[str, ...]) -> dict | None:
    try:
        data = json.loads(line)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    if any(data.get(name) in (None, "") for name in required):
        return None
    return data


def _read_valid(path: Path, required: tuple[str, ...], label: str, out: Additions) -> list[str]:
    lines: list[str] = []
    if not path.is_file():
        return lines
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw.strip():
            continue
        if _valid(raw, required) is None:
            print(f"{label} 추가분에서 형식이 맞지 않는 줄을 뺀다: {raw}")
            out.rejected += 1
            continue
        lines.append(raw.strip())
    return lines


def read_additions(append_dir: Path, run_id: str) -> Additions:
    """CCR-MS-001#finish.read_additions"""
    out = Additions()
    out.listed = _read_valid(append_dir / "competitions.jsonl", LIST_REQUIRED, "목록", out)
    out.history = _read_valid(append_dir / "processed.jsonl", HISTORY_REQUIRED, "처리 이력", out)
    runs = append_dir / "runs.jsonl"
    if runs.is_file():
        for raw in runs.read_text(encoding="utf-8", errors="replace").splitlines():
            if not raw.strip():
                continue
            data = _valid(raw, RUN_REQUIRED)
            if data is None or data.get("run_id") != run_id:
                print(f"실행 요약 추가분에서 형식이 맞지 않는 줄을 뺀다: {raw}")
                out.rejected += 1
                continue
            out.run = data
    return out


def base_date_of(started_at: str | None) -> str:
    """CCR-MS-001#finish.base_date_of"""
    if started_at:
        moment = datetime.fromisoformat(started_at.strip().replace("Z", "+00:00"))
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=UTC)
    else:
        moment = datetime.now(UTC)
    return moment.astimezone(KST).date().isoformat()


def _lines(path: Path) -> list[str]:
    if not path.is_file():
        return []
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def has_run(runs_path: Path, run_id: str) -> bool:
    """CCR-MS-001#finish.has_run"""
    for raw in _lines(runs_path):
        try:
            data = json.loads(raw)
        except ValueError:
            continue  # 읽히지 않는 줄은 건너뛴다(CCR-UC-001 UC-S7 2c)
        if isinstance(data, dict) and data.get("run_id") == run_id:
            return True
    return False


def count_keep(history_path: Path) -> int:
    """CCR-MS-001#finish.count_keep"""
    count = 0
    for raw in _lines(history_path):
        try:
            data = json.loads(raw)
        except ValueError:
            continue
        if isinstance(data, dict) and data.get("result") == "keep":
            count += 1
    return count


def existing_ids(list_path: Path) -> set[str]:
    """CCR-MS-001#finish.existing_ids"""
    ids: set[str] = set()
    for raw in _lines(list_path):
        try:
            data = json.loads(raw)
        except ValueError:
            continue
        if isinstance(data, dict) and data.get("id"):
            ids.add(str(data["id"]))
    return ids


def append_lines(path: Path, lines: list[str]) -> None:
    """CCR-MS-001#finish.append_lines"""
    if not lines:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_bytes() if path.is_file() else b""
    prefix = b"\n" if existing and not existing.endswith(b"\n") else b""
    with path.open("ab") as handle:
        handle.write(prefix + "".join(line + "\n" for line in lines).encode("utf-8"))


class Git:
    def __init__(self, workdir: Path, remote: str, token: str | None) -> None:
        self.workdir = workdir
        self.remote = remote
        self._auth: list[str] = []
        if token:
            basic = base64.b64encode(f"x-access-token:{token}".encode()).decode()
            self._auth = ["-c", f"http.extraheader=AUTHORIZATION: basic {basic}"]
        self._slow = ["-c", "http.lowSpeedLimit=1000", "-c", "http.lowSpeedTime=20"]

    def _run(self, args: list[str], *, auth: bool = False, cwd: Path | None = None) -> str:
        command = ["git", *self._slow, *(self._auth if auth else []), *args]
        try:
            done = subprocess.run(
                command,
                cwd=cwd or self.workdir,
                capture_output=True,
                text=True,
                timeout=GIT_TIMEOUT,
            )
        except subprocess.TimeoutExpired as exc:
            raise GitError(f"git {args[0]}이 {GIT_TIMEOUT}초 안에 끝나지 않았다") from exc
        if done.returncode != 0:
            # 명령 줄에는 토큰이 있으므로 찍지 않는다. git의 오류 문구만 남긴다
            raise GitError(f"git {args[0]} 실패: {done.stderr.strip()[-500:]}")
        return done.stdout

    def fresh_main(self) -> None:
        """CCR-MS-001#Git.fresh_main"""
        if (self.workdir / ".git").is_dir():
            self._run(["fetch", "--depth=1", "--no-tags", "origin", "main"], auth=True)
            self._run(["reset", "--hard", "FETCH_HEAD"])
            self._run(["clean", "-fdx"])
            return
        if self.workdir.exists():
            shutil.rmtree(self.workdir)
        self.workdir.parent.mkdir(parents=True, exist_ok=True)
        self._run(
            ["clone", "--depth=1", "--branch", "main", "--no-tags", self.remote, str(self.workdir)],
            auth=True,
            cwd=self.workdir.parent,
        )

    def commit_and_push(self, message: str) -> None:
        """CCR-MS-001#Git.commit_and_push"""
        # 첫 실행에는 목록 파일과 처리 이력 파일이 아직 없을 수 있다. 있는 경로만 스테이징한다
        paths = [path for path in (LIST, HISTORY, RUNS) if (self.workdir / path).exists()]
        self._run(["add", "--", *paths])
        self._run(
            [
                "-c",
                f"user.name={BOT_NAME}",
                "-c",
                f"user.email={BOT_EMAIL}",
                "commit",
                "--quiet",
                "-m",
                message,
            ]
        )
        self._run(["push", "origin", "HEAD:refs/heads/main"], auth=True)


@dataclass
class Outcome:
    code: int
    note: str


def _list_lines(list_path: Path, additions: Additions) -> list[str]:
    known = existing_ids(list_path)
    lines: list[str] = []
    for raw in additions.listed:
        entry_id = json.loads(raw).get("id")
        if entry_id in known:
            print(f"목록에 이미 있는 식별자라 건너뛴다: {entry_id}")
            continue
        known.add(entry_id)
        lines.append(raw)
    return lines


def finish(env: Mapping[str, str], git: Git) -> Outcome:
    """CCR-MS-001#finish.finish"""
    run_id = env["RUN_ID"]
    base_date = base_date_of(env.get("RUN_STARTED_AT"))
    kind = "schedule" if env.get("RUN_KIND") == "schedule" else "manual"
    additions = read_additions(Path(env["APPEND_DIR"]), run_id)
    failed = additions.rejected > 0
    aborted = additions.run is None
    if aborted:
        print("배치가 이 실행의 줄을 남기지 않았다. 결과 중단의 줄을 쓴다")
        failed = True
    last_error = ""
    pushed_before = False
    for attempt in range(1, ATTEMPTS + 1):
        try:
            git.fresh_main()
            runs_path = git.workdir / RUNS
            history_path = git.workdir / HISTORY
            list_path = git.workdir / LIST
            if has_run(runs_path, run_id):
                # 앞선 push가 응답만 끊기고 실제로 들어갔다
                note = (
                    "앞선 올리기가 이미 들어가 있다"
                    if pushed_before
                    else "이 실행의 줄이 이미 있다"
                )
                return Outcome(1 if failed else 0, note)
            list_lines = _list_lines(list_path, additions)
            append_lines(list_path, list_lines)
            append_lines(history_path, additions.history)
            keep_count = count_keep(history_path)
            if additions.run is not None:
                run_line = dict(additions.run)
                run_line["keep_count"] = keep_count
            else:
                run_line = {
                    "run_id": run_id,
                    "base_date": base_date,
                    "kind": kind,
                    "result": "aborted",
                    "keep_count": keep_count,
                }
            append_lines(
                runs_path, [json.dumps(run_line, ensure_ascii=False, separators=(",", ":"))]
            )
            result = run_line.get("result")
            message = f"실행 기록 {run_line.get('base_date', base_date)} · {run_id} · {result}"
            print(
                f"올리는 추가분: 목록 {len(list_lines)}줄 · 처리 이력 {len(additions.history)}줄 · "
                f"실행 요약 1줄(남김 기록 {keep_count})"
            )
            for raw in [*list_lines, *additions.history]:
                print(f"  {raw}")
            print(f"  {json.dumps(run_line, ensure_ascii=False)}")
            pushed_before = True
            git.commit_and_push(message)
            return Outcome(1 if failed else 0, f"{attempt}번째에 올렸다")
        except GitError as exc:
            last_error = str(exc)
            print(f"{attempt}번째 올리기 실패: {last_error}")
    return Outcome(1, f"{ATTEMPTS}번 모두 올리지 못했다: {last_error}")


def main() -> int:
    """CCR-MS-001#finish.main"""
    env = os.environ
    for name in ("RUN_ID", "APPEND_DIR", "WORK_DIR", "REMOTE_URL"):
        if not env.get(name):
            print(f"환경 변수 {name}이 없다")
            return 1
    git = Git(Path(env["WORK_DIR"]) / "finish-main", env["REMOTE_URL"], env.get("PUSH_TOKEN"))
    outcome = finish(env, git)
    print(outcome.note)
    return outcome.code


if __name__ == "__main__":
    sys.exit(main())
