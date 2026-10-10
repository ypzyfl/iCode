# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Integration tests for the Chrys session reporting mock server (mock_server/chrys_telemetry/server.py).

Conventions: bind port 0 (kernel-assigned), loopback only; every HTTP call
goes through ``direct_route`` (bypassing environment/system proxies).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from typing import Any

import httpx
import pytest

from mock_server.chrys_telemetry import server as chrys_telemetry_server
from mock_server.chrys_telemetry.server import RunningTelemetryMock

_CONTENT_HASH = "ab" * 32


@pytest.fixture
def mock_factory() -> Iterator[Callable[..., RunningTelemetryMock]]:
    """Start mocks on demand (port 0, in-memory, quiet) and reap them all."""
    started: list[RunningTelemetryMock] = []

    def _factory(**kwargs: Any) -> RunningTelemetryMock:
        running = chrys_telemetry_server.start(quiet=True, **kwargs)
        started.append(running)
        return running

    yield _factory
    for running in started:
        running.close()


@pytest.fixture
def mock(mock_factory: Callable[..., RunningTelemetryMock]) -> RunningTelemetryMock:
    return mock_factory()


async def _post(url: str, payload: object, *, headers: dict[str, str] | None = None) -> httpx.Response:
    async with httpx.AsyncClient() as client:
        return await client.post(url, json=payload, headers=headers)


async def _set_fault(mock: RunningTelemetryMock, **config: Any) -> None:
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{mock.origin}/debug/faults", json=config)
        assert response.status_code == 200


def _save_body() -> dict[str, object]:
    return {
        "productName": "icode",
        "funcType": 3,
        "funcName": "read_file",
        "funcId": "a" * 32,
        "value": "src/a.js",
        "fileName": "src/a.js",
        "codeStatus": 0,
        "sessionId": "session-1",
        "requestId": "b" * 32,
        "spanId": "11111111-2222-4333-8444-555555555555",
        "channelType": "tui",
        "unknownExtraField": {"kept": True},
    }


async def test_accepts_tool_detail_save_and_stores_queryable(mock: RunningTelemetryMock, direct_route: None) -> None:
    response = await _post(f"{mock.origin}/csas/telemetry/api/v1/tool-detail/save", _save_body())
    assert response.status_code == 200
    envelope = response.json()
    assert envelope["success"] is True
    assert envelope["code"] == 200

    rows = mock.store.query("tool-detail/save", session_id="session-1")
    assert len(rows) == 1
    row = rows[0]
    assert row["func_name"] == "read_file"
    assert row["has_value"] == 1
    stored = json.loads(row["body_json"])
    assert stored["unknownExtraField"] == {"kept": True}


async def test_rejects_invalid_save_into_rejected_table(mock: RunningTelemetryMock, direct_route: None) -> None:
    response = await _post(f"{mock.origin}/csas/telemetry/api/v1/tool-detail/save", {"funcName": "x"})
    assert response.status_code == 400
    assert mock.store.query("tool-detail/save") == []
    rejected = mock.store.query("rejected")
    assert len(rejected) == 1
    assert rejected[0]["interface"] == "tool-detail/save"
    assert "productName" in rejected[0]["problem"]


async def test_requires_token_when_configured(
    mock_factory: Callable[..., RunningTelemetryMock], direct_route: None
) -> None:
    mock = mock_factory(require_token="secret")
    url = f"{mock.origin}/csas/telemetry/api/v1/tool-detail/save"
    response = await _post(url, _save_body())
    assert response.status_code == 401
    response = await _post(url, _save_body(), headers={"token": "secret"})
    assert response.status_code == 200


async def test_batch_save_upserts_on_session_and_span(mock: RunningTelemetryMock, direct_route: None) -> None:
    url = f"{mock.origin}/csas/telemetry/api/v1/tool-detail/batch-save"
    item = {
        "funcType": 0,
        "funcName": "java_code_review",
        "sessionId": "session-1",
        "spanId": "11111111-2222-4333-8444-555555555555",
    }
    assert (await _post(url, [item])).status_code == 200
    assert (await _post(url, [item, {**item, "funcName": "java_unit_test"}])).status_code == 200
    rows = mock.store.query("tool-detail/batch-save")
    assert len(rows) == 1  # Same sessionId+spanId overwrites instead of appending.
    assert rows[0]["item_count"] == 2


async def test_tool_detail_save_version_headers_deduplicate(mock: RunningTelemetryMock, direct_route: None) -> None:
    url = f"{mock.origin}/csas/telemetry/api/v1/tool-detail/save"
    headers = {"X-Turn-Content-Hash": _CONTENT_HASH, "X-Analysis-Version": "3"}
    assert (await _post(url, _save_body(), headers=headers)).status_code == 200
    assert (await _post(url, _save_body(), headers=headers)).status_code == 200
    # Repeated arrivals without version headers never fold.
    assert (await _post(url, _save_body())).status_code == 200
    assert len(mock.store.query("tool-detail/save")) == 2


