"""같은 대회 판정(CCR-UC-001 UC-S4 판정표 · CCR-PRD-001 5.2).

대회 · 노션 행 · 처리 이력 기록에서 같은 방법으로 판정 값을 뽑고(CCR-DOM-001 4.2 규칙 6),
두 값이 같은지 다섯 단계로 가른다. 앞 단계에서 결론이 나면 뒤 단계는 보지 않는다.
수치(유사도 0.90 · 마감일 180일)는 조정값이 아니라 규칙이라 코드에 둔다(CCR-INFRA-001 4.1).
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from difflib import SequenceMatcher
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from collector.domains.collect.models import SOURCE_PRIORITY, Competition, SourceName
from collector.domains.list.models import ListEntry
from collector.domains.record.models import HistoryRecord
from collector.domains.screen.models import MatchKey, PairResult, Verdict
from collector.shared.text import clean_text

SIMILARITY = 0.90
DEADLINE_GAP_DAYS = 180

_HEAD_BRACKETS = re.compile(r"^\s*(?:[\[【〔][^\]】〕]*[\]】〕]\s*)+")
_PAREN = re.compile(r"\(([^()]*)\)")
_DATE_WORDS = re.compile(r"까지|마감|접수|연장|오전|오후|요일|[년월일시분화수목금토]")
_DATE_REST = re.compile(r"^[\s0-9~\-–—〜.:/,]*$")
_TAIL = re.compile(r"(?:\s+(?:참가자|참가팀|참여자|참가|작품))?\s*(?:모집|공고|안내)$")
_TRAILING_SYMBOLS = re.compile(r"[\W_]+$")
_YEAR_WORD = re.compile(r"(20\d{2})\s*년")
_NON_WORD = re.compile(r"[\W_]+")

_YEAR = re.compile(r"(?<!\d)(20\d{2})(?!\d)")
_ROUNDS = (
    re.compile(r"제\s*(\d{1,3})\s*[회차기]"),
    re.compile(r"(?<![\d.])(\d{1,3})\s*회차"),
    re.compile(r"(?<![\d.제])(\d{1,3})\s*회(?![가-힣])"),
    re.compile(r"(?<![\d.])(\d{1,3})\s*(?:st|nd|rd|th)\b", re.IGNORECASE),
    re.compile(r"(?<![\d.제])(\d{1,3})\s*기(?![가-힣])"),
)
_TRACKING = ("utm_",)
_TRACKING_EXACT = {"fbclid"}


def _is_date_note(inner: str) -> bool:
    """`(~9/20)` · `(9월 20일까지)` · `(금)`처럼 괄호 안이 날짜뿐인가."""
    text = inner.strip()
    if not text:
        return False
    rest = _DATE_WORDS.sub("", text)
    if not re.search(r"\d", text):
        return rest.strip() == "" and len(text) <= 3  # 요일 하나
    return bool(_DATE_REST.match(rest))


def _strip_head(text: str) -> str:
    stripped = _HEAD_BRACKETS.sub("", text)
    # 대회명 전체가 대괄호 안이면 떼지 않는다
    return stripped if _NON_WORD.sub("", stripped) else text


def normalize_title(title: str) -> str:
    """CCR-MS-001#matching.normalize_title

    판정 4 · 5단계가 견주는 대회명. 꼬리말 · 대괄호 머리말 · 괄호 날짜를 떼고 공백과 기호를 없앤다.
    """
    text = unicodedata.normalize("NFKC", clean_text(title))
    text = _strip_head(text)
    for _ in range(4):
        replaced = _PAREN.sub(lambda m: " " if _is_date_note(m.group(1)) else m.group(0), text)
        if replaced == text:
            break
        text = replaced
    while True:
        trimmed = _TAIL.sub("", _TRAILING_SYMBOLS.sub("", text))
        if trimmed == text or not _NON_WORD.sub("", trimmed):
            break
        text = trimmed
    text = _YEAR_WORD.sub(r"\1", text)
    return _NON_WORD.sub("", text).casefold()


def extract_marks(title: str) -> tuple[frozenset[int], frozenset[int]]:
    """CCR-MS-001#matching.extract_marks

    (연도, 회차). 회차는 제N회 · N회 · N회차 · 제N차 · N기 · 영문 서수(2nd)다.
    """
    text = unicodedata.normalize("NFKC", clean_text(title))
    years = frozenset(int(y) for y in _YEAR.findall(text))
    rounds: set[int] = set()
    for pattern in _ROUNDS:
        rounds.update(int(n) for n in pattern.findall(text))
    return years, frozenset(rounds)


def normalize_link(link: str | None) -> str | None:
    """CCR-MS-001#matching.normalize_link

    추적용 매개변수(`utm_…` · `fbclid`)만 뗀다. 쿼리 문자열을 통째로 떼지 않는다.
    """
    if not link or not link.strip():
        return None
    try:
        parts = urlsplit(link.strip())
    except ValueError:
        return link.strip()
    if not parts.netloc:
        return link.strip()
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith(_TRACKING) and k.lower() not in _TRACKING_EXACT
    ]
    scheme = "https" if parts.scheme.lower() in ("http", "https") else parts.scheme.lower()
    path = parts.path.rstrip("/") if len(parts.path) > 1 else parts.path
    return urlunsplit((scheme, parts.netloc.lower(), path, urlencode(query, doseq=True), parts.fragment))


def _key(
    *,
    source: str | None,
    source_id: str | None,
    link: str | None,
    from_list: bool,
    title: str,
    start: date | None,
    deadline: date | None,
) -> MatchKey:
    years, rounds = extract_marks(title)
    norm = normalize_title(title)
    return MatchKey(
        source=source,
        source_id=source_id,
        link=normalize_link(link),
        from_list=from_list,
        title_norm=norm,
        years=years,
        rounds=rounds,
        start=start,
        deadline=deadline,
        chars=frozenset(norm),
    )


def key_of_competition(competition: Competition) -> MatchKey:
    """CCR-MS-001#matching.key_of_competition"""
    return _key(
        source=str(competition.source),
        source_id=competition.source_id,
        link=competition.link,
        from_list=False,
        title=competition.title,
        start=competition.start_date,
        deadline=competition.deadline,
    )


