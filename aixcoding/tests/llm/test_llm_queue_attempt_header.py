# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""The gateway's queue key is upstream's per-attempt ``Chrys-Request-Attempt-Id``.

The client writes no body ``request_id``: the gateway reads the header the wire
client already stamps on every HTTP attempt, and the tracker reads the same value
back from the attempt whose response arrived. Wire checks run through the
production profile HTTP client, so the asserted headers are the ones the SDK
actually sent.
"""

from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import pytest

from chrys.foundation.util.chrys_headers import REQUEST_ATTEMPT_ID_HEADER
from chrys.kernel import Message
from chrys.service.llm.chat_completions.client import ChatCompletionsClient
from chrys.service.llm.clients import _build_openai_sdk_client, _build_profile_http_client
from chrys.service.profiles.models.schema import ModelProfile

_ATTEMPT_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")

CHUNK = {
    "id": "chatcmpl-1",
    "object": "chat.completion.chunk",
    "created": 1,
    "model": "glm-5.2",
    "choices": [{"index": 0, "delta": {"role": "assistant", "content": "hi"}, "finish_reason": "stop"}],
}
BLOCKING_REPLY = {
    "id": "resp-1",
    "object": "chat.completion",
    "created": 1,
    "model": "glm-5.2",
    "choices": [{"index": 0, "message": {"role": "assistant", "content": "hi"}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
}


@asynccontextmanager
async def _wire(requests: list[httpx.Request], *, stream: bool) -> AsyncIterator[ChatCompletionsClient]:
    """The production client over a recording transport; appends each attempt's request."""

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if stream:
            body = f"data: {json.dumps(CHUNK)}\n\ndata: [DONE]\n\n"
            return httpx.Response(200, text=body, headers={"content-type": "text/event-stream"})
        return httpx.Response(200, json=BLOCKING_REPLY)

    http = _build_profile_http_client(
        ModelProfile(id="p", name="p", provider="openai", model_id="glm-5.2", api_key="test"),
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
    client = ChatCompletionsClient(model="glm-5.2", sdk_client=sdk)
    try:
        yield client
    finally:
        await client.aclose()


async def _consume(client: ChatCompletionsClient) -> None:
    stream = client._open_stream(messages=[Message("user", ["hi"])], options={})
    async for _ in stream:
        pass


@pytest.mark.parametrize("stream", [True, False])
async def test_request_carries_the_attempt_header_and_no_body_id(stream: bool) -> None:
    requests: list[httpx.Request] = []
    async with _wire(requests, stream=stream) as client:
        if stream:
            await _consume(client)
        else:
            await client._send(messages=[Message("user", ["hi"])], options={})

    request = requests[0]
    assert _ATTEMPT_ID_PATTERN.fullmatch(request.headers[REQUEST_ATTEMPT_ID_HEADER])
    assert "request_id" not in json.loads(request.content)


async def test_tracker_uses_the_header_of_the_answering_attempt(monkeypatch: pytest.MonkeyPatch) -> None:
    """The id the tracker cancels with is the one on the wire for this attempt."""
    import chrys.service.aixcoding.llm_queue as package

    armed: list[str] = []
    real = package.track_queue_request

    def spy(request: httpx.Request, **kwargs: object) -> object:
        tracker = real(request, **kwargs)  # type: ignore[arg-type]
        if tracker is not None:
            armed.append(tracker.request_id)
        return tracker

    monkeypatch.setattr("chrys.service.aixcoding.llm_queue.track_queue_request", spy)
    requests: list[httpx.Request] = []
    async with _wire(requests, stream=True) as client:
        await _consume(client)

    assert armed == [requests[0].headers[REQUEST_ATTEMPT_ID_HEADER]]


async def test_missing_header_disarms_the_tracker(monkeypatch: pytest.MonkeyPatch) -> None:
    """A client without the upstream tracking hooks still streams; it just cannot cancel."""
    import chrys.service.aixcoding.llm_queue as package

    armed: list[object] = []
    real = package.track_queue_request
    monkeypatch.setattr(
        "chrys.service.aixcoding.llm_queue.track_queue_request",
        lambda request, **kwargs: armed.append(real(request, **kwargs)),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        body = f"data: {json.dumps(CHUNK)}\n\ndata: [DONE]\n\n"
        return httpx.Response(200, text=body, headers={"content-type": "text/event-stream"})

    sdk = _build_openai_sdk_client(
        api_key="test",
        base_url="http://llm.test/v1",
        timeout=5.0,
        max_retries=0,
        default_headers=None,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    client = ChatCompletionsClient(model="glm-5.2", sdk_client=sdk)
    try:
        await _consume(client)
    finally:
        await client.aclose()

    assert armed == [None]
