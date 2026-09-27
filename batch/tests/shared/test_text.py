from __future__ import annotations

from collector.domains.screen.matching import normalize_title
from collector.shared.text import clean_text, html_text

RAW = "\ufeff\ufeff\ufeff[외교부] 국제개발협력\u00a0 청년 공모전\u200b "


def test_only_the_ends_are_trimmed() -> None:
    # 앞뒤의 BOM · 폭 없는 공백 · 공백만 뗀다. 가운데는 소스가 준 그대로다(UC-S2 4)
    assert clean_text(RAW) == "[외교부] 국제개발협력\u00a0 청년 공모전"


def test_html_text_collapses_spaces_like_a_browser() -> None:
    assert html_text("\n  2026 인천관광\n\t혁신 공모전  ") == "2026 인천관광 혁신 공모전"
    assert html_text(RAW) == "[외교부] 국제개발협력 청년 공모전"


def test_matching_sees_through_invisible_characters() -> None:
    # event-us · 콘테스트코리아의 대회명 앞에 BOM이 여러 개 붙어 온다(2026-09-27 실측)
    assert normalize_title(RAW) == normalize_title("[외교부] 국제개발협력 청년 공모전 (~9/30)") == "국제개발협력청년공모전"


def test_none_is_empty() -> None:
    assert clean_text(None) == "" and html_text(None) == ""
