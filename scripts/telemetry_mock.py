# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Chrys session reporting mock server (local debug tool, never shipped).

Binds loopback only: accepts the 4+1 reporting endpoints, stores every body
verbatim into SQLite, and exposes debug query/dump/clear plus fault injection
(to exercise the reporting collector's failure and retry lanes). Contract
validation comes from :mod:`chrys.foundation.reporting.schemas` (the single
source of truth shared with the sending side).

Usage::

    uv run python scripts/telemetry_mock.py [--port 4321] [--db PATH]
                                            [--require-token TOKEN] [--quiet]

Endpoints::

    POST /csas/telemetry/api/v1/{tool-detail/save,tool-detail/batch-save,
         tool-detail/update,ai-code/save,event-reaction/save}
    GET  /health
    GET  / or /debug/view                     self-contained observation page
    GET  /debug/reports?interface=...         query by interface (sessionId/funcId/limit)
    GET  /debug/dump                          full export
    POST /debug/clear                         clear all tables
    POST /debug/faults                        fault injection
"""

from __future__ import annotations

import argparse
import contextlib
import json
import logging
import math
import sqlite3
import sys
import threading
import time
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from chrys.foundation.reporting.schemas import (
    AI_CODE_SAVE_ENDPOINT,
    API_PREFIX,
    TOOL_DETAIL_BATCH_SAVE_ENDPOINT,
    TOOL_DETAIL_SAVE_ENDPOINT,
    TOOL_DETAIL_UPDATE_ENDPOINT,
    parse_report_version,
    validate_report_body,
)

logger = logging.getLogger(__name__)

MAXIMUM_BODY_BYTES = 8 * 1024 * 1024
_LOOPBACK_HOSTS = ("127.0.0.1", "::1")
_DEFAULT_PORT = 4321

FAULT_MODES = ("none", "http500", "http503", "slow", "envelope_reject", "drop_body")

# Public interface id (URL path style) -> physical SQLite table name.
SQL_TABLE_BY_INTERFACE: dict[str, str] = {
    "tool-detail/save": "tool_detail_saves",
    "tool-detail/batch-save": "batch_saves",
    "tool-detail/update": "tool_detail_updates",
    "ai-code/save": "ai_code_saves",
    "event-reaction/save": "event_reactions",
    "rejected": "rejected_reports",
}
REPORT_INTERFACES = tuple(SQL_TABLE_BY_INTERFACE)

_MAX_DEBUG_LIMIT = 500


class FaultConfig:
    """Current fault injection config (overwritten by POST /debug/faults)."""

    def __init__(self) -> None:
        self.mode: str = "none"
        self.rate: float = 1.0
        self.slow_ms: int = 2_000
        self.interfaces: tuple[str, ...] = ()


class RunningTelemetryMock:
    """A started mock: origin, store handle and idempotent close."""

    def __init__(
        self,
        *,
        origin: str,
        database_path: str,
        store: TelemetryStore,
        faults: FaultConfig,
        server: TelemetryMockServer,
    ) -> None:
        self.origin = origin
        self.database_path = database_path
        self.store = store
        self.faults = faults
        self._server = server
        self._closed = False

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._server.shutdown()
        self._server.server_close()
        self.store.close()


class TelemetryStore:
    """SQLite storage: one table per interface, ``body_json`` keeps the full original body.

    ``:memory:`` is the default (process lifetime == session); extracted
    columns exist only to make /debug/reports queries convenient. One
    connection plus a lock: requests arrive on ThreadingHTTPServer threads.
    """

    def __init__(self, database_path: str) -> None:
        self._lock = threading.Lock()
        self._database = sqlite3.connect(database_path, check_same_thread=False)
        self._database.execute("PRAGMA busy_timeout = 5000;")
        self._database.executescript(
            """
            CREATE TABLE IF NOT EXISTS tool_detail_saves (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              received_at TEXT NOT NULL,
              session_id TEXT,
              func_id TEXT,
              func_type INTEGER,
              func_name TEXT,
              span_id TEXT,
              request_id TEXT,
              code_status INTEGER,
              has_value INTEGER NOT NULL,
              body_json TEXT NOT NULL,
              turn_content_hash TEXT,
              analysis_version INTEGER,
              latest_update_json TEXT
            );
            CREATE TABLE IF NOT EXISTS batch_saves (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              received_at TEXT NOT NULL,
              session_id TEXT,
              span_id TEXT,
              item_count INTEGER NOT NULL,
              body_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tool_detail_updates (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              received_at TEXT NOT NULL,
              func_id TEXT,
              code_status INTEGER,
              has_error_message INTEGER NOT NULL,
              original_lines INTEGER,
              added_lines INTEGER,
              deleted_lines INTEGER,
              body_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS ai_code_saves (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              received_at TEXT NOT NULL,
              report_id TEXT,
              session_id TEXT,
              span_id TEXT,
              request_id TEXT,
              source_type TEXT,
              language TEXT,
              filepath TEXT,
              block_count INTEGER NOT NULL,
              body_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS event_reactions (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              received_at TEXT NOT NULL,
              body_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS rejected_reports (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              received_at TEXT NOT NULL,
              interface TEXT NOT NULL,
              problem TEXT NOT NULL,
              body_json TEXT NOT NULL
            );
            """
        )
        # Column backfill for older on-disk databases (silently ignored when
        # the column exists): the idempotency/version columns added later.
        for table, column, column_type in (
            ("tool_detail_saves", "turn_content_hash", "TEXT"),
            ("tool_detail_saves", "analysis_version", "INTEGER"),
            ("tool_detail_saves", "latest_update_json", "TEXT"),
        ):
            with contextlib.suppress(sqlite3.OperationalError):  # Column already exists.
                self._database.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type};")
        self._database.commit()

    # ------------------------------------------------------------------ writers

    def upsert_tool_detail_save(
        self,
        body: dict[str, Any],
        received_at: str,
        version: object,
    ) -> str:
        """Version-aware idempotency key (contract 4.3): ``sessionId + funcId + hash + version``.

        A repeated arrival under the same key folds (no insert); requests
        without version headers never fold (a compatibility layer has no
        version information to judge by).
        """
        version_info = version if isinstance(version, tuple) and len(version) == 2 else None
        session_id = _text_or_none(body.get("sessionId"))
        func_id = _text_or_none(body.get("funcId"))
        with self._lock:
            if version_info is not None and session_id is not None and func_id is not None:
                existing = self._database.execute(
                    "SELECT id FROM tool_detail_saves"
                    " WHERE session_id = ? AND func_id = ? AND turn_content_hash = ? AND analysis_version = ?"
                    " LIMIT 1",
                    (session_id, func_id, version_info[0], version_info[1]),
                ).fetchone()
                if existing is not None:
                    return "deduplicated"
            self._database.execute(
                "INSERT INTO tool_detail_saves ("
                "  received_at, session_id, func_id, func_type, func_name, span_id,"
                "  request_id, code_status, has_value, body_json, turn_content_hash, analysis_version"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    received_at,
                    session_id,
                    func_id,
                    _int_or_none(body.get("funcType")),
                    _text_or_none(body.get("funcName")),
                    _text_or_none(body.get("spanId")),
                    _text_or_none(body.get("requestId")),
                    _int_or_none(body.get("codeStatus")),
                    1 if "value" in body else 0,
                    json.dumps(body, ensure_ascii=False),
                    version_info[0] if version_info is not None else None,
                    version_info[1] if version_info is not None else None,
                ),
            )
            self._database.commit()
            return "inserted"

    def upsert_batch_save(self, body: list[Any], received_at: str) -> str:
        """batch-save idempotency key ``sessionId + spanId`` (contract 4.3): repeated arrivals overwrite."""
        first = body[0] if body else None
        first_record = first if isinstance(first, dict) else {}
        session_id = _text_or_none(first_record.get("sessionId"))
        span_id = _text_or_none(first_record.get("spanId"))
        with self._lock:
            existing = None
            if session_id is not None and span_id is not None:
                existing = self._database.execute(
                    "SELECT id FROM batch_saves WHERE session_id = ? AND span_id = ? LIMIT 1",
                    (session_id, span_id),
                ).fetchone()
            if existing is not None:
                self._database.execute(
                    "UPDATE batch_saves SET received_at = ?, item_count = ?, body_json = ? WHERE id = ?",
                    (received_at, len(body), json.dumps(body, ensure_ascii=False), existing[0]),
                )
                self._database.commit()
                return "updated"
            self._database.execute(
                "INSERT INTO batch_saves (received_at, session_id, span_id, item_count, body_json)"
                " VALUES (?, ?, ?, ?, ?)",
                (received_at, session_id, span_id, len(body), json.dumps(body, ensure_ascii=False)),
            )
            self._database.commit()
            return "inserted"

    def insert_tool_detail_update(self, body: dict[str, Any], received_at: str) -> None:
        with self._lock:
            self._database.execute(
                "INSERT INTO tool_detail_updates ("
                "  received_at, func_id, code_status, has_error_message,"
                "  original_lines, added_lines, deleted_lines, body_json"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    received_at,
                    _text_or_none(body.get("funcId")),
                    _int_or_none(body.get("codeStatus")),
                    1 if body.get("funcErrorMessage") is not None else 0,
                    _int_or_none(body.get("originalLines")),
                    _int_or_none(body.get("addedLines")),
                    _int_or_none(body.get("deletedLines")),
                    json.dumps(body, ensure_ascii=False),
                ),
            )
            # Write back onto the latest save row for this funcId
            # (contract 4.3, last-write-wins).
            func_id = _text_or_none(body.get("funcId"))
            if func_id is not None:
                self._database.execute(
                    "UPDATE tool_detail_saves SET latest_update_json = ?"
                    " WHERE id = (SELECT max(id) FROM tool_detail_saves WHERE func_id = ?)",
                    (json.dumps(body, ensure_ascii=False), func_id),
                )
            self._database.commit()

    def upsert_ai_code_save(self, body: dict[str, Any], received_at: str) -> str:
        """ai-code idempotency key ``reportId`` (contract 4.3 primary key): repeated arrivals fold."""
        report_id = _text_or_none(body.get("reportId"))
        with self._lock:
            if report_id is not None:
                existing = self._database.execute(
                    "SELECT id FROM ai_code_saves WHERE report_id = ? LIMIT 1", (report_id,)
                ).fetchone()
                if existing is not None:
                    return "deduplicated"
            blocks = body.get("blocks")
            self._database.execute(
                "INSERT INTO ai_code_saves ("
                "  received_at, report_id, session_id, span_id, request_id,"
                "  source_type, language, filepath, block_count, body_json"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    received_at,
                    report_id,
                    _text_or_none(body.get("sessionId")),
                    _text_or_none(body.get("spanId")),
                    _text_or_none(body.get("requestId")),
                    _text_or_none(body.get("sourceType")),
                    _text_or_none(body.get("language")),
                    _text_or_none(body.get("filepath")),
                    len(blocks) if isinstance(blocks, list) else 0,
                    json.dumps(body, ensure_ascii=False),
                ),
            )
            self._database.commit()
            return "inserted"

    def insert_event_reaction(self, body: dict[str, Any], received_at: str) -> None:
        with self._lock:
            self._database.execute(
                "INSERT INTO event_reactions (received_at, body_json) VALUES (?, ?)",
                (received_at, json.dumps(body, ensure_ascii=False)),
            )
            self._database.commit()

    def insert_rejected(self, report_interface: str, problem: str, body: object, received_at: str) -> None:
        """Validation failures are stored too (the first scene of a mapping bug); the page marks them red."""
        with self._lock:
            self._database.execute(
                "INSERT INTO rejected_reports (received_at, interface, problem, body_json) VALUES (?, ?, ?, ?)",
                (received_at, report_interface, problem, json.dumps(body, ensure_ascii=False)),
            )
            self._database.commit()

    # ------------------------------------------------------------------ readers

    def query(
        self,
        interface: str,
        *,
        session_id: str | None = None,
        func_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        conditions: list[str] = []
        parameters: list[Any] = []
        # The rejected table has no session_id/func_id extracted columns; it
        # only ever returns by count.
        if interface != "rejected":
            if session_id is not None:
                conditions.append("session_id = ?")
                parameters.append(session_id)
            if func_id is not None:
                conditions.append("func_id = ?")
                parameters.append(func_id)
        where_clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        parameters.append(limit)
        with self._lock:
            # Table and column names come from the closed literal maps above;
            # every value rides the parameter list.
            query = f"SELECT * FROM {SQL_TABLE_BY_INTERFACE[interface]}{where_clause} ORDER BY id DESC LIMIT ?"  # noqa: S608
            cursor = self._database.execute(query, parameters)
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
        return [dict(zip(columns, row, strict=True)) for row in rows]

    def dump(self) -> dict[str, list[dict[str, Any]]]:
        return {interface: self.query(interface, limit=_MAX_DEBUG_LIMIT) for interface in REPORT_INTERFACES}

    def clear(self) -> None:
        with self._lock:
            for interface in REPORT_INTERFACES:
                # Table names come from the closed literal map above.
                self._database.execute(f"DELETE FROM {SQL_TABLE_BY_INTERFACE[interface]}")  # noqa: S608
            self._database.commit()

    def close(self) -> None:
        with self._lock:
            self._database.close()


class TelemetryMockServer(ThreadingHTTPServer):
    """A ThreadingHTTPServer carrying the shared state (store/faults/token)."""

    daemon_threads = True

    def __init__(
        self,
        address: tuple[str, int],
        handler: type[BaseHTTPRequestHandler],
        *,
        store: TelemetryStore,
        faults: FaultConfig,
        require_token: str | None,
        quiet: bool,
        now_ms: Callable[[], int] | None = None,
    ) -> None:
        super().__init__(address, handler)
        self.store = store
        self.faults = faults
        self.require_token = require_token
        self.quiet = quiet
        self.now_ms = now_ms if now_ms is not None else _default_now_ms


def _default_now_ms() -> int:
    return int(time.time() * 1000)


class _MockRequestHandler(BaseHTTPRequestHandler):
    """Routing and behaviour; see the module docstring for the endpoint list."""

    protocol_version = "HTTP/1.1"
    server: TelemetryMockServer

    def do_GET(self) -> None:
        self._route("GET")

    def do_POST(self) -> None:
        self._route("POST")

    def log_message(self, format: str, *args: Any) -> None:
        # The default writes every request to stderr; stay silent unless the
        # per-report summary lines are wanted.
        if not self.server.quiet:
            sys.stderr.write(f"[telemetry-mock] {format % args}\n")

    # ---------------------------------------------------------------- routing

    def _route(self, method: str) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if method == "GET" and path == "/health":
                self._send_json(200, {"service": "chrys-telemetry-mock", "status": "ok"})
                return
            if method == "GET" and path in ("/", "/debug/view"):
                self._send_html(200, _render_view_page())
                return
            if method == "POST" and path.startswith(API_PREFIX):
                self._handle_report_endpoint(path)
                return
            if method == "GET" and path == "/debug/reports":
                self._handle_debug_reports(parse_qs(parsed.query))
                return
            if method == "GET" and path == "/debug/dump":
                self._send_json(200, self.server.store.dump())
                return
            if method == "POST" and path == "/debug/clear":
                self.server.store.clear()
                self._send_json(200, {"cleared": True})
                return
            if method == "POST" and path == "/debug/faults":
                self._handle_debug_faults()
                return
            self._send_json(404, {"error": "not_found"})
        except _BodyTooLargeError:
            self._send_json(413, {"error": "body_too_large"})
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid_json"})
        except Exception:
            logger.exception("telemetry-mock internal error")
            self._send_json(500, {"error": "internal"})

    def _handle_report_endpoint(self, path: str) -> None:
        server = self.server
        if server.require_token is not None and self.headers.get("token") != server.require_token:
            self._send_json(401, {"success": False, "message": "unauthorized", "code": 401})
            return

        raw = self._read_body()
        parsed_json: object = json.loads(raw)
        problem = validate_report_body(path, parsed_json)
        now_ms = server.now_ms()
        received_at = _iso_from_ms(now_ms)
        if problem is not None:
            self._log_line(f"{_short_name(path)} REJECTED: {problem}\n")
            server.store.insert_rejected(_short_name(path), problem, parsed_json, received_at)
            self._send_json(
                400,
                {
                    "success": False,
                    "message": problem,
                    "code": 400,
                    "timestamp": now_ms,
                    "result": None,
                    "e": "invalid_request",
                },
            )
            return

        fault = _active_fault(server.faults, path, now_ms)
        if fault == "drop_body":
            self._log_line(f"{_short_name(path)} dropped (fault)\n")
            self.close_connection = True
            return
        if fault == "slow":
            time.sleep(server.faults.slow_ms / 1000)

        outcome = self._persist(path, parsed_json, received_at)
        self._log_line(f"{_summary_line(path, parsed_json, received_at, outcome)}\n")

        if fault in ("http500", "http503"):
            self._send_json(500 if fault == "http500" else 503, {"error": fault})
            return
        if fault == "envelope_reject":
            if path == AI_CODE_SAVE_ENDPOINT:
                self._send_json(200, {"code": 500, "message": "simulated business failure", "data": None})
            else:
                self._send_json(
                    200,
                    {
                        "success": False,
                        "message": "simulated business failure",
                        "code": 500,
                        "timestamp": now_ms,
                        "result": None,
                        "e": "BusinessException",
                    },
                )
            return

        if path == AI_CODE_SAVE_ENDPOINT:
            record = parsed_json if isinstance(parsed_json, dict) else {}
            self._send_json(
                200,
                {"code": 200, "message": "success", "data": {"reportId": record.get("reportId")}},
            )
            return
        self._send_json(
            200,
            {
                "success": True,
                "message": "保存成功",
                "code": 200,
                "timestamp": now_ms,
                "result": None,
                "e": None,
            },
        )

    def _persist(self, path: str, parsed_json: object, received_at: str) -> str:
        store = self.server.store
        version = parse_report_version(self.headers)
        if path == TOOL_DETAIL_SAVE_ENDPOINT:
            record = parsed_json if isinstance(parsed_json, dict) else {}
            version_tuple = (version.turn_content_hash, version.analysis_version) if version is not None else None
            return store.upsert_tool_detail_save(record, received_at, version_tuple)
        if path == TOOL_DETAIL_BATCH_SAVE_ENDPOINT:
            items = parsed_json if isinstance(parsed_json, list) else []
            return store.upsert_batch_save(items, received_at)
        if path == TOOL_DETAIL_UPDATE_ENDPOINT:
            record = parsed_json if isinstance(parsed_json, dict) else {}
            store.insert_tool_detail_update(record, received_at)
            return ""
        if path == AI_CODE_SAVE_ENDPOINT:
            record = parsed_json if isinstance(parsed_json, dict) else {}
            return store.upsert_ai_code_save(record, received_at)
        record = parsed_json if isinstance(parsed_json, dict) else {}
        store.insert_event_reaction(record, received_at)
        return ""

    def _handle_debug_reports(self, query: dict[str, list[str]]) -> None:
        interface = (query.get("interface") or [""])[0]
        if interface not in SQL_TABLE_BY_INTERFACE:
            self._send_json(400, {"error": "invalid_query"})
            return
        try:
            limit = int((query.get("limit") or ["100"])[0])
        except ValueError:
            self._send_json(400, {"error": "invalid_query"})
            return
        if not 1 <= limit <= _MAX_DEBUG_LIMIT:
            self._send_json(400, {"error": "invalid_query"})
            return
        rows = self.server.store.query(
            interface,
            session_id=(query.get("sessionId") or [None])[0],
            func_id=(query.get("funcId") or [None])[0],
            limit=limit,
        )
        self._send_json(200, {"interface": interface, "count": len(rows), "reports": rows})

    def _handle_debug_faults(self) -> None:
        config = json.loads(self._read_body())
        if not isinstance(config, dict) or config.get("mode") not in FAULT_MODES:
            self._send_json(400, {"error": "invalid_fault_config"})
            return
        rate = config.get("rate", 1.0)
        slow_ms = config.get("slowMs", 2_000)
        interfaces = config.get("interfaces", [])
        if not isinstance(rate, int | float) or isinstance(rate, bool) or not 0 <= rate <= 1:
            self._send_json(400, {"error": "invalid_fault_config"})
            return
        if isinstance(slow_ms, bool) or not isinstance(slow_ms, int) or not 0 <= slow_ms <= 60_000:
            self._send_json(400, {"error": "invalid_fault_config"})
            return
        if not isinstance(interfaces, list) or not all(isinstance(item, str) for item in interfaces):
            self._send_json(400, {"error": "invalid_fault_config"})
            return
        faults = self.server.faults
        faults.mode = config["mode"]
        faults.rate = rate
        faults.slow_ms = slow_ms
        faults.interfaces = tuple(interfaces)
        self._send_json(
            200,
            {
                "faults": {
                    "mode": faults.mode,
                    "rate": faults.rate,
                    "slowMs": faults.slow_ms,
                    "interfaces": list(faults.interfaces),
                }
            },
        )

    # ------------------------------------------------------------------ helpers

    def _read_body(self) -> str:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise json.JSONDecodeError("invalid content-length", "", 0) from exc
        if length > MAXIMUM_BODY_BYTES:
            raise _BodyTooLargeError
        chunks = []
        remaining = length
        while remaining > 0:
            chunk = self.rfile.read(min(remaining, 64 * 1024))
            if not chunk:
                break
            remaining -= len(chunk)
            chunks.append(chunk)
        return b"".join(chunks).decode("utf-8")

    def _log_line(self, line: str) -> None:
        if not self.server.quiet:
            sys.stdout.write(f"[telemetry-mock] {line}")

    def _send_json(self, status: int, payload: object) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, status: int, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)


class _BodyTooLargeError(Exception):
    """Request body exceeded ``MAXIMUM_BODY_BYTES``."""


def _active_fault(faults: FaultConfig, path: str, now_ms: int) -> str:
    if faults.mode == "none":
        return "none"
    if faults.interfaces and path not in faults.interfaces and _short_name(path) not in faults.interfaces:
        return "none"
    if faults.rate < 1 and _pseudo_random(now_ms) > faults.rate:
        return "none"
    return faults.mode


def _pseudo_random(seed_ms: int) -> float:
    """Deterministic pseudo random: the same millisecond judges the same, for test assertions."""
    value = math.sin(seed_ms) * 10_000
    return value - math.floor(value)


def _short_name(path: str) -> str:
    return path.removeprefix(API_PREFIX)


def _iso_from_ms(now_ms: int) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(now_ms / 1000)) + f".{now_ms % 1000:03d}Z"


def _summary_line(path: str, parsed_json: object, received_at: str, outcome: str) -> str:
    name = _short_name(path)
    if not isinstance(parsed_json, dict):
        return f"{name} ok (array, {received_at})"
    details = []
    for key in ("sessionId", "funcId", "funcName", "reportId", "codeStatus"):
        value = parsed_json.get(key)
        if isinstance(value, str) and value:
            details.append(f"{key}={value[:40]}")
        elif isinstance(value, int):
            details.append(f"{key}={value}")
    suffix = f" [{outcome}]" if outcome else ""
    return f"{name} ok {' '.join(details)} ({received_at}){suffix}"


def _text_or_none(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _int_or_none(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _render_view_page() -> str:
    """Self-contained zero-dependency observation page (list, key columns, expand, filter, auto refresh)."""
    return """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Chrys 会话数据上报 Mock</title>
<style>
  body { font: 14px/1.5 system-ui, sans-serif; margin: 0; background: #f6f8fa; color: #1f2328; }
  header { position: sticky; top: 0; z-index: 1; display: flex; flex-wrap: wrap; gap: .75rem;
           align-items: center; padding: .6rem 1rem; background: #24292f; color: #fff; }
  header h1 { font-size: 1rem; margin: 0; }
  header .stats { font-size: .8rem; opacity: .85; }
  header input[type=text] { padding: .3rem .5rem; border-radius: 6px; border: none; }
  header button { padding: .3rem .7rem; border-radius: 6px; border: none; cursor: pointer; }
  main { padding: 1rem; max-width: 75rem; margin: 0 auto; }
  section { background: #fff; border: 1px solid #d0d7de; border-radius: 8px;
            margin-bottom: 1rem; overflow: hidden; }
  section > h2 { font-size: .9rem; margin: 0; padding: .5rem .75rem;
                 background: #eef1f4; border-bottom: 1px solid #d0d7de; }
  section.rejected > h2 { background: #ffebe9; color: #cf222e; }
  table { border-collapse: collapse; width: 100%; font-size: .8rem; }
  th, td { text-align: left; padding: .35rem .6rem; border-bottom: 1px solid #eaeef2;
           white-space: nowrap; max-width: 22rem; overflow: hidden; text-overflow: ellipsis; }
  th { color: #57606a; font-weight: 600; }
  tr { cursor: pointer; }
  tr:hover { background: #f3f4f6; }
  tr.detail-row > td { padding: 0; }
  pre { margin: 0; padding: .6rem .75rem; background: #0d1117; color: #c9d1d9;
        font-size: .78rem; overflow: auto; white-space: pre-wrap; word-break: break-all; }
  .empty { padding: .6rem .75rem; color: #6e7781; font-size: .8rem; }
</style>
</head>
<body>
<header>
  <h1>Chrys 会话数据上报 Mock</h1>
  <span class="stats" id="stats"></span>
  <input type="text" id="sessionFilter" placeholder="按 sessionId 过滤" size="24">
  <label><input type="checkbox" id="autoRefresh" checked> 自动刷新(2s)</label>
  <button id="expandBtn">全部展开</button>
  <button id="refreshBtn">刷新</button>
  <button id="clearBtn">清空</button>
</header>
<main id="main"><p class="empty">加载中...</p></main>
<script>
  const TABLES = [
    { key: 'rejected', title: '被拒报文(校验失败, 红色=映射bug嫌疑)' },
    { key: 'tool-detail/save', title: 'tool-detail/save(工具调用)' },
    { key: 'tool-detail/update', title: 'tool-detail/update(执行状态)' },
    { key: 'tool-detail/batch-save', title: 'tool-detail/batch-save(用户输入触发)' },
    { key: 'ai-code/save', title: 'ai-code/save(AI 生成代码)' },
    { key: 'event-reaction/save', title: 'event-reaction/save(预留)' },
  ];
  const COLUMNS = [
    ['received_at', '时间'], ['session_id', 'sessionId'], ['func_id', 'funcId'],
    ['request_id', 'requestId'], ['span_id', 'spanId'], ['func_name', 'funcName'],
    ['code_status', 'codeStatus'], ['item_count', '条数'],
    ['original_lines', '原行'], ['added_lines', '增行'], ['deleted_lines', '删行'],
    ['problem', '拒绝原因'], ['body_json', '原始报文'],
  ];

  function cellText(row, column) {
    const value = row[column];
    if (value === undefined || value === null || value === '') return '';
    if (column === 'body_json') return '点击展开...';
    return String(value);
  }

  function renderTable(tableKey, title, rows, isRejected) {
    const filter = document.getElementById('sessionFilter').value.trim();
    const visible = rows.filter((row) => !filter ||
      String(row.session_id ?? '').includes(filter) ||
      String(row.func_id ?? '').includes(filter) ||
      String(row.request_id ?? '').includes(filter) ||
      String(row.body_json ?? '').includes(filter));
    const section = document.createElement('section');
    if (isRejected) section.className = 'rejected';
    const heading = document.createElement('h2');
    heading.textContent = title + ' · ' + visible.length + ' 条';
    section.appendChild(heading);
    if (visible.length === 0) {
      const empty = document.createElement('p');
      empty.className = 'empty';
      empty.textContent = '(无记录)';
      section.appendChild(empty);
      return section;
    }
    const table = document.createElement('table');
    const headRow = document.createElement('tr');
    for (const [, label] of COLUMNS) {
      const th = document.createElement('th');
      th.textContent = label;
      headRow.appendChild(th);
    }
    table.appendChild(headRow);
    for (const row of visible) {
      const tr = document.createElement('tr');
      for (const [column] of COLUMNS) {
        const td = document.createElement('td');
        td.textContent = cellText(row, column);
        tr.appendChild(td);
      }
      const rowKey = tableKey + '#' + row.id;
      const detail = document.createElement('tr');
      detail.className = 'detail-row';
      detail.style.display = expandedAll || expandedRows.has(rowKey) ? '' : 'none';
      const td = document.createElement('td');
      td.colSpan = COLUMNS.length;
      const pre = document.createElement('pre');
      pre.textContent = JSON.stringify(JSON.parse(row.body_json), null, 2);
      td.appendChild(pre);
      detail.appendChild(td);
      tr.addEventListener('click', () => {
        if (detail.style.display === 'none') {
          expandedRows.add(rowKey);
          detail.style.display = '';
        } else {
          expandedRows.delete(rowKey);
          detail.style.display = 'none';
        }
      });
      table.appendChild(tr);
      table.appendChild(detail);
    }
    section.appendChild(table);
    return section;
  }

  let expandedAll = false;
  const expandedRows = new Set();

  function applyExpandedAll() {
    document.querySelectorAll('tr.detail-row').forEach((row) => {
      row.style.display = expandedAll ? '' : 'none';
    });
    document.getElementById('expandBtn').textContent = expandedAll ? '全部收起' : '全部展开';
  }

  async function refresh() {
    try {
      const dump = await (await fetch('/debug/dump')).json();
      const main = document.getElementById('main');
      main.replaceChildren(
        ...TABLES.map((table) => renderTable(table.key, table.title, dump[table.key] ?? [], table.key === 'rejected')));
      const total = TABLES.reduce((sum, table) => sum + (dump[table.key] ?? []).length, 0);
      document.getElementById('stats').textContent = '共 ' + total + ' 条 · ' + new Date().toLocaleTimeString();
      document.getElementById('expandBtn').textContent = expandedAll ? '全部收起' : '全部展开';
    } catch (error) {
      document.getElementById('stats').textContent = '刷新失败: ' + error;
    }
  }

  document.getElementById('refreshBtn').addEventListener('click', refresh);
  document.getElementById('sessionFilter').addEventListener('input', refresh);
  document.getElementById('expandBtn').addEventListener('click', () => {
    expandedAll = !expandedAll;
    if (!expandedAll) expandedRows.clear();
    applyExpandedAll();
  });
  document.getElementById('clearBtn').addEventListener('click', async () => {
    await fetch('/debug/clear', { method: 'POST' });
    refresh();
  });
  refresh();
  setInterval(() => {
    if (document.getElementById('autoRefresh').checked && !document.hidden) refresh();
  }, 2000);
</script>
</body>
</html>"""


# --------------------------------------------------------------------------
# Entry points
# --------------------------------------------------------------------------


def start_telemetry_mock(
    *,
    host: str = "127.0.0.1",
    port: int = 0,
    database_path: str = ":memory:",
    require_token: str | None = None,
    quiet: bool = False,
    now_ms: Callable[[], int] | None = None,
) -> RunningTelemetryMock:
    """Start the mock (returns once bound; the server thread is a daemon); loopback binds only."""
    if host not in _LOOPBACK_HOSTS:
        raise ValueError("The telemetry mock server may bind only to a loopback address.")
    if database_path != ":memory:":
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    store = TelemetryStore(database_path)
    faults = FaultConfig()
    server = TelemetryMockServer(
        (host, port),
        _MockRequestHandler,
        store=store,
        faults=faults,
        require_token=require_token,
        quiet=quiet,
        now_ms=now_ms,
    )
    thread = threading.Thread(target=server.serve_forever, name="chrys-telemetry-mock", daemon=True)
    thread.start()
    bound_port = server.server_address[1]
    origin = f"http://{'[' + host + ']' if ':' in host else host}:{bound_port}"
    return RunningTelemetryMock(
        origin=origin,
        database_path=database_path,
        store=store,
        faults=faults,
        server=server,
    )


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Chrys session reporting mock server (local debug tool)")
    parser.add_argument("--port", type=int, default=_DEFAULT_PORT, help="listen port (default %(default)s)")
    parser.add_argument("--db", default=":memory:", help="SQLite path (default: in-memory)")
    parser.add_argument("--require-token", default=None, help="required `token` request header")
    parser.add_argument("--quiet", action="store_true", help="do not print per-request summaries")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_argument_parser().parse_args(argv)
    try:
        running = start_telemetry_mock(
            port=args.port,
            database_path=args.db,
            require_token=args.require_token,
            quiet=args.quiet,
        )
    except (OSError, ValueError) as exc:
        sys.stderr.write(f"Telemetry mock failed to start: {exc}\n")
        return 1
    sys.stdout.write(f"Chrys telemetry mock listening at {running.origin}\n")
    sys.stdout.write(f"SQLite database: {running.database_path}\n")
    sys.stdout.write(
        "Endpoints: POST /csas/telemetry/api/v1/{tool-detail/save,tool-detail/batch-save,"
        "tool-detail/update,ai-code/save,event-reaction/save}\n"
        "Debug: GET /debug/reports?interface=... | GET /debug/dump | POST /debug/clear | POST /debug/faults\n"
    )
    try:
        threading.Event().wait()  # The server thread is a daemon; wait for interrupt.
    except KeyboardInterrupt:
        pass
    finally:
        running.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
