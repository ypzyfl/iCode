# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""HTTP report sink: dispatch a SessionTelemetryReport's reportEvents
by event kind to 4 backend interfaces (TS ``report/http-sink.ts``;
contract §2/§4).

Ordering: send in the events' original order, one by one (the analysis
core guarantees a same-funcId save precedes its update); consecutive
input-triggered-use events aggregate into one batch-save array request.
Failure semantics: any failed request stops the run and fails the whole
report (every segment must succeed; ADR 0041 decision 5: a failure
never advances the ledger — a retry re-analyzes and re-reports, the
backend deduplicates by business keys).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx

from chrys.aixcoding.telemetry.collector.analysis.context import derive_span_id
from chrys.aixcoding.telemetry.collector.report.port import PortResult, SessionTelemetryReport


@dataclass(frozen=True, slots=True)
class HttpReportSinkOptions:
    # Reporting base (e.g. ``http://127.0.0.1:4321/csas/telemetry/api/v1``).
    endpoint: str
    token: str | None
    client: httpx.Client
    timeout_ms: int = 10_000
    # Registration-focus fields (value/fileName/extra/gitRemote/
    # funcErrorMessage/filepath/blocks[].snippet) stay out of the
    # remote payload until the D1 registration table is approved (ADR
    # 0041 decision 4 allowlist boundary; the file sink observes them
    # locally regardless). Flipping this plus advancing
    # ANALYSIS_VERSION releases them in one shot.
    focus_fields_enabled: bool = False


@dataclass(frozen=True, slots=True)
class PlannedReportRequest:
    """One HTTP request to send (the event-planning product; a pure
    function, unit-testable)."""

    path: str
    body: Any
    # Idempotency helper headers carried by save/ai-code only
    # (contract §2.1/§4.3).
    headers: dict[str, str] | None = None


@dataclass(frozen=True, slots=True)
class ReportRequestPlanning:
    """Version-idempotency-header planning input: analysisVersion plus
    per-spanId turn content_hash (derived by the orchestration layer
    from incrementalTurns; update/batch-save carry none)."""

    analysis_version: int
    content_hash_by_span_id: dict[str, str]


def plan_report_requests(
    events: list[dict[str, Any]],
    planning: ReportRequestPlanning | None = None,
    focus_fields_enabled: bool = False,
) -> list[PlannedReportRequest]:
    """Events → request sequence. Consecutive input-triggered-use
    events aggregate into a batch-save array. Body construction omits
    absent/None event fields (the TS omitUndefined parity: event dicts
    never carry explicit null values — the analysis constructors add
    keys conditionally). focus_fields_enabled gates the
    registration-focus fields out of the remote payload (registration
    table §3.1; the file sink observes them locally)."""
    requests: list[PlannedReportRequest] = []
    pending_batch: list[dict[str, Any]] | None = None

    def flush_batch() -> None:
        nonlocal pending_batch
        if pending_batch:
            requests.append(PlannedReportRequest(path="tool-detail/batch-save", body=pending_batch))
        pending_batch = None

    def version_headers(event: dict[str, Any]) -> dict[str, str] | None:
        if planning is None:
            return None
        content_hash = planning.content_hash_by_span_id.get(event["spanId"])
        if content_hash is None:
            return None
        return {
            "X-Turn-Content-Hash": content_hash,
            "X-Analysis-Version": str(planning.analysis_version),
        }

    for event in events:
        kind = event.get("kind")
        if kind == "input-triggered-use":
            # flush_batch reassigns the nonlocal via closure, so the
            # None-narrowing does not survive across statements — bind
            # a local alias.
            batch = pending_batch if pending_batch is not None else []
            batch.append(_input_triggered_use_body(event, focus_fields_enabled))
            pending_batch = batch
            continue
        flush_batch()
        if kind == "tool-use-saved":
            requests.append(
                PlannedReportRequest(
                    path="tool-detail/save",
                    body=_tool_use_saved_body(event, focus_fields_enabled),
                    headers=version_headers(event),
                )
            )
        elif kind == "tool-status-updated":
            requests.append(
                PlannedReportRequest(
                    path="tool-detail/update",
                    body=_tool_status_updated_body(event, focus_fields_enabled),
                )
            )
        else:
            requests.append(
                PlannedReportRequest(
                    path="ai-code/save",
                    body=_ai_code_saved_body(event, focus_fields_enabled),
                    headers=version_headers(event),
                )
            )
    flush_batch()
    return requests


