# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Chrys session reporting collector: EventBus events -> report bodies -> background delivery.

Hard rule (same as trajectory recording): reporting never blocks or breaks a
user-visible path. ``EventBus.publish`` awaits every handler inline, so the
handlers here only project the event into an in-memory queue
(``put_nowait``, never awaiting the network); HTTP delivery happens on a
dedicated background task. Transport failures retry on a bounded backoff and
are then dropped with a counter — telemetry's value never outweighs the cost
of it dragging down a session.

The contract and the send-side self check share
:mod:`chrys.foundation.reporting.schemas` (single source of truth): a
projected body is validated locally before it is queued, so a mapping bug is
dropped at the first site with a log line instead of shipping an invalid body
to the backend to earn a 400.

Current projection coverage (see the phased plan in this package's
``docs/design.md``):

* ``tool-detail/save`` — ``InvocationToolCallStart`` (a tool call started).
* ``tool-detail/update`` — ``InvocationToolCallResult`` (execution outcome).

Not yet covered: ``tool-detail/batch-save`` (user-input trigger),
``ai-code/save`` (AI-generated code blocks, needs mutations data) and the
``X-Turn-Content-Hash`` idempotency headers (needs turn content fingerprints
from the engine assembly layer).
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import httpx

from chrys.foundation.events.bus import EventBus
from chrys.foundation.events.types import InvocationToolCallResult, InvocationToolCallStart
from chrys.foundation.util.httpx_helpers import BYPASS_PROXY_MOUNTS

from .schemas import (
    TOOL_DETAIL_SAVE_ENDPOINT,
    TOOL_DETAIL_UPDATE_ENDPOINT,
    report_is_accepted,
    validate_report_body,
)

logger = logging.getLogger(__name__)

# codeStatus semantics are pending alignment with the Chrys backend enum (see
# docs/design.md open items); 0=started, 1=success, 2=error is the current
# conservative convention.
_CODE_STATUS_STARTED = 0
_CODE_STATUS_SUCCESS = 1
_CODE_STATUS_ERROR = 2

# Result text marks failure with the ``Error: `` prefix (the ``tool_error``
# contract the UI and persistence also read).
_ERROR_PREFIX = "Error: "
_MAX_ERROR_MESSAGE_LENGTH = 4096

# call_id values recur across exchanges ("ids are not identity"); this table
# only pairs one turn's start->result with the same funcId. When the cap is
# hit the table is cleared wholesale; an occasionally unpaired result just
# mints a fresh funcId.
_MAX_TRACKED_CALL_IDS = 4096

_VALUE_ARG_KEYS = (
    "path",
    "file_path",
    "filePath",
    "file",
    "command",
    "cmd",
    "pattern",
    "query",
    "prompt",
    "url",
    "name",
)
_FILE_ARG_KEYS = frozenset({"path", "file_path", "filePath", "file"})


@dataclass(frozen=True, slots=True)
class ReportCollectorConfig:
    """One config per session host (one bus)."""

    endpoint: str
    """Backend base origin, e.g. ``http://127.0.0.1:4321``; no endpoint path."""

    session_id: str = ""
    """The reported sessionId; per-event ``session_id`` is used when blank."""

    token: str | None = None
    """The ``token`` header sent with every request (backend auth; the local mock pairs it with ``--require-token``)."""

    product_name: str = "icode"
    channel_type: str = "tui"
    func_type: int = 0
    """Placeholder until aligned with the Chrys backend funcType enum (then mapped by tool_kind)."""

    queue_limit: int = 1000
    request_timeout_seconds: float = 5.0
    retry_delays_seconds: tuple[float, ...] = (0.5, 2.0)
    """Backoff before each retry; an empty tuple means no retries (tests)."""

    bypass_proxy: bool = False
    """Connect directly, bypassing environment/system proxies (mirrors the MCP transport mounts convention)."""


@dataclass(frozen=True, slots=True)
class _OutgoingReport:
    endpoint: str
    body: dict[str, Any]


