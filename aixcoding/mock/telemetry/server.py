# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Telemetry receive mock (mock 1B; batch telemetry-after-turn-slice design §3.6).

Implements the B7/B8 contracts against in-memory state:

- three save endpoints, each with idempotency by its contract key — a byte-
  normalized replay of the same payload answers 200 (no new row), the same
  key with different content answers 409, malformed payloads (missing
  fields, non-32hex ids, unknown fields - strict allowlist) answer 400;
- the ``_test/join`` view returns, for one requestId, everything the mock
  knows: the captured model record (per-request attempt header via the combo
  hook, BR-1: each request records its own attempt, no success verdict), the
  LLM report, the tool details and the ai-code reports - the join closure
  the slice's end-to-end test asserts on.

Ids stay raw 32hex everywhere (the 2026-11-18 original-value ruling); no
UUID normalization exists on any path. Allowlists are deliberately strict:
the mock is a contract oracle, silently-accepted extras would hide drift.
"""

from __future__ import annotations

import json
import re
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

DEFAULT_HOST = "127.0.0.1"
#: The combo port is the primary form; the independent factory exists for
#: contract tests (port=0) and focused debugging (DIRECTORY §6).
DEFAULT_PORT = 15678

LLM_SAVE_ROUTE = "/csas/telemetry/api/v1/llm-report/save"
TOOL_SAVE_ROUTE = "/csas/telemetry/api/v1/tool-detail/save"
AI_CODE_SAVE_ROUTE = "/csas/telemetry/api/v1/ai-code/save"
JOIN_ROUTE = "/csas/telemetry/_test/join"
FAULT_CONTROL_ROUTE = "/csas/telemetry/_test/fault"


@dataclass
class MockTelemetryFault:
    """Fault-injection knob: rehearsal for the real backend's transient
    failures (batch-1 self-fragility testing, 2026-11-23 ruling).

    ``ok`` answers normally; ``slow`` delays ``slow_ms``; ``error`` answers
    ``status`` (default 503); ``rate_limit`` answers 429; ``flaky`` fails the
    first ``fail_attempts`` tries per idempotency key with ``status``, then
    succeeds — exactly the shape that exercises the client's single backoff
    retry end to end.
    """

    mode: str = "ok"
    slow_ms: int = 0
    status: int = 503
    fail_attempts: int = 1


_HEX32 = re.compile(r"^[0-9a-f]{32}$")

#: field allowlists (every listed field is required by the contract)
_LLM_FIELDS = ("schemaVersion", "sessionId", "eventType", "eventSubType", "requestId", "spanId")
_TOOL_FIELDS = ("requestId", "funcId", "funcName", "funcType", "sessionId", "spanId", "codeStatus")
_AI_CODE_FIELDS = ("reportId", "requestId", "filepath", "blocks", "sourceType", "inputMethod", "codeStatus")

#: fields that must be strict 32hex (analytics ids / token_hex products);
#: sessionId/spanId are checked as non-empty strings only - their format is
#: the product's concern, the mock must not invent stricter rules than the
#: contract.
_STRICT_HEX_FIELDS = ("requestId", "funcId", "reportId")

_MAX_BODY_BYTES = 1 << 20


class _SaveResult(Exception):
    """Carries (status, payload) out of the save paths to the handler."""

    def __init__(self, status: int, payload: dict[str, object]) -> None:
        super().__init__(str(status))
        self.status = status
        self.payload = payload


class MockTelemetryState:
    """In-memory telemetry storage + model-request capture; thread-safe."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.llm_reports: dict[str, dict] = {}
        self.tool_details: dict[tuple[str, str], dict] = {}
        self.ai_codes: dict[tuple[str, str], dict] = {}
        #: BR-1: every chat request records its own attempt header - no
        #: success verdict, no cross-request aggregation.
        self.model_records: dict[str, dict] = {}
        #: Fault injection (test-only routes drive this).
        self.fault = MockTelemetryFault()
        self._fault_tries: dict[str, int] = {}
        self.save_attempts = 0

    def set_fault(self, payload: dict[str, object]) -> MockTelemetryFault:
        allowed = {"mode", "slow_ms", "status", "fail_attempts"}
        unknown = sorted(set(payload) - allowed)
        if unknown or payload.get("mode") not in {"ok", "slow", "error", "rate_limit", "flaky"}:
            raise _SaveResult(400, {"error": "invalid fault payload"})
        with self._lock:
            self.fault = MockTelemetryFault(
                mode=str(payload["mode"]),
                slow_ms=int(payload.get("slow_ms", 0)),
                status=int(payload.get("status", 503)),
                fail_attempts=max(1, int(payload.get("fail_attempts", 1))),
            )
            self._fault_tries.clear()
            return self.fault

    def _fault_sleep(self) -> None:
        if self.fault.mode == "slow" and self.fault.slow_ms > 0:
            time.sleep(self.fault.slow_ms / 1000.0)

    def _fault_gate(self, key: str) -> int | None:
        """Count the save attempt; return the error status when this attempt
        is faulted (None = proceed to normal save semantics)."""
        with self._lock:
            self.save_attempts += 1
            mode, status = self.fault.mode, self.fault.status
            if mode == "error":
                return status
            if mode == "rate_limit":
                return 429
            if mode == "flaky":
                tries = self._fault_tries.get(key, 0) + 1
                self._fault_tries[key] = tries
                if tries <= self.fault.fail_attempts:
                    return status
                return None
            return None

    # -- model capture (injected into the combo's catalog chat handler) ------

    def capture_model_request(
        self, *, attempt: str | None, request_model: str, response_model: str, stream: bool
    ) -> None:
        if not attempt or not _HEX32.match(attempt):
            return  # header absent/invalid => nothing to associate; no fake ids
        with self._lock:
            self.model_records[attempt] = {
                "requestId": attempt,
                "requestModel": request_model,
                "responseModel": response_model,
                "stream": stream,
            }

    # -- saves ----------------------------------------------------------------

    def save_llm_report(self, payload: dict[str, object]) -> None:
        self._validate(payload, _LLM_FIELDS)
        self._fault_sleep()
        request_id = str(payload["requestId"])
        gated = self._fault_gate(f"llm:{request_id}")
        if gated is not None:
            raise _SaveResult(gated, {"error": "fault-injected"})
        with self._lock:
            existing = self.llm_reports.get(request_id)
            if existing is not None and existing != payload:
                raise _SaveResult(409, {"error": "idempotency-conflict", "key": f"llm:{request_id}"})
            self.llm_reports[request_id] = dict(payload)

    def save_tool_detail(self, payload: dict[str, object]) -> None:
        self._validate(payload, _TOOL_FIELDS)
        self._fault_sleep()
        key = (str(payload["requestId"]), str(payload["funcId"]))
        gated = self._fault_gate(f"tool:{key[0]}:{key[1]}")
        if gated is not None:
            raise _SaveResult(gated, {"error": "fault-injected"})
        with self._lock:
            existing = self.tool_details.get(key)
            if existing is not None and existing != payload:
                raise _SaveResult(409, {"error": "idempotency-conflict", "key": f"tool:{key[0]}:{key[1]}"})
            self.tool_details[key] = dict(payload)

    def save_ai_code(self, payload: dict[str, object]) -> None:
        self._validate(payload, _AI_CODE_FIELDS)
        self._fault_sleep()
        key = (str(payload["requestId"]), str(payload["reportId"]))
        gated = self._fault_gate(f"aicode:{key[0]}:{key[1]}")
        if gated is not None:
            raise _SaveResult(gated, {"error": "fault-injected"})
        with self._lock:
            existing = self.ai_codes.get(key)
            if existing is not None and existing != payload:
                raise _SaveResult(409, {"error": "idempotency-conflict", "key": f"aicode:{key[0]}:{key[1]}"})
            self.ai_codes[key] = dict(payload)

    @staticmethod
    def _validate(payload: dict[str, object], fields: tuple[str, ...]) -> None:
        unknown = sorted(set(payload) - set(fields))
        if unknown:
            raise _SaveResult(400, {"error": "unknown-field", "field": unknown[0]})
        missing = [name for name in fields if name not in payload or payload[name] in (None, "")]
        if missing:
            raise _SaveResult(400, {"error": "missing-field", "field": missing[0]})
        for name in _STRICT_HEX_FIELDS:
            if name in payload and not _HEX32.match(str(payload[name])):
                raise _SaveResult(400, {"error": "invalid-id", "field": name})

    # -- join -----------------------------------------------------------------

    def join(self, request_id: str) -> dict[str, object]:
        with self._lock:
            return {
                "requestId": request_id,
                "modelRecord": self.model_records.get(request_id),
                "llmReport": self.llm_reports.get(request_id),
                "toolDetails": [dict(row) for row in self.tool_details.values() if row["requestId"] == request_id],
                "aiCodes": [dict(row) for row in self.ai_codes.values() if row["requestId"] == request_id],
            }


