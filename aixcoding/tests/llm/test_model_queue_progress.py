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
    assert queue_note(0) == "已排到队首，当前为队列第一位"
    for position in (1, 2, 4, 9):
        assert queue_note(position) == f"当前模型请求量大，请求排队约 {position} 人"


def test_queue_note_does_not_show_the_queue_size() -> None:
    """The total is accepted but not rendered: the copy speaks about the position only."""
    from chrys.kernel.aixcoding.queue_progress import queue_note

    assert queue_note(2, 5) == queue_note(2)
    assert "共" not in queue_note(2, 5)


def test_queue_status_event_passes_the_headless_boundary() -> None:
    """CLI and ACP read headless events through the type tuple; this event must pass."""
    from chrys.kernel.aixcoding.queue_progress import GatewayQueueStatus
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


async def test_tracker_names_every_forwarded_status() -> None:
    """The tracker fills the request id on both the queued positions and the release."""
    from chrys.service.aixcoding.llm_queue import RELEASED_POSITION, QueueRequestTracker, QueueStatus

    seen: list[str | None] = []

    async def on_status(status: Any) -> None:
        seen.append(status.request_id)

    tracker = QueueRequestTracker(request_id="rid-1", model="m", endpoint=None, api_key="k")
    observe = tracker.observing(on_status)
    await observe(QueueStatus(position=2, queue_size=5))
    await observe(QueueStatus(position=RELEASED_POSITION, queue_size=0))

    assert seen == ["rid-1", "rid-1"]


async def test_untracked_statuses_stay_unnamed() -> None:
    """Without a tracker the observer sees the statuses exactly as the guard built them."""
    from chrys.service.aixcoding.llm_queue import QueueStatus, wire_queue_callback
    from chrys.service.llm.observer import WireCallObserver

    seen: list[str | None] = []

    async def on_status(status: Any) -> None:
        seen.append(status.request_id)

    callback = wire_queue_callback(WireCallObserver(on_queue_status=on_status), None)
    assert callback is not None
    await callback(QueueStatus(position=2, queue_size=5))

    assert seen == [None]


async def test_publisher_carries_the_request_id() -> None:
    """The bus event carries the request id the tracker filled."""
    from chrys.kernel.aixcoding.queue_progress import GatewayQueueStatus, make_queue_status_publisher
    from chrys.service.aixcoding.llm_queue import QueueStatus

    class _Bus:
        def __init__(self) -> None:
            self.events: list[Any] = []

        async def publish(self, event: Any) -> None:
            self.events.append(event)

    bus = _Bus()
    await make_queue_status_publisher(bus, "s1")(QueueStatus(position=2, queue_size=5, request_id="rid-1"))

    event = bus.events[0]
    assert isinstance(event, GatewayQueueStatus)
    assert (event.session_id, event.position, event.queue_size, event.request_id) == ("s1", 2, 5, "rid-1")


async def test_observer_sees_the_attempt_header_id() -> None:
    """End to end: the ids the observer receives are the attempt header the gateway saw."""
    import re

    import httpx

    from chrys.foundation.util.chrys_headers import REQUEST_ATTEMPT_ID_HEADER
    from chrys.kernel import Message
    from chrys.service.llm.chat_completions.client import ChatCompletionsClient
    from chrys.service.llm.clients import _build_openai_sdk_client, _build_profile_http_client
    from chrys.service.llm.observer import WireCallObserver
    from chrys.service.profiles.models.schema import ModelProfile

    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=_sse(QUEUE_STATUS % (2, 5), CHUNK % "hi", "data: [DONE]"),
        )

    http = _build_profile_http_client(
        ModelProfile(id="p", name="p", provider="openai", model_id="m", api_key="test"),
        httpx.Timeout(5),
        transport=httpx.MockTransport(handler),
    )
    sdk = _build_openai_sdk_client(
        api_key="test",
        base_url="http://llm.test/v1",
        timeout=5.0,
        max_retries=0,
        default_headers=None,
        http_client=http,
    )
    seen: list[str | None] = []

    async def on_status(status: Any) -> None:
        seen.append(status.request_id)

    client = ChatCompletionsClient(model="m", sdk_client=sdk, observer=WireCallObserver(on_queue_status=on_status))
    try:
        stream = client._open_stream(messages=[Message("user", ["hi"])], options={})
        updates = [update async for update in stream]
    finally:
        await client.aclose()

    attempt_id = requests[0].headers[REQUEST_ATTEMPT_ID_HEADER]
    assert re.fullmatch(r"[0-9a-f]{32}", attempt_id)
    # The queued position and the release both name the request that was queued.
    assert seen == [attempt_id, attempt_id]
    assert "".join(update.text or "" for update in updates) == "hi"