def key_of_entry(entry: ListEntry) -> MatchKey:
    """CCR-MS-001#matching.key_of_entry"""
    # 원천 ID로 1단계를 보고, 링크는 소스 개편으로 원천 ID가 바뀐 공고를 잇는 예비다(CCR-DOM-001 ListEntry)
    return _key(
        source=entry.source,
        source_id=entry.source_id,
        link=entry.link,
        from_list=True,
        title=entry.title,
        start=entry.start_date,
        deadline=entry.deadline,
    )


def key_of_history(record: HistoryRecord) -> MatchKey:
    """CCR-MS-001#matching.key_of_history"""
    return _key(
        source=record.source,
        source_id=record.source_id,
        link=None,  # 링크는 목록 항목과 견줄 때만 쓴다
        from_list=False,
        title=record.title,
        start=record.start_date,
        deadline=record.deadline,
    )


def similarity(a: MatchKey, b: MatchKey) -> float:
    """CCR-MS-001#matching.similarity

    정규화한 대회명의 유사도. 0.90에 닿을 수 없으면 계산하지 않고 0을 돌려준다.
    """
    la, lb = len(a.title_norm), len(b.title_norm)
    total = la + lb
    if total == 0 or 2 * min(la, lb) < SIMILARITY * total:
        return 0.0
    shared = len(a.chars & b.chars)
    # 한쪽에만 있는 글자는 적어도 한 번씩 나오므로 맞는 글자 수의 상한이 준다
    bound = min(la - (len(a.chars) - shared), lb - (len(b.chars) - shared))
    if 2 * bound < SIMILARITY * total:
        return 0.0
    matcher = SequenceMatcher(None, a.title_norm, b.title_norm, autojunk=False)
    if matcher.quick_ratio() < SIMILARITY:
        return 0.0
    return matcher.ratio()


def _marks_differ(a: MatchKey, b: MatchKey) -> bool:
    if a.years and b.years and not (a.years & b.years):
        return True
    return bool(a.rounds and b.rounds and not (a.rounds & b.rounds))


