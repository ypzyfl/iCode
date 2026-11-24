# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Contract tests for the telemetry receive mock (mock 1B; design §3.6).

Two layers:

- the independent factory (port=0): idempotency semantics — replay 200, key
  conflict 409, malformed 400 (strict allowlist) — and the join view;
- the single-port combo: telemetry saves route on :15678's successor, and the
  catalog chat hook captures each request's own ``Chrys-Request-Attempt-Id``
  (BR-1: no success verdict) so the join closes end to end.

Loopback calls use stdlib ``urllib`` with an empty ``ProxyHandler`` — no
environment or system proxy can intercept loopback traffic (the same
guarantee the update/catalog mock tests get).
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
import uuid
from collections.abc import Iterator

import pytest
from aixcoding.mock.combined import start_combined
from aixcoding.mock.telemetry.server import (
    AI_CODE_SAVE_ROUTE,
    JOIN_ROUTE,
    LLM_SAVE_ROUTE,
    TOOL_SAVE_ROUTE,
    create_server,
)

_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _hex32() -> str:
    return uuid.uuid4().hex


def _post(base: str, route: str, payload: dict[str, object]) -> tuple[int, dict[str, object]]:
    request = urllib.request.Request(
        base + route, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}
    )
    try:
        with _OPENER.open(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def _get(base: str, route: str) -> tuple[int, dict[str, object]]:
    try:
        with _OPENER.open(base + route, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


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


def _tool_payload(request_id: str, func_id: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "requestId": request_id,
        "funcId": func_id,
        "funcName": "write_file",
        "funcType": "file",
        "sessionId": _hex32(),
        "spanId": _hex32(),
        "codeStatus": "ok",
    }
    payload.update(overrides)
    return payload


def _ai_code_payload(request_id: str, report_id: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "reportId": report_id,
        "requestId": request_id,
        "filepath": "src/app.py",
        "blocks": [{"kind": "replace", "path": "src/app.py"}],
        "sourceType": "agent",
        "inputMethod": "chat",
        "codeStatus": "ok",
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def base() -> Iterator[str]:
    """The independent telemetry factory on a random port."""
    server = create_server(port=0)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def test_llm_report_save_replay_and_conflict(base: str) -> None:
    request_id = _hex32()
    payload = _llm_payload(request_id)
    assert _post(base, LLM_SAVE_ROUTE, payload)[0] == 200
    assert _post(base, LLM_SAVE_ROUTE, payload)[0] == 200  # byte-identical replay
    different = _llm_payload(request_id)
    different["eventSubType"] = "failed"
    assert _post(base, LLM_SAVE_ROUTE, different)[0] == 409  # same key, different content


def test_tool_detail_combo_key_idempotency(base: str) -> None:
    request_id, func_id = _hex32(), _hex32()
    payload = _tool_payload(request_id, func_id)
    assert _post(base, TOOL_SAVE_ROUTE, payload)[0] == 200
    assert _post(base, TOOL_SAVE_ROUTE, payload)[0] == 200  # byte-identical replay
    # same requestId, different funcId = a different record, not a conflict
    assert _post(base, TOOL_SAVE_ROUTE, _tool_payload(request_id, _hex32()))[0] == 200
    different = _tool_payload(request_id, func_id)
    different["codeStatus"] = "error"
    assert _post(base, TOOL_SAVE_ROUTE, different)[0] == 409  # same key, different content


def test_ai_code_combo_key_idempotency(base: str) -> None:
    request_id, report_id = _hex32(), _hex32()
    assert _post(base, AI_CODE_SAVE_ROUTE, _ai_code_payload(request_id, report_id))[0] == 200
    assert _post(base, AI_CODE_SAVE_ROUTE, _ai_code_payload(request_id, report_id))[0] == 200
    assert _post(base, AI_CODE_SAVE_ROUTE, _ai_code_payload(request_id, report_id, codeStatus="error"))[0] == 409


def test_malformed_payloads_answer_400(base: str) -> None:
    missing = _llm_payload(_hex32())
    del missing["requestId"]
    assert _post(base, LLM_SAVE_ROUTE, missing)[0] == 400
    assert _post(base, LLM_SAVE_ROUTE, _llm_payload("not-hex"))[0] == 400
    unknown = _tool_payload(_hex32(), _hex32())
    unknown["providerCallId"] = "must be rejected"
    assert _post(base, TOOL_SAVE_ROUTE, unknown)[0] == 400
    assert _post(base, "/csas/telemetry/api/v1/llm-report/save", {"no": "route"})[0] == 400


def test_join_collects_every_record_kind(base: str) -> None:
    request_id, func_id, report_id = _hex32(), _hex32(), _hex32()
    _post(base, LLM_SAVE_ROUTE, _llm_payload(request_id))
    _post(base, TOOL_SAVE_ROUTE, _tool_payload(request_id, func_id))
    _post(base, AI_CODE_SAVE_ROUTE, _ai_code_payload(request_id, report_id))
    status, joined = _get(base, f"{JOIN_ROUTE}?requestId={request_id}")
    assert status == 200
    assert joined["llmReport"] is not None
    assert [row["funcId"] for row in joined["toolDetails"]] == [func_id]
    assert [row["reportId"] for row in joined["aiCodes"]] == [report_id]
    assert joined["modelRecord"] is None  # nothing captured on the factory form
    status, _ = _get(base, f"{JOIN_ROUTE}?requestId=zzz")
    assert status == 400


def test_combo_routes_telemetry_and_captures_model_attempts() -> None:
    """One port: telemetry saves route, and each catalog chat request records
    its own attempt header (BR-1) so the join closes across model+report."""
    origin, server, _thread = start_combined(port=0, with_telemetry=True)
    attempt = _hex32()
    chat = {
        "model": "model-test",
        "messages": [{"role": "user", "content": "hi"}],
    }
    request = urllib.request.Request(
        origin + "/v1/chat/completions",
        data=json.dumps(chat).encode("utf-8"),
        headers={"Content-Type": "application/json", "Chrys-Request-Attempt-Id": attempt},
    )
    with _OPENER.open(request, timeout=5) as response:
        assert response.status == 200
    assert _post(origin, LLM_SAVE_ROUTE, _llm_payload(attempt))[0] == 200
    status, joined = _get(origin, f"{JOIN_ROUTE}?requestId={attempt}")
    assert status == 200
    model_record = joined["modelRecord"]
    assert model_record is not None
    assert model_record["requestId"] == attempt  # own attempt, raw value
    assert model_record["requestModel"] == "model-test"
    assert joined["llmReport"] is not None
    server.shutdown()
    server.server_close()


def test_combo_without_telemetry_keeps_routes_clean() -> None:
    origin, server, _thread = start_combined(port=0, with_telemetry=False)
    status, _ = _get(origin, f"{JOIN_ROUTE}?requestId={_hex32()}")
    assert status == 404  # catalog answers: unknown route, not telemetry
    server.shutdown()
    server.server_close()
