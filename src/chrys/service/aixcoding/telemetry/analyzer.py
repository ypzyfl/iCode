# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Analyzer: turn facts + saved files -> the three outbound DTO groups.

Fail-closed throughout: a record without its evidence (missing function name
in the transcript, unreadable mutation ledger) is skipped and listed, never
fabricated. The ai-code group reads the mutation ledger
(``session.json.state.chrys_mutations``); when the ledger is absent or its
shape is not understood, the whole ai-code group degrades to a logged skip —
the llm/tool groups still report (their sources are independent).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from chrys.foundation.trajectory.metadata import ANALYTICS_ITEM_ID_KEY
from chrys.service.aixcoding.telemetry import dto
from chrys.service.aixcoding.telemetry.reader import TurnFacts

logger = logging.getLogger(__name__)


@dataclass
class ReportBatch:
    session_id: str
    span_id: str
    llm: list[dict[str, Any]] = field(default_factory=list)
    tools: list[dict[str, Any]] = field(default_factory=list)
    ai_codes: list[dict[str, Any]] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def _transcript_call_names(session_dir: Path, session_id: str) -> dict[str, tuple[str, str]]:
    """Map call_item_id -> (function name, request_attempt_id-of-its-message)."""
    session_file = Path(session_dir) / "session.json"
    try:
        document = json.loads(session_file.read_text(encoding="utf-8"))
    except OSError, ValueError:
        logger.debug("telemetry analyzer: cannot read %s", session_file, exc_info=True)
        return {}
    names: dict[str, tuple[str, str]] = {}
    messages = document.get("messages")
    if not isinstance(messages, list):
        state = document.get("state")
        messages = state.get("messages") if isinstance(state, dict) else None
    if not isinstance(messages, list):
        logger.debug("telemetry analyzer: no messages array in %s", session_file)
        return {}
    for item in messages:
        if not isinstance(item, dict) or item.get("role") != "assistant":
            continue
        properties = item.get("additional_properties") or {}
        attempt = properties.get("_chrys_request_attempt_id", "")
        for content in item.get("contents") or []:
            # On disk a function_call is flat: {"type", "call_id", "name",
            # "arguments", "additional_properties"} — the wire-style nested
            # "function" object does not exist in the saved shape.
            if not isinstance(content, dict) or content.get("type") != "function_call":
                continue
            call_properties = content.get("additional_properties") or {}
            item_id = call_properties.get(ANALYTICS_ITEM_ID_KEY)
            function_name = content.get("name")
            if item_id and function_name:
                names[str(item_id)] = (str(function_name), str(attempt))
    return names


def build_report_batch(session_dir: Path, facts: TurnFacts) -> ReportBatch:
    batch = ReportBatch(session_id=facts.session_id, span_id=facts.logical_turn_id)
    call_names = _transcript_call_names(session_dir, facts.session_id)

    # tool parent exchange -> its A (the successful call that produced it)
    exchange_to_attempt = {fact.model_call_id: fact.request_attempt_id for fact in facts.llm}

    for fact in facts.llm:
        batch.llm.append(
            dto.llm_report(
                session_id=facts.session_id,
                request_id=fact.request_attempt_id,
                span_id=facts.logical_turn_id,
            )
        )
    for tool in facts.tools:
        entry = call_names.get(tool.call_item_id or "")
        if entry is None:
            batch.skipped.append(f"tool-no-transcript-name:{tool.tool_op_id}")
            continue
        func_name, _attempt_of_message = entry
        request_attempt = exchange_to_attempt.get(tool.model_call_id)
        if request_attempt is None:
            batch.skipped.append(f"tool-orphan-exchange:{tool.tool_op_id}")
            continue
        batch.tools.append(
            dto.tool_detail(
                request_id=request_attempt,
                func_id=tool.tool_op_id,
                func_name=func_name,
                func_type=dto.func_type_for(func_name),
                session_id=facts.session_id,
                span_id=facts.logical_turn_id,
                code_status="ok",
            )
        )
    _collect_ai_codes(session_dir, facts, batch)
    return batch


def _collect_ai_codes(session_dir: Path, facts: TurnFacts, batch: ReportBatch) -> None:
    """Mutation ledger -> ai-code reports; degrade as a group on any surprise."""
    session_file = Path(session_dir) / "session.json"
    try:
        document = json.loads(session_file.read_text(encoding="utf-8"))
        ledger = document.get("state", {}).get("chrys_mutations")
    except OSError, ValueError:
        ledger = None
    if not isinstance(ledger, list) or not ledger:
        batch.skipped.append("ai-code:ledger-unavailable")
        return
    exchange_to_attempt = {fact.model_call_id: fact.request_attempt_id for fact in facts.llm}
    tool_ids = {tool.tool_op_id for tool in facts.tools}
    emitted: set[tuple[str, str]] = set()
    for entry in ledger:
        if not isinstance(entry, dict):
            batch.skipped.append("ai-code:ledger-entry-shape")
            return  # degrade the group, do not guess
        tool_op = str(entry.get("tool_operation_id") or "")
        if not tool_op or tool_op not in tool_ids:
            continue
        filepath = str(entry.get("path") or entry.get("filepath") or "")
        content_hash = str(entry.get("hash") or entry.get("content_hash") or "")
        if not filepath or not content_hash:
            batch.skipped.append("ai-code:ledger-entry-fields")
            return
        tool = next(item for item in facts.tools if item.tool_op_id == tool_op)
        request_attempt = exchange_to_attempt.get(tool.model_call_id)
        if request_attempt is None:
            continue
        key = (request_attempt, tool_op)
        if key in emitted:
            continue  # same T with multiple mutations: report once per (A, T)
        emitted.add(key)
        batch.ai_codes.append(
            dto.ai_code_report(
                report_id=tool_op,
                request_id=request_attempt,
                filepath=filepath,
                blocks=[{"kind": "content-ref", "sha256": content_hash}],
                source_type="agent",
                input_method="chat",
                code_status="ok",
            )
        )
