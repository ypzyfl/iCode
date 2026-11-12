# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""State-file tests: the daily cache, the skipped version, and the D2 bookkeeping.

Design: aixcoding/docs/batches/auto-update/design.md §3.2
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path

from chrys.service.aixcoding.update.state import (
    CHECK_INTERVAL_SECONDS,
    FAILURES_THRESHOLD,
    UpdateState,
    create_skip_today,
    drop_failure_tally,
    drop_skip_today,
    failures_path,
    is_today,
    mark_skipped,
    read_failure_tally,
    read_state,
    skip_today_active,
    skip_today_path,
    state_path,
    write_state,
)

DAY = 24 * 60 * 60


def test_state_roundtrip(tmp_path: Path) -> None:
    state = UpdateState(checked_at=1.5, latest="0.36.0", force_upgrade=True, skipped_version="0.35.0")

    assert write_state(tmp_path, state) is True
    assert read_state(tmp_path) == state


def test_read_state_degrades_to_defaults(tmp_path: Path) -> None:
    assert read_state(tmp_path) == UpdateState()

    state_path(tmp_path).write_text("{not json", encoding="utf-8")
    assert read_state(tmp_path) == UpdateState()

    state_path(tmp_path).write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")
    assert read_state(tmp_path) == UpdateState()

    state_path(tmp_path).write_text(json.dumps({"checked_at": "x", "latest": 1}), encoding="utf-8")
    assert read_state(tmp_path) == UpdateState()


def test_read_state_ignores_the_retired_asked_at_field(tmp_path: Path) -> None:
    """A state file from before revision 9 still reads; asked_at is dropped."""
    state_path(tmp_path).write_text(
        json.dumps(
            {"checked_at": 1.5, "latest": "0.36.0", "force_upgrade": False, "skipped_version": "", "asked_at": 2.5}
        ),
        encoding="utf-8",
    )

    assert read_state(tmp_path) == UpdateState(checked_at=1.5, latest="0.36.0")


def test_write_state_is_atomic_json(tmp_path: Path) -> None:
    write_state(tmp_path, UpdateState(latest="0.36.0"))

    data = json.loads(state_path(tmp_path).read_text(encoding="utf-8"))
    assert set(data) == {"checked_at", "latest", "force_upgrade", "skipped_version"}


def test_is_today_uses_the_local_calendar_day() -> None:
    # Pin "now" to local noon: an hour earlier is then always on the same
    # calendar day.  A real clock at 00:30 puts that hour on yesterday, making
    # the assertion depend on when the suite happens to run (revision 15).
    noon = datetime.fromtimestamp(time.time(), tz=UTC).astimezone().replace(hour=12, minute=0, second=0, microsecond=0)
    now = noon.timestamp()

    assert is_today(now, now=now) is True
    assert is_today(now - 3600, now=now) is True  # same day, an hour ago
    assert is_today(now - DAY, now=now) is False  # exactly one day old at least
    assert is_today(0, now=now) is False


def test_check_interval_is_one_day() -> None:
    assert CHECK_INTERVAL_SECONDS == DAY


def test_mark_skipped_persists(tmp_path: Path) -> None:
    state = UpdateState(latest="0.36.0")

    skipped = mark_skipped(tmp_path, state, "0.36.0", now=200.0)
    assert skipped.skipped_version == "0.36.0"
    assert read_state(tmp_path).skipped_version == "0.36.0"


def test_failure_tally_counts_lines(tmp_path: Path) -> None:
    assert read_failure_tally(tmp_path) == (0, None)

    failures_path(tmp_path).write_text("1760000000\n1760000001\n", encoding="utf-8")
    count, mtime = read_failure_tally(tmp_path)

    assert count == 2
    assert mtime is not None and mtime > 0


def test_drop_failure_tally_is_idempotent(tmp_path: Path) -> None:
    failures_path(tmp_path).write_text("x\n", encoding="utf-8")

    drop_failure_tally(tmp_path)
    drop_failure_tally(tmp_path)

    assert not failures_path(tmp_path).exists()


def test_skip_today_marker_lifecycle(tmp_path: Path) -> None:
    now = time.time()

    assert skip_today_active(tmp_path, now=now) is False

    assert create_skip_today(tmp_path, now=now) is True
    assert skip_today_active(tmp_path, now=now) is True
    assert skip_today_active(tmp_path, now=now + DAY) is False  # stale tomorrow

    drop_skip_today(tmp_path)
    drop_skip_today(tmp_path)
    assert not skip_today_path(tmp_path).exists()


def test_failures_threshold_is_three() -> None:
    assert FAILURES_THRESHOLD == 3
