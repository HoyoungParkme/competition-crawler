from __future__ import annotations

import logging

from collector.core.logging import SecretFilter, register_actions_masks, secret_variants

NOTION_ID = "0123456789abcdef0123456789abcdef"
DASHED = "01234567-89ab-cdef-0123-456789abcdef"


def test_notion_id_is_masked_in_both_shapes() -> None:
    variants = secret_variants([NOTION_ID])
    assert NOTION_ID in variants and DASHED in variants


def test_actions_masks_are_emitted_for_every_variant() -> None:
    lines: list[str] = []
    register_actions_masks([NOTION_ID, "sk-test"], emit=lines.append)
    assert f"::add-mask::{DASHED}" in lines
    assert "::add-mask::sk-test" in lines


def test_filter_masks_message_and_exception_text() -> None:
    record = logging.LogRecord("x", logging.ERROR, __file__, 1, "404 for %s", (DASHED,), None)
    try:
        raise RuntimeError(f"object {DASHED} not found")
    except RuntimeError:
        import sys

        record.exc_info = sys.exc_info()
    SecretFilter([NOTION_ID]).filter(record)
    formatted = logging.Formatter().format(record)
    assert DASHED not in formatted
    assert "***" in formatted
