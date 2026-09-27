"""KST 날짜 도구.

시각은 KST로 바꾼 뒤 날짜만 쓴다. 시간대 표기가 없는 값은 KST로 보고 바꾸지 않는다
(CCR-API-001 1.1 · CCR-UC-001 UC-S2 2 · 2b).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))


def kst_date_of(moment: datetime) -> date:
    """시간대가 붙은 시각을 KST 날짜로 바꾼다."""
    if moment.tzinfo is None:
        raise ValueError("시간대가 없는 시각은 받지 않는다")
    return moment.astimezone(KST).date()


def parse_to_kst_date(text: str | None) -> date | None:
    """ISO 모양의 시각이나 날짜를 KST 날짜로 바꾼다. 읽지 못하면 None.

    `Z`나 `+00:00`이 붙은 값은 KST로 바꾸고, 시간대가 없으면 KST로 보고 날짜만 뗀다.
    """
    if not text:
        return None
    value = text.strip()
    if not value:
        return None
    if value.endswith(("Z", "z")):
        value = value[:-1] + "+00:00"
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        return None
    if moment.tzinfo is None:
        return moment.date()
    return moment.astimezone(KST).date()


def kst_midnight_utc(day: date) -> datetime:
    """KST 날짜의 0시를 UTC 시각으로 나타낸다. 2026-09-23 → 2026-09-22T15:00:00+00:00."""
    return datetime(day.year, day.month, day.day, tzinfo=KST).astimezone(timezone.utc)
