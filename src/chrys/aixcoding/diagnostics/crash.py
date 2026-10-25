# ruff: noqa: T201
# (stderr notes are the observable-degradation channel, DEVELOPMENT.md §9)
"""Crash capture: faulthandler + interpreter/thread excepthooks + atexit safety.

Design: aixcoding/docs/diagnostics/design.md (signed off 2026-10-25).

Installed by the launcher (``python -m chrys.aixcoding.diagnostics.launcher``)
or by any embedder. Diagnostics must never become a fault source: every hook
wraps its work in a broad except, and original hooks stay chained so upstream
behavior is preserved. Crash artifacts land in a per-run session directory as
plain text files.
"""

from __future__ import annotations

import atexit
import contextlib
import faulthandler
import os
import sys
import threading
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import IO

CRASH_FILE_NAME = "crash.txt"

_fh_target: IO[str] | None = None  # keep the faulthandler file object alive
_installed_dir: Path | None = None


def session_stem() -> str:
    """Stable, filesystem-safe run identifier (timestamp + pid)."""
    now = datetime.now(UTC)
    return f"{now.strftime('%Y%m%dT%H%M%SZ')}-{os.getpid()}"


def write_crash_report(session_dir: Path, header: str, exc: BaseException | None) -> Path:
    """Append one human-readable crash entry to the session's crash file."""
    crash_path = session_dir / CRASH_FILE_NAME
    try:
        session_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).isoformat(timespec="seconds")
        if exc is not None:
            detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        else:
            detail = "(no exception object)\n"
        with crash_path.open("a", encoding="utf-8") as fh:
            fh.write(f"=== {stamp} {header} ===\n{detail}\n")
    except Exception:
        print(f"aixcoding.crash: failed to write crash report to {crash_path}", file=sys.stderr)
    return crash_path


def _wrap_sys_hook(session_dir: Path) -> None:
    original = sys.excepthook

    def hook(exc_type, exc_value, exc_tb) -> None:
        write_crash_report(session_dir, "unhandled exception", exc_value)
        if original is not None:
            with contextlib.suppress(Exception):  # original hook must not break us
                original(exc_type, exc_value, exc_tb)

    sys.excepthook = hook


def _wrap_threading_hook(session_dir: Path) -> None:
    original = threading.excepthook

    def hook(args: threading.ExceptHookArgs) -> None:
        thread_name = args.thread.name if args.thread is not None else "<unknown>"
        write_crash_report(session_dir, f"unhandled exception in thread {thread_name!r}", args.exc_value)
        if original is not None:
            with contextlib.suppress(Exception):
                original(args)

    threading.excepthook = hook


def install_crash_hooks(session_dir: Path) -> Path:
    """Install all crash capture for this run into ``session_dir``.

    Idempotent per process: a second call with the same directory is a no-op
    (hooks stay pointed at the first session). Returns the crash file path.
    """
    global _fh_target, _installed_dir
    if _installed_dir == session_dir:
        return session_dir / CRASH_FILE_NAME
    _installed_dir = session_dir
    try:
        session_dir.mkdir(parents=True, exist_ok=True)
        _fh_target = (session_dir / "faulthandler.txt").open("w", encoding="utf-8")
        faulthandler.enable(file=_fh_target)
        atexit.register(_close_fh_target)
    except Exception as exc:
        print(f"aixcoding.crash: faulthandler setup failed ({exc})", file=sys.stderr)
    _wrap_sys_hook(session_dir)
    _wrap_threading_hook(session_dir)
    return session_dir / CRASH_FILE_NAME


def _close_fh_target() -> None:
    global _fh_target
    if _fh_target is not None:
        with contextlib.suppress(Exception):
            faulthandler.disable()
            _fh_target.close()
    _fh_target = None
