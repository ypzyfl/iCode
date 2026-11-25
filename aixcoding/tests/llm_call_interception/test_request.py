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
