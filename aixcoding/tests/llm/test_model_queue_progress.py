# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Behavior anchors for the queue-progress channel (model-queue-progress).

The stream cases drive the production client over ``httpx.MockTransport`` so the
SDK's own SSE decoding runs for real.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any

QUEUE_STATUS = 'event:queue_status\ndata:{"position":%d,"queueSize":%d}'
CHUNK = (
    'data: {"id":"chatcmpl-1","object":"chat.completion.chunk","created":1,"model":"m",'
    '"choices":[{"index":0,"delta":{"content":"%s"},"finish_reason":null}]}'
)


def _sse(*frames: str) -> bytes:
    return "".join(f"{frame}\n\n" for frame in frames).encode()


async def _client(body: bytes, *, observer: Any = None) -> Any:
    import httpx

    from chrys.service.llm.chat_completions.client import ChatCompletionsClient
    from chrys.service.llm.clients import _build_openai_sdk_client

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=body)

    sdk = _build_openai_sdk_client(
        api_key="test-key",
        base_url="http://llm.test/v1",
        timeout=5.0,
        max_retries=0,
        default_headers=None,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    return ChatCompletionsClient(model="m", sdk_client=sdk, observer=observer)


def _queue_chunk(position: int, queue_size: int) -> Any:
    return SimpleNamespace(
        choices=None,
        id=None,
        usage=None,
        model_extra={"position": position, "queueSize": queue_size},
    )


def _data_chunk(text: str) -> Any:
    return SimpleNamespace(choices=[], id=None, usage=None, model_extra={"content": text})


def test_queue_note_branches() -> None:
    """Release, next-up and every queued position get their own copy."""
    from chrys.kernel.aixcoding.queue_progress import queue_note

    assert queue_note(-1) == ""
    assert queue_note(0) == "正在获取模型资源"
    for position in (1, 2, 4, 9):
        note = queue_note(position)
        assert f"约 {position} 人" in note
        assert "请稍候或切换至其他模型" in note


def test_queue_note_does_not_show_the_queue_size() -> None:
    """The total is accepted but not rendered: the copy speaks about the position only."""
    from chrys.kernel.aixcoding.queue_progress import queue_note

    assert queue_note(2, 5) == queue_note(2)
    assert "共" not in queue_note(2, 5)


def test_queue_status_event_passes_the_headless_boundary() -> None:
    """CLI and ACP read headless events through the type tuple; this event must pass."""
    from chrys.foundation.events.types import GatewayQueueStatus
    from chrys.orchestration.session_host import allows_headless_event

    event = GatewayQueueStatus(session_id="s1", position=2, queue_size=5)

    assert allows_headless_event(event) is True
    assert not hasattr(event, "origin")


async def test_guard_reports_every_absorbed_position() -> None:
    """Each position frame reaches the callback, in order, and never the chunk stream."""
    from chrys.service.aixcoding.llm_queue import guard_queue_frames

    async def chunks() -> AsyncIterator[Any]:
        yield _queue_chunk(2, 5)
        yield _queue_chunk(1, 4)
        yield _data_chunk("hi")

    seen: list[tuple[int, int]] = []

    async def on_status(status: Any) -> None:
        seen.append((status.position, status.queue_size))

    forwarded = [chunk async for chunk in guard_queue_frames(chunks(), on_status=on_status)]

    # The first data chunk reports the release once, so no frontend keeps the note.
    assert seen == [(2, 5), (1, 4), (-1, 0)]
    assert len(forwarded) == 1


async def test_guard_reports_the_release_only_after_a_queue_wait() -> None:
    """A stream that never queued reports no release, so a frontend has nothing to clear."""
    from chrys.service.aixcoding.llm_queue import guard_queue_frames

    async def chunks() -> AsyncIterator[Any]:
        yield _data_chunk("hi")

    seen: list[int] = []

    async def on_status(status: Any) -> None:
        seen.append(status.position)

    forwarded = [chunk async for chunk in guard_queue_frames(chunks(), on_status=on_status)]

    assert seen == []
    assert len(forwarded) == 1


async def test_status_callback_failure_never_breaks_the_stream() -> None:
    """A broken frontend is logged, not allowed to fail the queued answer."""
    from chrys.service.aixcoding.llm_queue import guard_queue_frames

    async def chunks() -> AsyncIterator[Any]:
        yield _queue_chunk(1, 2)
        yield _data_chunk("hi")

    async def on_status(status: Any) -> None:
        raise RuntimeError("frontend exploded")

    forwarded = [chunk async for chunk in guard_queue_frames(chunks(), on_status=on_status)]

    assert len(forwarded) == 1


async def test_stream_with_callback_still_returns_the_answer() -> None:
    """End to end: the observer's callback reaches the guard and the reply survives."""
    from chrys.kernel import Message
    from chrys.service.llm.observer import WireCallObserver

    seen: list[int] = []

    async def on_status(status: Any) -> None:
        seen.append(status.position)

    client = await _client(
        _sse(QUEUE_STATUS % (2, 5), CHUNK % "hi", "data: [DONE]"),
        observer=WireCallObserver(on_queue_status=on_status),
    )
    try:
        stream = client._open_stream(messages=[Message("user", ["hi"])], options={})
        updates = [update async for update in stream]
    finally:
        await client.aclose()

    assert seen == [2, -1]
    assert "".join(update.text or "" for update in updates) == "hi"


class _RecordingWriter:
    def __init__(self) -> None:
        self.lines: list[tuple[Any, ...]] = []

    def line(self, *parts: Any) -> None:
        self.lines.append(parts)


def test_cli_writes_one_line_per_position_change() -> None:
    """The gateway's position heartbeat repeats a position; the CLI must not repeat its line."""
    from chrys.app.cli.progress import TurnProgress
    from chrys.foundation.events.types import GatewayQueueStatus

    writer = _RecordingWriter()
    progress = TurnProgress(writer, render=lambda reference: "", context=lambda: None)  # type: ignore[arg-type]

    progress.handle(GatewayQueueStatus(session_id="s1", position=3, queue_size=5))
    progress.handle(GatewayQueueStatus(session_id="s1", position=3, queue_size=5))
    progress.handle(GatewayQueueStatus(session_id="s1", position=1, queue_size=4))

    assert len(writer.lines) == 2


def test_cli_release_clears_the_dedupe() -> None:
    """After the queue releases, the same position must print again in a later wait."""
    from chrys.app.cli.progress import TurnProgress
    from chrys.foundation.events.types import GatewayQueueStatus

    writer = _RecordingWriter()
    progress = TurnProgress(writer, render=lambda reference: "", context=lambda: None)  # type: ignore[arg-type]

    progress.handle(GatewayQueueStatus(session_id="s1", position=2, queue_size=5))
    progress.handle(GatewayQueueStatus(session_id="s1", position=-1, queue_size=0))
    progress.handle(GatewayQueueStatus(session_id="s1", position=2, queue_size=5))

    assert len(writer.lines) == 2


def test_waiting_row_note_is_set_and_cleared() -> None:
    """The row keeps the note until cleared, so a new turn must clear it explicitly."""
    from chrys.app.tui.widgets.chat.waiting_row import WaitingRow

    row = WaitingRow()

    row.set_queue_note("排队中 · 前方 2 个请求")
    assert row._queue_note == "排队中 · 前方 2 个请求"

    row.set_queue_note("")
    assert row._queue_note == ""
