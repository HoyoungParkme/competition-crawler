"""두 기록 파일을 읽고, 이번 실행의 추가분 파일을 쓴다(CCR-INFRA-001 6.2).

배치는 작업 트리의 데이터 파일을 직접 고치지 않는다. 추가분은 작업 트리 밖의 파일에 쌓고, 쓸 때마다
새 이름의 임시 파일에 쓴 뒤 이름을 바꿔 통째로 교체한다. 저장소에 올리는 일은 마무리 단계가 한다.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from collector.domains.record.models import HistoryRecord

LIST_FILE = "competitions.jsonl"  # 목록 파일. 꺼내기만 하고 읽기는 목록 경계가 한다
HISTORY_FILE = "processed.jsonl"
RUNS_FILE = "runs.jsonl"


class HistoryReadFailed(Exception):
    """처리 이력 파일이 있는데 읽히지 않는다(CCR-UC-001 UC-S4 2b)."""


@dataclass
class RunsFile:
    lines: list[dict[str, Any]] = field(default_factory=list)
    corrupt: int = 0  # 읽히지 않아 건너뛴 줄의 수(CCR-UC-001 UC-S7 2c)


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _jsonl(lines: list[dict[str, Any]]) -> str:
    return "".join(json.dumps(line, ensure_ascii=False, separators=(",", ":")) + "\n" for line in lines)


def export_main_state(repo_root: Path, dest: Path) -> Path:
    """CCR-MS-001#record.export_main_state

    기본 브랜치 최신 판의 세 파일을 `dest`에 꺼낸다. 받지 못하면 HistoryReadFailed.

    기본 브랜치가 아닌 곳이나 Actions 밖에서 도는 실행은 작업 트리의 사본이 아니라 이것을 읽는다
    (CCR-UC-001 UC-A1 1b7 · CCR-INFRA-001 4.1).
    """

    def git(*args: str) -> subprocess.CompletedProcess[bytes]:
        try:
            return subprocess.run(["git", "-C", str(repo_root), *args], capture_output=True, timeout=60, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:  # git이 없거나 60초 안에 끝나지 않았다
            raise HistoryReadFailed(f"git {args[0]}을 돌리지 못했다: {type(exc).__name__}") from exc

    # 얕게 받은 저장소(Actions의 브랜치 실행)만 얕게 받는다. 개발자 PC의 저장소를 얕게 만들지 않는다
    shallow = git("rev-parse", "--is-shallow-repository").stdout.strip() == b"true"
    depth = ["--depth=1"] if shallow else []
    fetched = git("fetch", "--quiet", "--no-tags", *depth, "origin", "+refs/heads/main:refs/remotes/origin/main")
    if fetched.returncode != 0:
        raise HistoryReadFailed(f"origin/main을 받지 못했다: {fetched.stderr.decode(errors='replace').strip()}")
    dest.mkdir(parents=True, exist_ok=True)
    for name in (LIST_FILE, HISTORY_FILE, RUNS_FILE):
        target = dest / name
        target.unlink(missing_ok=True)
        spec = f"origin/main:data/{name}"
        if git("cat-file", "-e", spec).returncode != 0:
            continue  # 기본 브랜치에 아직 없다
        shown = git("show", spec)
        if shown.returncode != 0:
            raise HistoryReadFailed(f"{spec}를 꺼내지 못했다")
        target.write_bytes(shown.stdout)
    return dest


class RecordCrud:
    def __init__(self, state_dir: Path, append_dir: Path, *, export_from: Path | None = None) -> None:
        """`export_from`(저장소 루트)이 있으면 읽기 전에 기본 브랜치 최신 판을 `state_dir`에 꺼낸다."""
        if state_dir.resolve() == append_dir.resolve():
            raise ValueError("추가분 폴더가 데이터 폴더와 같다")
        self._state_dir = state_dir
        self._append_dir = append_dir
        self._export_from = export_from

    def prepare(self) -> None:
        if self._export_from is not None:
            export_main_state(self._export_from, self._state_dir)

    def read_history(self) -> list[HistoryRecord] | None:
        """처리 이력. 파일이 없으면 None. 한 줄이라도 읽히지 않으면 HistoryReadFailed."""
        path = self._state_dir / HISTORY_FILE
        if not path.exists():
            return None
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise HistoryReadFailed(f"{path.name}을 열지 못했다: {exc}") from exc
        records: list[HistoryRecord] = []
        for number, line in enumerate(raw.split(b"\n"), start=1):
            if not line.strip():
                continue
            try:
                data = json.loads(line.decode("utf-8"))
                if not isinstance(data, dict):
                    raise ValueError("객체가 아니다")
                records.append(HistoryRecord.from_dict(data))
            except (UnicodeDecodeError, ValueError, KeyError, TypeError) as exc:
                raise HistoryReadFailed(f"{path.name} {number}번째 줄을 읽지 못했다: {exc}") from exc
        return records

    def read_runs(self) -> RunsFile:
        """실행 요약. 파일이 없으면 빈 것. 읽히지 않는 줄은 건너뛰고 센다."""
        path = self._state_dir / RUNS_FILE
        if not path.exists():
            return RunsFile()
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise HistoryReadFailed(f"{path.name}을 열지 못했다: {exc}") from exc
        result = RunsFile()
        for line in raw.split(b"\n"):
            if not line.strip():
                continue
            try:
                data = json.loads(line.decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                result.corrupt += 1
                continue
            if isinstance(data, dict) and data.get("run_id") and data.get("base_date"):
                result.lines.append(data)
            else:
                result.corrupt += 1
        return result

    def reset_appends(self) -> None:
        _atomic_write(self._append_dir / HISTORY_FILE, "")
        _atomic_write(self._append_dir / RUNS_FILE, "")

    def write_history_appends(self, lines: list[dict[str, Any]]) -> None:
        _atomic_write(self._append_dir / HISTORY_FILE, _jsonl(lines))

    def write_run_append(self, line: dict[str, Any]) -> None:
        _atomic_write(self._append_dir / RUNS_FILE, _jsonl([line]))
