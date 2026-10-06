# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Session file location and own-state file naming (TS baseline ``locator.ts``).

``short_id`` follows the engine's ``session_ids.py::session_short_id``
character rule and is used only for locating the engine session directory;
``safe_file_id`` applies the same substitution to the full id without
truncation — uniqueness comes from the full id — and names the
ledger/locks/reports files.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

LocateFailure = ("root_unreadable", "session_not_found")


@dataclass(frozen=True, slots=True)
class LocatedSession:
    ordered_paths: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LocateFailureResult:
    reason: str


def _sanitize(session_id: str) -> str:
    return session_id.replace("/", "_").replace("\\", "_").replace("-", "")


def session_short_id(session_id: str) -> str:
    return _sanitize(session_id)[:12]


def safe_file_id(session_id: str) -> str:
    return _sanitize(session_id)


def locate_session_file(sessions_root: str, session_id: str) -> LocatedSession | LocateFailureResult:
    """Return priority-ordered candidates (primary → backup → legacy flat).

    Any candidate existing counts; reading and degradation are the revision
    reader's job.
    """
    if not Path(sessions_root).is_dir():
        return LocateFailureResult(reason="root_unreadable")
    short_id = session_short_id(session_id)
    directory = Path(sessions_root) / short_id
    candidates = [
        directory / "session.json",
        directory / "session.json.bak",
    ]
    # Legacy flat layout only for ids without path fragments (no traversal).
    if "/" not in session_id and "\\" not in session_id and ".." not in session_id:
        candidates.append(Path(sessions_root) / f"{session_id}.json")
    if not any(candidate.is_file() for candidate in candidates):
        return LocateFailureResult(reason="session_not_found")
    return LocatedSession(ordered_paths=tuple(str(candidate) for candidate in candidates))