class TelemetryReportCollector:
    """Subscribes to invocation tool events and reports them to the Chrys session backend.

    Lifecycle: ``start(bus)`` subscribes and starts the sender task;
    ``stop()`` unsubscribes, cancels the task and closes the HTTP client.
    Both are idempotent. Failure semantics: transport errors and non-200
    responses retry on the configured backoff; exhausted retries and backend
    business rejections (HTTP 200 + ``success=false``) drop the report — the
    backend already gave a definitive answer, so resending is not worth it.
    """

    def __init__(self, config: ReportCollectorConfig) -> None:
        self._config = config
        self._bus: EventBus | None = None
        self._queue: asyncio.Queue[_OutgoingReport] | None = None
        self._sender_task: asyncio.Task[None] | None = None
        self._client: httpx.AsyncClient | None = None
        self._func_ids: dict[str, str] = {}
        self._sent_count = 0
        self._dropped_count = 0

    @property
    def sent_count(self) -> int:
        """Reports the backend accepted."""
        return self._sent_count

    @property
    def dropped_count(self) -> int:
        """Reports dropped by queue overflow, exhausted retries, self check or business rejection."""
        return self._dropped_count

    # -------------------------------------------------------------- lifecycle

    async def start(self, bus: EventBus) -> None:
        if self._bus is not None:
            return
        self._bus = bus
        self._queue = asyncio.Queue(maxsize=self._config.queue_limit)
        await bus.subscribe(InvocationToolCallStart, self._on_tool_call_start)
        await bus.subscribe(InvocationToolCallResult, self._on_tool_call_result)
        self._sender_task = asyncio.create_task(self._sender_loop(), name="chrys-telemetry-report-sender")

    async def stop(self) -> None:
        bus, self._bus = self._bus, None
        if bus is not None:
            await bus.unsubscribe(InvocationToolCallStart, self._on_tool_call_start)
            await bus.unsubscribe(InvocationToolCallResult, self._on_tool_call_result)
        task, self._sender_task = self._sender_task, None
        if task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        client, self._client = self._client, None
        if client is not None:
            with contextlib.suppress(Exception):
                await client.aclose()

    # --------------------------------------------------------------- handlers

    async def _on_tool_call_start(self, event: InvocationToolCallStart) -> None:
        """The publisher awaits this handler inline: sync projection and queueing only, never the network."""
        body = self._tool_detail_save_body(event)
        if body is not None:
            self._enqueue(TOOL_DETAIL_SAVE_ENDPOINT, body)

    async def _on_tool_call_result(self, event: InvocationToolCallResult) -> None:
        body = self._tool_detail_update_body(event)
        if body is not None:
            self._enqueue(TOOL_DETAIL_UPDATE_ENDPOINT, body)

    # ------------------------------------------------------------- projection

    def _tool_detail_save_body(self, event: InvocationToolCallStart) -> dict[str, Any] | None:
        func_id = uuid.uuid4().hex
        if event.call_id:
            self._remember_func_id(event.call_id, func_id)
        body: dict[str, Any] = {
            "productName": self._config.product_name,
            "funcType": self._config.func_type,
            "funcName": event.tool_name or event.tool_kind or "unknown",
            "funcId": func_id,
            "codeStatus": _CODE_STATUS_STARTED,
            "channelType": self._config.channel_type,
            "requestId": event.origin.root.invocation_id,
            "spanId": str(uuid.uuid4()),
        }
        session_id = self._config.session_id or event.session_id
        if session_id:
            body["sessionId"] = session_id
        value, file_name = _primary_argument(event.args)
        if value is not None:
            body["value"] = value
        if file_name is not None:
            body["fileName"] = file_name
        return self._self_checked(TOOL_DETAIL_SAVE_ENDPOINT, body)

    def _tool_detail_update_body(self, event: InvocationToolCallResult) -> dict[str, Any] | None:
        func_id = self._func_ids.get(event.call_id) or uuid.uuid4().hex
        errored = event.result.startswith(_ERROR_PREFIX)
        body: dict[str, Any] = {
            "funcId": func_id,
            "codeStatus": _CODE_STATUS_ERROR if errored else _CODE_STATUS_SUCCESS,
            "funcName": event.tool_name or "unknown",
        }
        if errored:
            body["funcErrorMessage"] = event.result[:_MAX_ERROR_MESSAGE_LENGTH]
        return self._self_checked(TOOL_DETAIL_UPDATE_ENDPOINT, body)

    def _self_checked(self, endpoint: str, body: dict[str, Any]) -> dict[str, Any] | None:
        """The other half of the single source of truth: an invalid projection is dropped here with a log."""
        problem = validate_report_body(endpoint, body)
        if problem is not None:
            logger.warning("Chrys report dropped by local contract check (%s): %s", problem, endpoint)
            self._dropped_count += 1
            return None
        return body

    def _remember_func_id(self, call_id: str, func_id: str) -> None:
        if len(self._func_ids) >= _MAX_TRACKED_CALL_IDS and call_id not in self._func_ids:
            self._func_ids.clear()
        self._func_ids[call_id] = func_id

    # ----------------------------------------------------------------- sending

    def _enqueue(self, endpoint: str, body: dict[str, Any]) -> None:
        queue = self._queue
        if queue is None:
            return
        try:
            queue.put_nowait(_OutgoingReport(endpoint=endpoint, body=body))
        except asyncio.QueueFull:
            self._dropped_count += 1
            logger.warning(
                "Chrys report queue full (limit %d); report for %s dropped",
                self._config.queue_limit,
                endpoint,
            )

    async def _sender_loop(self) -> None:
        queue = self._queue
        if queue is None:
            return
        while True:
            report = await queue.get()
            try:
                await self._send(report)
            except Exception:
                logger.debug("Chrys report send failed", exc_info=True)

    async def _send(self, report: _OutgoingReport) -> None:
        delays = self._config.retry_delays_seconds
        for attempt in range(len(delays) + 1):
            try:
                if await self._post(report):
                    self._sent_count += 1
                    return
                # Business rejection: the backend answered definitively; no retry.
                self._dropped_count += 1
                return
            except Exception:
                logger.debug("Chrys report attempt %d failed", attempt + 1, exc_info=True)
            if attempt < len(delays):
                await asyncio.sleep(delays[attempt])
        self._dropped_count += 1
        logger.warning(
            "Chrys report dropped after %d attempts (endpoint=%s)",
            len(delays) + 1,
            report.endpoint,
        )

    async def _post(self, report: _OutgoingReport) -> bool:
        """Send once; returns whether the backend accepted it. Transport/HTTP failures raise (retry lane)."""
        headers: dict[str, str] = {}
        if self._config.token is not None:
            headers["token"] = self._config.token
        response = await self._ensure_client().post(
            f"{self._config.endpoint}{report.endpoint}",
            json=report.body,
            headers=headers,
        )
        if response.status_code != 200:
            raise RuntimeError(f"chrys report endpoint answered HTTP {response.status_code}")
        try:
            payload: object = response.json()
        except ValueError:
            payload = response.text
        if report_is_accepted(report.endpoint, status_code=200, payload=payload):
            return True
        logger.warning("Chrys report rejected by backend (endpoint=%s): %s", report.endpoint, payload)
        return False

    def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self._config.request_timeout_seconds,
                mounts=dict(BYPASS_PROXY_MOUNTS) if self._config.bypass_proxy else None,
            )
        return self._client


def _primary_argument(args: Mapping[str, Any]) -> tuple[str | None, str | None]:
    """Pick one representative argument as ``value`` (paths/commands/queries first); path-like keys double as fileName."""
    for key in _VALUE_ARG_KEYS:
        value = args.get(key)
        if isinstance(value, str) and value:
            return value, value if key in _FILE_ARG_KEYS else None
    return None, None
