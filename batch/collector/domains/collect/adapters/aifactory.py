"""AI팩토리 경진대회 목록(CCR-API-001 GET/aifactory.space/ko/competition).

접수 기간은 페이지 스크립트 안의 페이로드에만 있어 그것을 읽는다. 페이지 이름과 접수시작일이
같은 과제를 대회 하나로 합치고, 대회명은 네 차례로 정한다.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import date
from typing import Any, Iterator

import httpx

from collector.domains.collect.models import Collected, Competition, SourceName
from collector.infra.http import FormatError, SourceHttp
from collector.shared.dates import parse_to_kst_date
from collector.shared.text import clean_text

URL = "https://aifactory.space/ko/competition"
_PUSH = re.compile(r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)')
_YEAR = re.compile(r"(?<!\d)(20\d{2})(?!\d)")
_LEAD_TAG = re.compile(r"^\s*(?:\[[^\]]*\]|\([^)]*\))\s*")
_TOPIC = re.compile(r"^\s*[\[(]?\s*(?:주제|문제|분야|트랙|track|공모)\s*\d+", re.IGNORECASE)
_SENTINEL = "1970-01-01"


@dataclass(frozen=True)
class Task:
    id: int
    name: str
    page: str
    start: date | None  # participationStartDate, 없으면 startDate
    deadline: date | None  # participationDeadline, 없으면 endDate


def extract_payload(html: str) -> str:
    chunks = _PUSH.findall(html)
    if not chunks:
        raise FormatError("self.__next_f.push 조각이 없다")
    return "".join(json.loads(f'"{chunk}"') for chunk in chunks)


def _walk(value: Any, depth: int = 0) -> Iterator[dict[str, Any]]:
    if depth > 40:
        return
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child, depth + 1)


def _date(value: Any) -> date | None:
    if not isinstance(value, str) or value.startswith(_SENTINEL):
        return None  # 1970-01-01은 값이 없는 것으로 본다
    return parse_to_kst_date(value)


def parse_tasks(payload: str) -> list[Task]:
    refs: dict[str, Any] = {}
    raw_tasks: list[dict[str, Any]] = []
    for line in payload.split("\n"):
        key, sep, value = line.partition(":")
        if not sep or not value or value[0] not in "{[":
            continue
        try:
            obj = json.loads(value)
        except ValueError:
            continue
        refs[key] = obj
        for node in _walk(obj):
            if "id" in node and "name" in node and "page" in node and ("endDate" in node or "participationDeadline" in node):
                raw_tasks.append(node)

    def page_name(page: Any) -> str:
        if isinstance(page, dict):
            return clean_text(page.get("name"))
        if isinstance(page, str) and page.startswith("$"):
            target = refs.get(page[1:])
            if isinstance(target, dict):
                return clean_text(target.get("name"))
        return ""

    tasks: dict[int, Task] = {}
    for raw in raw_tasks:
        try:
            task_id = int(str(raw["id"]))  # 문자열로 오므로 정수로 바꿔 견준다
        except ValueError:
            continue
        if task_id in tasks:
            continue
        tasks[task_id] = Task(
            id=task_id,
            name=clean_text(raw.get("name")),
            page=page_name(raw.get("page")),
            start=_date(raw.get("participationStartDate")) or _date(raw.get("startDate")),
            deadline=_date(raw.get("participationDeadline")) or _date(raw.get("endDate")),
        )
    return list(tasks.values())


def _clean(prefix: str) -> str:
    text = prefix.strip()
    while True:
        before = text
        text = text.rstrip(" _-:·").strip()
        for opener, closer in (("(", ")"), ("[", "]")):
            if text.count(opener) > text.count(closer):
                text = text[: text.rfind(opener)].strip()
        if text == before:
            return text


def _common(names: list[str]) -> str:
    return _clean(os.path.commonprefix(names))


def competition_name(page: str, tasks: list[Task], start: date | None) -> str:
    """대회명을 네 차례로 정한다(CCR-API-001 3.1 AI팩토리)."""
    year = _YEAR.search(page)
    if year and start is not None and int(year.group(1)) in (start.year, start.year + 1):
        return page
    ordered = sorted(tasks, key=lambda t: t.id)
    names = [t.name for t in ordered]
    if len(names) == 1:
        return names[0]
    common = _common(names)
    if len(common) >= 10:
        return common
    stripped = _common([_LEAD_TAG.sub("", n, count=1) for n in names])
    if len(stripped) >= 10:
        return stripped
    first = names[0]
    if _TOPIC.match(first) and page:
        return page
    return first


def group_tasks(tasks: list[Task]) -> list[list[Task]]:
    groups: dict[tuple[str, date | None], list[Task]] = {}
    for task in sorted(tasks, key=lambda t: t.id):
        groups.setdefault((task.page, task.start), []).append(task)
    return list(groups.values())


def to_competition(group: list[Task]) -> Competition | None:
    named = [t for t in group if t.name]
    if not named:
        return None
    first = min(named, key=lambda t: t.id)
    starts = [t.start for t in named if t.start is not None]
    ends = [t.deadline for t in named if t.deadline is not None]
    start = min(starts) if starts else None
    deadline = max(ends) if ends else None
    if start is not None and deadline is not None and start > deadline:
        start = None
    page = first.page
    return Competition(
        source=SourceName.AIFACTORY,
        source_id=str(first.id),
        title=competition_name(page, named, start),
        link=f"https://aifactory.space/competitions/{first.id}",
        start_date=start,
        deadline=deadline,
        extras=tuple(([page] if page else []) + [t.name for t in sorted(named, key=lambda t: t.id)]),
    )


def parse_page(response: httpx.Response) -> list[Task]:
    tasks = parse_tasks(extract_payload(response.text))
    if not tasks:
        raise FormatError("과제를 찾지 못했다")
    return tasks


class AiFactorySource:
    name = SourceName.AIFACTORY
    origin = "https://aifactory.space"
    robots_paths = ("/ko/competition",)

    def missing_config(self) -> bool:
        return False

    def collect(self, http: SourceHttp, base_date: date, page_cap: int) -> Collected:
        tasks = http.fetch("GET", URL, parse=parse_page)
        competitions: list[Competition] = []
        dropped = 0
        for group in group_tasks(tasks):
            competition = to_competition(group)
            if competition is None:
                dropped += len(group)
            else:
                competitions.append(competition)
        # 수집 건수는 합치기 전 과제의 수다(CCR-DOM-001 SourceResult)
        return Collected(competitions, collected=len(tasks), dropped=dropped)
