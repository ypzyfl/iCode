# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

from __future__ import annotations

import json

import httpx

from chrys.service.aixcoding.llm_call_interception import HttpChange
from chrys.service.aixcoding.llm_call_interception.hooks import build_http_hooks
from chrys.service.aixcoding.llm_call_interception.interceptor import set_http_policy


class RequestMutation:
    async def before_request(self, context, headers, body):
        payload = json.loads(body)
        payload["policy"] = True
        updated = dict(headers)
        updated["X-Example-Policy"] = "enabled"
        assert context.provider == "openai"
        assert context.model == "model-test"
        return HttpChange(headers=updated, body=json.dumps(payload).encode())


async def test_request_header_and_body_mutation_reaches_transport() -> None:
    set_http_policy(RequestMutation())
    seen = {}

    async def handle(request: httpx.Request) -> httpx.Response:
        seen["headers"] = request.headers
        seen["body"] = await request.aread()
        return httpx.Response(200, json={"ok": True})

    hooks = build_http_hooks(provider="openai", model="model-test")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle), event_hooks=hooks) as client:
        await client.post("http://llm.test", json={"original": True})

    assert seen["headers"]["X-Example-Policy"] == "enabled"
    assert json.loads(seen["body"]) == {"original": True, "policy": True}
    assert seen["headers"]["Content-Length"] == str(len(seen["body"]))


class IdentityOnHeadersCopy:
    async def before_request(self, context, headers, body):
        updated = httpx.Headers(headers)
        updated["Accept-Encoding"] = "identity"
        return HttpChange(headers=updated)


class IdentityOnDictWithDifferentlyCasedKey:
    async def before_request(self, context, headers, body):
        updated = dict(headers)
        updated["Accept-Encoding"] = "identity"
        return HttpChange(headers=updated)


async def accept_encoding_on_the_wire(policy) -> list[str]:
    set_http_policy(policy)
    seen = {}

    async def handle(request: httpx.Request) -> httpx.Response:
        seen["accept_encoding"] = request.headers.get_list("Accept-Encoding")
        return httpx.Response(200, json={"ok": True})

    hooks = build_http_hooks(provider="openai", model="model-test")
    client_headers = {"Accept-Encoding": "gzip, deflate"}
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handle), event_hooks=hooks, headers=client_headers
    ) as client:
        await client.post("http://llm.test", json={"original": True})
    return seen["accept_encoding"]


async def test_replacing_accept_encoding_on_headers_copy_negotiates_identity() -> None:
    assert await accept_encoding_on_the_wire(IdentityOnHeadersCopy()) == ["identity"]


async def test_dict_with_differently_cased_key_sends_accept_encoding_twice() -> None:
    # Pins the documented pitfall: policy headers are forwarded as given, without merging or
    # reporting duplicates, so a gateway may still pick a listed encoding.
    policy = IdentityOnDictWithDifferentlyCasedKey()
    assert await accept_encoding_on_the_wire(policy) == ["gzip, deflate", "identity"]
