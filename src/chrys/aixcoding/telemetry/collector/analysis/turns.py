# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""② Turn slicing, turn_input projection, content_hash and increments
(TS ``turns.ts``; Session guide §9.2/§19.3/§19.4).

A turn opens with a real user message (opener) and closes with a trailing
turn marker (``_chrys_kind=turn``); content between a marker and the next
opener belongs to the next closed action — intervals (prev marker, this
marker] are contiguous and lose nothing. Numbering reads marker evidence
only, never message indices. Markerless tails and displaced openers are
pending (temp ``pending-<seq>`` ids: no events, no increments). A repeated
turn_id (rollback) re-cuts a new content version in place (overwrite, keep
position).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from chrys.aixcoding.telemetry.collector.analysis.canonical import canonical_json_encode
from chrys.aixcoding.telemetry.collector.analysis.history import HistoryEntry
from chrys.aixcoding.telemetry.collector.analysis.util import (
    as_object,
    read_positive_integer,
    read_string,
)

type TurnStatus = str  # "ok" | "interrupted" | "failed" | "pending"


@dataclass(frozen=True, slots=True)
class PriorTurnRef:
    """Read-only projection of ledger-reported turns (increment input)."""

    turn_id: str
    content_hash: str


@dataclass(frozen=True, slots=True)
class TurnSegment:
    """Turn slicing output: fact fields + in-turn entries (event input)."""

    turn_id: str
    turn_index: int
    content_hash: str
    status: TurnStatus
    visible_message_count: int | None
    entries: list[HistoryEntry] = field(default_factory=list)


# Message-own keys participating in turn_input (Message structure closed,
# guide §6.1).
_HASHED_MESSAGE_SCALAR_KEYS = ("type", "role", "author_name", "message_id")

# additional_properties whitelist for turn_input: keys the analysis actually
# depends on; observability keys outside the list never trigger a rehash.
_HASHED_ADDITIONAL_PROPERTY_KEYS = frozenset(
    {
        "_chrys_kind",
        "_turn",
        "_turn_id",
        "_chrys_timing",
        "_chrys_tool_kind",
        "_chrys_tool_context",
        "_chrys_tool_result_metadata",
        "_chrys_operation_id",
        "_chrys_analytics_item_id",
        "_chrys_tool_invocation_order",
        "_injected",
        "_continuation",
    }
)

# Content keys excluded from turn_input: display annotations and provider
# usage fragments are not analysis dependencies.
_EXCLUDED_CONTENT_KEYS = frozenset({"additional_properties", "annotations", "usage_details"})


def _message_properties(message: dict[str, Any]) -> dict[str, Any]:
    properties = as_object(message.get("additional_properties"))
    return properties if properties is not None else {}


def _is_opening_user_message(message: dict[str, Any]) -> bool:
    """A real user input opens a turn (guide §9.2): injected messages and
    synthetic continuations do not."""
    if message.get("role") != "user":
        return False
    properties = _message_properties(message)
    return properties.get("_injected") is not True and properties.get("_continuation") is not True


def _is_turn_marker(message: dict[str, Any]) -> bool:
    return _message_properties(message).get("_chrys_kind") == "turn"


def _filter_additional_properties(value: object) -> dict[str, Any]:
    source = as_object(value)
    if source is None:
        return {}
    return {key: entry for key, entry in source.items() if key in _HASHED_ADDITIONAL_PROPERTY_KEYS}


def _project_content(value: object) -> object:
    if isinstance(value, list):
        return [_project_content(entry) for entry in value]
    content = as_object(value)
    if content is None:
        return value
    output: dict[str, Any] = {}
    for key, entry in content.items():
        if key in _EXCLUDED_CONTENT_KEYS:
            continue
        output[key] = _project_content(entry) if key == "items" else entry
    return output


