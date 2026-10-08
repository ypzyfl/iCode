# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""End-to-end tests for the Chrys session reporting collector (EventBus -> collector -> mock server)."""

from __future__ import annotations

from collections.abc import Iterator

import httpx
import pytest
from scripts import telemetry_mock
from scripts.telemetry_mock import RunningTelemetryMock

from chrys.foundation.events.bus import EventBus
from chrys.foundation.events.types import InvocationToolCallResult, InvocationToolCallStart
from chrys.foundation.models.invocations import InvocationOrigin
from chrys.foundation.reporting.collector import ReportCollectorConfig, TelemetryReportCollector
from tests.support.waiting import wait_for


async def _set_fault(mock: RunningTelemetryMock, **config: object) -> None:
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{mock.origin}/debug/faults", json=config)
        assert response.status_code == 200


@pytest.fixture
def mock() -> Iterator[RunningTelemetryMock]:
    running = telemetry_mock.start_telemetry_mock(port=0, quiet=True)
    yield running
    running.close()


def _origin(session_id: str) -> InvocationOrigin:
    return InvocationOrigin(
        kind="turn",
        session_id=session_id,
        invocation_id="c" * 32,
        parent=None,
    )


def _start_event(origin: InvocationOrigin, session_id: str) -> InvocationToolCallStart:
    return InvocationToolCallStart(
        origin=origin,
        session_id=session_id,
        agent_name="Code",
        tool_name="read_file",
        tool_kind="read",
        args={"path": "src/a.py"},
        call_id="call_1",
    )


def _result_event(origin: InvocationOrigin, session_id: str, result: str) -> InvocationToolCallResult:
    return InvocationToolCallResult(
        origin=origin,
        session_id=session_id,
        agent_name="Code",
        tool_name="read_file",
        call_id="call_1",
        result=result,
        duration_ms=12,
    )


def _collector(mock: RunningTelemetryMock, **overrides: object) -> TelemetryReportCollector:
    values: dict[str, object] = {
        "endpoint": mock.origin,
        "session_id": "session-1",
        "retry_delays_seconds": (),
    }
    values.update(overrides)
    return TelemetryReportCollector(ReportCollectorConfig(**values))  # type: ignore[arg-type]


async def test_projects_and_sends_tool_call_save_then_update(mock: RunningTelemetryMock, direct_route: None) -> None:
    bus = EventBus()
    collector = _collector(mock)
    await collector.start(bus)
    try:
        await bus.publish(_start_event(_origin("session-1"), "session-1"))
        await bus.publish(_result_event(_origin("session-1"), "session-1", "contents of src/a.py"))

        def _both_rows_present() -> bool:
            return bool(mock.store.query("tool-detail/save")) and bool(mock.store.query("tool-detail/update"))

        await wait_for(_both_rows_present)

        save_rows = mock.store.query("tool-detail/save", session_id="session-1")
        assert len(save_rows) == 1
        save = save_rows[0]
        assert save["func_name"] == "read_file"
        assert save["has_value"] == 1
        assert save["request_id"] == "c" * 32
        assert collector.sent_count == 2

        update_rows = mock.store.query("tool-detail/update")
        assert len(update_rows) == 1
        update = update_rows[0]
        # start->result pairs onto the same funcId through call_id.
        assert update["func_id"] == save["func_id"]
        assert update["code_status"] == 1
        assert update["has_error_message"] == 0
    finally:
        await collector.stop()


async def test_error_result_reports_failure_status(mock: RunningTelemetryMock, direct_route: None) -> None:
    bus = EventBus()
    collector = _collector(mock)
    await collector.start(bus)
    try:
        await bus.publish(_start_event(_origin("session-1"), "session-1"))
        await bus.publish(_result_event(_origin("session-1"), "session-1", "Error: path_not_found: no such file"))
        await wait_for(lambda: bool(mock.store.query("tool-detail/update")))
        update = mock.store.query("tool-detail/update")[0]
        assert update["code_status"] == 2
        assert update["has_error_message"] == 1
    finally:
        await collector.stop()


async def test_business_rejection_is_dropped_without_retry(mock: RunningTelemetryMock, direct_route: None) -> None:
    await _set_fault(mock, mode="envelope_reject")
    bus = EventBus()
    collector = _collector(mock)
    await collector.start(bus)
    try:
        await bus.publish(_start_event(_origin("session-1"), "session-1"))
        await wait_for(lambda: collector.dropped_count >= 1)
        assert collector.sent_count == 0
        # The mock persists before answering with the fault; the collector
        # still counts the business rejection as dropped.
        assert len(mock.store.query("tool-detail/save")) == 1
    finally:
        await collector.stop()


async def test_retries_then_succeeds_after_fault_is_cleared(mock: RunningTelemetryMock, direct_route: None) -> None:
    await _set_fault(mock, mode="http500", interfaces=["tool-detail/save"])
    bus = EventBus()
    # One retry with zero backoff: 2 attempts in total.
    collector = _collector(mock, retry_delays_seconds=(0.0,))
    await collector.start(bus)
    try:
        await bus.publish(_start_event(_origin("session-1"), "session-1"))
        await wait_for(lambda: collector.dropped_count >= 1)

        await _set_fault(mock, mode="none")
        await bus.publish(_result_event(_origin("session-1"), "session-1", "ok"))
        await wait_for(lambda: collector.sent_count >= 1)
        assert len(mock.store.query("tool-detail/update")) == 1
    finally:
        await collector.stop()


async def test_start_and_stop_are_idempotent(mock: RunningTelemetryMock) -> None:
    bus = EventBus()
    collector = _collector(mock)
    await collector.start(bus)
    await collector.start(bus)
    await collector.stop()
    await collector.stop()
    # After stop, publishing on the bus must not deliver anything (handlers unsubscribed).
    await bus.publish(_start_event(_origin("session-1"), "session-1"))
    assert mock.store.query("tool-detail/save") == []
