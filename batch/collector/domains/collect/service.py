"""여섯 소스를 동시에 돌려 소스별 결과를 모은다(CCR-UC-001 UC-S1 · UC-S2).

소스 하나가 실패해도 예외가 밖으로 새지 않고 빈 목록과 실패 표시로 바뀐다. 소스마다 시간 예산을
두고, 그 안에서 robots.txt 확인과 목록 요청을 한다(CCR-INFRA-001 8.5 · CCR-API-001 2.1).
"""

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from typing import Callable, Sequence

from collector.core.settings import SourceSettings
from collector.domains.collect.models import FailureKind, SourceResult
from collector.domains.collect.ports import Source
from collector.infra.http import FormatError, HttpFailure, SourceHttp, Stopped
from collector.infra.robots import RobotsDisallowed, ensure_allowed

log = logging.getLogger(__name__)

_CATEGORY_TO_KIND = {
    "connection": FailureKind.CONNECTION,
    "budget": FailureKind.CONNECTION,  # 시간 예산을 넘긴 것은 연결로 본다(CCR-DOM-001 SourceResult)
    "status": FailureKind.HTTP_STATUS,
    "format": FailureKind.FORMAT,
}

HttpFactory = Callable[[SourceSettings, float, threading.Event], SourceHttp]


def _default_http(settings: SourceSettings, deadline: float, stop: threading.Event) -> SourceHttp:
    return SourceHttp(settings, deadline=deadline, stop=stop)


class CollectService:
    def __init__(
        self,
        settings: SourceSettings,
        sources: Sequence[Source],
        stop: threading.Event,
        http_factory: HttpFactory = _default_http,
    ) -> None:
        self._settings = settings
        self._sources = list(sources)
        self._stop = stop
        self._http_factory = http_factory

    def collect_all(self, base_date: date) -> list[SourceResult]:
        """소스 순서대로 결과를 돌려준다. 신호를 받으면 Stopped를 낸다."""
        with ThreadPoolExecutor(max_workers=max(1, len(self._sources)), thread_name_prefix="source") as pool:
            futures = [pool.submit(self._collect_one, source, base_date) for source in self._sources]
            results = [future.result() for future in futures]
        if self._stop.is_set():
            raise Stopped()
        return results

    def _collect_one(self, source: Source, base_date: date) -> SourceResult:
        if source.missing_config():
            log.warning("%s: 자격증명이 설정에 없어 요청하지 않는다", source.name)
            return SourceResult.failed(source.name, FailureKind.MISSING_CONFIG, "자격증명 없음")
        deadline = time.monotonic() + self._settings.budget_seconds
        http = self._http_factory(self._settings, deadline, self._stop)
        started = time.monotonic()
        try:
            ensure_allowed(http, source.origin, source.robots_paths)
            collected = source.collect(http, base_date, self._settings.page_cap)
        except Stopped:
            return SourceResult.failed(source.name, FailureKind.CONNECTION, "신호를 받아 멈췄다")
        except RobotsDisallowed as exc:
            log.warning("%s: robots.txt가 %s를 막는다", source.name, exc)
            return SourceResult.failed(source.name, FailureKind.ROBOTS, f"robots.txt 막음: {exc}")
        except HttpFailure as exc:
            log.warning("%s: 실패(%s) %s", source.name, exc.category, exc.detail)
            return SourceResult.failed(source.name, _CATEGORY_TO_KIND[exc.category], exc.detail)
        except FormatError as exc:
            log.warning("%s: 형식 %s", source.name, exc)
            return SourceResult.failed(source.name, FailureKind.FORMAT, str(exc))
        except Exception as exc:  # 파서의 예상하지 못한 오류도 소스 실패로 가둔다(CCR-INFRA-001 C7)
            log.exception("%s: 예상하지 못한 오류", source.name)
            return SourceResult.failed(source.name, FailureKind.FORMAT, f"{type(exc).__name__}: {exc}")
        finally:
            http.close()
        elapsed = time.monotonic() - started
        for note in collected.notes:
            log.info("%s: %s", source.name, note)
        if collected.page_cap_hit:
            log.warning("%s: 쪽 상한 %d에 닿아 멈췄다", source.name, self._settings.page_cap)
        log.info(
            "%s: 수집 %d · 정규화 뒤 %d · 탈락 %d · 요청 %d회 · %.1f초",
            source.name,
            collected.collected,
            len(collected.competitions),
            collected.dropped,
            http.requests,
            elapsed,
        )
        return SourceResult(
            source=source.name,
            competitions=collected.competitions,
            collected=collected.collected,
            dropped=collected.dropped,
            page_cap_hit=collected.page_cap_hit,
        )
