"""무엇을 넣을지 가른다(CCR-UC-001 UC-S3 · UC-S4 3~7 · UC-S5).

마감 판정, 후보 묶기, 아는 대회 가르기, 관심 분야 판별이 차례로 돈다. 처리 이력에 적을 값은
여기서 정해 기록 경계에 넘긴다(CCR-DOM-001 4.2 규칙 5).
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import date

from collector.domains.collect.models import Competition
from collector.domains.list.models import ListEntry
from collector.domains.record.models import HistoryEntry, HistoryRecord, Result
from collector.domains.record.service import RecordService
from collector.domains.screen.matching import (
    SIMILARITY,
    group,
    judge_pair,
    key_of_competition,
    key_of_entry,
    key_of_history,
    representative_order,
)
from collector.domains.screen.models import (
    Bundle,
    Known,
    KnownKind,
    MatchKey,
    Outcome,
    PairResult,
    Verdict,
)
from collector.domains.screen.ports import Answer, Judge, JudgeError
from collector.infra.http import Stopped

log = logging.getLogger(__name__)

CAUSE_MISSING_KEY = "missing_key"
CAUSE_CALL_FAILED = "call_failed"


@dataclass
class KnownSet:
    """아는 대회(UC-S4 3). 목록 항목과 처리 이력을 합친 것이다."""

    items: list[Known] = field(default_factory=list)
    by_id: dict[tuple[str, str], list[int]] = field(default_factory=lambda: defaultdict(list))
    by_link: dict[str, list[int]] = field(default_factory=lambda: defaultdict(list))
    by_title: dict[str, list[int]] = field(default_factory=lambda: defaultdict(list))
    history_ids: set[tuple[str, str]] = field(default_factory=set)

    def add(self, known: Known) -> None:
        """CCR-MS-001#KnownSet.add"""
        index = len(self.items)
        self.items.append(known)
        key = known.key
        if key.source is not None and key.source_id is not None:
            self.by_id[(key.source, key.source_id)].append(index)
        if key.from_list and key.link:
            self.by_link[key.link].append(index)
        if key.title_norm:
            self.by_title[key.title_norm].append(index)


@dataclass
class JudgeOutcome:
    to_load: list[Bundle] = field(default_factory=list)
    discarded: int = 0
    judge_failed: int = 0
    deferred: int = 0
    cause: str | None = None  # 미뤘을 때 missing_key · call_failed


def entries_for(
    bundle: Bundle, result: Result, members: list[Competition] | None = None
) -> list[HistoryEntry]:
    """CCR-MS-001#screen.entries_for

    구성원마다 한 줄. 구성원에게 없는 접수 날짜는 대표의 날짜로 채운다(UC-S4 0.1 · CCR-PRD-001 5.2).
    """
    rep = bundle.representative
    seen: set[tuple[str, str]] = set()
    entries: list[HistoryEntry] = []
    for member in members if members is not None else bundle.members:
        key = (str(member.source), member.source_id)
        if key in seen:
            continue
        seen.add(key)
        entries.append(
            HistoryEntry(
                source=str(member.source),
                source_id=member.source_id,
                link=member.link,
                title=member.title,
                start_date=member.start_date or rep.start_date,
                deadline=member.deadline or rep.deadline,
                result=result,
            )
        )
    return entries


def _could_be_same(a: MatchKey, b: MatchKey) -> bool:
    """4 · 5단계로 같다고 나올 수 있는가. 유사도를 계산하기 전에 싸게 거른다."""
    la, lb = len(a.title_norm), len(b.title_norm)
    total = la + lb
    if not la or not lb or 2 * min(la, lb) < SIMILARITY * total:
        return False
    shared = len(a.chars & b.chars)
    bound = min(la - (len(a.chars) - shared), lb - (len(b.chars) - shared))
    return 2 * bound >= SIMILARITY * total


