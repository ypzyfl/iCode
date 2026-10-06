# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Per-session file lock (TS ``lock.ts``): ``O_CREAT | O_EXCL`` semantics.

The lock lives in the state directory, not the engine session directory. On
an existing lock: stale judgement (pid not alive, or file older than the
limit → delete and retry once); still locked → caller defers with
``EXIT_DEFERRED`` (42). Normal exits release; crash residue is reclaimed by
the stale check.
"""

from __future__ import annotations

import contextlib
import ctypes
import json
import os
import socket
import sys
import time
from pathlib import Path

from chrys.aixcoding.telemetry.collector.locator import safe_file_id

_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


class SessionLock:
    """Releases the lock file on ``release()``."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def release(self) -> None:
        with contextlib.suppress(OSError):
            self._path.unlink()


def _pid_alive(pid: int) -> bool:
    if sys.platform == "win32":
        return _pid_alive_windows(pid)
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        # EPERM: process exists but probing is not permitted.
        return True
    except OSError:
        return False


def _pid_alive_windows(pid: int) -> bool:
    # os.kill(pid, 0) is NOT a liveness probe on Windows: signal 0 IS
    # CTRL_C_EVENT there, so it broadcasts a real Ctrl+C to the whole
    # console process group (CPython win32_kill routes sig 0 straight
    # into the console-event branch). The TS reference's
    # process.kill(pid, 0) is a probe — libuv special-cases sig 0 — so
    # replicate that with OpenProcess.
    windll = getattr(ctypes, "windll", None)
    if windll is None:
        # Cannot probe: assume alive (conservative — never reclaim a
        # live lock; the age rule still bounds staleness).
        return True
    handle = windll.kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return False
    windll.kernel32.CloseHandle(handle)
    return True


def _is_stale(record: dict[str, object], max_age_ms: int) -> bool:
    pid = record.get("pid")
    if not isinstance(pid, int) or not _pid_alive(pid):
        return True
    created_at = record.get("created_at")
    if not isinstance(created_at, (int, float)):
        return True
    return (time.time() * 1000) - created_at > max_age_ms


def acquire_session_lock(state_dir: str, session_id: str, max_age_ms: int) -> SessionLock | None:
    """Acquire the per-session lock; ``None`` means deferred (EXIT_DEFERRED)."""
    locks_directory = Path(state_dir) / "locks"
    locks_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = locks_directory / f"{safe_file_id(session_id)}.lock"
    record = {
        "pid": os.getpid(),
        "created_at": time.time() * 1000,
        "host": socket.gethostname(),
    }
    for _attempt in range(2):
        try:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(record, handle)
            return SessionLock(path)
        # Exists → stale judgement.
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except OSError, json.JSONDecodeError:
            existing = {}
        if not isinstance(existing, dict) or not _is_stale(existing, max_age_ms):
            return None
        try:
            path.unlink()
        except OSError:
            return None
    return None
