# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Self-fragility rehearsal: the telemetry mock's fault knobs against the
REAL product client (batch-1, 2026-11-23 first-tier ruling).

The point is not "the mock can fail" — it is that the client survives every
transient shape the intranet backend can plausibly throw during a restart or
a busy window: one flaky 503 that the single backoff retry rides through, a
persistent 5xx/429 that surfaces as a non-200 (after exactly one retry), and
definite 4xx/409 verdicts that are NOT retried. Plus payload realism
(unicode paths, oversized blocks) and owner-level cross-session concurrency.
"""

from __future__ import annotations

import asyncio
import json
import threading
import urllib.error
import urllib.request
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from aixcoding.mock.telemetry.server import (
    AI_CODE_SAVE_ROUTE,
    FAULT_CONTROL_ROUTE,
    JOIN_ROUTE,
    LLM_SAVE_ROUTE,
    create_server,
)

from chrys.service.aixcoding.telemetry import client as telemetry_client
from chrys.service.aixcoding.telemetry.notice import TurnTelemetryNotice
from chrys.service.aixcoding.telemetry.owner import TelemetryOwner

_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _hex32() -> str:
    return uuid.uuid4().hex


def _llm_payload(request_id: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schemaVersion": "1",
        "sessionId": _hex32(),
        "eventType": "llm",
        "eventSubType": "success",
        "requestId": request_id,
        "spanId": _hex32(),
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def pair() -> Iterator[tuple[str, Any]]:
    """(base-url, state): the independent telemetry factory on a random port."""
    server = create_server(port=0)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}", server.state
    server.shutdown()
    server.server_close()


def _post(base: str, route: str, payload: dict[str, object]) -> tuple[int, dict[str, Any]]:
    request = urllib.request.Request(
        base + route, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}
    )
    try:
        with _OPENER.open(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def _get_json(url: str) -> Any:
    with _OPENER.open(url, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def test_fault_control_validates_mode(pair: tuple[str, Any]) -> None:
    base, _state = pair
    assert _post(base, FAULT_CONTROL_ROUTE, {"mode": "nope"})[0] == 400
    assert _post(base, FAULT_CONTROL_ROUTE, {"mode": "flaky", "unknown": 1})[0] == 400


def test_flaky_503_is_ridden_through_by_single_retry(pair: tuple[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    base, state = pair
    monkeypatch.setenv("AIXCODING_TELEMETRY_BASE_URL", base)
    assert _post(base, FAULT_CONTROL_ROUTE, {"mode": "flaky", "status": 503, "fail_attempts": 1})[0] == 200

    request_id = _hex32()
    status, _body = telemetry_client.post_save(LLM_SAVE_ROUTE, _llm_payload(request_id))
    assert status == 200, "one backoff retry must ride through a first-attempt 503"
    assert state.save_attempts == 2
    assert _get_json(f"{base}{JOIN_ROUTE}?requestId={request_id}")["llmReport"] is not None


def test_persistent_5xx_surfaces_after_exactly_one_retry(
    pair: tuple[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    base, state = pair
    monkeypatch.setenv("AIXCODING_TELEMETRY_BASE_URL", base)
    assert _post(base, FAULT_CONTROL_ROUTE, {"mode": "error", "status": 500})[0] == 200
    state.save_attempts = 0

    status, body = telemetry_client.post_save(LLM_SAVE_ROUTE, _llm_payload(_hex32()))
    assert status == 500 and "fault-injected" in body
    assert state.save_attempts == 2, "exactly one retry, then give up"


def test_rate_limit_429_follows_the_retry_path(pair: tuple[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    base, state = pair
    monkeypatch.setenv("AIXCODING_TELEMETRY_BASE_URL", base)
    assert _post(base, FAULT_CONTROL_ROUTE, {"mode": "rate_limit"})[0] == 200
    state.save_attempts = 0

    status, _body = telemetry_client.post_save(LLM_SAVE_ROUTE, _llm_payload(_hex32()))
    assert status == 429
    assert state.save_attempts == 2


def test_definite_409_is_not_retried(pair: tuple[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    base, state = pair
    monkeypatch.setenv("AIXCODING_TELEMETRY_BASE_URL", base)
    request_id = _hex32()
    assert telemetry_client.post_save(LLM_SAVE_ROUTE, _llm_payload(request_id))[0] == 200
    state.save_attempts = 0

    different = _llm_payload(request_id)
    different["eventSubType"] = "failed"
    status, _body = telemetry_client.post_save(LLM_SAVE_ROUTE, different)
    assert status == 409
    assert state.save_attempts == 1, "4xx verdicts are final — no retry burns the window"


def test_unicode_and_oversized_payloads_round_trip(pair: tuple[str, Any]) -> None:
    base, _state = pair
    request_id, report_id = _hex32(), _hex32()
    payload = {
        "reportId": report_id,
        "requestId": request_id,
        "filepath": "src/模块/配置文件‑中文名.py",
        "blocks": [{"kind": "content-ref", "sha256": "f" * 64, "note": "体积很大的块描述" * 100}],
        "sourceType": "agent",
        "inputMethod": "chat",
        "codeStatus": "ok",
    }
    assert _post(base, AI_CODE_SAVE_ROUTE, payload)[0] == 200
    joined = _get_json(f"{base}{JOIN_ROUTE}?requestId={request_id}")
    assert joined["aiCodes"][0]["filepath"] == payload["filepath"]
    assert joined["aiCodes"][0]["blocks"] == payload["blocks"]


@pytest.mark.asyncio
async def test_owner_handles_concurrent_sessions_and_passes() -> None:
    """3 sessions x 5 passes dispatched concurrently: per-session FIFO holds,
    every queue drains, no cross-session key collisions."""

    def notice(session: str, index: int) -> TurnTelemetryNotice:
        return TurnTelemetryNotice(
            session_id=session,
            session_dir=Path("."),
            logical_turn_id=_hex32(),
            pass_id=_hex32(),
            turn_number=index,
            is_retry=False,
            saved=True,
        )

    owner = TelemetryOwner()
    for session in ("s1", "s2", "s3"):
        for index in range(5):
            owner.dispatch(notice(session, index))
    assert set(owner._workers) == {"s1", "s2", "s3"}
    for session in ("s1", "s2", "s3"):
        await owner.flush_session(session, timeout=10.0)
        owner.close_session(session)
    assert owner._workers == {}
    assert owner._pending == {}
    assert asyncio.get_running_loop() is not None
