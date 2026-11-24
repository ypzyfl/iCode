# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Outbound telemetry DTOs (B7/B8 contracts; ids stay raw 32hex everywhere).

Field sets mirror the mock 1B allowlists exactly — an unknown field here would
be rejected server-side, so the DTO constructors are the single place both
sides agree on. No execution timestamps, no providerCallId (BR-8 withdrawn),
no parentSpanId on ordinary independent turns.
"""

from __future__ import annotations

from typing import Any

SCHEMA_VERSION = "1"


def llm_report(*, session_id: str, request_id: str, span_id: str, event_sub_type: str = "success") -> dict[str, Any]:
    return {
        "schemaVersion": SCHEMA_VERSION,
        "sessionId": session_id,
        "eventType": "llm",
        "eventSubType": event_sub_type,
        "requestId": request_id,
        "spanId": span_id,
    }


def tool_detail(
    *,
    request_id: str,
    func_id: str,
    func_name: str,
    func_type: str,
    session_id: str,
    span_id: str,
    code_status: str,
) -> dict[str, Any]:
    return {
        "requestId": request_id,
        "funcId": func_id,
        "funcName": func_name,
        "funcType": func_type,
        "sessionId": session_id,
        "spanId": span_id,
        "codeStatus": code_status,
    }


def ai_code_report(
    *,
    report_id: str,
    request_id: str,
    filepath: str,
    blocks: list[dict[str, Any]],
    source_type: str,
    input_method: str,
    code_status: str,
) -> dict[str, Any]:
    return {
        "reportId": report_id,
        "requestId": request_id,
        "filepath": filepath,
        "blocks": blocks,
        "sourceType": source_type,
        "inputMethod": input_method,
        "codeStatus": code_status,
    }


def func_type_for(tool_name: str) -> str:
    """Coarse function-type bucket for the B8 ``funcType`` field."""
    name = tool_name.lower()
    if any(part in name for part in ("write", "edit", "read", "file")):
        return "file"
    return "other"
