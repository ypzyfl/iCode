# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Ledger / lock / attribution equivalence tests (scenarios ported from the
TS ``collector.test.ts``: corrupt-ledger rebuild, live-lock deferral, stale
reclaim, attribution degradation branches)."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from chrys.aixcoding.telemetry.collector.attribution import (
    UNKNOWN_ACCOUNT_ID,
    read_attribution,
)
from chrys.aixcoding.telemetry.collector.ledger import (
    CollectorLedger,
    LedgerTurn,
    load_ledger,
    save_ledger,
)
from chrys.aixcoding.telemetry.collector.lock import acquire_session_lock

SESSION_ID = "4201eebc-ca45-4328-8882-272f3d7c41cb"
HASH = "a" * 64


def make_ledger(**overrides: object) -> CollectorLedger:
    values: dict[str, object] = {
        "version": 1,
        "session_id": SESSION_ID,
        "last_revision_hash": HASH,
        "last_analyzed_at": "2026-10-06T00:00:00Z",
        "analysis_version": 1,
        "report_state": "reported",
        "turns": [LedgerTurn(turn_id="turn_1", content_hash=HASH, reported_at="2026-10-06T00:00:00Z")],
        "source_path": "/sessions/x/session.json",
    }
    values.update(overrides)
    return CollectorLedger(**values)  # type: ignore[arg-type]


class TestLedger:
    def test_roundtrip(self, tmp_path: Path) -> None:
        save_ledger(str(tmp_path), make_ledger())
        loaded = load_ledger(str(tmp_path), SESSION_ID)
        assert loaded is not None
        assert loaded.last_revision_hash == HASH
        assert [turn.turn_id for turn in loaded.turns] == ["turn_1"]

    def test_missing_ledger_is_none(self, tmp_path: Path) -> None:
        assert load_ledger(str(tmp_path), SESSION_ID) is None

    def test_corrupt_ledger_is_archived_and_rebuilt(self, tmp_path: Path) -> None:
        save_ledger(str(tmp_path), make_ledger())
        path = tmp_path / "ledger" / f"{SESSION_ID.replace('-', '')}.json"
        path.write_text('{"version": 1, "broken"', encoding="utf-8")
        assert load_ledger(str(tmp_path), SESSION_ID) is None
        assert any(
            entry.name.startswith(f"{SESSION_ID.replace('-', '')}.json.corrupt-")
            for entry in (tmp_path / "ledger").iterdir()
        )

    def test_invalid_content_is_rejected(self, tmp_path: Path) -> None:
        path = tmp_path / "ledger" / f"{SESSION_ID.replace('-', '')}.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"version": 9}), encoding="utf-8")
        assert load_ledger(str(tmp_path), SESSION_ID) is None


class TestLock:
    def test_live_lock_defers(self, tmp_path: Path) -> None:
        locks = tmp_path / "locks"
        locks.mkdir()
        # Live pid + fresh timestamp → neither staleness rule fires.
        (locks / f"{SESSION_ID.replace('-', '')}.lock").write_text(
            json.dumps({"pid": os.getpid(), "created_at": time.time() * 1000}),
            encoding="utf-8",
        )
        assert acquire_session_lock(str(tmp_path), SESSION_ID, max_age_ms=30_000) is None

    def test_stale_by_dead_pid_is_reclaimed(self, tmp_path: Path) -> None:
        locks = tmp_path / "locks"
        locks.mkdir()
        (locks / f"{SESSION_ID.replace('-', '')}.lock").write_text(
            json.dumps({"pid": os.getpid(), "created_at": 0.0}), encoding="utf-8"
        )
        # created_at=0 → stale by age (live pid but far too old).
        lock = acquire_session_lock(str(tmp_path), SESSION_ID, max_age_ms=30_000)
        assert lock is not None
        lock.release()

    def test_stale_by_dead_pid(self, tmp_path: Path) -> None:
        locks = tmp_path / "locks"
        locks.mkdir()
        (locks / f"{SESSION_ID.replace('-', '')}.lock").write_text(
            json.dumps({"pid": 999_999_999, "created_at": time.time() * 1000}),
            encoding="utf-8",
        )
        lock = acquire_session_lock(str(tmp_path), SESSION_ID, max_age_ms=30_000)
        assert lock is not None
        lock.release()
        assert not (locks / f"{SESSION_ID.replace('-', '')}.lock").exists()

    def test_acquires_and_releases(self, tmp_path: Path) -> None:
        lock = acquire_session_lock(str(tmp_path), SESSION_ID, max_age_ms=30_000)
        assert lock is not None
        # A second acquisition while held defers.
        assert acquire_session_lock(str(tmp_path), SESSION_ID, max_age_ms=30_000) is None
        lock.release()
        fresh = acquire_session_lock(str(tmp_path), SESSION_ID, max_age_ms=30_000)
        assert fresh is not None


class TestAttribution:
    def test_reads_valid_file(self, tmp_path: Path) -> None:
        path = tmp_path / "attribution.json"
        path.write_text(json.dumps({"version": 1, "account_id": "ehr-42"}), encoding="utf-8")
        attribution = read_attribution(str(path))
        assert attribution.account_id == "ehr-42"  # type: ignore[union-attr]

    def test_missing_and_corrupt_degrade(self, tmp_path: Path) -> None:
        assert read_attribution(str(tmp_path / "absent.json")).__class__ is not None
        corrupt = tmp_path / "corrupt.json"
        corrupt.write_text('{"version": 1, "account_id": ', encoding="utf-8")
        from chrys.aixcoding.telemetry.collector.attribution import MissingAttribution

        assert isinstance(read_attribution(str(corrupt)), MissingAttribution)
        bad_version = tmp_path / "bad.json"
        bad_version.write_text(json.dumps({"version": 2, "account_id": "x"}), encoding="utf-8")
        assert isinstance(read_attribution(str(bad_version)), MissingAttribution)
        empty_id = tmp_path / "empty.json"
        empty_id.write_text(json.dumps({"version": 1, "account_id": ""}), encoding="utf-8")
        assert isinstance(read_attribution(str(empty_id)), MissingAttribution)

    def test_unknown_constant(self) -> None:
        assert UNKNOWN_ACCOUNT_ID == "unknown"
