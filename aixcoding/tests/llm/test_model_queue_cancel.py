# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Behavior anchors for leaving the gateway queue on interrupt (model-queue-client).

The stream cases drive the production client over ``httpx.MockTransport`` so the
SDK's own SSE decoding runs for real, through the production profile HTTP client,
which stamps the ``Chrys-Request-Attempt-Id`` header the queue is keyed by. The
cancel call is observed through a second transport injected into the tracker, so
the test asserts on the request the customization actually builds (URL, body,
token header).
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest

from chrys.foundation.util.chrys_headers import REQUEST_ATTEMPT_ID_HEADER

QUEUE_STATUS = 'event:queue_status\ndata:{"position":%d,"queueSize":%d}'
CHUNK = (
    'data: {"id":"chatcmpl-1","object":"chat.completion.chunk","created":1,"model":"m",'
    '"choices":[{"index":0,"delta":{"content":"%s"},"finish_reason":null}]}'
)
CANCEL_URL = "http://h/api/v3/chat/completions/cancel"


def _sse(*frames: str) -> bytes:
    return "".join(f"{frame}\n\n" for frame in frames).encode()


async def _client(body: bytes, requests: list[httpx.Request] | None = None) -> Any:
    from chrys.service.llm.chat_completions.client import ChatCompletionsClient
    from chrys.service.llm.clients import _build_openai_sdk_client, _build_profile_http_client
    from chrys.service.profiles.models.schema import ModelProfile

    async def handler(request: httpx.Request) -> httpx.Response:
        if requests is not None:
            requests.append(request)
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=body)

    # The production HTTP client stamps ``Chrys-Request-Attempt-Id`` on every attempt.
    http = _build_profile_http_client(
        ModelProfile(id="p", name="p", provider="openai", model_id="m", api_key="test-key"),
        httpx.Timeout(5),
        transport=httpx.MockTransport(handler),
    )
    sdk = _build_openai_sdk_client(
        api_key="test-key",
        base_url="http://llm.test/v1",
        timeout=5.0,
        max_retries=0,
        default_headers=None,
        http_client=http,
    )
    return ChatCompletionsClient(model="m", sdk_client=sdk)


async def _drain(client: Any) -> BaseException | None:
    """Consume the stream to its end, returning what broke it (``None`` when nothing did)."""
    from chrys.kernel import Message

    stream = client._open_stream(messages=[Message("user", ["hi"])], options={})
    try:
        async for _ in stream:
            pass
    except BaseException as exc:
        return exc
    return None


def _with_transport(transport: httpx.AsyncBaseTransport) -> Any:
    """The production tracker factory, with the cancel call routed to *transport*."""
    import chrys.service.aixcoding.llm_queue as package

    real = package.track_queue_request

    def tracked(request: httpx.Request, *, model: str, base_url: str, api_key: str) -> Any:
        return real(request, model=model, base_url=base_url, api_key=api_key, transport=transport)

    return tracked


async def _queued_tracker(transport: httpx.AsyncBaseTransport, *, api_key: str = "k") -> Any:
    from chrys.service.aixcoding.llm_queue import QueueRequestTracker, QueueStatus

    tracker = QueueRequestTracker(
        request_id="rid", model="m", endpoint=CANCEL_URL, api_key=api_key, transport=transport
    )
    await tracker.observing(None)(QueueStatus(position=1, queue_size=2))
    return tracker


