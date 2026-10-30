# (tests — asserts are pytest idiom, Chinese prose is the data)
"""Entry wiring: app.py main() -> aixcoding_startup() -> ensure_file_sink.

Design: aixcoding/docs/auth-logging/design.md §验证方式 2 (signed off
2026-10-30). The main() anchor test is an architecture-level regression
guard: an upstream refactor that drops the wiring call turns it red.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from chrys.app.aixcoding import startup
from chrys.kernel.aixcoding.diagnostics import logging_support
from chrys.kernel.aixcoding.diagnostics.logging_support import _Marker

AIX_LOGGER = logging.getLogger("aixcoding")


def markers() -> list[_Marker]:
    return [h for h in AIX_LOGGER.handlers if isinstance(h, _Marker)]


# --- ① ensure_file_sink: idempotent + fail-safe ---------------------------------


def test_ensure_file_sink_idempotent(tmp_path: Path, aix_logger_state):
    first = logging_support.ensure_file_sink(config_dir=tmp_path)
    second = logging_support.ensure_file_sink(config_dir=tmp_path)
    assert first is not None
    assert first == second
    assert first == tmp_path / logging_support.LOG_DIR_NAME / logging_support.LOG_FILE_NAME
    assert len(markers()) == 1  # second call reused the existing sink


def test_ensure_file_sink_fail_safe(tmp_path: Path, monkeypatch, capsys):
    def boom(config_dir=None):
        raise RuntimeError("unexpected failure")

    monkeypatch.setattr("chrys.kernel.aixcoding.diagnostics.config.load_config", boom)
    result = logging_support.ensure_file_sink(config_dir=tmp_path)
    assert result is None  # never raises
    assert "file sink setup failed" in capsys.readouterr().err  # §9 stderr note


# --- ② aixcoding_startup: per-task fail-safe, aggregate idempotent ---------------


def test_startup_contains_task_failures(monkeypatch, capsys):
    calls = []

    def ok():
        calls.append("ok")

    def boom():
        raise RuntimeError("task exploded")

    def after():
        calls.append("after")

    monkeypatch.setattr(startup, "_TASKS", (ok, boom, after))
    startup.aixcoding_startup()  # must not raise
    assert calls == ["ok", "after"]  # failing task did not block the rest
    assert "task boom failed" in capsys.readouterr().err  # §9 stderr note


def test_startup_idempotent_when_tasks_are(tmp_path: Path, monkeypatch, aix_logger_state):
    monkeypatch.setattr(
        startup,
        "_TASKS",
        (lambda: logging_support.ensure_file_sink(config_dir=tmp_path),),
    )
    startup.aixcoding_startup()
    startup.aixcoding_startup()
    assert len(markers()) == 1  # aggregate idempotence = task idempotence


# --- ③ main() wiring anchor (upstream refactor drops it -> red) ------------------


def test_main_calls_aixcoding_startup(monkeypatch):
    from chrys.app.cli import app as cli_app

    # Assumes main()'s in-function import (app.py:175): patching the source module
    # attribute only reaches a from-import resolved on each call — a top-level
    # import in upstream would miss the patch and turn this red (by design then:
    # re-confirm the wiring shape).
    called = []
    monkeypatch.setattr("chrys.app.aixcoding.startup.aixcoding_startup", lambda: called.append(True))
    monkeypatch.setattr(sys, "argv", ["icode", "--version"])
    rc = cli_app.main()
    assert rc == 0
    assert called == [True]


# --- ④ startup.py placement: app-tier host-seam package -------------------------


def test_startup_placement_and_task_registration():
    file = Path(startup.__file__)
    assert file.parts[-3:-1] == ("app", "aixcoding")  # host-seam package
    assert (file.parent / "tui").is_dir()  # tui sibling (same placement rule)
    assert callable(startup.aixcoding_startup)
    assert (startup._ensure_file_sink,) == startup._TASKS  # file-sink task registered