class _RecordingWriter:
    def __init__(self) -> None:
        self.lines: list[tuple[Any, ...]] = []

    def line(self, *parts: Any) -> None:
        self.lines.append(parts)


def test_cli_writes_one_line_per_position_change() -> None:
    """The gateway's position heartbeat repeats a position; the CLI must not repeat its line."""
    from chrys.app.cli.progress import TurnProgress
    from chrys.kernel.aixcoding.queue_progress import GatewayQueueStatus

    writer = _RecordingWriter()
    progress = TurnProgress(writer, render=lambda reference: "", context=lambda: None)  # type: ignore[arg-type]

    progress.handle(GatewayQueueStatus(session_id="s1", position=3, queue_size=5))
    progress.handle(GatewayQueueStatus(session_id="s1", position=3, queue_size=5))
    progress.handle(GatewayQueueStatus(session_id="s1", position=1, queue_size=4))

    assert len(writer.lines) == 2


def test_cli_release_clears_the_dedupe() -> None:
    """After the queue releases, the same position must print again in a later wait."""
    from chrys.app.cli.progress import TurnProgress
    from chrys.kernel.aixcoding.queue_progress import GatewayQueueStatus

    writer = _RecordingWriter()
    progress = TurnProgress(writer, render=lambda reference: "", context=lambda: None)  # type: ignore[arg-type]

    progress.handle(GatewayQueueStatus(session_id="s1", position=2, queue_size=5))
    progress.handle(GatewayQueueStatus(session_id="s1", position=-1, queue_size=0))
    progress.handle(GatewayQueueStatus(session_id="s1", position=2, queue_size=5))

    assert len(writer.lines) == 2


def test_cli_turn_started_clears_the_dedupe() -> None:
    """A new turn must print the same position again, not inherit the previous turn's dedupe."""
    from chrys.app.cli.progress import TurnProgress
    from chrys.foundation.events.types import TurnStarted
    from chrys.kernel.aixcoding.queue_progress import GatewayQueueStatus

    writer = _RecordingWriter()
    progress = TurnProgress(writer, render=lambda reference: "", context=lambda: None)  # type: ignore[arg-type]

    progress.handle(GatewayQueueStatus(session_id="s1", position=2, queue_size=5))
    progress.handle(TurnStarted(session_id="s1", turn_id="t2"))
    progress.handle(GatewayQueueStatus(session_id="s1", position=2, queue_size=5))

    assert len(writer.lines) == 2


async def test_acp_queue_status_is_deduped_per_session() -> None:
    """The same position is sent once per session, and a release lets it be sent again."""
    from chrys.app.acp.server import ChrysAcpServer
    from chrys.kernel.aixcoding.queue_progress import GatewayQueueStatus

    class _Client:
        def __init__(self) -> None:
            self.sent: list[tuple[str, dict[str, Any]]] = []

        async def ext_notification(self, method: str, params: dict[str, Any]) -> None:
            self.sent.append((method, params))

    client = _Client()
    server = ChrysAcpServer(manager=object(), initial_vision=False)  # type: ignore[arg-type]
    server.on_connect(client)  # type: ignore[arg-type]

    await server._handle_turn_event("fallback", GatewayQueueStatus(session_id="s1", position=2, queue_size=5), None)  # type: ignore[arg-type]
    await server._handle_turn_event("fallback", GatewayQueueStatus(session_id="s1", position=2, queue_size=5), None)  # type: ignore[arg-type]
    await server._handle_turn_event("fallback", GatewayQueueStatus(session_id="s2", position=2, queue_size=5), None)  # type: ignore[arg-type]
    await server._handle_turn_event("fallback", GatewayQueueStatus(session_id="s1", position=-1, queue_size=0), None)  # type: ignore[arg-type]
    await server._handle_turn_event("fallback", GatewayQueueStatus(session_id="s1", position=2, queue_size=5), None)  # type: ignore[arg-type]

    assert client.sent == [
        ("chrys/queue_status", {"sessionId": "s1", "position": 2, "queueSize": 5}),
        ("chrys/queue_status", {"sessionId": "s2", "position": 2, "queueSize": 5}),
        ("chrys/queue_status", {"sessionId": "s1", "released": True}),
        ("chrys/queue_status", {"sessionId": "s1", "position": 2, "queueSize": 5}),
    ]


