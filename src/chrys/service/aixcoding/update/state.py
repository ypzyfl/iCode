# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Persisted state for the AIxCoding auto-update flow.

Three files under the config dir:

* ``aixcoding-update.json`` — the daily check cache (``checked_at`` /
  ``latest`` / ``force_upgrade`` / ``skipped_version``), written atomically.
* ``update-failures`` — the failure tally the detached update wrapper
  appends one line to whenever the update command fails (design D2: the
  wrapper never deletes anything).  Consumed here: an mtime from before
  today means the tally is stale and is dropped wholesale ("retry
  tomorrow" = the count does not carry across days); ``FAILURES_THRESHOLD``
  or more lines turn into the skip-today marker and the tally is removed.
* ``update-skip-today`` — created only here, when the tally trips the
  threshold.  While its mtime is today the whole update check is off for
  the day; a stale one is deleted on the next start.  Deleting the file by
  hand is the documented "retry right now" escape hatch.

Design: aixcoding/docs/batches/auto-update/design.md
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from chrys.foundation.platform.files import atomic_write_text

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 24 * 60 * 60
STATE_FILE_NAME = "aixcoding-update.json"
FAILURES_FILE_NAME = "update-failures"
SKIP_TODAY_FILE_NAME = "update-skip-today"
FAILURES_THRESHOLD = 3


@dataclass(frozen=True, slots=True)
class UpdateState:
    """The persisted snapshot of the last check and the user's answers.

    ``asked_at`` (the once-per-calendar-day "later" record) was removed in
    design revision 9: "remind next time" no longer suppresses anything, so
    there is nothing to remember; a stale field in an old state file is
    ignored on read.
    """

    checked_at: float = 0.0
    latest: str = ""
    force_upgrade: bool = False
    skipped_version: str = ""


def state_path(config_dir: Path) -> Path:
    return config_dir / STATE_FILE_NAME


def failures_path(config_dir: Path) -> Path:
    return config_dir / FAILURES_FILE_NAME


def skip_today_path(config_dir: Path) -> Path:
    return config_dir / SKIP_TODAY_FILE_NAME


def read_state(config_dir: Path) -> UpdateState:
    """The cached state; unreadable/corrupt content degrades to the defaults."""
    try:
        data = json.loads(state_path(config_dir).read_text(encoding="utf-8"))
    except OSError, ValueError:
        return UpdateState()
    if not isinstance(data, dict):
        return UpdateState()
    checked_at = data.get("checked_at")
    latest = data.get("latest")
    force_upgrade = data.get("force_upgrade")
    skipped_version = data.get("skipped_version")
    if not isinstance(checked_at, int | float) or not isinstance(latest, str):
        return UpdateState()
    return UpdateState(
        checked_at=float(checked_at),
        latest=latest,
        force_upgrade=force_upgrade is True,
        skipped_version=skipped_version if isinstance(skipped_version, str) else "",
    )


def write_state(config_dir: Path, state: UpdateState) -> bool:
    """Persist ``state`` atomically; False when the write failed."""
    payload = json.dumps(
        {
            "checked_at": state.checked_at,
            "latest": state.latest,
            "force_upgrade": state.force_upgrade,
            "skipped_version": state.skipped_version,
        }
    )
    try:
        atomic_write_text(state_path(config_dir), payload + "\n")
    except OSError:
        logger.debug("update state: could not save %s", state_path(config_dir), exc_info=True)
        return False
    return True


def _local_date(timestamp: float) -> datetime:
    # Local wall-clock day (tz=UTC + astimezone is the repo's DTZ-clean spelling
    # of the naive-local fromtimestamp): "today" is the user's calendar day.
    return datetime.fromtimestamp(timestamp, tz=UTC).astimezone()


def is_today(timestamp: float, *, now: float) -> bool:
    """Whether ``timestamp`` falls on the same local calendar day as ``now``."""
    if timestamp <= 0:
        return False
    return _local_date(timestamp).date() == _local_date(now).date()


def read_failure_tally(config_dir: Path) -> tuple[int, float | None]:
    """The wrapper-appended failure tally: ``(line count, mtime)``; ``(0, None)`` when absent."""
    path = failures_path(config_dir)
    try:
        mtime = path.stat().st_mtime
        with path.open(encoding="utf-8", errors="replace") as stream:
            count = sum(1 for line in stream if line.strip())
    except OSError:
        return 0, None
    return count, mtime


def drop_failure_tally(config_dir: Path) -> None:
    """Remove the tally file; a missing file is already the goal."""
    failures_path(config_dir).unlink(missing_ok=True)


def skip_today_active(config_dir: Path, *, now: float) -> bool:
    """Whether the skip-today marker exists and was written today."""
    try:
        mtime = skip_today_path(config_dir).stat().st_mtime
    except OSError:
        return False
    return is_today(mtime, now=now)


def create_skip_today(config_dir: Path, *, now: float) -> bool:
    """Write the skip-today marker; False when the write failed."""
    try:
        atomic_write_text(skip_today_path(config_dir), f"{now}\n")
    except OSError:
        logger.debug("update state: could not save %s", skip_today_path(config_dir), exc_info=True)
        return False
    return True


def drop_skip_today(config_dir: Path) -> None:
    """Remove a stale skip-today marker; a missing file is already the goal."""
    skip_today_path(config_dir).unlink(missing_ok=True)


def mark_skipped(config_dir: Path, state: UpdateState, version: str, *, now: float) -> UpdateState:
    """Record the skipped version; returns the updated snapshot.

    ``now`` is kept in the signature for the flow's call symmetry; the skip
    needs no timestamp of its own (a skip is a version, not a day).
    """
    updated = replace(state, skipped_version=version)
    write_state(config_dir, updated)
    return updated
