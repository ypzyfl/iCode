# ruff: noqa: S101
# (tests — asserts are pytest idiom, Chinese prose is the data)
"""Behavior anchor tests: the F6 panel really accepts aixcoding records.

These tests import the real upstream symbols (DEVELOPMENT.md §5: anchors are
called for real, never mocked) so an upstream refactor of MODULE_ORDER /
_TuiLogHandler turns them red and forces the customization to follow.
"""

from __future__ import annotations

import logging

from chrys.app.tui.screens.logs.screen import MODULE_ORDER, MODULE_WHITELIST, _TuiLogHandler


def test_module_order_lists_aixcoding():
    assert "aixcoding" in MODULE_ORDER


def test_whitelist_derives_from_module_order():
    # The derivation upstream relies on: whitelist follows MODULE_ORDER.
    assert frozenset(MODULE_ORDER) == MODULE_WHITELIST
    assert "aixcoding" in MODULE_WHITELIST


def test_tui_handler_buffers_aixcoding_record():
    handler = _TuiLogHandler()
    handler.setFormatter(logging.Formatter("%(name)s %(message)s"))
    record = logging.LogRecord("aixcoding.telemetry", logging.WARNING, __file__, 1, "panel line", None, None)
    handler.emit(record)
    lines, total = handler.snapshot("aixcoding", 0)
    assert total == 1
    assert len(lines) == 1
    assert "panel line" in lines[0]


def test_tui_handler_ignores_unknown_toplevel():
    handler = _TuiLogHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    record = logging.LogRecord("some.other.namespace", logging.WARNING, __file__, 1, "no tab", None, None)
    handler.emit(record)
    lines, total = handler.snapshot("some", 0)
    assert (lines, total) == ([], 0)