async def test_acp_turn_started_resets_the_dedupe() -> None:
    """A new turn must notify the same position again, not inherit the previous turn's dedupe.

    A queued turn interrupted without a release leaves no reset behind otherwise:
    the next turn's first notification would be swallowed until the position changes.
    """
    from chrys.app.acp.server import ChrysAcpServer
    from chrys.foundation.events.types import TurnStarted
    from chrys.kernel.aixcoding.queue_progress import GatewayQueueStatus

    class _Client:
        def __init__(self) -> None:
            self.sent: list[tuple[str, dict[str, Any]]] = []

        async def ext_notification(self, method: str, params: dict[str, Any]) -> None:
            self.sent.append((method, params))

    client = _Client()
    server = ChrysAcpServer(manager=object(), initial_vision=False)  # type: ignore[arg-type]
    server.on_connect(client)  # type: ignore[arg-type]

    await server._handle_turn_event("fallback", GatewayQueueStatus(session_id="s1", position=2, queue_size=5), None)  # type: ignore[arg-type]
    # The queued turn is interrupted: no release ever arrives, then a new turn starts.
    await server._handle_turn_event("fallback", TurnStarted(session_id="s1", turn_id="t2"), None)  # type: ignore[arg-type]
    await server._handle_turn_event("fallback", GatewayQueueStatus(session_id="s1", position=2, queue_size=5), None)  # type: ignore[arg-type]

    queue_sends = [params for method, params in client.sent if method == "chrys/queue_status"]
    assert queue_sends == [
        {"sessionId": "s1", "position": 2, "queueSize": 5},
        {"sessionId": "s1", "position": 2, "queueSize": 5},
    ]


async def test_acp_payload_carries_the_request_id() -> None:
    """Both payloads name the queued request; an unknown id omits the key entirely."""
    from chrys.app.acp.server import ChrysAcpServer
    from chrys.kernel.aixcoding.queue_progress import GatewayQueueStatus

    class _Client:
        def __init__(self) -> None:
            self.sent: list[tuple[str, dict[str, Any]]] = []

        async def ext_notification(self, method: str, params: dict[str, Any]) -> None:
            self.sent.append((method, params))

    client = _Client()
    server = ChrysAcpServer(manager=object(), initial_vision=False)  # type: ignore[arg-type]
    server.on_connect(client)  # type: ignore[arg-type]

    await server._handle_turn_event("fb", GatewayQueueStatus(session_id="s1", position=2, queue_size=5, request_id="rid-1"), None)  # type: ignore[arg-type]
    await server._handle_turn_event("fb", GatewayQueueStatus(session_id="s1", position=-1, queue_size=0, request_id="rid-1"), None)  # type: ignore[arg-type]
    await server._handle_turn_event("fb", GatewayQueueStatus(session_id="s1", position=1, queue_size=3), None)  # type: ignore[arg-type]

    assert client.sent == [
        ("chrys/queue_status", {"sessionId": "s1", "requestId": "rid-1", "position": 2, "queueSize": 5}),
        ("chrys/queue_status", {"sessionId": "s1", "requestId": "rid-1", "released": True}),
        ("chrys/queue_status", {"sessionId": "s1", "position": 1, "queueSize": 3}),
    ]


