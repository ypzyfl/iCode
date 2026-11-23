# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Minimal unit tests for the real telemetry notice/owner (design §3.1/§3.2).

The V2 probe in test_precondition_probe.py pinned the merge-key contract on a
prototype; these tests pin the same contract on the production classes plus
the lifecycle semantics (bounded flush, idempotent close, worker recreation).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from chrys.service.aixcoding.telemetry.notice import TurnTelemetryNotice, dispatch_telemetry_notice
from chrys.service.aixcoding.telemetry.owner import TelemetryOwner, reset_telemetry_owner_for_tests


def _notice(session: str = "s1", logical: str = "t1", pas: str = "p1", *, saved: bool = True) -> TurnTelemetryNotice:
    return TurnTelemetryNotice(
        session_id=session,
        session_dir=Path("unused") if saved else None,
        logical_turn_id=logical,
        pass_id=pas,
        turn_number=1,
        is_retry=False,
        saved=saved,
    )


@pytest.fixture(autouse=True)
def _fresh_owner() -> None:
    reset_telemetry_owner_for_tests()


@pytest.mark.asyncio
async def test_dispatch_enqueues_and_flush_drains() -> None:
    owner = TelemetryOwner()
    owner.dispatch(_notice())
    worker = owner._workers["s1"]
    assert worker.queue.qsize() == 1
    await owner.flush_session("s1", timeout=2.0)
    assert worker.queue.qsize() == 0  # join() returned: every task done


@pytest.mark.asyncio
async def test_same_pass_merges_and_new_pass_survives() -> None:
    owner = TelemetryOwner()
    for _ in range(3):
        owner.dispatch(_notice())
    owner.dispatch(_notice(pas="p2"))
    assert owner._workers["s1"].queue.qsize() == 2
    await owner.flush_session("s1", timeout=2.0)


@pytest.mark.asyncio
async def test_unsaved_notice_is_skipped() -> None:
    owner = TelemetryOwner()
    owner.dispatch(_notice(saved=False))
    assert "s1" not in owner._workers
    assert owner._pending == {}


@pytest.mark.asyncio
async def test_sessions_are_isolated_and_close_is_idempotent() -> None:
    owner = TelemetryOwner()
    owner.dispatch(_notice(session="s1"))
    owner.dispatch(_notice(session="s2"))
    assert set(owner._workers) == {"s1", "s2"}
    await owner.flush_session("s1", timeout=2.0)
    owner.close_session("s1")
    owner.close_session("s1")  # idempotent
    assert set(owner._workers) == {"s2"}


@pytest.mark.asyncio
async def test_dispatch_after_close_recreates_worker() -> None:
    owner = TelemetryOwner()
    owner.dispatch(_notice())
    owner.close_session("s1")
    owner.dispatch(_notice(pas="p2"))
    assert "s1" in owner._workers
    await owner.flush_session("s1", timeout=2.0)
    owner.close_session("s1")


@pytest.mark.asyncio
async def test_dispatch_entry_contains_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(notice: TurnTelemetryNotice) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr("chrys.service.aixcoding.telemetry.owner.TelemetryOwner.dispatch", _boom)
    dispatch_telemetry_notice(_notice())  # must not raise
