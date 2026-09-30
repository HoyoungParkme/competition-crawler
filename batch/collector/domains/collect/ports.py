"""소스 어댑터의 인터페이스. 소스마다 구현이 다르고 인터페이스는 같다(CCR-UC-001 UC-S1 일반화)."""

from __future__ import annotations

from datetime import date
from typing import Protocol

from collector.domains.collect.models import Collected, SourceName
from collector.infra.http import SourceHttp


class Source(Protocol):
    name: SourceName
    origin: str  # robots.txt를 받을 호스트. 예: https://www.wevity.com
    robots_paths: tuple[str, ...]  # 그 호스트에서 요청하는 경로

    def missing_config(self) -> bool:
        """CCR-MS-001#Source.missing_config

        필요한 자격증명이 설정에 없으면 True. 그때는 요청하지 않는다(UC-S1 1a).
        """
        ...

    def collect(self, http: SourceHttp, base_date: date, page_cap: int) -> Collected:
        """CCR-MS-001#Source.collect

        목록을 받아 공통 형식으로 맞춘다. 틀을 찾지 못하면 FormatError, 요청 실패는 HttpFailure.
        """
        ...