def judge_pair(a: MatchKey, b: MatchKey) -> PairResult:
    """CCR-MS-001#matching.judge_pair

    두 판정 값을 다섯 단계로 견준다(CCR-UC-001 UC-S4 판정표).
    """
    # 1단계. 출처와 원천 ID. 목록 항목과는 링크로도 견주되 2단계를 더 본다
    if a.source_id is not None and a.source == b.source and a.source_id == b.source_id:
        return PairResult(Verdict.SAME, step=1, similarity=1.0, certain=True)
    if (a.from_list or b.from_list) and a.link and a.link == b.link:
        if _marks_differ(a, b):
            return PairResult(Verdict.DIFFERENT, step=2)
        return PairResult(Verdict.SAME, step=1, similarity=1.0, certain=True)

    compared = False
    # 2단계. 둘 다 적힌 연도나 회차가 서로 다르다
    if a.years and b.years:
        compared = True
        if not (a.years & b.years):
            return PairResult(Verdict.DIFFERENT, step=2)
    if a.rounds and b.rounds:
        compared = True
        if not (a.rounds & b.rounds):
            return PairResult(Verdict.DIFFERENT, step=2)
    # 3단계. 한쪽 접수가 다른 쪽 마감 뒤에 시작하거나, 두 마감이 180일 넘게 떨어졌다
    if a.start is not None and b.deadline is not None:
        compared = True
        if a.start > b.deadline:
            return PairResult(Verdict.DIFFERENT, step=3)
    if b.start is not None and a.deadline is not None:
        compared = True
        if b.start > a.deadline:
            return PairResult(Verdict.DIFFERENT, step=3)
    if a.deadline is not None and b.deadline is not None:
        compared = True
        if abs((a.deadline - b.deadline).days) > DEADLINE_GAP_DAYS:
            return PairResult(Verdict.DIFFERENT, step=3)

    if not a.title_norm or not b.title_norm:
        return PairResult(Verdict.UNDECIDED)
    # 4단계. 정규화한 대회명이 같다
    if a.title_norm == b.title_norm:
        return PairResult(Verdict.SAME, step=4, similarity=1.0, certain=compared)
    # 5단계. 유사도 0.90 이상. 못 미치면 판단하지 않는다
    ratio = similarity(a, b)
    if ratio >= SIMILARITY:
        return PairResult(Verdict.SAME, step=5, similarity=ratio, certain=compared)
    return PairResult(Verdict.UNDECIDED, similarity=ratio)


def representative_order(competition: Competition) -> tuple[int, int, str]:
    """CCR-MS-001#matching.representative_order

    대표를 고르는 차례. 접수 날짜가 더 채워진 쪽, 같으면 소스 우선순위가 앞선 쪽(UC-S4 4a).
    """
    return (-competition.dates_filled(), SOURCE_PRIORITY[SourceName(competition.source)], competition.source_id)


def group(competitions: list[Competition], keys: list[MatchKey]) -> list[list[int]]:
    """CCR-MS-001#matching.group

    후보끼리 같은 대회를 묶는다(UC-S4 4). 합친 묶음 안의 모든 짝이 같음일 때만 합친다(CCR-DOM-002 5장 결정 7).
    """
    n = len(competitions)
    same: list[tuple[tuple, int, int]] = []
    for i in range(n):
        for j in range(i + 1, n):
            result = judge_pair(keys[i], keys[j])
            if result.verdict is Verdict.SAME:
                first, second = sorted((i, j), key=lambda x: _order_of(competitions[x]))
                order = (
                    result.step,
                    -result.similarity,
                    _order_of(competitions[first]),
                    _order_of(competitions[second]),
                )
                same.append((order, i, j))
    same_pairs = {(i, j) for _, i, j in same}

    owner = list(range(n))
    members: dict[int, list[int]] = {i: [i] for i in range(n)}
    for _, i, j in sorted(same):
        gi, gj = owner[i], owner[j]
        if gi == gj:
            continue
        if any((min(x, y), max(x, y)) not in same_pairs for x in members[gi] for y in members[gj]):
            continue  # UC-S4 4b. 다름이나 판단하지 않음이 하나라도 있으면 먼저 본 짝 쪽 묶음에 남는다
        if len(members[gi]) < len(members[gj]):
            gi, gj = gj, gi
        for x in members[gj]:
            owner[x] = gi
        members[gi].extend(members.pop(gj))
    return [sorted(group) for _, group in sorted(members.items())]


def _order_of(competition: Competition) -> tuple[int, str, str]:
    return (SOURCE_PRIORITY[SourceName(competition.source)], competition.source_id, competition.title)
