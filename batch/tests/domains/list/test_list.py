"""목록 경계(CCR-UC-001 UC-S4 1 · UC-S6)의 읽기와 더하기."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from collector.domains.list.crud import ListCrud, ListReadFailed
from collector.domains.list.models import ListEntry, entry_of
from collector.domains.list.service import ListService
from tests.conftest import comp

BASE = date(2026, 9, 29)


def entry_line(source_id: str, **extra: object) -> str:
    line = {
        "id": f"DACON:{source_id}",
        "source": "DACON",
        "source_id": source_id,
        "title": f"대회 {source_id}",
        "link": f"https://dacon.io/{source_id}",
        "start_date": None,
        "deadline": "2026-10-06",
        "collected_on": "2026-09-28",
        "reason": "AI 대회",
    }
    line.update(extra)
    return json.dumps(line, ensure_ascii=False)


def make(tmp_path: Path, lines: list[str] | None = None, *, write: bool = True) -> tuple[ListService, Path]:
    state = tmp_path / "data"
    state.mkdir()
    if lines is not None:
        (state / "competitions.jsonl").write_text("".join(x + "\n" for x in lines), encoding="utf-8")
    append = tmp_path / "append"
    return ListService(ListCrud(state, append), write=write), append


def appended(append: Path) -> list[dict]:
    path = append / "competitions.jsonl"
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []


def test_first_run_has_no_list_file(tmp_path: Path) -> None:
    service, append = make(tmp_path)
    loaded = service.load()
    assert loaded.entries == [] and loaded.exists is False and loaded.error is None
    assert (append / "competitions.jsonl").read_text(encoding="utf-8") == ""


def test_entries_are_read_and_id_comes_from_source_and_source_id(tmp_path: Path) -> None:
    service, _ = make(tmp_path, [entry_line("1", id="틀린 값")])
    loaded = service.load()
    assert loaded.exists is True
    assert [e.id for e in loaded.entries] == ["DACON:1"]
    assert loaded.entries[0].deadline == date(2026, 10, 6) and loaded.entries[0].start_date is None


def test_broken_line_is_a_read_failure(tmp_path: Path) -> None:
    service, _ = make(tmp_path, [entry_line("1"), "{broken"])
    loaded = service.load()
    assert loaded.error is not None and "2번째" in loaded.error
    assert loaded.entries == []


@pytest.mark.parametrize("bad", [{"link": ""}, {"collected_on": None}, {"deadline": "10/06"}])
def test_missing_required_field_or_bad_date_is_a_read_failure(tmp_path: Path, bad: dict) -> None:
    service, _ = make(tmp_path, [entry_line("1", **bad)])
    assert service.load().error is not None


def test_duplicate_ids_are_all_known(tmp_path: Path) -> None:
    service, append = make(tmp_path, [entry_line("1"), entry_line("1", title="다른 이름")])
    loaded = service.load()
    assert len(loaded.entries) == 2 and loaded.ids() == {"DACON:1"}
    assert service.append(comp("대회 1", source_id="1"), BASE, "x") is not None  # 출처가 다르면 다른 식별자
    assert appended(append)[0]["id"] == "event-us:1"


def test_append_writes_whole_file_each_time(tmp_path: Path) -> None:
    service, append = make(tmp_path)
    service.load()
    first = service.append(comp("2026 AI 해커톤", source_id="a", start=date(2026, 9, 1), deadline=date(2026, 10, 1)), BASE, "  AI 해커톤  ")
    second = service.append(comp("데이터 대회", source_id="b"), BASE, "")
    assert first is not None and second is not None
    lines = appended(append)
    assert [x["id"] for x in lines] == ["event-us:a", "event-us:b"]
    assert lines[0] == {
        "id": "event-us:a",
        "source": "event-us",
        "source_id": "a",
        "title": "2026 AI 해커톤",
        "link": "https://example.com/event-us/a",
        "start_date": "2026-09-01",
        "deadline": "2026-10-01",
        "collected_on": "2026-09-29",
        "reason": "AI 해커톤",
    }
    assert lines[1]["reason"] == "" and lines[1]["deadline"] is None
    assert service.appended_count == 2
    assert [p.name for p in append.iterdir()] == ["competitions.jsonl"]  # 임시 파일이 남지 않는다


def test_same_id_is_not_appended_twice(tmp_path: Path) -> None:
    service, append = make(tmp_path, [entry_line("1")])
    service.load()
    assert service.append(comp("대회 1", source="DACON", source_id="1"), BASE, "x") is None  # 읽은 목록에 있다
    assert service.append(comp("새 대회", source_id="n"), BASE, "x") is not None
    assert service.append(comp("새 대회 다시", source_id="n"), BASE, "x") is None  # 이번 추가분에 있다
    assert [x["id"] for x in appended(append)] == ["event-us:n"]


def test_preview_returns_the_entry_but_writes_nothing(tmp_path: Path) -> None:
    service, append = make(tmp_path, write=False)
    service.load()
    entry = service.append(comp("AI 대회", source_id="p"), BASE, "AI")
    assert isinstance(entry, ListEntry) and entry.reason == "AI"
    assert service.appended_count == 0
    assert not append.exists()


def test_entry_of_truncates_reason() -> None:
    entry = entry_of(comp("대회", source_id="1"), BASE, "x" * 400)
    assert len(entry.reason) == 300 and entry.collected_on == BASE


def test_crud_read_fails_on_unreadable_line(tmp_path: Path) -> None:
    state = tmp_path / "data"
    state.mkdir()
    (state / "competitions.jsonl").write_text("[]\n", encoding="utf-8")
    with pytest.raises(ListReadFailed):
        ListCrud(state, tmp_path / "append").read()
    with pytest.raises(ValueError):
        ListCrud(state, state)
