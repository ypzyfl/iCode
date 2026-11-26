# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

from __future__ import annotations

import json

import httpx
import pytest
from aixcoding.tests.llm_call_interception.support import (
    ANTHROPIC_REPLY,
    OPENAI_REPLY,
    RESPONSES_REPLY,
    ChunkStream,
    RetryPolicy,
    profile,
    stream_payload,
)
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from chrys.foundation.errors import classify_error
from chrys.kernel import Message
from chrys.service.aixcoding.llm_call_interception import Block
from chrys.service.aixcoding.llm_call_interception.installer import install_http_interception
from chrys.service.aixcoding.llm_call_interception.interceptor import set_http_policy
from chrys.service.llm import clients


class BlockStage:
    def __init__(self, stage: str) -> None:
        self.stage = stage

    def __getattr__(self, name: str):
        if name != self.stage:
            raise AttributeError(name)

        async def block(*args):
            return Block("private strategy reason")

        return block


async def _call(protocol: str, sdk) -> None:
    if protocol == "anthropic":
        await sdk.messages.create(model="model-test", max_tokens=16, messages=[{"role": "user", "content": "hi"}])
    elif protocol == "responses":
        await sdk.responses.create(model="model-test", input="hi")
    else:
        await sdk.chat.completions.create(model="model-test", messages=[{"role": "user", "content": "hi"}])


@pytest.mark.parametrize("protocol", ["chat", "responses", "anthropic"])
@pytest.mark.parametrize("stage", ["before_request", "before_response", "before_response_body"])
@pytest.mark.parametrize("buffered", [True, False])
async def test_block_does_not_retry_and_has_clean_classification(
    protocol: str, stage: str, buffered: bool, monkeypatch: pytest.MonkeyPatch, caplog
) -> None:
    monkeypatch.setattr(AsyncOpenAI, "_calculate_retry_timeout", lambda *args: 0.0)
    monkeypatch.setattr(AsyncAnthropic, "_calculate_retry_timeout", lambda *args: 0.0)
    original = clients._build_profile_http_client
    monkeypatch.setattr(clients, "_build_profile_http_client", original)
    install_http_interception()
    set_http_policy(BlockStage(stage))
    calls = 0

    async def handle(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        payload = (
            ANTHROPIC_REPLY if protocol == "anthropic" else RESPONSES_REPLY if protocol == "responses" else OPENAI_REPLY
        )
        if stage == "before_response_body" and not buffered:
            return httpx.Response(200, stream=ChunkStream([json.dumps(payload).encode()]))
        return httpx.Response(200, json=payload)

    provider = "anthropic" if protocol == "anthropic" else "openai"
    api_style = "responses" if protocol == "responses" else "chat_completions"
    http = clients._build_profile_http_client(
        profile(provider, api_style=api_style),
        httpx.Timeout(5),
        transport=httpx.MockTransport(handle),
    )
    sdk = (
        AsyncAnthropic(api_key="key-test", http_client=http, max_retries=2)
        if protocol == "anthropic"
        else AsyncOpenAI(api_key="key-test", http_client=http, max_retries=2)
    )
    try:
        with pytest.raises(Exception) as caught:
            await _call(protocol, sdk)
    finally:
        await sdk.close()

    assert calls == (0 if stage == "before_request" else 1)
    classification = classify_error(caught.value)
    assert classification.retryable is False
    assert classification.transient is False
    assert str(caught.value) == "AIxCoding blocked the model HTTP call."
    assert caught.value.args == ("AIxCoding blocked the model HTTP call.",)
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ is True
    assert "private strategy reason" not in str(caught.value)
    assert "private strategy reason" in caplog.text


@pytest.mark.parametrize("protocol", ["chat", "responses", "anthropic"])
async def test_final_block_classification_and_exception_hygiene(
    protocol: str, monkeypatch: pytest.MonkeyPatch, caplog
) -> None:
    original = clients._build_profile_http_client
    monkeypatch.setattr(clients, "_build_profile_http_client", original)
    install_http_interception()
    installed = clients._build_profile_http_client
    set_http_policy(BlockStage("before_request"))
    calls = 0

    async def handle(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=OPENAI_REPLY)

    def with_transport(profile_value, timeout, **kwargs):
        return installed(profile_value, timeout, **kwargs, transport=httpx.MockTransport(handle))

    monkeypatch.setattr(clients, "_build_profile_http_client", with_transport)
    provider = "anthropic" if protocol == "anthropic" else "openai"
    api_style = "responses" if protocol == "responses" else "chat_completions"
    stack = await clients.create_client(profile(provider, api_style=api_style))
    try:
        with pytest.raises(Exception) as caught:
            await stack.get_response([Message("user", ["hi"])], client_kwargs={"wire_retry_policy": RetryPolicy()})
    finally:
        await stack.aclose()

    assert calls == 0
    classification = classify_error(caught.value)
    assert classification.retryable is False
    assert classification.transient is False
    assert "AIxCoding blocked the model HTTP call." in str(caught.value)
    assert "private strategy reason" not in str(caught.value)
    assert "private strategy reason" in caplog.text


@pytest.mark.parametrize(
    ("protocol", "terminal", "event_count"),
    [("chat", b"[DONE]", 2), ("responses", b"response.completed", 2), ("anthropic", b"message_stop", 6)],
)
async def test_stream_block_after_delivered_event_does_not_replay(
    protocol: str, terminal: bytes, event_count: int, monkeypatch: pytest.MonkeyPatch, caplog
) -> None:
    class BlockTerminal:
        def __init__(self) -> None:
            self.events = 0

        async def before_sse_event(self, context, status_code, headers, event):
            self.events += 1
            return Block("stream stop") if terminal in event else None

    original = clients._build_profile_http_client
    monkeypatch.setattr(clients, "_build_profile_http_client", original)
    install_http_interception()
    installed = clients._build_profile_http_client
    policy = BlockTerminal()
    set_http_policy(policy)
    calls = 0
    payload = stream_payload(protocol)

    async def handle(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            headers={"Content-Type": "text/event-stream"},
            stream=ChunkStream([payload]),
        )

    def with_transport(profile_value, timeout, **kwargs):
        return installed(profile_value, timeout, **kwargs, transport=httpx.MockTransport(handle))

    monkeypatch.setattr(clients, "_build_profile_http_client", with_transport)
    provider = "anthropic" if protocol == "anthropic" else "openai"
    api_style = "responses" if protocol == "responses" else "chat_completions"
    stack = await clients.create_client(profile(provider, api_style=api_style))
    try:
        result = stack.get_response(
            [Message("user", ["hi"])],
            stream=True,
            client_kwargs={"wire_retry_policy": RetryPolicy()},
        )
        with pytest.raises(Exception) as caught:
            async for _ in result:
                pass
    finally:
        await stack.aclose()

    assert calls == 1
    assert policy.events == event_count
    classification = classify_error(caught.value)
    assert classification.retryable is False
    assert classification.transient is False
    assert "AIxCoding blocked the model HTTP call." in str(caught.value)
    assert "stream stop" not in str(caught.value)
    assert "stream stop" in caplog.text
