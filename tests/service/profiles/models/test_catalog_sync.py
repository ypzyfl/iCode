# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Tests for the periodic model catalog sync.

The sync itself is exercised against a stubbed fetch: what these cover is the
clock, the stop signal, and the in-memory replacement a sync triggers — the
parts that decide whether a server-side change reaches a running session.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

import pytest

from chrys.service.profiles.models import catalog as catalog_module
from chrys.service.profiles.models.catalog import (
    CatalogSyncResult,
    start_periodic_sync,
)
from chrys.service.profiles.models.registry import ModelProfileRegistry

_POLL_INTERVAL = 0.01


def _result(*profile_ids: str) -> CatalogSyncResult:
    return CatalogSyncResult(
        replaced=True,
        version="v1",
        profile_ids=profile_ids,
        default_profile_id=profile_ids[0] if profile_ids else "",
    )


def _wait_for(predicate: Callable[[], bool], *, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(_POLL_INTERVAL)
    return False


def test_syncs_on_the_clock_and_stops_when_signalled(monkeypatch: pytest.MonkeyPatch) -> None:
    """One fetch per interval, and setting the event ends the loop."""
    monkeypatch.setattr(catalog_module, "catalog_url", lambda: "http://127.0.0.1:1/base")
    monkeypatch.setattr(catalog_module, "sync_catalog_blocking", lambda **_kwargs: _result("a"))

    seen: list[CatalogSyncResult] = []
    stop = start_periodic_sync(interval=_POLL_INTERVAL, on_applied=seen.append)
    try:
        assert stop is not None, "a configured source must start the loop"
        assert _wait_for(lambda: len(seen) >= 2), f"expected repeated syncs, got {len(seen)}"
        assert seen[0].profile_ids == ("a",)
    finally:
        stop.set()

    time.sleep(5 * _POLL_INTERVAL)
    settled = len(seen)
    time.sleep(20 * _POLL_INTERVAL)
    assert len(seen) == settled, "a stopped loop must not keep fetching"


def test_without_a_source_there_is_nothing_to_poll(monkeypatch: pytest.MonkeyPatch) -> None:
    """No catalog configured means no thread — the directory stays the user's."""
    monkeypatch.setattr(catalog_module, "catalog_url", lambda: "")
    assert start_periodic_sync() is None


def test_a_failing_callback_does_not_kill_the_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    """The callback refreshes a registry; its failure must not end the clock."""
    monkeypatch.setattr(catalog_module, "catalog_url", lambda: "http://127.0.0.1:1/base")
    monkeypatch.setattr(catalog_module, "sync_catalog_blocking", lambda **_kwargs: _result("a"))

    calls: list[int] = []

    def _boom_once(result: CatalogSyncResult) -> None:
        calls.append(len(calls))
        if len(calls) == 1:
            raise RuntimeError("callback blew up")

    stop = start_periodic_sync(interval=_POLL_INTERVAL, on_applied=_boom_once)
    try:
        assert _wait_for(lambda: len(calls) >= 2), f"loop died after {len(calls)} call(s)"
    finally:
        if stop is not None:
            stop.set()


def test_replace_profiles_forgets_deleted_profiles(tmp_path: Path) -> None:
    """A catalog sync is a wholesale replacement, so the registry must drop too."""
    directory = tmp_path / "models"
    directory.mkdir()
    (directory / "a.yaml").write_text("name: A\n", encoding="utf-8")
    (directory / "b.yaml").write_text("name: B\n", encoding="utf-8")

    registry = ModelProfileRegistry()
    assert registry.load_profiles(directory) == 2

    (directory / "b.yaml").unlink()
    assert registry.replace_profiles(directory) == 1
    assert sorted(registry.list_ids()) == ["a"]