class HttpReportSink:
    def __init__(self, options: HttpReportSinkOptions) -> None:
        self._endpoint = options.endpoint
        self._token = options.token
        self._client = options.client
        self._timeout_ms = options.timeout_ms
        self._focus_fields_enabled = options.focus_fields_enabled

    def report(self, event: SessionTelemetryReport) -> PortResult:
        # Version idempotency headers (contract §2.1): save/ai-code
        # associate the turn's content_hash by spanId.
        content_hash_by_span_id = {
            derive_span_id(str(event.session.get("sessionId") or ""), turn["turnId"]): turn["contentHash"]
            for turn in event.incremental_turns
        }
        planning = ReportRequestPlanning(
            analysis_version=event.analysis_version,
            content_hash_by_span_id=content_hash_by_span_id,
        )
        for request in plan_report_requests(event.report_events, planning, self._focus_fields_enabled):
            result = self._send(request)
            if not result.success:
                return result
        return PortResult(success=True)

    def _send(self, request: PlannedReportRequest) -> PortResult:
        url = f"{self._endpoint}/{request.path}"
        headers: dict[str, str] = {"content-type": "application/json"}
        if self._token is not None:
            headers["token"] = self._token
        if request.headers is not None:
            headers.update(request.headers)
        try:
            response = self._client.post(
                url,
                headers=headers,
                content=json.dumps(request.body),
                timeout=self._timeout_ms / 1000,
            )
            if response.status_code < 200 or response.status_code >= 300:
                return PortResult(
                    success=False,
                    retryable=True,
                    message=f"Report to {request.path} failed with status {response.status_code}.",
                )
            envelope = response.json()
            accepted = (
                envelope.get("code") == 200
                if request.path == "ai-code/save"
                else envelope.get("success") is True and envelope.get("code") == 200
            )
            if not accepted:
                message = envelope.get("message") or f"code {envelope.get('code')}"
                return PortResult(
                    success=False,
                    retryable=False,
                    message=f"Report to {request.path} rejected by backend: {message}.",
                )
            return PortResult(success=True)
        except (httpx.HTTPError, ValueError) as error:
            detail = f": {error}" if str(error) else "."
            return PortResult(
                success=False,
                retryable=True,
                message=f"Report to {request.path} failed{detail}",
            )


def _pick(event: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {key: event[key] for key in keys if event.get(key) is not None}


def _input_triggered_use_body(event: dict[str, Any], focus_fields_enabled: bool = False) -> dict[str, Any]:
    keys = (
        "funcType",
        "funcName",
        "spanId",
        "sessionId",
        "userId",
        "projectName",
        "channelType",
        "channelName",
        "channelVersion",
        "pluginVersion",
        "gitBranch",
        "gitRevision",
        "gitOwner",
        "gitRepo",
    )
    if focus_fields_enabled:
        keys += ("gitRemote",)
    return _pick(event, keys)


def _tool_use_saved_body(event: dict[str, Any], focus_fields_enabled: bool = False) -> dict[str, Any]:
    keys = (
        "productName",
        "projectName",
        "funcType",
        "funcName",
        "funcId",
        "requestId",
        "spanId",
        "sessionId",
        "userId",
        "codeStatus",
        "channelType",
        "channelName",
        "channelVersion",
        "pluginVersion",
        "gitBranch",
        "gitRevision",
        "gitOwner",
        "gitRepo",
    )
    if focus_fields_enabled:
        keys += ("value", "fileName", "extra", "gitRemote")
    return _pick(event, keys)


def _tool_status_updated_body(event: dict[str, Any], focus_fields_enabled: bool = False) -> dict[str, Any]:
    keys = (
        "funcId",
        "codeStatus",
        "originalLines",
        "addedLines",
        "deletedLines",
    )
    if focus_fields_enabled:
        keys += ("funcErrorMessage",)
    return _pick(event, keys)


def _ai_code_saved_body(event: dict[str, Any], focus_fields_enabled: bool = False) -> dict[str, Any]:
    keys = (
        "reportId",
        "sessionId",
        "spanId",
        "requestId",
        "blocks",
        "sourceType",
        "channelType",
        "inputMethod",
        "language",
        "remoteUrl",
        "branch",
        "gitUserName",
        "gitUserEmail",
    )
    if focus_fields_enabled:
        keys += ("filepath",)
    body = _pick(event, keys)
    if not focus_fields_enabled:
        blocks = body.get("blocks")
        if blocks:
            # The per-block snippet is a registration-focus field:
            # strip it while the ranges stay (the block itself is not
            # gated — the snippet source alone is).
            body["blocks"] = [
                {key: value for key, value in block.items() if key != "snippet"}
                for block in blocks
                if isinstance(block, dict)
            ]
    return body
