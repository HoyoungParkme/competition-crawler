from __future__ import annotations

import json
import threading
from datetime import date

import httpx
import pytest

from collector.domains.collect.models import SourceName
from collector.domains.notion.crud import NotionCrud
from collector.domains.notion.models import NotionReadFailed
from collector.domains.notion.service import NotionService, check_schema, properties_of, row_of
from collector.infra.notion import NotionHttp
from tests.conftest import NOTION_SETTINGS, FakeClock, comp

SCHEMA = {
    "기타": {"type": "title"},
    "링크": {"type": "url"},
    "시작일": {"type": "date"},
    "마감일": {"type": "date"},
    "상태": {"type": "status", "status": {"options": [{"name": "시작 전"}, {"name": "진행 중"}]}},
    "출처": {"type": "select"},
    "수집일": {"type": "date"},
}


def service(handler, *, write: bool = True) -> NotionService:
    clock = FakeClock()
    client = httpx.Client(base_url="https://api.notion.com", transport=httpx.MockTransport(handler))
    http = NotionHttp(NOTION_SETTINGS, "t", threading.Event(), client=client, sleep=clock.sleep, clock=clock)
    return NotionService(NotionCrud(http, "ds"), write=write)


def page(title: str, link: str | None, start: str | None) -> dict:
    return {
        "id": "p",
        "properties": {
            "기타": {"title": [{"plain_text": title[:3]}, {"plain_text": title[3:]}]},
            "링크": {"url": link},
            "시작일": {"date": {"start": start} if start else None},
            "마감일": {"date": None},
        },
    }


def test_row_reads_columns_by_name() -> None:
    row = row_of(page("2026 Big Data 활용 대회", "https://x.test/1", "2026-08-04T15:00:00.000+00:00"))
    assert row.title == "2026 Big Data 활용 대회"
    assert row.link == "https://x.test/1"
    assert row.start_date == date(2026, 8, 5)
    assert row.deadline is None
    assert row_of({"id": "q", "properties": {}}).title == ""


def test_read_rows_follows_cursors() -> None:
    bodies = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        bodies.append(body)
        if "start_cursor" not in body:
            return httpx.Response(200, json={"results": [page("a", None, None)], "has_more": True, "next_cursor": "c2"})
        return httpx.Response(200, json={"results": [page("b", None, None)], "has_more": False, "next_cursor": None})

    rows = service(handler).read_rows()
    assert [r.title for r in rows] == ["a", "b"]
    assert bodies == [{"page_size": 100}, {"page_size": 100, "start_cursor": "c2"}]


def test_incomplete_query_is_a_read_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": [], "has_more": False, "request_status": {"type": "incomplete"}})

    with pytest.raises(NotionReadFailed):
        service(handler).read_rows()


def test_schema_problems() -> None:
    assert check_schema(SCHEMA) == ([], None)
    missing = {k: v for k, v in SCHEMA.items() if k not in ("출처", "수집일")}
    assert check_schema(missing) == (["출처", "수집일"], None)
    assert check_schema({k: v for k, v in SCHEMA.items() if k != "링크"})[1] is not None
    assert check_schema({**SCHEMA, "출처": {"type": "rich_text"}})[1] is not None
    no_option = {**SCHEMA, "상태": {"type": "status", "status": {"options": [{"name": "진행 중"}]}}}
    assert "시작 전" in (check_schema(no_option)[1] or "")


def test_missing_columns_are_created_only_when_writing() -> None:
    sent = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "PATCH":
            sent.append(json.loads(request.content))
            return httpx.Response(200, json={})
        return httpx.Response(200, json={"properties": {k: v for k, v in SCHEMA.items() if k != "수집일"}})

    check = service(handler).check_columns()
    assert check.ok and check.created == ["수집일"]
    assert sent == [{"properties": {"수집일": {"date": {}}}}]
    sent.clear()
    preview = service(handler, write=False).check_columns()
    assert preview.ok and sent == []


def test_schema_read_failure_blocks_rows_without_raising() -> None:
    check = service(lambda r: httpx.Response(403, json={"code": "restricted_resource"})).check_columns()
    assert not check.ok and "스키마" in (check.problem or "")


def test_properties_follow_the_table() -> None:
    c = comp("x" * 2100, source=SourceName.AIFACTORY, link="https://aifactory.space/competitions/9304", start=date(2026, 7, 31))
    props = properties_of(c, date(2026, 9, 27))
    assert len(props["기타"]["title"][0]["text"]["content"]) == 2000
    assert props["링크"] == {"url": "https://aifactory.space/competitions/9304"}
    assert props["시작일"] == {"date": {"start": "2026-07-31"}}
    assert props["마감일"] == {"date": None}
    assert props["상태"] == {"status": {"name": "시작 전"}}
    assert props["출처"] == {"select": {"name": "AI팩토리"}}
    assert props["수집일"] == {"date": {"start": "2026-09-27"}}
    assert "결과날" not in props


def test_create_row_outcomes() -> None:
    created = service(lambda r: httpx.Response(200, json={"id": "new"})).create_row(comp("a"), date(2026, 9, 27))
    assert created.created and created.page_id == "new"
    committed = service(
        lambda r: httpx.Response(503, json={"additional_data": {"committed_resource_id": "p9"}})
    ).create_row(comp("a"), date(2026, 9, 27))
    assert committed.created and committed.via_committed
    failed = service(lambda r: httpx.Response(400, json={"code": "validation_error"})).create_row(comp("a"), date(2026, 9, 27))
    assert not failed.created and "validation_error" in (failed.error or "")
