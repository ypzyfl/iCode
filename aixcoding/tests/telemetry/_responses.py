# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""In-process Responses SDK payloads used by telemetry tests."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Self


@dataclass(frozen=True, slots=True)
class Reply:
    status: int
    body: bytes
    headers: tuple[tuple[str, str], ...]


def snapshot(
    *output: Mapping[str, Any], status: str = "completed", error: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    return {
        "id": "resp_1",
        "object": "response",
        "created_at": 1_767_225_600,
        "status": status,
        "model": "golden-model-2026",
        "output": [dict(item) for item in output],
        "parallel_tool_calls": True,
        "tool_choice": "auto",
        "tools": [],
        "error": dict(error) if error is not None else None,
        "incomplete_details": None,
        "usage": {
            "input_tokens": 70,
            "input_tokens_details": {"cached_tokens": 0},
            "output_tokens": 9,
            "output_tokens_details": {"reasoning_tokens": 0},
            "total_tokens": 79,
        },
    }


def resp_message(item_id: str, text: str) -> dict[str, Any]:
    return {
        "type": "message",
        "id": item_id,
        "role": "assistant",
        "status": "completed",
        "content": [{"type": "output_text", "text": text, "annotations": []}],
    }


def call_item(item_id: str, call_id: str, arguments: str) -> dict[str, Any]:
    return {
        "type": "function_call",
        "id": item_id,
        "call_id": call_id,
        "name": "lookup",
        "arguments": arguments,
        "status": "completed",
    }


def mcp_item(item_id: str) -> dict[str, Any]:
    """A hosted MCP call that ran, with side effects the client cannot undo."""
    return {
        "type": "mcp_call",
        "id": item_id,
        "server_label": "github",
        "name": "create_issue",
        "arguments": "{}",
        "output": "created #42",
        "status": "completed",
    }


@dataclass(slots=True)
class Script:
    """Build a stream in provider order, including deliberately unfinished streams."""

    events: list[tuple[str, dict[str, Any]]] = field(default_factory=list)

    def emit(self, event_type: str, **fields: Any) -> Self:
        self.events.append((event_type, {"type": event_type, "sequence_number": len(self.events), **fields}))
        return self

    def started(self, *, status: str = "in_progress") -> Self:
        running = {**snapshot(status=status), "usage": None}
        return self.emit("response.created", response=running).emit("response.in_progress", response=running)

    def text(self, index: int, item_id: str, text: str) -> Self:
        where = {"item_id": item_id, "output_index": index, "content_index": 0}
        part = {"type": "output_text", "text": text, "annotations": []}
        added = {"type": "message", "id": item_id, "role": "assistant", "status": "in_progress", "content": []}
        self.emit("response.output_item.added", output_index=index, item=added)
        self.emit("response.content_part.added", **where, part={**part, "text": ""})
        self.emit("response.output_text.delta", **where, delta=text, logprobs=[])
        self.emit("response.output_text.done", **where, text=text, logprobs=[])
        self.emit("response.content_part.done", **where, part=part)
        done = {**added, "status": "completed", "content": [part]}
        return self.emit("response.output_item.done", output_index=index, item=done)

    def call_deltas(self, index: int, item_id: str, arguments: str) -> Self:
        for start in range(0, len(arguments), 6):
            self.emit(
                "response.function_call_arguments.delta",
                item_id=item_id,
                output_index=index,
                delta=arguments[start : start + 6],
            )
        return self

    def call_arguments_done(self, index: int, item_id: str, arguments: str) -> Self:
        return self.emit(
            "response.function_call_arguments.done", item_id=item_id, output_index=index, arguments=arguments
        )

    def hosted(self, index: int, item: Mapping[str, Any]) -> Self:
        self.emit("response.output_item.added", output_index=index, item={**item, "status": "in_progress"})
        return self.emit("response.output_item.done", output_index=index, item=dict(item))

    def finished(self, *output: Mapping[str, Any]) -> Self:
        return self.emit("response.completed", response=snapshot(*output))

    def reply(self) -> Reply:
        body = "".join(f"event: {kind}\ndata: {json.dumps(data)}\n\n" for kind, data in self.events)
        return Reply(200, body.encode("utf-8"), (("content-type", "text/event-stream"),))


def blocking(*output: Mapping[str, Any], **fields: Any) -> Reply:
    return Reply(200, json.dumps(snapshot(*output, **fields)).encode("utf-8"), (("content-type", "application/json"),))
