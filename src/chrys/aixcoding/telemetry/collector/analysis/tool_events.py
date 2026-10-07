# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""④ Tool save / update events (TS ``tool-events.ts``; M5 plan §6.1;
contract §3.2/§3.3).

Every ToolTriple (non-informational, non-hosted) yields one save
(codeStatus=0 initial) plus, only with a result, one terminal update.
codeStatus mirrors the engine's ``foundation/tool_result_metadata.py``
structured decisions (approval rejected → 4, failure evidence → 2,
default → 1). The line-count columns' mutation ownership matching lives
in mutation_matching.py (exact call_id first; on an ID-system break,
uniqueness/timing-window fallbacks); mutations with missing blobs are
skipped without blocking. Focus fields (value/fileName/extra/
funcErrorMessage) are constructed with the registration redaction
rules (focus_fields.py, M4); the HTTP sink's focus_fields_enabled
switch (default False) keeps them out of the remote payload while
the file sink observes them locally.
"""

from __future__ import annotations

from typing import Any

from chrys.aixcoding.telemetry.collector.analysis.attachments import MutationBlobReader, split_lines
from chrys.aixcoding.telemetry.collector.analysis.context import EventCommonContext, build_event_common
from chrys.aixcoding.telemetry.collector.analysis.exchanges import ToolTriple, build_tool_triples
from chrys.aixcoding.telemetry.collector.analysis.focus_fields import (
    derive_func_error_message,
    derive_save_focus_fields,
)
from chrys.aixcoding.telemetry.collector.analysis.line_diff import compute_line_diff
from chrys.aixcoding.telemetry.collector.analysis.mutation_matching import (
    MutationMatching,
    build_mutation_matching,
    match_mutations,
)
from chrys.aixcoding.telemetry.collector.analysis.turns import TurnSegment
from chrys.aixcoding.telemetry.collector.analysis.util import as_object, read_string

# kind "tool-use-saved" | "tool-status-updated" (ToolUseSavedEvent |
# ToolStatusUpdatedEvent in the TS contracts package).
ToolEvent = dict[str, Any]


def _content_properties(content: dict[str, Any]) -> dict[str, Any]:
    properties = as_object(content.get("additional_properties"))
    return properties if properties is not None else {}


def _derive_func_id(triple: ToolTriple) -> str | None:
    """funcId (contract §3.1): content-level ``_chrys_operation_id``
    (shared by call and result, the update write-back locator); missing
    falls back (K6) to ``call_id + occurrence_id``; then to ``call_id +
    in-turn registration index`` (deterministic). Never the bare
    call_id — it repeats across exchanges and updates would write the
    wrong row."""
    operation_id = read_string(_content_properties(triple.call), "_chrys_operation_id")
    if operation_id is not None:
        return operation_id
    call_id = read_string(triple.call, "call_id")
    if call_id is None:
        return None
    occurrence_id = read_string(_content_properties(triple.call), "_chrys_analytics_item_id")
    if occurrence_id is not None:
        return f"{call_id}:{occurrence_id}"
    return f"{call_id}:registration-{triple.registration_index}"


def _derive_request_id(triple: ToolTriple) -> str | None:
    """requestId: the carrying message's message-level
    ``_chrys_operation_id`` (exchange id / wire call). Omitted when
    missing (K6)."""
    properties = as_object(triple.assistant_message.get("additional_properties"))
    return read_string(properties if properties is not None else {}, "_chrys_operation_id")


def _int_or_null(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _derive_code_status(result: dict[str, Any]) -> int:
    """codeStatus (contract §3.3, engine structured-decision parity):
    rejection (approval=user_rejected / tool_error_kind in
    {approval_rejected, hook_denied}) → 4; failure evidence
    (errored/failed/exception/timeout/non-zero exit) → 2; interrupted →
    2; failed=false/exit 0/no evidence → 1."""
    metadata = as_object(_content_properties(result).get("_chrys_tool_result_metadata"))
    meta = metadata if metadata is not None else {}
    if meta.get("approval") == "user_rejected":
        return 4
    error_kind = meta.get("tool_error_kind")
    if error_kind == "approval_rejected" or error_kind == "hook_denied":
        return 4
    if meta.get("errored") is True or meta.get("failed") is True:
        return 2
    if meta.get("process_timed_out") is True or meta.get("shell_timed_out") is True:
        return 2
    exit_code = _int_or_null(meta.get("process_exit_code"))
    if exit_code is None:
        exit_code = _int_or_null(meta.get("shell_exit_code"))
    if exit_code is not None and exit_code != 0:
        return 2
    if read_string(result, "exception") is not None:
        return 2
    if meta.get("interrupted") is True or meta.get("interrupted_post_processing") is True:
        return 2
    return 1


def _read_blob_text(mutation: dict[str, Any], key: str, blob_reader: MutationBlobReader) -> str | None:
    blob_hash = read_string(mutation, key)
    if blob_hash is None:
        return None
    return blob_reader.read_blob_text(blob_hash)


def _collect_line_counts(
    mutations: list[dict[str, Any]] | None,
    blob_reader: MutationBlobReader,
) -> dict[str, int] | None:
    """Line-count columns (contract §3.3/§2.4): aggregate the write-class
    mutations matched to this call; originalLines = before line count,
    added/deleted = per-line diff counts before→after. Mutations with
    missing blobs or over-cap diffs are skipped (events never blocked,
    counts omitted)."""
    if not mutations:
        return None
    original = 0
    added = 0
    deleted = 0
    counted = False
    for mutation in mutations:
        operation = read_string(mutation, "operation")
        before_text = _read_blob_text(mutation, "before_hash", blob_reader)
        after_text = _read_blob_text(mutation, "after_hash", blob_reader)
        if operation == "create":
            if after_text is None:
                continue
            added += len(split_lines(after_text))
            counted = True
            continue
        if operation == "delete":
            if before_text is None:
                continue
            lines = len(split_lines(before_text))
            original += lines
            deleted += lines
            counted = True
            continue
        # modify / move: per-line diff before→after.
        if before_text is None or after_text is None:
            continue
        before_lines = split_lines(before_text)
        after_lines = split_lines(after_text)
        diff = compute_line_diff(before_lines, after_lines)
        if diff is None:
            continue
        original += len(before_lines)
        added += diff.count("+")
        deleted += diff.count("-")
        counted = True
    if not counted:
        return None
    return {"originalLines": original, "addedLines": added, "deletedLines": deleted}


def build_tool_events(
    segment: TurnSegment,
    context: EventCommonContext,
    mutations_ledger: Any,
    blob_reader: MutationBlobReader,
) -> list[ToolEvent]:
    triples = build_tool_triples(segment)
    events: list[ToolEvent] = []
    if not triples:
        return events
    matching: MutationMatching = build_mutation_matching(triples, mutations_ledger, segment.turn_index)
    for triple in triples:
        func_id = _derive_func_id(triple)
        func_name = read_string(triple.call, "name")
        if func_id is None or func_name is None:
            continue
        request_id = _derive_request_id(triple)
        save: ToolEvent = {
            "kind": "tool-use-saved",
            **build_event_common(context, segment.turn_id),
            "funcType": 1 if _content_properties(triple.call).get("_chrys_tool_kind") == "mcp" else 3,
            "funcName": func_name,
            "funcId": func_id,
            "codeStatus": 0,
        }
        if request_id is not None:
            save["requestId"] = request_id
        save.update(derive_save_focus_fields(triple.call, context.git_root, context.primary_cwd))
        events.append(save)
        if triple.result is not None:
            code_status = _derive_code_status(triple.result)
            line_counts = _collect_line_counts(match_mutations(triple, matching), blob_reader)
            update: ToolEvent = {
                "kind": "tool-status-updated",
                "funcId": func_id,
                "codeStatus": code_status,
            }
            if line_counts is not None:
                update.update(line_counts)
            if code_status == 2:
                error_message = derive_func_error_message(triple.result)
                if error_message is not None:
                    update["funcErrorMessage"] = error_message
            events.append(update)
    return events
