# ruff: noqa: T201
# (stderr notes are the observable-degradation channel, DEVELOPMENT.md §9)
"""Startup environment snapshot — allowlist-based, never a full env dump.

Design: aixcoding/docs/diagnostics/design.md (signed off 2026-10-25).

Privacy stance: only explicitly allowlisted facts are collected (interpreter,
platform, diagnostics switches). ``os.environ`` is never dumped; caller-supplied
extras are rendered as ``key = value`` lines under a fixed header.
"""

from __future__ import annotations

import platform
import sys
from datetime import UTC, datetime
from pathlib import Path

SNAPSHOT_FILE_NAME = "snapshot.txt"

_FIELDS: tuple[tuple[str, object], ...] = (
    ("python", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"),
    ("implementation", sys.implementation.name),
    ("platform", platform.platform()),
    ("machine", platform.machine()),
    ("os", platform.system() + " " + platform.release()),
)


def take_snapshot(extras: dict[str, object] | None = None) -> str:
    """Render the snapshot as plain text (allowlist fields + caller extras)."""
    lines = [f"# aixcoding diagnostics snapshot {datetime.now(UTC).isoformat(timespec='seconds')}"]
    for key, value in _FIELDS:
        lines.append(f"{key} = {value}")
    for key, value in (extras or {}).items():
        lines.append(f"{key} = {value}")
    return "\n".join(lines) + "\n"


def write_snapshot(session_dir: Path, extras: dict[str, object] | None = None) -> Path | None:
    """Write the snapshot into ``session_dir``; None (stderr note) on failure."""
    path = session_dir / SNAPSHOT_FILE_NAME
    try:
        session_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(take_snapshot(extras), encoding="utf-8")
        return path
    except OSError as exc:
        print(f"aixcoding.snapshot: cannot write {path} ({exc})", file=sys.stderr)
        return None