def build_handler_class(state: MockTelemetryState) -> type[BaseHTTPRequestHandler]:
    class TelemetryMockHandler(BaseHTTPRequestHandler):
        server_version = "ChrysMockTelemetry/1.0"

        def _reply(self, status: int, payload: dict[str, object]) -> None:
            body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _read_body(self) -> dict[str, object] | None:
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                return None
            if length > _MAX_BODY_BYTES:
                return None
            raw = self.rfile.read(length) if length else b""
            if not raw.strip():
                return None
            try:
                parsed = json.loads(raw.decode("utf-8"))
            except OSError, ValueError:
                return None
            return parsed if isinstance(parsed, dict) else None

        def do_POST(self) -> None:
            route = urlsplit(self.path).path
            body = self._read_body()
            if body is None:
                self._reply(400, {"error": "request body must be a JSON object"})
                return
            try:
                if route == LLM_SAVE_ROUTE:
                    state.save_llm_report(body)
                elif route == TOOL_SAVE_ROUTE:
                    state.save_tool_detail(body)
                elif route == AI_CODE_SAVE_ROUTE:
                    state.save_ai_code(body)
                elif route == FAULT_CONTROL_ROUTE:
                    state.set_fault(body)
                else:
                    self._reply(404, {"error": f"no such route: {route}"})
                    return
            except _SaveResult as conflict:
                self._reply(conflict.status, conflict.payload)
                return
            self._reply(200, {"status": "ok"})

        def do_GET(self) -> None:
            parts = urlsplit(self.path)
            if parts.path != JOIN_ROUTE:
                self._reply(404, {"error": f"no such route: {parts.path}"})
                return
            request_id = (parse_qs(parts.query).get("requestId") or [""])[0]
            if not _HEX32.match(request_id):
                self._reply(400, {"error": "requestId must be 32 lowercase hex chars"})
                return
            self._reply(200, state.join(request_id))

        def log_message(self, format: str, *args: object) -> None:
            server = getattr(self, "server", None)
            quiet = bool(getattr(server, "quiet", False)) if server is not None else False
            if not quiet:
                super().log_message(format, *args)

    return TelemetryMockHandler


class TelemetryMockServer(ThreadingHTTPServer):
    """Threaded server carrying the telemetry state (mirrors peer mocks)."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        address: tuple[str, int],
        handler: type[BaseHTTPRequestHandler],
        *,
        state: MockTelemetryState | None = None,
        quiet: bool = False,
    ) -> None:
        super().__init__(address, handler)
        self.state = state if state is not None else MockTelemetryState()
        self.quiet = quiet


def create_server(
    state: MockTelemetryState | None = None, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT
) -> TelemetryMockServer:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("mock binds loopback only")
    own_state = state if state is not None else MockTelemetryState()
    return TelemetryMockServer((host, port), build_handler_class(own_state), state=own_state)
