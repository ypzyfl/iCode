# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Locator / reader equivalence tests (scenarios ported from the TS
``collector.test.ts`` end-to-end block: short-id replacement, backup
fallback, hash-over-bytes, malformed vs not-found)."""

from __future__ import annotations

import json
from pathlib import Path

from chrys.aixcoding.telemetry.collector.locator import (
    locate_session_file,
    safe_file_id,
    session_short_id,
)
from chrys.aixcoding.telemetry.collector.reader import read_revision

SESSION_ID = "4201eebc-ca45-4328-8882-272f3d7c41cb"


def test_short_id_follows_the_engine_rule() -> None:
    assert session_short_id(SESSION_ID) == "4201eebcca45"
    assert safe_file_id(SESSION_ID) == SESSION_ID.replace("-", "")
    assert safe_file_id("a/b-c") == "a_bc"


def test_locates_the_session_directory_and_orders_candidates(tmp_path: Path) -> None:
    sessions = tmp_path / "sessions"
    directory = sessions / session_short_id(SESSION_ID)
    directory.mkdir(parents=True)
    (directory / "session.json").write_text("{}", encoding="utf-8")

    located = locate_session_file(str(sessions), SESSION_ID)
    assert located.ordered_paths[0].endswith("session.json")
    assert located.ordered_paths[1].endswith("session.json.bak")


def test_root_unreadable_when_missing() -> None:
    result = locate_session_file(str(Path("does") / "not" / "exist"), SESSION_ID)
    assert result.reason == "root_unreadable"


def test_session_not_found_when_no_candidate_exists(tmp_path: Path) -> None:
    (tmp_path / "sessions").mkdir()
    result = locate_session_file(str(tmp_path / "sessions"), SESSION_ID)
    assert result.reason == "session_not_found"


def test_reader_hashes_exact_bytes_and_falls_back_to_backup(tmp_path: Path) -> None:
    primary = tmp_path / "session.json"
    backup = tmp_path / "session.json.bak"
    primary.write_text('{"broken"', encoding="utf-8")
    backup.write_text('{"ok": true}', encoding="utf-8")

    revision = read_revision([str(primary), str(backup)])
    assert revision.path == str(backup)
    assert revision.envelope == {"ok": True}
    import hashlib

    assert revision.hash == hashlib.sha256(backup.read_bytes()).hexdigest()


def test_reader_malformed_when_all_parses_fail(tmp_path: Path) -> None:
    candidate = tmp_path / "session.json"
    candidate.write_text("{nope", encoding="utf-8")
    assert read_revision([str(candidate)]).reason == "malformed"


def test_reader_not_found_when_all_unreadable(tmp_path: Path) -> None:
    assert read_revision([str(tmp_path / "absent.json")]).reason == "not_found"


def test_reader_accepts_legacy_flat_candidate(tmp_path: Path) -> None:
    flat = tmp_path / f"{SESSION_ID}.json"
    flat.write_text(json.dumps({"meta": {}}), encoding="utf-8")
    revision = read_revision([str(flat)])
    assert revision.envelope == {"meta": {}}