async def test_interrupt_while_queued_sends_cancel(monkeypatch: pytest.MonkeyPatch) -> None:
    """A stream that breaks off while queued leaves the queue with the same id."""
    main_requests: list[httpx.Request] = []
    cancels: list[httpx.Request] = []

    async def cancel_handler(request: httpx.Request) -> httpx.Response:
        cancels.append(request)
        return httpx.Response(204)

    monkeypatch.setattr(
        "chrys.service.aixcoding.llm_queue.track_queue_request",
        _with_transport(httpx.MockTransport(cancel_handler)),
    )
    client = await _client(_sse(QUEUE_STATUS % (2, 5), "data: {oops"), main_requests)
    try:
        assert await _drain(client) is not None
    finally:
        await client.aclose()

    assert len(cancels) == 1
    cancel = cancels[0]
    assert cancel.method == "POST"
    assert cancel.url.path == "/api/v3/chat/completions/cancel"
    assert cancel.headers["token"] == "test-key"
    attempt_id = main_requests[0].headers[REQUEST_ATTEMPT_ID_HEADER]
    assert len(attempt_id) == 32
    assert json.loads(cancel.content) == {"model": "m", "request_id": attempt_id}
    assert "request_id" not in json.loads(main_requests[0].content)


async def test_interrupt_after_release_sends_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Once the first data chunk arrived the gateway is forwarding: no cancel."""
    cancels: list[httpx.Request] = []

    async def cancel_handler(request: httpx.Request) -> httpx.Response:
        cancels.append(request)
        return httpx.Response(204)

    monkeypatch.setattr(
        "chrys.service.aixcoding.llm_queue.track_queue_request",
        _with_transport(httpx.MockTransport(cancel_handler)),
    )
    client = await _client(_sse(QUEUE_STATUS % (0, 2), CHUNK % "hi", "data: {oops"))
    try:
        assert await _drain(client) is not None
    finally:
        await client.aclose()

    assert cancels == []


async def test_interrupt_without_queue_sends_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    """A request that never queued has nothing to cancel."""
    cancels: list[httpx.Request] = []

    async def cancel_handler(request: httpx.Request) -> httpx.Response:
        cancels.append(request)
        return httpx.Response(204)

    monkeypatch.setattr(
        "chrys.service.aixcoding.llm_queue.track_queue_request",
        _with_transport(httpx.MockTransport(cancel_handler)),
    )
    client = await _client(_sse(CHUNK % "hi", "data: {oops"))
    try:
        assert await _drain(client) is not None
    finally:
        await client.aclose()

    assert cancels == []


async def test_completed_stream_carries_the_attempt_header_only() -> None:
    """The gateway keys the queue on the header; the body carries no request_id."""
    main_requests: list[httpx.Request] = []
    client = await _client(_sse(CHUNK % "hi", "data: [DONE]"), main_requests)
    try:
        assert await _drain(client) is None
    finally:
        await client.aclose()

    request = main_requests[0]
    assert len(request.headers[REQUEST_ATTEMPT_ID_HEADER]) == 32
    assert "request_id" not in json.loads(request.content)


@pytest.mark.parametrize(
    ("base_url", "expected"),
    [
        ("http://h:1/v1", "http://h:1/api/v3/chat/completions/cancel"),
        ("http://h:1/v1/", "http://h:1/api/v3/chat/completions/cancel"),
        ("http://h:1", "http://h:1/api/v3/chat/completions/cancel"),
        ("http://h/aicoding/v1", "http://h/aicoding/api/v3/chat/completions/cancel"),
        ("http://h/aicoding/api/v3", "http://h/aicoding/api/v3/chat/completions/cancel"),
        ("http://h/aicoding", "http://h/aicoding/api/v3/chat/completions/cancel"),
        ("ftp://h/v1", None),
        ("", None),
    ],
)
def test_cancel_endpoint_derivation(base_url: str, expected: str | None) -> None:
    from chrys.service.aixcoding.llm_queue import cancel_endpoint

    assert cancel_endpoint(base_url) == expected


def test_tracker_reads_the_attempt_header() -> None:
    from chrys.service.aixcoding.llm_queue import track_queue_request

    request = httpx.Request("POST", "http://h/v1/chat/completions", headers={REQUEST_ATTEMPT_ID_HEADER: "a" * 32})
    tracker = track_queue_request(request, model="m", base_url="http://h/v1", api_key="k")

    assert tracker is not None
    assert tracker.request_id == "a" * 32


def test_underivable_endpoint_returns_no_tracker() -> None:
    from chrys.service.aixcoding.llm_queue import track_queue_request

    request = httpx.Request("POST", "http://h/v1/chat/completions", headers={REQUEST_ATTEMPT_ID_HEADER: "a" * 32})
    assert track_queue_request(request, model="m", base_url="ftp://h", api_key="k") is None


def test_missing_attempt_header_returns_no_tracker(caplog: pytest.LogCaptureFixture) -> None:
    """Without the upstream tracking hook there is no id to cancel with: say so, keep streaming."""
    from chrys.service.aixcoding.llm_queue import track_queue_request

    caplog.set_level(logging.WARNING, logger="chrys.service.aixcoding.llm_queue.queue_cancel")
    request = httpx.Request("POST", "http://h/v1/chat/completions")

    assert track_queue_request(request, model="m", base_url="http://h/v1", api_key="k") is None
    assert REQUEST_ATTEMPT_ID_HEADER in caplog.text


@pytest.mark.parametrize("status", [204, 404, 409, 500])
async def test_cancel_status_never_raises(status: int) -> None:
    calls: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(status)

    tracker = await _queued_tracker(httpx.MockTransport(handler))
    await tracker.cancel_on_close()

    # Sent exactly once: a 404/409 is a contract answer, never a reason to retry.
    assert len(calls) == 1


async def test_cancel_connection_error_is_swallowed() -> None:
    calls: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        raise httpx.ConnectError("boom", request=request)

    tracker = await _queued_tracker(httpx.MockTransport(handler))
    await tracker.cancel_on_close()

    assert len(calls) == 1


async def test_cancel_timeout_is_swallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("chrys.service.aixcoding.llm_queue.queue_cancel.CANCEL_TIMEOUT_SECONDS", 0.05)
    calls: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        await asyncio.sleep(0.3)
        return httpx.Response(204)

    tracker = await _queued_tracker(httpx.MockTransport(handler))
    await asyncio.wait_for(tracker.cancel_on_close(), timeout=2.0)

    assert len(calls) == 1


@pytest.mark.parametrize("api_key", ["", None])
async def test_missing_api_key_sends_nothing(api_key: Any) -> None:
    cancels: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        cancels.append(request)
        return httpx.Response(204)

    from chrys.service.aixcoding.llm_queue import QueueRequestTracker, QueueStatus

    tracker = QueueRequestTracker(
        request_id="rid",
        model="m",
        endpoint=CANCEL_URL,
        api_key=api_key,
        transport=httpx.MockTransport(handler),
    )
    await tracker.observing(None)(QueueStatus(position=0, queue_size=1))
    await tracker.cancel_on_close()

    assert cancels == []


async def test_released_tracker_is_not_queued() -> None:
    from chrys.service.aixcoding.llm_queue import RELEASED_POSITION, QueueStatus

    tracker = await _queued_tracker(httpx.MockTransport(lambda request: httpx.Response(204)))
    assert tracker.queued is True

    await tracker.observing(None)(QueueStatus(position=RELEASED_POSITION, queue_size=0))
    assert tracker.queued is False


async def test_cancel_attempt_and_success_are_logged(caplog: pytest.LogCaptureFixture) -> None:
    """The intranet log shows what was cancelled, where, and whether the gateway accepted it."""
    caplog.set_level(logging.INFO, logger="chrys.service.aixcoding.llm_queue.queue_cancel")

    tracker = await _queued_tracker(httpx.MockTransport(lambda request: httpx.Response(204)))
    await tracker.cancel_on_close()

    assert "正在离开网关队列" in caplog.text
    assert "request_id=rid" in caplog.text
    assert "已离开网关队列" in caplog.text


async def test_missing_api_key_while_queued_is_reported(caplog: pytest.LogCaptureFixture) -> None:
    """A keyless gateway deployment silently loses the cancel: the log must say so."""
    caplog.set_level(logging.WARNING, logger="chrys.service.aixcoding.llm_queue.queue_cancel")

    tracker = await _queued_tracker(httpx.MockTransport(lambda request: httpx.Response(204)), api_key="")
    await tracker.cancel_on_close()

    assert "没有 api_key" in caplog.text
    assert "留在队列中" in caplog.text
    assert "request_id=rid" in caplog.text


async def test_cancel_404_is_reported_in_the_detail_channel(
    detail_records: list[logging.LogRecord],
) -> None:
    """A 404 is a normal no-op, but its endpoint is the only clue when the URL was derived wrong."""
    tracker = await _queued_tracker(httpx.MockTransport(lambda request: httpx.Response(404)))
    await tracker.cancel_on_close()

    messages = [record.getMessage() for record in detail_records]
    assert any("status=404" in message and CANCEL_URL in message for message in messages)


async def test_cancel_request_and_response_body_are_logged(
    detail_records: list[logging.LogRecord],
) -> None:
    """The cancel POST's address/body and the gateway's status/body are both in the detail log."""

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": {"code": "REQUEST_NOT_FOUND", "traceId": "t-9"}})

    tracker = await _queued_tracker(httpx.MockTransport(handler))
    await tracker.cancel_on_close()

    messages = [record.getMessage() for record in detail_records]
    assert any("发送取消排队请求：POST" in message and "body=" in message for message in messages)
    assert any("status=404" in message and "REQUEST_NOT_FOUND" in message for message in messages)


def test_armed_tracker_is_reported_in_the_detail_channel(
    detail_records: list[logging.LogRecord],
) -> None:
    """The request id the gateway will know is written before the stream can queue."""
    from chrys.service.aixcoding.llm_queue import track_queue_request

    request = httpx.Request("POST", "http://h/v1/chat/completions", headers={REQUEST_ATTEMPT_ID_HEADER: "b" * 32})
    tracker = track_queue_request(request, model="m", base_url="http://h/v1", api_key="k")

    assert tracker is not None
    messages = [record.getMessage() for record in detail_records]
    assert any("取消已就绪" in message and tracker.request_id in message for message in messages)


class _HeldOpenStream(httpx.AsyncByteStream):
    """One queue frame, then the connection stays open like a gateway queue does."""

    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield (QUEUE_STATUS % (2, 5)).encode() + b"\n\n"
        await asyncio.sleep(3600)


async def test_cancelled_task_while_queued_sends_cancel(monkeypatch: pytest.MonkeyPatch) -> None:
    """The real interrupt path: the consuming task is cancelled, not the stream broken by bad data."""
    from chrys.kernel import Message
    from chrys.service.llm.chat_completions.client import ChatCompletionsClient
    from chrys.service.llm.clients import _build_openai_sdk_client, _build_profile_http_client
    from chrys.service.profiles.models.schema import ModelProfile

    cancels: list[httpx.Request] = []

    async def cancel_handler(request: httpx.Request) -> httpx.Response:
        cancels.append(request)
        return httpx.Response(204)

    monkeypatch.setattr(
        "chrys.service.aixcoding.llm_queue.track_queue_request",
        _with_transport(httpx.MockTransport(cancel_handler)),
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, stream=_HeldOpenStream())

    http = _build_profile_http_client(
        ModelProfile(id="p", name="p", provider="openai", model_id="m", api_key="test-key"),
        httpx.Timeout(5),
        transport=httpx.MockTransport(handler),
    )
    sdk = _build_openai_sdk_client(
        api_key="test-key",
        base_url="http://llm.test/v1",
        timeout=5.0,
        max_retries=0,
        default_headers=None,
        http_client=http,
    )
    client = ChatCompletionsClient(model="m", sdk_client=sdk)

    async def consume() -> None:
        stream = client._open_stream(messages=[Message("user", ["hi"])], options={})
        async for _ in stream:
            pass

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.5)  # the queue frame has been absorbed by now
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    for _ in range(40):  # the shielded cancel runs on after the task is cancelled
        if cancels:
            break
        await asyncio.sleep(0.05)
    await client.aclose()

    assert len(cancels) == 1
    assert json.loads(cancels[0].content)["request_id"].strip()


async def test_observing_forwards_every_status() -> None:
    from chrys.service.aixcoding.llm_queue import QueueRequestTracker, QueueStatus

    seen: list[int] = []

    async def on_status(status: QueueStatus) -> None:
        seen.append(status.position)

    tracker = QueueRequestTracker(request_id="rid", model="m", endpoint=CANCEL_URL, api_key="k")
    observe = tracker.observing(on_status)
    await observe(QueueStatus(position=2, queue_size=3))
    await observe(QueueStatus(position=0, queue_size=1))

    assert seen == [2, 0]


async def test_broken_customization_leaves_the_request_untracked(monkeypatch: pytest.MonkeyPatch) -> None:
    """The customization is optional: without it the request goes out exactly as before v1.1."""
    main_requests: list[httpx.Request] = []
    cancels: list[httpx.Request] = []

    async def cancel_handler(request: httpx.Request) -> httpx.Response:
        cancels.append(request)
        return httpx.Response(204)

    monkeypatch.setattr(
        "chrys.service.aixcoding.llm_queue.track_queue_request",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("customization unavailable")),
    )
    client = await _client(_sse(CHUNK % "hi", "data: [DONE]"), main_requests)
    try:
        assert await _drain(client) is None
    finally:
        await client.aclose()

    assert "request_id" not in json.loads(main_requests[0].content)
    # The attempt header is upstream's, so it is sent even with the customization unavailable.
    assert len(main_requests[0].headers[REQUEST_ATTEMPT_ID_HEADER]) == 32
    assert cancels == []


CHAT_COMPLETION = {
    "id": "chatcmpl-1",
    "object": "chat.completion",
    "created": 1,
    "model": "m",
    "choices": [{"index": 0, "message": {"role": "assistant", "content": "hi"}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
}


async def test_non_streaming_request_carries_the_header_without_a_tracker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only streaming arms a tracker; a blocking request still carries the header."""
    from chrys.kernel import Message
    from chrys.service.aixcoding.llm_queue import track_queue_request as real
    from chrys.service.llm.chat_completions.client import ChatCompletionsClient
    from chrys.service.llm.clients import _build_openai_sdk_client, _build_profile_http_client
    from chrys.service.profiles.models.schema import ModelProfile

    armed: list[int] = []

    def spy(*args: Any, **kwargs: Any) -> Any:
        armed.append(1)
        return real(*args, **kwargs)

    monkeypatch.setattr("chrys.service.aixcoding.llm_queue.track_queue_request", spy)

    main_requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        main_requests.append(request)
        return httpx.Response(
            200, headers={"content-type": "application/json"}, content=json.dumps(CHAT_COMPLETION).encode()
        )

    http = _build_profile_http_client(
        ModelProfile(id="p", name="p", provider="openai", model_id="m", api_key="test-key"),
        httpx.Timeout(5),
        transport=httpx.MockTransport(handler),
    )
    sdk = _build_openai_sdk_client(
        api_key="test-key",
        base_url="http://llm.test/v1",
        timeout=5.0,
        max_retries=0,
        default_headers=None,
        http_client=http,
    )
    client = ChatCompletionsClient(model="m", sdk_client=sdk)
    try:
        await client._send(messages=[Message("user", ["hi"])], options={})
    finally:
        await client.aclose()

    assert armed == []
    request = main_requests[0]
    assert len(request.headers[REQUEST_ATTEMPT_ID_HEADER]) == 32
    assert "request_id" not in json.loads(request.content)
