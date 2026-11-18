# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Behavior anchors for the gateway model-queue guard (model-queue-client).

The stream cases drive the production client over ``httpx.MockTransport`` so the
SDK's own SSE decoding runs for real; the guard cases feed the guarded iterator
directly. Nothing mocks the SDK's framing, which is where the whole risk of this
customization lives.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any

import pytest

QUEUE_STATUS = 'event:queue_status\ndata:{"position":%d,"queueSize":%d}'
CHUNK = (
    'data: {"id":"chatcmpl-1","object":"chat.completion.chunk","created":1,"model":"m",'
    '"choices":[{"index":0,"delta":{"content":"%s"},"finish_reason":null}]}'
)
USAGE = (
    'data: {"id":"chatcmpl-1","object":"chat.completion.chunk","created":1,"model":"m",'
    '"choices":[],"usage":{"prompt_tokens":1,"completion_tokens":1,"total_tokens":2}}'
)


def _sse(*frames: str) -> bytes:
    return "".join(f"{frame}\n\n" for frame in frames).encode()


async def _client(body: bytes) -> Any:
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
    return ChatCompletionsClient(model="m", sdk_client=sdk)


async def _updates(client: Any) -> list[Any]:
    from chrys.kernel import Message

    stream = client._open_stream(messages=[Message("user", ["hi"])], options={})
    return [update async for update in stream]


def _api_error(code: str, message: str = "gateway rejected the request") -> BaseException:
    import httpx
    from openai import APIError

    return APIError(
        message,
        request=httpx.Request("POST", "http://llm.test/v1/chat/completions"),
        body={"code": code, "message": message, "traceId": "trace-1"},
    )


async def _failing(exc: BaseException) -> AsyncIterator[Any]:
    raise exc
    yield  # pragma: no cover - an async generator needs a yield to be one


def _queue_chunk(position: int, queue_size: int) -> Any:
    return SimpleNamespace(
        choices=None,
        id=None,
        usage=None,
        model_extra={"position": position, "queueSize": queue_size},
    )


def _data_chunk(text: str) -> Any:
    return SimpleNamespace(choices=[], id=None, usage=None, model_extra={"content": text})


async def test_queue_status_frames_do_not_break_the_stream() -> None:
    """A position frame is absorbed: the queued stream still returns its answer."""
    client = await _client(_sse(QUEUE_STATUS % (2, 5), CHUNK % "hi", "data: [DONE]"))
    try:
        updates = await _updates(client)
    finally:
        await client.aclose()

    assert "".join(update.text or "" for update in updates) == "hi"


async def test_queue_status_frames_keep_usage() -> None:
    """Absorbed frames do not disturb the usage chunk that follows the answer."""
    client = await _client(_sse(QUEUE_STATUS % (0, 2), CHUNK % "hi", USAGE, "data: [DONE]"))
    try:
        updates = await _updates(client)
    finally:
        await client.aclose()

    assert any(content.type == "usage" for update in updates for content in update.contents)


async def test_chunk_without_queue_fields_is_still_invalid() -> None:
    """The guard is not a general sink: an unexplained ``choices: null`` still fails."""
    from chrys.kernel.exceptions import ChatClientException, ChatClientInvalidResponseException

    client = await _client(_sse('data: {"position":2}', "data: [DONE]"))
    try:
        with pytest.raises(ChatClientException) as caught:
            await _updates(client)
    finally:
        await client.aclose()

    assert isinstance(caught.value.args[1], ChatClientInvalidResponseException)


async def test_terminal_queue_codes_are_not_retryable() -> None:
    """``QUEUE_TIMEOUT`` / ``QUEUE_CANCELLED`` become a terminal provider failure."""
    from chrys.foundation.errors import ProviderResponseError, is_retryable
    from chrys.service.aixcoding.llm_queue import guard_queue_frames

    for code in ("QUEUE_TIMEOUT", "QUEUE_CANCELLED"):
        error = _api_error(code)
        with pytest.raises(ProviderResponseError) as caught:
            async for _ in guard_queue_frames(_failing(error)):
                pass
        translated = caught.value
        assert translated.retryable is False
        assert translated.__cause__ is error
        assert is_retryable(translated) is False


async def test_queue_full_stays_retryable() -> None:
    """``QUEUE_FULL`` passes through untouched and keeps its transient verdict."""
    from chrys.foundation.errors import is_retryable
    from chrys.service.aixcoding.llm_queue import guard_queue_frames

    error = _api_error("QUEUE_FULL")
    with pytest.raises(BaseException) as caught:
        async for _ in guard_queue_frames(_failing(error)):
            pass

    assert caught.value is error
    assert is_retryable(caught.value) is True


async def test_non_queue_error_passes_through_the_guard_unchanged() -> None:
    """A stream error that is not a queue rejection keeps its own classification."""
    from chrys.foundation.errors import is_retryable
    from chrys.service.aixcoding.llm_queue import guard_queue_frames

    error = _api_error("UPSTREAM_TIMEOUT")
    with pytest.raises(BaseException) as caught:
        async for _ in guard_queue_frames(_failing(error)):
            pass

    assert caught.value is error
    assert is_retryable(caught.value) is is_retryable(error)


async def test_queue_status_heartbeat_restarts_the_stall_watchdog() -> None:
    """Every absorbed position frame reports wire progress, as the watchdog expects."""
    from chrys.kernel.client import wire_progress_scope
    from chrys.service.aixcoding.llm_queue import guard_queue_frames

    async def chunks() -> AsyncIterator[Any]:
        yield _queue_chunk(2, 3)
        yield _queue_chunk(1, 2)
        yield _data_chunk("hi")

    reports: list[int] = []
    with wire_progress_scope(lambda: reports.append(1)):
        forwarded = [chunk async for chunk in guard_queue_frames(chunks())]

    assert len(reports) == 2
    assert len(forwarded) == 1


async def test_unavailable_customization_falls_back_to_the_plain_stream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A broken customization import must not take the upstream stream down with it."""
    import sys

    from chrys.kernel.exceptions import ChatClientException, ChatClientInvalidResponseException

    monkeypatch.setitem(sys.modules, "chrys.service.aixcoding.llm_queue", None)
    client = await _client(_sse(QUEUE_STATUS % (1, 2), CHUNK % "hi", "data: [DONE]"))
    try:
        with pytest.raises(ChatClientException) as caught:
            await _updates(client)
    finally:
        await client.aclose()

    # The fallback keeps the original stream: the first queue frame fails it as
    # an invalid event, not as the import error the guard swallowed.
    assert isinstance(caught.value.args[1], ChatClientInvalidResponseException)
