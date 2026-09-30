"""로그 설정과 비밀값 가리기.

요청 헤더와 요청 객체는 로그에 찍지 않는다. 그래도 새는 경우에 대비해 두 겹으로 가린다
(CCR-INFRA-001 5.4 · CCR-UC-001 UC-S7 7).
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable, Iterable


def _to_mask(values: Iterable[str]) -> list[str]:
    # 긴 것부터 가려야 짧은 것이 긴 것의 일부를 먼저 지우지 않는다
    return sorted({v for v in values if v}, key=len, reverse=True)


def register_actions_masks(
    values: Iterable[str], emit: Callable[[str], None] | None = None
) -> None:
    """CCR-MS-001#logging.register_actions_masks

    GitHub Actions에 가릴 값을 알린다. 어떤 출력보다 먼저 부른다.
    """
    write = emit or (lambda line: print(line, flush=True))
    for value in _to_mask(values):
        write(f"::add-mask::{value}")


class SecretFilter(logging.Filter):
    def __init__(self, values: Iterable[str]) -> None:
        super().__init__()
        self._variants = _to_mask(values)

    def _mask(self, text: str) -> str:
        for variant in self._variants:
            text = text.replace(variant, "***")
        return text

    def filter(self, record: logging.LogRecord) -> bool:
        """CCR-MS-001#SecretFilter.filter"""
        if self._variants:
            record.msg = self._mask(record.getMessage())
            record.args = ()
            # 예외의 원문도 가린다. 미리 만들어 두면 포매터가 다시 만들지 않는다
            if record.exc_info and not record.exc_text:
                record.exc_text = logging.Formatter().formatException(record.exc_info)
            if record.exc_text:
                record.exc_text = self._mask(record.exc_text)
            if record.stack_info:
                record.stack_info = self._mask(record.stack_info)
        return True


def setup_logging(secrets: Iterable[str]) -> None:
    """CCR-MS-001#logging.setup_logging"""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    handler.addFilter(SecretFilter(secrets))
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(logging.INFO)
    # 라이브러리의 요청 로그에는 헤더가 섞일 수 있어 경고 이상만 남긴다
    for noisy in ("httpx", "httpcore", "openai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
