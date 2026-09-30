"""하루치 실행의 흐름(CCR-UC-001 UC-A1).

네 경계를 차례로 부르고, 목록 파일에 항목 하나를 더할 때마다 기록 경계에 남김을 적게 한다. 묶음을
센 건수와 경고에 쓸 사실도 여기서 모아 넘긴다(CCR-DOM-001 4.2). 실패로 끝나는 확장에서는 8로
건너뛰어 실행 요약 한 줄을 남긴다. 신호를 받으면 Stopped가 밖으로 나가고 줄은 쓰지 않는다.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from datetime import date
from typing import Callable

from collector.core.settings import RunContext, Settings
from collector.domains.collect.models import SourceResult
from collector.domains.list.service import ListService
from collector.domains.record.models import (
    FailureReason,
    Result,
    RunLine,
    RunResult,
    RunWarning,
    SourceLine,
    WarningKind,
)
from collector.domains.record.service import RecordService, State
from collector.domains.screen.models import Bundle, Outcome
from collector.domains.screen.service import ScreenService, entries_for
from collector.infra.http import Stopped

log = logging.getLogger(__name__)


@dataclass
class Services:
    collect: Callable[[date], list[SourceResult]]
    list: ListService
    record: RecordService
    screen: ScreenService


class Pipeline:
    def __init__(
        self,
        ctx: RunContext,
        settings: Settings,
        services: Services,
        stop: threading.Event,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ctx = ctx
        self._settings = settings
        self._s = services
        self._stop = stop
        self._clock = clock

    def _check(self) -> None:
        if self._stop.is_set():
            raise Stopped()

    def run(self) -> RunLine:
        """CCR-MS-001#Pipeline.run"""
        started = self._clock()
        ctx = self._ctx
        line = RunLine(run_id=ctx.run_id, base_date=ctx.base_date, kind=ctx.kind)
        log.info(
            "실행 %s · 기준일 %s · %s · %s",
            ctx.run_id,
            ctx.base_date,
            "예약" if ctx.kind == "schedule" else "수동",
            "목록에 쓴다" if ctx.write else "목록에 쓰지 않는다(미리보기)",
        )
        if ctx.ignore_discards_requested and not ctx.ignore_discards:
            log.warning("목록에 쓰는 실행이라 버림 기록을 없는 것으로 보라는 입력을 무시한다")
        self._s.record.start()  # 데이터 폴더를 꺼낸다. 목록 파일을 읽기 전이어야 한다
        state, results = self._run(line)
        self._finish(line, state, results, started)
        return line

    def _run(self, line: RunLine) -> tuple[State, list[SourceResult]]:
        """CCR-MS-001#Pipeline._run"""
        s, ctx = self._s, self._ctx

        # UC-A1 2 · 3. 수집과 정규화. 반드시 있어야 하는 시크릿은 없다(1d1)
        results = s.collect(ctx.base_date)
        self._check()
        line.sources = {
            str(r.source): SourceLine(
                collected=r.collected,
                normalized=r.normalized,
                failure=str(r.failure) if r.failure else None,
            )
            for r in results
        }
        line.dropped["normalize"] = sum(r.dropped for r in results)
        listed = s.list.load()
        state = s.record.load()
        if all(r.failure is not None for r in results):
            log.error("여섯 소스가 모두 실패했다")
            line.fail(FailureReason.ALL_SOURCES_FAILED)
            return state, results

        # UC-A1 4. 마감 판정
        competitions = [c for r in results for c in r.competitions]
        candidates, expired = s.screen.drop_expired(competitions)
        line.dropped["expired"] = expired
        log.info("정규화 뒤 %d건 · 마감 지남 %d건 · 남은 후보 %d건", len(competitions), expired, len(candidates))

        # UC-A1 5. 이미 아는 대회. 목록 파일을 먼저 보고 처리 이력의 문제를 본다(UC-S4 1 · 2)
        if listed.error is not None:
            line.fail(FailureReason.LIST_READ_FAILED)
            return state, results
        if state.history_error is not None:
            line.fail(FailureReason.HISTORY_READ_FAILED)
            return state, results
        if s.record.history_shrank(state):
            line.fail(FailureReason.HISTORY_SHRANK)
            return state, results
        known = s.screen.build_known(listed.entries, state.history)
        bundles = s.screen.bundle(candidates)
        self._check()
        unknown, known_count = s.screen.split_known(bundles, known)
        line.dropped["known"] = known_count
        log.info("묶음 %d개 가운데 아는 대회 %d개 · 판별할 묶음 %d개", len(bundles), known_count, len(unknown))
        self._check()

        # UC-A1 6. 관심 분야 판별
        judged = s.screen.judge(unknown)
        line.dropped["discarded"] = judged.discarded
        line.judge_failed = judged.judge_failed
        line.deferred = judged.deferred
        if judged.deferred:
            line.warnings.append(RunWarning(WarningKind.JUDGE_DEFERRED, cause=judged.cause))
        self._check()

        # UC-A1 7. 목록 파일에 더하기
        self._load(line, judged.to_load)
        return state, results

    def _load(self, line: RunLine, bundles: list[Bundle]) -> None:
        """CCR-MS-001#Pipeline._load"""
        s, ctx = self._s, self._ctx
        if not bundles:
            return
        verb = "적재" if ctx.write else "미리보기: 넣었을 대회"
        for bundle in bundles:
            self._check()
            rep = bundle.representative
            entry = s.list.append(rep, ctx.base_date, bundle.reason)
            if entry is not None:
                bundle.outcome = Outcome.LOADED
                line.loaded += 1
            else:
                bundle.outcome = Outcome.KNOWN  # 이미 목록에 있다. 처리 이력에만 적는다(UC-S6 2a)
            # 항목을 더한 그 자리에서 곧바로 남김으로 적는다(UC-S6 3). 넣는 일에는 실패가 없다
            s.record.append(entries_for(bundle, Result.KEEP))
            log.info(
                "%s — %s (%s) 마감 %s · %s",
                verb if entry is not None else "이미 목록에 있어 처리 이력에만 적는다",
                rep.title,
                rep.source,
                rep.deadline or "없음",
                bundle.reason or "근거 없음",
            )
        if not ctx.write:
            log.info("미리보기: 넣었을 묶음 %d개", line.loaded)

    def _finish(self, line: RunLine, state: State, results: list[SourceResult], started: float) -> None:
        """CCR-MS-001#Pipeline._finish"""
        zero = self._s.record.zero_count_warnings(results, state, self._settings.zero_count_days)
        line.warnings[:0] = zero
        if state.runs.corrupt:
            line.warnings.append(RunWarning(WarningKind.SUMMARY_CORRUPT))
        line.duration_s = self._clock() - started
        self._s.record.write_run(line)
        for warning in line.warnings:
            log.warning("경고: %s", warning.to_dict())
        log.info(
            "결과 %s%s · 적재 %d · 판별 실패 %d · 미룸 %d · 탈락 %s · %.1f초",
            line.result,
            f"({line.failure_reason})" if line.failure_reason else "",
            line.loaded,
            line.judge_failed,
            line.deferred,
            line.dropped,
            line.duration_s,
        )
        if line.result is not RunResult.SUCCESS:
            log.error("실행이 실패로 끝났다")