async def test_ai_code_save_report_id_dedup_and_envelope(mock: RunningTelemetryMock, direct_route: None) -> None:
    url = f"{mock.origin}/csas/telemetry/api/v1/ai-code/save"
    body = {
        "reportId": "report-1",
        "sourceType": "file_edit",
        "blocks": [{"rangeStart": 0, "rangeEnd": 3}],
        "sessionId": "session-1",
    }
    first = await _post(url, body)
    assert first.status_code == 200
    # ai-code/save answers with a different envelope (code/message/data) than the rest.
    assert first.json() == {"code": 200, "message": "success", "data": {"reportId": "report-1"}}
    assert (await _post(url, body)).status_code == 200
    assert len(mock.store.query("ai-code/save")) == 1


async def test_tool_detail_update_writes_back_latest_update(mock: RunningTelemetryMock, direct_route: None) -> None:
    assert (await _post(f"{mock.origin}/csas/telemetry/api/v1/tool-detail/save", _save_body())).status_code == 200
    update = {"funcId": "a" * 32, "codeStatus": 1, "addedLines": 3, "deletedLines": 1}
    assert (await _post(f"{mock.origin}/csas/telemetry/api/v1/tool-detail/update", update)).status_code == 200
    save_rows = mock.store.query("tool-detail/save")
    assert save_rows[0]["latest_update_json"] is not None
    update_rows = mock.store.query("tool-detail/update")
    assert update_rows[0]["added_lines"] == 3


async def test_fault_http500(mock: RunningTelemetryMock, direct_route: None) -> None:
    await _set_fault(mock, mode="http500", interfaces=["tool-detail/save"])
    response = await _post(f"{mock.origin}/csas/telemetry/api/v1/tool-detail/save", _save_body())
    assert response.status_code == 500
    # Matches the ported implementation: persist first, then answer with the fault (exercises the collector retry lane).
    assert len(mock.store.query("tool-detail/save")) == 1


async def test_fault_envelope_reject(mock: RunningTelemetryMock, direct_route: None) -> None:
    await _set_fault(mock, mode="envelope_reject")
    response = await _post(f"{mock.origin}/csas/telemetry/api/v1/tool-detail/save", _save_body())
    assert response.status_code == 200
    assert response.json()["success"] is False


async def test_fault_drop_body_closes_connection(mock: RunningTelemetryMock, direct_route: None) -> None:
    await _set_fault(mock, mode="drop_body")
    with pytest.raises(httpx.TransportError):
        await _post(f"{mock.origin}/csas/telemetry/api/v1/tool-detail/save", _save_body())


async def test_fault_interfaces_filter_leaves_other_endpoints(mock: RunningTelemetryMock, direct_route: None) -> None:
    await _set_fault(mock, mode="http500", interfaces=["ai-code/save"])
    response = await _post(f"{mock.origin}/csas/telemetry/api/v1/tool-detail/save", _save_body())
    assert response.status_code == 200


async def test_health_and_view_page(mock: RunningTelemetryMock, direct_route: None) -> None:
    async with httpx.AsyncClient() as client:
        health = await client.get(f"{mock.origin}/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"
        view = await client.get(f"{mock.origin}/")
        assert view.status_code == 200
        assert "text/html" in view.headers["content-type"]
        assert "Chrys 会话数据上报 Mock" in view.text
        assert "/debug/dump" in view.text


async def test_debug_dump_and_clear(mock: RunningTelemetryMock, direct_route: None) -> None:
    assert (await _post(f"{mock.origin}/csas/telemetry/api/v1/tool-detail/save", _save_body())).status_code == 200
    async with httpx.AsyncClient() as client:
        dump = await client.get(f"{mock.origin}/debug/dump")
        assert dump.status_code == 200
        assert len(dump.json()["tool-detail/save"]) == 1
        assert (await client.post(f"{mock.origin}/debug/clear")).status_code == 200
    assert mock.store.dump()["tool-detail/save"] == []


def test_rejects_non_loopback_host() -> None:
    with pytest.raises(ValueError, match="loopback"):
        chrys_telemetry_server.start(host="0.0.0.0", quiet=True)


async def test_invalid_fault_config_is_rejected(mock: RunningTelemetryMock, direct_route: None) -> None:
    for config in (
        {"mode": "not-a-mode"},
        {"mode": "http500", "rate": 2},
        {"mode": "slow", "slowMs": -1},
        {"mode": "http500", "interfaces": "not-a-list"},
    ):
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{mock.origin}/debug/faults", json=config)
        assert response.status_code == 400, config
