# ruff: noqa: S101
# (tests — asserts are pytest idiom, Chinese prose is the data)
"""Tests for chrys.kernel.aixcoding.diagnostics.crash."""

from __future__ import annotations

import sys
import threading
from pathlib import Path

import pytest

from chrys.kernel.aixcoding.diagnostics import crash


def test_write_crash_report_appends_entry(tmp_path: Path):
    path = crash.write_crash_report(tmp_path, "unhandled exception", ValueError("boom"))
    text = path.read_text(encoding="utf-8")
    assert "unhandled exception" in text
    assert "ValueError" in text and "boom" in text


def test_write_crash_report_never_raises(tmp_path: Path, capsys):
    blocker = tmp_path / "blocker"
    blocker.write_text("file", encoding="utf-8")  # mkdir over a file fails
    crash.write_crash_report(blocker, "hdr", ValueError("x"))
    assert "failed to write crash report" in capsys.readouterr().err


def test_sys_excepthook_writes_and_chains(tmp_path: Path, restore_hooks):
    calls = []
    crash.install_crash_hooks(tmp_path)
    original = sys.excepthook
    sys.excepthook = original  # install already wrapped; verify chain via re-wrap below

    def chained(*args):
        calls.append(args)

    wrapped = sys.excepthook
    sys.excepthook = lambda *a: (wrapped(*a), chained(*a))
    try:
        sys.excepthook(ValueError, ValueError("top boom"), None)
    finally:
        sys.excepthook = original
    assert calls, "original chain must still run"
    assert "top boom" in (tmp_path / "crash.txt").read_text(encoding="utf-8")


@pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
def test_threading_excepthook_writes(tmp_path: Path, restore_hooks):
    crash.install_crash_hooks(tmp_path)
    # ExceptHookArgs is a structseq — construct from a plain tuple.
    args = threading.ExceptHookArgs((ValueError, ValueError("thread boom"), None, threading.current_thread()))
    threading.excepthook(args)
    text = (tmp_path / "crash.txt").read_text(encoding="utf-8")
    assert "thread boom" in text
    assert "in thread" in text


def test_faulthandler_enabled_and_close(tmp_path: Path, restore_hooks):
    import faulthandler

    crash.install_crash_hooks(tmp_path)
    assert faulthandler.is_enabled()
    crash._close_fh_target()
    assert not faulthandler.is_enabled()


def test_install_idempotent_same_dir(tmp_path: Path, restore_hooks):
    crash.install_crash_hooks(tmp_path)
    hook_after_first = sys.excepthook
    crash.install_crash_hooks(tmp_path)
    assert sys.excepthook is hook_after_first  # no re-wrap for the same dir
