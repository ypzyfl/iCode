# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

from __future__ import annotations

import gzip

import httpx
import pytest
from aixcoding.tests.llm_call_interception.support import ChunkStream

from chrys.service.aixcoding.llm_call_interception import HttpChange
from chrys.service.aixcoding.llm_call_interception.hooks import build_http_hooks
from chrys.service.aixcoding.llm_call_interception.interceptor import set_http_policy


class ResponseMutation:
    async def before_response(self, context, status_code, headers):
        updated = dict(headers)
        updated["X-Policy-Response"] = "yes"
        return HttpChange(headers=updated)

    async def before_response_body(self, context, status_code, headers, body):
        return HttpChange(body=body.replace(b"original", b"modified"))


@pytest.mark.parametrize("buffered", [True, False])
async def test_response_mutation_is_visible_to_httpx(buffered: bool) -> None:
    set_http_policy(ResponseMutation())

    async def handle(request: httpx.Request) -> httpx.Response:
        if buffered:
            return httpx.Response(200, content=b'{"value":"original"}')
        return httpx.Response(200, stream=ChunkStream([b'{"value":"orig', b'inal"}']))

    hooks = build_http_hooks(provider="openai", model="model-test")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle), event_hooks=hooks) as client:
        response = await client.get("http://llm.test")

    assert response.content == b'{"value":"modified"}'
    assert response.headers["X-Policy-Response"] == "yes"
    assert response.headers["Content-Length"] == str(len(response.content))


class FailingBody:
    async def before_response_body(self, context, status_code, headers, body):
        raise RuntimeError("sensitive-original-body-must-not-be-logged")


@pytest.mark.parametrize("buffered", [True, False])
async def test_buffered_and_stream_responses_fail_open_with_original_body(buffered: bool, caplog) -> None:
    set_http_policy(FailingBody())

    async def handle(request: httpx.Request) -> httpx.Response:
        if buffered:
            return httpx.Response(200, content=b"original")
        return httpx.Response(200, stream=ChunkStream([b"orig", b"inal"]))

    hooks = build_http_hooks(provider="openai", model="model-test")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle), event_hooks=hooks) as client:
        response = await client.get("http://llm.test")

    assert response.content == b"original"
    assert "response_body" in caplog.text
    assert "sensitive-original-body-must-not-be-logged" not in caplog.text


async def test_encoded_response_passes_through() -> None:
    calls = []

    class BodyPolicy:
        async def before_response_body(self, context, status_code, headers, body):
            calls.append(body)
            return HttpChange(body=b"changed")

    set_http_policy(BodyPolicy())

    async def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=gzip.compress(b"original"), headers={"Content-Encoding": "gzip"})

    hooks = build_http_hooks(provider="openai", model="model-test")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle), event_hooks=hooks) as client:
        response = await client.get("http://llm.test")

    assert response.content == b"original"
    assert calls == []


@pytest.mark.parametrize("buffered", [True, False])
async def test_content_sniff_dispatches_mislabelled_json_to_body_policy(buffered: bool) -> None:
    set_http_policy(ResponseMutation())
    body = b'{"value":"original"}'

    async def handle(request: httpx.Request) -> httpx.Response:
        headers = {"Content-Type": "text/event-stream"}
        if buffered:
            return httpx.Response(200, content=body, headers=headers)
        return httpx.Response(200, stream=ChunkStream([body[:8], body[8:]]), headers=headers)

    hooks = build_http_hooks(provider="openai", model="model-test")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle), event_hooks=hooks) as client:
        response = await client.get("http://llm.test")

    assert response.content == b'{"value":"modified"}'


async def test_normal_response_with_only_sse_policy_logs_mismatch(caplog) -> None:
    class EventOnly:
        def __init__(self) -> None:
            self.calls = 0

        async def before_sse_event(self, context, status_code, headers, event):
            self.calls += 1

    policy = EventOnly()
    set_http_policy(policy)

    async def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b'{"value":"original"}')

    hooks = build_http_hooks(provider="openai", model="model-test")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle), event_hooks=hooks) as client:
        response = await client.get("http://llm.test")

    assert response.content == b'{"value":"original"}'
    assert policy.calls == 0
    assert "response_handler_mismatch:normal" in caplog.text


@pytest.mark.parametrize(("colon_index", "expected"), [(511, "sse"), (512, "normal")])
async def test_sniff_window_boundary_and_oversized_chunk_replay(colon_index: int, expected: str) -> None:
    class CaptureContent:
        def __init__(self) -> None:
            self.bodies = []
            self.events = []

        async def before_response_body(self, context, status_code, headers, body):
            self.bodies.append(body)

        async def before_sse_event(self, context, status_code, headers, event):
            self.events.append(event)

    policy = CaptureContent()
    set_http_policy(policy)
    original = b"a" * colon_index + b": value\n\n"

    async def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Type": "application/json"},
            stream=ChunkStream([original]),
        )

    hooks = build_http_hooks(provider="openai", model="model-test")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle), event_hooks=hooks) as client:
        response = await client.get("http://llm.test")

    assert response.content == original
    assert bool(policy.events) == (expected == "sse")
    assert bool(policy.bodies) == (expected == "normal")
    assert (policy.events + policy.bodies) == [original]
