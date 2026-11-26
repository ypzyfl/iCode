# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

from __future__ import annotations

import json
from functools import wraps

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
    trajectory,
)
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from chrys.foundation.trajectory.context import TRAJECTORY_CONTEXT_KWARG
from chrys.kernel import Message
from chrys.service.aixcoding.llm_call_interception import HttpChange
from chrys.service.aixcoding.llm_call_interception.installer import _CLIENT_MARKER, install_http_interception
from chrys.service.aixcoding.llm_call_interception.interceptor import set_http_policy
from chrys.service.llm import clients
from chrys.service.llm.request_tracking import RequestTracking


def _install_with_transport(transport: httpx.AsyncBaseTransport, monkeypatch: pytest.MonkeyPatch) -> None:
    original = clients._build_profile_http_client
    monkeypatch.setattr(clients, "_build_profile_http_client", original)
    install_http_interception()
    installed = clients._build_profile_http_client

    @wraps(installed)
    def with_transport(profile_value, timeout, **kwargs):
        return installed(profile_value, timeout, **kwargs, transport=transport)

    monkeypatch.setattr(clients, "_build_profile_http_client", with_transport)


@pytest.mark.parametrize(
    ("provider", "api_style"),
    [
        ("openai", "chat_completions"),
        ("openai", "responses"),
        ("deepseek-openai", "chat_completions"),
        ("deepseek-openai", "responses"),
        ("glm-openai", "chat_completions"),
        ("anthropic", "chat_completions"),
    ],
)
async def test_create_client_uses_installed_http_client(
    provider: str, api_style: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(500))
    set_http_policy(object())  # type: ignore[arg-type]
    _install_with_transport(transport, monkeypatch)
    stack = await clients.create_client(profile(provider, api_style=api_style))
    try:
        wire = stack.inner.inner
        http = wire.sdk_client._client
        assert getattr(http, _CLIENT_MARKER) is True
        assert wire.sdk_client.max_retries == 2
    finally:
        await stack.aclose()


class CaptureStages:
    def __init__(self) -> None:
        self.requests = []
        self.responses = []
        self.bodies = []
        self.events = []

    async def before_request(self, context, headers, body):
        self.requests.append(context)

    async def before_response(self, context, status_code, headers):
        self.responses.append(context)

    async def before_response_body(self, context, status_code, headers, body):
        self.bodies.append(body)

    async def before_sse_event(self, context, status_code, headers, event):
        self.events.append(event)


async def _exercise_sdk(protocol: str, sdk, *, stream: bool, retrieve: bool = False) -> None:
    if protocol == "anthropic":
        result = await sdk.messages.create(
            model="model-test",
            max_tokens=16,
            messages=[{"role": "user", "content": "hi"}],
            stream=stream,
        )
    elif protocol == "responses":
        if retrieve:
            result = await sdk.responses.retrieve("resp_1", stream=stream)
        else:
            result = await sdk.responses.create(model="model-test", input="hi", stream=stream)
    else:
        result = await sdk.chat.completions.create(
            model="model-test", messages=[{"role": "user", "content": "hi"}], stream=stream
        )
    if stream:
        async for _ in result:
            pass


