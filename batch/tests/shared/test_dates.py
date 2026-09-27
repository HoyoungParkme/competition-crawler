from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from collector.shared.dates import kst_date_of, kst_midnight_utc, parse_to_kst_date


def test_utc_after_15_is_the_next_kst_day() -> None:
    # CCR-PRD-001 5.3. 2026-08-04T15:00Z는 KST로 8월 5일이다
    assert parse_to_kst_date("2026-08-04T15:00:00+00:00") == date(2026, 8, 5)
    assert parse_to_kst_date("2026-08-04T15:00:00Z") == date(2026, 8, 5)


def test_value_without_timezone_is_taken_as_kst() -> None:
    assert parse_to_kst_date("2026-09-30 23:59:59") == date(2026, 9, 30)
    assert parse_to_kst_date("2026-09-30") == date(2026, 9, 30)


def test_unreadable_values_are_none() -> None:
    assert parse_to_kst_date(None) is None
    assert parse_to_kst_date("") is None
    assert parse_to_kst_date("곧") is None


def test_base_date_at_0850_kst_is_not_the_utc_date() -> None:
    # 08:50 KST는 UTC로 전날 23:50이다(CCR-UC-001 UC-A1 1a2)
    started = datetime(2026, 9, 26, 23, 50, tzinfo=timezone.utc)
    assert kst_date_of(started) == date(2026, 9, 27)


def test_naive_moment_is_rejected() -> None:
    with pytest.raises(ValueError):
        kst_date_of(datetime(2026, 9, 27, 8, 50))


def test_kst_midnight_in_utc() -> None:
    assert kst_midnight_utc(date(2026, 9, 23)).isoformat() == "2026-09-22T15:00:00+00:00"