class ScreenService:
    def __init__(
        self,
        record: RecordService,
        *,
        base_date: date,
        ignore_discards: bool,
        judge: Judge | None,
        concurrency: int,
        stop: threading.Event,
    ) -> None:
        self._record = record
        self._base_date = base_date
        self._ignore_discards = ignore_discards
        self._judge = judge
        self._concurrency = max(1, concurrency)
        self._stop = stop

    # UC-S3
    def drop_expired(self, competitions: list[Competition]) -> tuple[list[Competition], int]:
        """CCR-MS-001#ScreenService.drop_expired

        접수마감일이 기준일보다 이른 대회와 Kaggle 상시 연습용 대회를 버린다. 마감일이 비면 남긴다.
        """
        kept = [
            c
            for c in competitions
            if not c.practice and (c.deadline is None or c.deadline >= self._base_date)
        ]
        return kept, len(competitions) - len(kept)

    # UC-S4 4
    def bundle(self, competitions: list[Competition]) -> list[Bundle]:
        """CCR-MS-001#ScreenService.bundle"""
        keys = [key_of_competition(c) for c in competitions]
        bundles: list[Bundle] = []
        for indexes in group(competitions, keys):
            members = [competitions[i] for i in indexes]
            rep = min(members, key=representative_order)
            bundles.append(
                Bundle(members=members, representative=rep, keys=[keys[i] for i in indexes])
            )
        merged = sum(1 for b in bundles if len(b.members) > 1)
        log.info(
            "후보 대회 %d건을 묶음 %d개로 묶었다(구성원 둘 이상 %d개)",
            len(competitions),
            len(bundles),
            merged,
        )
        return bundles

    # UC-S4 3
    def build_known(self, entries: list[ListEntry], history: list[HistoryRecord]) -> KnownSet:
        """CCR-MS-001#ScreenService.build_known"""
        known = KnownSet()
        for entry in entries:
            # 참가자가 지운 항목도 파일에 남아 있어 그대로 아는 대회다(UC-S4 3)
            known.add(
                Known(
                    KnownKind.LIST,
                    key_of_entry(entry),
                    Result.KEEP,
                    f"목록 항목 {entry.id} {entry.title}",
                )
            )
        skipped = 0
        for record in history:
            known.history_ids.add((record.source, record.source_id))
            if self._ignore_discards and record.result is Result.DISCARD:
                skipped += 1
                continue  # UC-A1 1b6. 버림 기록을 없는 것으로 본다
            label = f"처리 이력 {record.source}:{record.source_id} {record.title}"
            known.add(Known(KnownKind.HISTORY, key_of_history(record), str(record.result), label))
        if skipped:
            log.info("버림 기록 %d개를 없는 것으로 본다", skipped)
        return known

    # UC-S4 5 · 6 · 7
    def split_known(self, bundles: list[Bundle], known: KnownSet) -> tuple[list[Bundle], int]:
        """CCR-MS-001#ScreenService.split_known

        아는 대회와 같은 묶음을 빼고 나머지를 돌려준다.
        확실하게 같았으면 구성원을 처리 이력에 적는다.
        """
        unknown: list[Bundle] = []
        known_count = 0
        for bundle in bundles:
            matches = self._matches(bundle, known)
            if not matches:
                unknown.append(bundle)
                continue
            known_count += 1
            bundle.outcome = Outcome.KNOWN
            bundle.matched = matches
            self._record_known(bundle, matches, known)
        return unknown, known_count

    def _matches(self, bundle: Bundle, known: KnownSet) -> list[tuple[Known, PairResult]]:
        """CCR-MS-001#ScreenService._matches"""
        keys = bundle.keys or [key_of_competition(m) for m in bundle.members]
        shortlist: set[int] = set()
        for key in keys:
            if key.source is not None and key.source_id is not None:
                shortlist.update(known.by_id.get((key.source, key.source_id), ()))
            if key.link:
                shortlist.update(known.by_link.get(key.link, ()))
            shortlist.update(known.by_title.get(key.title_norm, ()))
            for index, item in enumerate(known.items):
                if index not in shortlist and _could_be_same(key, item.key):
                    shortlist.add(index)
        matches: list[tuple[Known, PairResult]] = []
        for index in sorted(shortlist):
            item = known.items[index]
            results = [judge_pair(key, item.key) for key in keys]
            first = next((r for r in results if r.verdict is Verdict.SAME and r.step == 1), None)
            if first is not None:
                # 1단계로 같으면 다른 구성원과의 2·3단계를 보지 않는다(UC-S4 5 첫째)
                matches.append((item, first))
                continue
            if any(r.verdict is Verdict.DIFFERENT for r in results):
                continue
            same = [r for r in results if r.verdict is Verdict.SAME]
            if same:
                matches.append(
                    (
                        item,
                        max(
                            same, key=lambda r: (r.certain, -r.step if r.step else 0, r.similarity)
                        ),
                    )
                )
        return matches

    def _record_known(
        self, bundle: Bundle, matches: list[tuple[Known, PairResult]], known: KnownSet
    ) -> None:
        """CCR-MS-001#ScreenService._record_known"""
        certain = [item for item, result in matches if result.certain]
        best = min(matches, key=lambda m: (m[1].step or 9, -m[1].similarity))
        if best[1].step != 1:
            log.info(
                "아는 대회로 뺀다: %s (%s) ≈ %s [%d단계 %.2f%s]",
                bundle.representative.title,
                bundle.representative.source,
                best[0].label,
                best[1].step or 0,
                best[1].similarity,
                "" if certain else " · 이름만으로 같아 적지 않는다",
            )
        if not certain:
            return  # 연도 · 날짜 없이 이름만으로 같았다(UC-S4 6 · 5b)
        # 결과가 다른 둘과 함께 같으면 남김을 따른다. 남김은 버림을 비울 때도 지워지지 않는다
        result = (
            Result.KEEP if any(item.result == Result.KEEP for item in certain) else Result.DISCARD
        )
        missing = [
            m for m in bundle.members if (str(m.source), m.source_id) not in known.history_ids
        ]
        if missing:
            self._record.append(entries_for(bundle, result, missing))

    # UC-S5
    def judge(self, bundles: list[Bundle]) -> JudgeOutcome:
        """CCR-MS-001#ScreenService.judge"""
        outcome = JudgeOutcome()
        if not bundles:
            return outcome
        ordered = sorted(bundles, key=_deadline_first)
        failed: list[Bundle] = []
        if self._judge is None:
            log.warning("OpenAI 키가 설정에 없어 묶음 %d개를 판별하지 않는다", len(ordered))
            failed = list(ordered)
            cause = CAUSE_MISSING_KEY
        else:
            failed = self._ask_all(ordered, outcome)
            cause = CAUSE_CALL_FAILED
        for bundle in failed:
            bundle.judge_failed = True
        outcome.judge_failed = len(failed)
        defer = 2 * len(failed) > len(ordered)
        for bundle in failed:
            if defer and bundle.deadline != self._base_date:
                bundle.outcome = Outcome.DEFERRED
                outcome.deferred += 1
            else:
                outcome.to_load.append(bundle)  # UC-S5 2b · 2c1. 남김으로 본다
        if outcome.deferred:
            outcome.cause = cause
            log.warning(
                "판별 실패 %d / %d로 묶음 %d개를 다음 실행으로 미룬다",
                len(failed),
                len(ordered),
                outcome.deferred,
            )
        outcome.to_load.sort(key=_deadline_first)
        return outcome

    def _ask_all(self, bundles: list[Bundle], outcome: JudgeOutcome) -> list[Bundle]:
        """CCR-MS-001#ScreenService._ask_all"""
        fatal = threading.Event()
        judge = self._judge
        assert judge is not None

        def ask(bundle: Bundle) -> tuple[Answer | None, str | None]:
            if self._stop.is_set():
                raise Stopped()
            if fatal.is_set():
                return None, "앞선 호출이 다시 물어도 같은 답이 올 오류라 묻지 않았다"
            try:
                return judge.judge(bundle.representative), None
            except JudgeError as exc:
                if exc.fatal:
                    fatal.set()
                return None, exc.detail
            except Stopped:
                raise
            except Exception as exc:  # 예상하지 못한 오류도 그 묶음의 판별 실패로 가둔다
                log.exception("판별 중 예상하지 못한 오류")
                return None, f"{type(exc).__name__}: {exc}"

        failed: list[Bundle] = []
        pool = ThreadPoolExecutor(max_workers=self._concurrency, thread_name_prefix="judge")
        futures: dict[Future[tuple[Answer | None, str | None]], Bundle] = {}
        try:
            futures = {pool.submit(ask, bundle): bundle for bundle in bundles}
            for future in as_completed(futures):
                bundle = futures[future]
                answer, error = future.result()
                rep = bundle.representative
                if answer is None:
                    log.warning("판별 실패: %s (%s) — %s", rep.title, rep.source, error)
                    failed.append(bundle)
                elif answer.keep:
                    bundle.reason = answer.reason
                    log.info("남김: %s (%s) — %s", rep.title, rep.source, answer.reason)
                    outcome.to_load.append(bundle)
                else:
                    bundle.reason = answer.reason
                    bundle.outcome = Outcome.DISCARDED
                    outcome.discarded += 1
                    log.info("버림: %s (%s) — %s", rep.title, rep.source, answer.reason)
                    self._record.append(entries_for(bundle, Result.DISCARD))
        except BaseException:
            pool.shutdown(wait=False, cancel_futures=True)
            raise
        pool.shutdown(wait=True)
        return failed


def _deadline_first(bundle: Bundle) -> tuple[bool, date, str]:
    deadline = bundle.deadline
    return (deadline is None, deadline or date.max, bundle.representative.title)
