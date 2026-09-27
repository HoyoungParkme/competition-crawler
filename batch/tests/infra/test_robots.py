from __future__ import annotations

import httpx
import pytest

from collector.infra.http import HttpFailure
from collector.infra.robots import RobotsDisallowed, ensure_allowed
from tests.conftest import FakeClock, make_http


def robots(body: str, status: int = 200):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/robots.txt"
        return httpx.Response(status, text=body)

    return handler


def test_allowed_path_passes(clock: FakeClock) -> None:
    http = make_http(robots("User-agent: *\nAllow: /\n"), clock=clock)
    ensure_allowed(http, "https://src.test", ["/list"])


def test_disallowed_path_raises(clock: FakeClock) -> None:
    http = make_http(robots("User-agent: *\nDisallow: /list\n"), clock=clock)
    with pytest.raises(RobotsDisallowed):
        ensure_allowed(http, "https://src.test", ["/list"])


def test_agent_specific_rule_applies(clock: FakeClock) -> None:
    http = make_http(robots("User-agent: competition-crawler\nDisallow: /\n\nUser-agent: *\nAllow: /\n"), clock=clock)
    with pytest.raises(RobotsDisallowed):
        ensure_allowed(http, "https://src.test", ["/list"])


def test_missing_robots_means_no_restriction(clock: FakeClock) -> None:
    http = make_http(robots("", status=404), clock=clock)
    ensure_allowed(http, "https://src.test", ["/list"])


def test_server_error_on_robots_stops_the_source(clock: FakeClock) -> None:
    http = make_http(robots("", status=503), clock=clock)
    with pytest.raises(HttpFailure):
        ensure_allowed(http, "https://src.test", ["/list"])