def _project_message(message: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key in _HASHED_MESSAGE_SCALAR_KEYS:
        if key in message:
            output[key] = message[key]
    if "contents" in message:
        output["contents"] = _project_content(message["contents"])
    if "additional_properties" in message:
        output["additional_properties"] = _filter_additional_properties(message["additional_properties"])
    return output


def _count_visible_messages(turn_entries: list[HistoryEntry]) -> int:
    """Visible message count (per-turn application of the guide §9.2
    message_count rule)."""
    count = 0
    for entry in turn_entries:
        message = entry.message
        properties = _message_properties(message)
        kind = properties.get("_chrys_kind")
        if kind in ("turn", "interrupted", "awaiting_sub_agents"):
            continue
        role = message.get("role")
        if role == "user":
            if properties.get("_continuation") is not True:
                count += 1
            continue
        if role == "assistant":
            contents = message.get("contents")
            if isinstance(contents, list) and any(
                isinstance(content, dict)
                and content.get("type") == "text"
                and isinstance(content.get("text"), str)
                and content["text"].strip()
                for content in contents
            ):
                count += 1
    return count


def _derive_status(turn_entries: list[HistoryEntry]) -> str:
    for entry in turn_entries:
        if _message_properties(entry.message).get("_chrys_kind") == "interrupted":
            return "interrupted"
    return "ok"


def _build_turn_fact(
    turn_id: str,
    turn_index: int,
    status: str,
    turn_entries: list[HistoryEntry],
) -> TurnSegment:
    messages = [_project_message(entry.message) for entry in turn_entries]
    # turnUsage: state-level fields the analysis depends on (tool timing and
    # result metadata live in the message/content whitelists; none at state
    # level for now).
    turn_input = {"messages": messages, "turnUsage": {}}
    content_hash = hashlib.sha256(canonical_json_encode(turn_input).encode("utf-8")).hexdigest()
    return TurnSegment(
        turn_id=turn_id,
        turn_index=turn_index,
        content_hash=content_hash,
        status=status,
        visible_message_count=_count_visible_messages(turn_entries),
        entries=turn_entries,
    )


def _build_closed_turn_fact(
    turn_entries: list[HistoryEntry],
    marker: dict[str, Any],
    next_pending_sequence: list[int],
) -> TurnSegment:
    properties = _message_properties(marker)
    turn_id = read_string(properties, "_turn_id")
    turn = read_positive_integer(properties, "_turn")
    if turn_id is not None:
        return _build_turn_fact(turn_id, turn or 0, _derive_status(turn_entries), turn_entries)
    if turn is not None:
        # _turn_id's formula IS turn_<number> (guide §19.2) — not an index guess.
        return _build_turn_fact(f"turn_{turn}", turn, _derive_status(turn_entries), turn_entries)
    # No turn identity evidence: uncertain → pending; never invent a turn_id.
    next_pending_sequence[0] += 1
    return _build_turn_fact(f"pending-{next_pending_sequence[0]}", 0, "pending", turn_entries)


def slice_turn_segments(entries: list[HistoryEntry]) -> list[TurnSegment]:
    facts_by_id: dict[str, TurnSegment] = {}
    order: list[str] = []
    pending_sequence = [0]

    def emit(fact: TurnSegment) -> None:
        if fact.turn_id not in facts_by_id:
            order.append(fact.turn_id)
        # Rollback: a repeated turn_id re-cuts a new content version in place.
        facts_by_id[fact.turn_id] = fact

    def emit_pending(turn_entries: list[HistoryEntry]) -> None:
        if not turn_entries:
            return
        pending_sequence[0] += 1
        emit(_build_turn_fact(f"pending-{pending_sequence[0]}", 0, "pending", turn_entries))

    buffer: list[HistoryEntry] = []
    has_opener = False
    for entry in entries:
        message = entry.message
        if _is_turn_marker(message):
            emit(_build_closed_turn_fact([*buffer, entry], message, pending_sequence))
            buffer = []
            has_opener = False
            continue
        if _is_opening_user_message(message):
            if has_opener and buffer:
                # Previous opener displaced unclosed: incomplete evidence →
                # keep as pending.
                emit_pending(buffer)
                buffer = []
            buffer.append(entry)
            has_opener = True
            continue
        buffer.append(entry)
    # Markerless tail: pending region, not prematurely treated as analysed.
    emit_pending(buffer)
    return [facts_by_id[turn_id] for turn_id in order]


def to_turn_fact(segment: TurnSegment) -> dict[str, Any]:
    """TurnSegment → core SessionTurnFact JSON projection."""
    return {
        "turnId": segment.turn_id,
        "turnIndex": segment.turn_index,
        "contentHash": segment.content_hash,
        "status": segment.status,
        "visibleMessageCount": segment.visible_message_count,
    }


def compute_incremental(
    turn_facts: list[TurnSegment],
    prior_turns: list[PriorTurnRef],
) -> list[TurnSegment]:
    """Increment = turns whose turn_id is absent from the ledger projection
    or whose content_hash differs; pending turns excluded (unconfirmed, no
    events)."""
    prior = {prior.turn_id: prior.content_hash for prior in prior_turns}
    return [turn for turn in turn_facts if turn.status != "pending" and prior.get(turn.turn_id) != turn.content_hash]
