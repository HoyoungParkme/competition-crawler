from __future__ import annotations

from collector.domains.screen.matching import normalize_title
from collector.shared.text import clean_text


def test_invisible_characters_are_removed() -> None:
    # event-us · 콘테스트코리아의 대회명 앞에 BOM이 여러 개 붙어 온다(2026-09-27 실측)
    raw = "﻿﻿﻿[외교부] 국제개발협력 청년 공모전​ "
    assert clean_text(raw) == "[외교부] 국제개발협력 청년 공모전"
    assert normalize_title(raw) == normalize_title("[외교부] 국제개발협력 청년 공모전 (~9/30)") == "국제개발협력청년공모전"


def test_none_is_empty() -> None:
    assert clean_text(None) == ""
