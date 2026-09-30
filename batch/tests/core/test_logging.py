from __future__ import annotations

import logging
import sys

from collector.core.logging import SecretFilter, register_actions_masks

KEY = "sk-proj-0123456789abcdef"


def test_actions_masks_are_emitted_for_every_value() -> None:
    lines: list[str] = []
    register_actions_masks([KEY, "kaggle-token", ""], emit=lines.append)
    assert lines == [f"::add-mask::{KEY}", "::add-mask::kaggle-token"]


def test_filter_masks_message_and_exception_text() -> None:
    record = logging.LogRecord("x", logging.ERROR, __file__, 1, "401 for %s", (KEY,), None)
    try:
        raise RuntimeError(f"key {KEY} rejected")
    except RuntimeError:
        record.exc_info = sys.exc_info()
    SecretFilter([KEY]).filter(record)
    formatted = logging.Formatter().format(record)
    assert KEY not in formatted
    assert "***" in formatted


def test_longer_values_are_masked_first() -> None:
    record = logging.LogRecord("x", logging.ERROR, __file__, 1, "%s", ("sk-abc-long",), None)
    SecretFilter(["sk-abc", "sk-abc-long"]).filter(record)
    assert record.getMessage() == "***"
