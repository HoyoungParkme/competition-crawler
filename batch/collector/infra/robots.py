"""robots.txt 확인.

요청하는 호스트의 robots.txt를 실행마다 한 번 받는다. 4xx면 제한이 없는 것으로 보고, 5xx나
연결 오류로 끝내 받지 못하면 목록을 요청하지 않는다. 리디렉션은 다섯 번까지 따라간다
(CCR-API-001 1.2 · RFC 9309).
"""

from __future__ import annotations

from typing import Iterable
from urllib import robotparser

import httpx

from collector.infra.http import SourceHttp

ROBOTS_AGENT = "competition-crawler"


class RobotsDisallowed(Exception):
    """robots.txt가 목록 경로를 막고 있다."""


def ensure_allowed(http: SourceHttp, origin: str, paths: Iterable[str]) -> None:
    """CCR-MS-001#robots.ensure_allowed

    `origin`(예: https://www.wevity.com)의 robots.txt가 `paths`를 막으면 RobotsDisallowed.
    """

    def read(response: httpx.Response) -> str | None:
        if 400 <= response.status_code < 500:
            return None
        return response.text

    text = http.fetch(
        "GET",
        origin.rstrip("/") + "/robots.txt",
        parse=read,
        follow_redirects=True,
        accept_client_errors=True,
    )
    if text is None:
        return
    parser = robotparser.RobotFileParser()
    parser.parse(text.splitlines())
    for path in paths:
        if not parser.can_fetch(ROBOTS_AGENT, origin.rstrip("/") + path):
            raise RobotsDisallowed(path)
