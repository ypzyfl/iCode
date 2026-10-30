# (tests — asserts are pytest idiom, Chinese prose is the data)
"""Tests for chrys.kernel.aixcoding.diagnostics.logging_support."""

from __future__ import annotations

import logging
from pathlib import Path

from chrys.kernel.aixcoding.diagnostics.config import DiagnosticsConfig, LoggingConfig
from chrys.kernel.aixcoding.diagnostics.logging_support import (
    _Marker,
    get_logger,
    setup_logging,
)


def make_cfg(level: int = logging.INFO, panel: bool = False) -> DiagnosticsConfig:
    return DiagnosticsConfig(logging=LoggingConfig(level=level, panel=panel), source=None)


def test_get_logger_names():
    assert get_logger().name == "aixcoding"
    assert get_logger("telemetry").name == "aixcoding.telemetry"


def test_setup_creates_sink_and_records(tmp_path: Path, aix_logger_state):
    log_path = setup_logging(make_cfg(), tmp_path)
    assert log_path is not None and log_path.parent == tmp_path / "aixcoding-logs"
    get_logger("telemetry").warning("hello sink")
    for h in logging.getLogger("aixcoding").handlers:
        h.flush()
    assert "hello sink" in log_path.read_text(encoding="utf-8")


def test_setup_is_idempotent(tmp_path: Path, aix_logger_state):
    first = setup_logging(make_cfg(), tmp_path)
    second = setup_logging(make_cfg(), tmp_path)
    assert first == second
    markers = [h for h in logging.getLogger("aixcoding").handlers if isinstance(h, _Marker)]
    assert len(markers) == 1


def test_propagate_follows_panel_switch(tmp_path: Path, aix_logger_state):
    logger = logging.getLogger("aixcoding")
    setup_logging(make_cfg(panel=True), tmp_path)
    assert logger.propagate is True
    setup_logging(make_cfg(panel=False), tmp_path)
    assert logger.propagate is False


def test_level_applies_to_subtree(tmp_path: Path, aix_logger_state):
    setup_logging(make_cfg(level=logging.WARNING), tmp_path)
    assert logging.getLogger("aixcoding").level == logging.WARNING


def test_sink_failure_degrades_with_stderr_note(tmp_path: Path, aix_logger_state, capsys):
    blocker = tmp_path / "blocker"
    blocker.write_text("i am a file", encoding="utf-8")
    result = setup_logging(make_cfg(), blocker)  # mkdir over a file fails
    assert result is None
    assert "file sink unavailable" in capsys.readouterr().err