@pytest.mark.parametrize("protocol", ["chat", "responses", "anthropic"])
@pytest.mark.parametrize("stream", [False, True])
async def test_provider_wire_calls_pass_through_interceptor(
    protocol: str, stream: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy = CaptureStages()
    set_http_policy(policy)

    async def handle(request: httpx.Request) -> httpx.Response:
        if stream:
            return httpx.Response(
                200,
                headers={"Content-Type": "text/event-stream"},
                stream=ChunkStream([stream_payload(protocol)]),
            )
        payload = (
            ANTHROPIC_REPLY if protocol == "anthropic" else RESPONSES_REPLY if protocol == "responses" else OPENAI_REPLY
        )
        return httpx.Response(200, stream=ChunkStream([json.dumps(payload).encode()]))

    _install_with_transport(httpx.MockTransport(handle), monkeypatch)
    provider = "anthropic" if protocol == "anthropic" else "openai"
    http = clients._build_profile_http_client(profile(provider), httpx.Timeout(5))
    sdk = (
        AsyncAnthropic(api_key="key-test", http_client=http, max_retries=0)
        if protocol == "anthropic"
        else AsyncOpenAI(api_key="key-test", http_client=http, max_retries=0)
    )
    try:
        await _exercise_sdk(protocol, sdk, stream=stream)
    finally:
        await sdk.close()

    assert len(policy.requests) == len(policy.responses) == 1
    assert len(policy.events if stream else policy.bodies) > 0
    assert policy.requests[0].provider == provider


@pytest.mark.parametrize("stream", [False, True])
async def test_responses_retrieve_and_poll_pass_through_interceptor(
    stream: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy = CaptureStages()
    set_http_policy(policy)

    async def handle(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        if stream:
            return httpx.Response(
                200,
                headers={"Content-Type": "text/event-stream"},
                stream=ChunkStream([stream_payload("responses")]),
            )
        return httpx.Response(200, json=RESPONSES_REPLY)

    _install_with_transport(httpx.MockTransport(handle), monkeypatch)
    http = clients._build_profile_http_client(profile("openai", api_style="responses"), httpx.Timeout(5))
    sdk = AsyncOpenAI(api_key="key-test", http_client=http, max_retries=0)
    try:
        await _exercise_sdk("responses", sdk, stream=stream, retrieve=True)
    finally:
        await sdk.close()
    assert len(policy.requests) == 1
    assert len(policy.events if stream else policy.bodies) > 0


async def test_sdk_retry_attempt_ids_and_cycle_correlation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(AsyncOpenAI, "_calculate_retry_timeout", lambda *args: 0.0)
    policy = CaptureStages()
    set_http_policy(policy)
    context, _ = trajectory()
    calls = 0

    async def handle(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, json={"error": {"message": "retry"}}, headers={"retry-after-ms": "0"})
        return httpx.Response(200, json=OPENAI_REPLY)

    _install_with_transport(httpx.MockTransport(handle), monkeypatch)
    http = clients._build_profile_http_client(profile(), httpx.Timeout(5))
    sdk = AsyncOpenAI(api_key="key-test", http_client=http, max_retries=1)
    try:
        with RequestTracking(context).scope():
            await sdk.chat.completions.create(model="model-test", messages=[{"role": "user", "content": "hi"}])
    finally:
        await sdk.close()

    assert calls == 2
    assert len({item.request_attempt_id for item in policy.requests}) == 2
    assert {item.cycle_operation_id for item in policy.requests} == {"cycle-1"}
    assert {item.exchange_operation_id for item in policy.requests} == {"exchange-1"}


async def test_chrys_retry_changes_exchange_and_attempt_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    policy = CaptureStages()
    set_http_policy(policy)
    context, _ = trajectory()
    calls = 0

    async def handle(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, json={"error": {"message": "retry"}})
        return httpx.Response(200, json=OPENAI_REPLY)

    _install_with_transport(httpx.MockTransport(handle), monkeypatch)
    model_profile = profile()
    model_profile.http_max_retries = 0
    stack = await clients.create_client(model_profile)
    try:
        response = await stack.get_response(
            [Message("user", ["hi"])],
            client_kwargs={TRAJECTORY_CONTEXT_KWARG: context, "wire_retry_policy": RetryPolicy()},
        )
        assert response.text == "ok"
    finally:
        await stack.aclose()

    assert calls == 2
    assert len({item.request_attempt_id for item in policy.requests}) == 2
    assert len({item.exchange_operation_id for item in policy.requests}) == 2
    cycles = {item.cycle_operation_id for item in policy.requests}
    assert None not in cycles
    assert len(cycles) == 1


class SdkResponseMutation:
    async def before_response(self, context, status_code, headers):
        updated = dict(headers)
        updated["X-Policy-Sdk"] = "visible"
        return HttpChange(headers=updated)

    async def before_response_body(self, context, status_code, headers, body):
        payload = json.loads(body)
        if "choices" in payload:
            payload["choices"][0]["message"]["content"] = "modified-by-policy"
        elif payload.get("type") == "message":
            payload["content"][0]["text"] = "modified-by-policy"
        else:
            payload["output"][0]["content"][0]["text"] = "modified-by-policy"
        return HttpChange(body=json.dumps(payload).encode())


@pytest.mark.parametrize("protocol", ["chat", "responses", "anthropic"])
@pytest.mark.parametrize("buffered", [True, False])
async def test_response_mutation_is_visible_to_sdk_parsed_result(
    protocol: str, buffered: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    set_http_policy(SdkResponseMutation())
    payload = (
        ANTHROPIC_REPLY if protocol == "anthropic" else RESPONSES_REPLY if protocol == "responses" else OPENAI_REPLY
    )

    async def handle(request: httpx.Request) -> httpx.Response:
        if buffered:
            return httpx.Response(200, json=payload)
        return httpx.Response(200, stream=ChunkStream([json.dumps(payload).encode()]))

    _install_with_transport(httpx.MockTransport(handle), monkeypatch)
    provider = "anthropic" if protocol == "anthropic" else "openai"
    api_style = "responses" if protocol == "responses" else "chat_completions"
    http = clients._build_profile_http_client(profile(provider, api_style=api_style), httpx.Timeout(5))
    sdk = (
        AsyncAnthropic(api_key="key-test", http_client=http, max_retries=0)
        if protocol == "anthropic"
        else AsyncOpenAI(api_key="key-test", http_client=http, max_retries=0)
    )
    try:
        if protocol == "anthropic":
            raw = await sdk.messages.with_raw_response.create(
                model="model-test", max_tokens=16, messages=[{"role": "user", "content": "hi"}]
            )
        elif protocol == "responses":
            raw = await sdk.responses.with_raw_response.create(model="model-test", input="hi")
        else:
            raw = await sdk.chat.completions.with_raw_response.create(
                model="model-test", messages=[{"role": "user", "content": "hi"}]
            )
        assert raw.headers["X-Policy-Sdk"] == "visible"
        parsed = raw.parse()
    finally:
        await sdk.close()

    if protocol == "anthropic":
        assert parsed.content[0].text == "modified-by-policy"
    elif protocol == "responses":
        assert parsed.output[0].content[0].text == "modified-by-policy"
    else:
        assert parsed.choices[0].message.content == "modified-by-policy"


@pytest.mark.parametrize("protocol", ["chat", "responses", "anthropic"])
async def test_mislabelled_sse_passes_real_sdk_stream(protocol: str, monkeypatch: pytest.MonkeyPatch) -> None:
    policy = CaptureStages()
    set_http_policy(policy)

    async def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Type": "application/json"},
            stream=ChunkStream([stream_payload(protocol)]),
        )

    _install_with_transport(httpx.MockTransport(handle), monkeypatch)
    provider = "anthropic" if protocol == "anthropic" else "openai"
    api_style = "responses" if protocol == "responses" else "chat_completions"
    http = clients._build_profile_http_client(profile(provider, api_style=api_style), httpx.Timeout(5))
    sdk = (
        AsyncAnthropic(api_key="key-test", http_client=http, max_retries=0)
        if protocol == "anthropic"
        else AsyncOpenAI(api_key="key-test", http_client=http, max_retries=0)
    )
    try:
        await _exercise_sdk(protocol, sdk, stream=True)
    finally:
        await sdk.close()

    assert len(policy.requests) == 1
    assert len(policy.events) > 0
    assert policy.bodies == []
