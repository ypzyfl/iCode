# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Local test doubles; deliberately independent from upstream tests/support."""

from __future__ import annotations

import json
from typing import Any

import httpx

from chrys.foundation.errors import classify_error
from chrys.foundation.trajectory.context import TrajectoryContext
from chrys.foundation.trajectory.envelope import Actor
from chrys.service.profiles.models.schema import ModelProfile


def profile(provider: str = "openai", *, api_style: str = "chat_completions") -> ModelProfile:
    return ModelProfile(
        id="profile-id",
        name="profile",
        provider=provider,
        api_style=api_style,  # type: ignore[arg-type]
        model_id="model-test",
        api_key="key-test",
        base_url="http://llm.test/v1" if provider != "anthropic" else "http://llm.test",
        http_max_retries=2,
    )


class Sink:
    def __init__(self) -> None:
        self.drafts: list[Any] = []

    def emit_soon(self, draft: Any) -> None:
        self.drafts.append(draft)

    async def emit(self, draft: Any) -> None:
        self.emit_soon(draft)


class RetryPolicy:
    max_retries = 1
    stall_timeout_seconds = None
    stall_max_retries = 0
    stall_exhausted_action = None
    answer_shown = None

    def backoff_seconds(self, attempt: int) -> int:
        return 0

    def hosted_commits_in_flight(self) -> tuple[str, ...]:
        return ()

    def is_retryable(self, exc: BaseException) -> bool:
        return classify_error(exc).retryable

    def is_interrupted(self) -> bool:
        return False

    async def sleep(self, seconds: int) -> bool:
        return False

    async def on_retry(self, message: str, attempt: int, max_attempts: int, delay: int, exc: BaseException) -> None:
        return None

    def before_retry(self) -> None:
        return None


def trajectory(*, session_id: str = "session-real", turn_id: str | None = "turn-1") -> tuple[TrajectoryContext, Sink]:
    sink = Sink()
    context = TrajectoryContext(
        sink=sink,  # type: ignore[arg-type]
        session_id=session_id,
        actor=Actor(kind="agent", role="main"),
        turn_id=turn_id,
        cycle_operation_id="cycle-1",
        exchange_operation_id="exchange-1",
    )
    return context, sink


class ChunkStream(httpx.AsyncByteStream):
    def __init__(self, chunks: list[bytes], *, error: Exception | None = None) -> None:
        self.chunks = chunks
        self.error = error
        self.close_count = 0

    async def __aiter__(self):
        for chunk in self.chunks:
            yield chunk
        if self.error is not None:
            raise self.error

    async def aclose(self) -> None:
        self.close_count += 1


OPENAI_REPLY = {
    "id": "cmpl-1",
    "object": "chat.completion",
    "created": 0,
    "model": "model-test",
    "choices": [
        {
            "index": 0,
            "message": {"role": "assistant", "content": "ok"},
            "finish_reason": "stop",
        }
    ],
    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
}

RESPONSES_REPLY = {
    "id": "resp_1",
    "object": "response",
    "created_at": 0,
    "model": "model-test",
    "status": "completed",
    "output": [
        {
            "type": "message",
            "id": "msg_1",
            "role": "assistant",
            "status": "completed",
            "content": [{"type": "output_text", "text": "ok", "annotations": []}],
        }
    ],
}

ANTHROPIC_REPLY = {
    "id": "msg_1",
    "type": "message",
    "role": "assistant",
    "model": "model-test",
    "content": [{"type": "text", "text": "ok"}],
    "stop_reason": "end_turn",
    "stop_sequence": None,
    "usage": {"input_tokens": 1, "output_tokens": 1},
}


def stream_payload(protocol: str) -> bytes:
    if protocol == "chat":
        chunk = {
            "id": "chunk-1",
            "object": "chat.completion.chunk",
            "created": 0,
            "model": "model-test",
            "choices": [{"index": 0, "delta": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
        }
        return f"data: {json.dumps(chunk)}\n\ndata: [DONE]\n\n".encode()
    if protocol == "responses":
        return _sse(
            {
                "type": "response.output_text.delta",
                "sequence_number": 0,
                "item_id": "msg_1",
                "output_index": 0,
                "content_index": 0,
                "delta": "ok",
            },
            {"type": "response.completed", "sequence_number": 1, "response": RESPONSES_REPLY},
        )
    message_start = {
        "type": "message_start",
        "message": {
            **ANTHROPIC_REPLY,
            "content": [],
            "stop_reason": None,
            "usage": {"input_tokens": 1, "output_tokens": 1},
        },
    }
    return _sse(
        message_start,
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "ok"}},
        {"type": "content_block_stop", "index": 0},
        {
            "type": "message_delta",
            "delta": {"stop_reason": "end_turn", "stop_sequence": None},
            "usage": {"output_tokens": 1},
        },
        {"type": "message_stop"},
    )


def _sse(*events: dict) -> bytes:
    return b"".join(f"event: {event['type']}\ndata: {json.dumps(event)}\n\n".encode() for event in events)