async def test_acp_new_request_same_position_is_not_deduped() -> None:
    """A retried request landing on the same position is a fresh fact: its id is the live one."""
    from chrys.app.acp.server import ChrysAcpServer
    from chrys.kernel.aixcoding.queue_progress import GatewayQueueStatus

    class _Client:
        def __init__(self) -> None:
            self.sent: list[tuple[str, dict[str, Any]]] = []

        async def ext_notification(self, method: str, params: dict[str, Any]) -> None:
            self.sent.append((method, params))

    client = _Client()
    server = ChrysAcpServer(manager=object(), initial_vision=False)  # type: ignore[arg-type]
    server.on_connect(client)  # type: ignore[arg-type]

    await server._handle_turn_event("fb", GatewayQueueStatus(session_id="s1", position=2, queue_size=5, request_id="rid-a"), None)  # type: ignore[arg-type]
    await server._handle_turn_event("fb", GatewayQueueStatus(session_id="s1", position=2, queue_size=5, request_id="rid-a"), None)  # type: ignore[arg-type]
    await server._handle_turn_event("fb", GatewayQueueStatus(session_id="s1", position=2, queue_size=5, request_id="rid-b"), None)  # type: ignore[arg-type]

    queue_sends = [params for method, params in client.sent if method == "chrys/queue_status"]
    assert queue_sends == [
        {"sessionId": "s1", "requestId": "rid-a", "position": 2, "queueSize": 5},
        {"sessionId": "s1", "requestId": "rid-b", "position": 2, "queueSize": 5},
    ]


async def test_tui_turn_started_clears_the_waiting_row_note() -> None:
    """The handler chain must call the presenter's clear before applying the turn."""
    from chrys.app.tui.screens.main.event_handlers import BackendEventHandler
    from chrys.foundation.events.types import TurnStarted

    calls: list[str] = []

    class _Presenter:
        def clear_queue_status(self) -> None:
            calls.append("clear")

    handler = object.__new__(BackendEventHandler)
    handler._presenter = _Presenter()  # type: ignore[attr-defined]

    async def _apply(event: Any) -> None:
        calls.append("apply")

    handler.apply_turn_event = _apply

    await handler.on_turn_started(TurnStarted(session_id="s1", turn_id="t1"))

    assert calls == ["clear", "apply"]


def test_tui_presenter_forwards_queue_status_to_the_view() -> None:
    """The presenter facade is the only path from the handler to the WaitingRow view."""
    from chrys.app.tui.screens.main.main_screen_presenter import MainScreenPresenter

    calls: list[tuple[str, int, int]] = []

    class _View:
        def show_queue_status(self, position: int, queue_size: int = 0) -> None:
            calls.append(("show", position, queue_size))

        def clear_queue_status(self) -> None:
            calls.append(("clear", 0, 0))

    presenter = MainScreenPresenter(_View())  # type: ignore[arg-type]
    presenter.show_queue_status(2, 5)
    presenter.clear_queue_status()

    assert calls == [("show", 2, 5), ("clear", 0, 0)]


def test_tui_view_adapter_sets_and_clears_the_waiting_row_note() -> None:
    """The view adapter maps the presenter call onto the WaitingRow's note, and clears it."""
    from chrys.app.tui.screens.main.view_adapter import MainScreenViewAdapter
    from chrys.app.tui.widgets.chat.waiting_row import WaitingRow
    from chrys.kernel.aixcoding.queue_progress import queue_note

    row = WaitingRow()

    class _Screen:
        def query(self, widget_type: Any) -> list[Any]:
            return [row] if widget_type is WaitingRow else []

    adapter = object.__new__(MainScreenViewAdapter)
    adapter._screen = _Screen()  # type: ignore[attr-defined]

    adapter.show_queue_status(2, 5)
    assert row._queue_note == queue_note(2, 5)

    adapter.clear_queue_status()
    assert row._queue_note == ""


def test_waiting_row_note_is_set_and_cleared() -> None:
    """The row keeps the note until cleared, so a new turn must clear it explicitly."""
    from chrys.app.tui.widgets.chat.waiting_row import WaitingRow

    row = WaitingRow()

    row.set_queue_note("排队中 · 前方 2 个请求")
    assert row._queue_note == "排队中 · 前方 2 个请求"

    row.set_queue_note("")
    assert row._queue_note == ""
