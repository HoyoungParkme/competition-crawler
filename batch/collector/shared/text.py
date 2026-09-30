"""글자 다듬기(CCR-UC-001 UC-S2 4).

대회명은 앞뒤의 공백만 정리하고 그 밖에는 소스가 준 그대로 둔다. 앞뒤에 붙은 보이지 않는 서식 문자
(BOM · 폭 없는 공백)도 공백처럼 뗀다. event-us와 콘테스트코리아의 대회명 앞에 BOM(U+FEFF)이 여러 개
붙어 오는 일이 있다(2026-09-27 실측). 노션에 그대로 들어가고, 판정의 대괄호 머리말 떼기도 막는다.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

_SPACES = re.compile(r"\s+")


def _blank(ch: str) -> bool:
    return ch.isspace() or unicodedata.category(ch) == "Cf"


def clean_text(value: Any) -> str:
    """CCR-MS-001#text.clean_text

    앞뒤의 공백과 서식 문자만 뗀다. 가운데는 건드리지 않는다.
    """
    text = str(value or "")
    start, end = 0, len(text)
    while start < end and _blank(text[start]):
        start += 1
    while end > start and _blank(text[end - 1]):
        end -= 1
    return text[start:end]


def html_text(value: Any) -> str:
    """CCR-MS-001#text.html_text

    HTML에서 꺼낸 글자. 브라우저가 보여 주는 대로 이어진 공백을 하나로 모은 뒤 앞뒤를 정리한다.
    """
    return clean_text(_SPACES.sub(" ", str(value or "")))
