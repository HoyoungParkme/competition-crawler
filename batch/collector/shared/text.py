"""글자 다듬기. 소스가 준 대회명에 섞인 보이지 않는 문자를 걷는다(CCR-UC-001 UC-S2).

event-us와 콘테스트코리아의 대회명 앞에 BOM(U+FEFF)이 여러 개 붙어 오는 일이 있다(2026-09-27 실측).
노션에 그대로 들어가고, 판정의 대괄호 머리말 떼기도 막는다.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

_SPACES = re.compile(r"\s+")


def clean_text(value: Any) -> str:
    """서식 문자(BOM · 폭 없는 공백 등)를 빼고 공백을 하나로 모은다."""
    text = "".join(ch for ch in str(value or "") if unicodedata.category(ch) != "Cf")
    return _SPACES.sub(" ", text).strip()
