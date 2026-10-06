# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""③ Exchange rebuilding and tool pairing (TS ``exchanges.ts``; M5 plan
§5; Session guide §8.1 all 8 rules).

An exchange = a consecutive assistant segment (tool calls; plain body
and reasoning assistant messages belong to it) + the trailing result
output segment (``tool`` role, or assistant messages carrying tool
results). Pairing domain is the exchange, never global; only locally
executed function_call/function_result pairs are produced —
informational_only calls and provider-hosted content types never are.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from chrys.aixcoding.telemetry.collector.analysis.turns import TurnSegment
from chrys.aixcoding.telemetry.collector.analysis.util import (
    as_object,
    read_number,
    read_string,
)


@dataclass(frozen=True, slots=True)
class ToolTriple:
    """Pairing output: call + result (missing is legal — truncation,
    interruption or pending) + the assistant message carrying it."""

    call: dict[str, Any]
    result: dict[str, Any] | None
    assistant_message: dict[str, Any]
    # In-turn registration order (funcId three-level fallback locator,
    # deterministic).
    registration_index: int


@dataclass(slots=True)
class _RegisteredCall:
    call: dict[str, Any]
    message: dict[str, Any]
    registration_index: int
    result: dict[str, Any] | None = None


def _message_properties(message: dict[str, Any]) -> dict[str, Any]:
    properties = as_object(message.get("additional_properties"))
    return properties if properties is not None else {}


def _content_objects(message: dict[str, Any]) -> list[dict[str, Any]]:
    contents = message.get("contents")
    if not isinstance(contents, list):
        return []
    return [content for content in contents if isinstance(content, dict)]


def build_tool_triples(segment: TurnSegment) -> list[ToolTriple]:
    triples: list[ToolTriple] = []
    active_calls: list[_RegisteredCall] = []
    saw_output = False
    registration_counter = 0

    def flush() -> None:
        nonlocal saw_output
        triples.extend(
            ToolTriple(
                call=registered.call,
                result=registered.result,
                assistant_message=registered.message,
                registration_index=registered.registration_index,
            )
            for registered in active_calls
        )
        active_calls.clear()
        saw_output = False

    # Rule 6: in the "already answered" sense one result covers every
    # unpaired same-id call in the exchange; unmatched results stay
    # orphaned (no events, no global pairing).
    def consume_results(results: list[dict[str, Any]]) -> None:
        for result in results:
            call_id = read_string(result, "call_id")
            if call_id is None:
                continue
            for registered in active_calls:
                if registered.result is None and read_string(registered.call, "call_id") == call_id:
                    registered.result = result

    for entry in segment.entries:
        message = entry.message
        kind = _message_properties(message).get("_chrys_kind")
        if isinstance(kind, str) and kind:
            # Rule 1: messages carrying _chrys_kind are hard boundaries;
            # never pair across them.
            flush()
            continue
        role = message.get("role")
        if role not in ("assistant", "tool"):
            continue
        contents = _content_objects(message)
        calls = [
            content
            for content in contents
            if content.get("type") == "function_call" and content.get("informational_only") is not True
        ]
        results = [content for content in contents if content.get("type") == "function_result"]

        if role == "assistant" and calls:
            if saw_output:
                # Rule 2: after tool output appears, a new call-carrying
                # assistant message opens a new exchange.
                flush()
            # Rule 3: register all calls of the message first, then
            # consume its embedded results (a result preceding its call
            # still pairs); rule 4: embedded results never answer calls
            # introduced by later siblings.
            for call in calls:
                active_calls.append(
                    _RegisteredCall(call=call, message=message, registration_index=registration_counter)
                )
                registration_counter += 1
            consume_results(results)
            continue
        if results:
            # Result output segment: tool-role messages, or assistant
            # messages carrying tool results (an assistant with empty
            # contents is not a "results-only message" and never enters
            # this branch).
            saw_output = True
            consume_results(results)
    flush()

    # Ascending _chrys_tool_invocation_order (missing sorts last,
    # stable by registration order).
    def sort_key(item: tuple[int, ToolTriple]) -> tuple[float, int]:
        index, triple = item
        properties = as_object(triple.call.get("additional_properties"))
        order = read_number(properties if properties is not None else {}, "_chrys_tool_invocation_order")
        return (float("inf") if order is None else order, index)

    return [triple for _, triple in sorted(enumerate(triples), key=sort_key)]
