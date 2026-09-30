"""목록 파일을 읽고, 이번 실행의 목록 추가분을 쓴다(CCR-INFRA-001 6.2).

배치는 작업 트리의 목록 파일을 직접 고치지 않는다. 추가분은 작업 트리 밖의 파일에 쌓고, 쓸 때마다
새 이름의 임시 파일에 쓴 뒤 이름을 바꿔 통째로 교체한다. 데이터 폴더를 꺼내는 일은 기록 경계가
세 파일을 한 번에 하므로(CCR-DOM-002 5장 결정 5) 여기서는 읽기만 한다.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from collector.domains.list.models import ListEntry

LIST_FILE = "competitions.jsonl"


class ListReadFailed(Exception):
    """목록 파일이 있는데 읽히지 않는다(CCR-UC-001 UC-S4 1b)."""


def _atomic_write(path: Path, text: str) -> None:
    # 기록 경계의 _atomic_write와 같은 방법. 경계를 넘어 비공개 함수를 부르지 않으려고 따로 둔다
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


class ListCrud:
    def __init__(self, state_dir: Path, append_dir: Path) -> None:
        if state_dir.resolve() == append_dir.resolve():
            raise ValueError("추가분 폴더가 데이터 폴더와 같다")
        self._state_dir = state_dir
        self._append_dir = append_dir

    def read(self) -> list[ListEntry] | None:
        """CCR-MS-001#ListCrud.read"""
        path = self._state_dir / LIST_FILE
        if not path.exists():
            return None
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise ListReadFailed(f"{path.name}을 열지 못했다: {exc}") from exc
        entries: list[ListEntry] = []
        for number, line in enumerate(raw.split(b"\n"), start=1):
            if not line.strip():
                continue
            try:
                data = json.loads(line.decode("utf-8"))
                if not isinstance(data, dict):
                    raise ValueError("객체가 아니다")
                entries.append(ListEntry.from_dict(data))
            except (UnicodeDecodeError, ValueError, KeyError, TypeError) as exc:
                raise ListReadFailed(f"{path.name} {number}번째 줄을 읽지 못했다: {exc}") from exc
        return entries

    def reset_appends(self) -> None:
        """CCR-MS-001#ListCrud.reset_appends"""
        _atomic_write(self._append_dir / LIST_FILE, "")

    def write_appends(self, lines: list[dict[str, Any]]) -> None:
        """CCR-MS-001#ListCrud.write_appends"""
        text = "".join(json.dumps(line, ensure_ascii=False, separators=(",", ":")) + "\n" for line in lines)
        _atomic_write(self._append_dir / LIST_FILE, text)
