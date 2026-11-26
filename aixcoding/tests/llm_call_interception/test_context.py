# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

from __future__ import annotations

import asyncio

import httpx
import pytest
from aixcoding.tests.llm_call_interception.support import trajectory

from chrys.service.aixcoding.llm_call_interception.hooks import build_http_hooks
from chrys.service.aixcoding.llm_call_interception.interceptor import set_http_policy
from chrys.service.llm.request_tracking import RequestTracking, build_request_tracking_hooks


class CaptureContext:
    def __init__(self) -> None:
        self.requests = []
        self.responses = []

    async def before_request(self, context, headers, body):
        self.requests.append(context)

    async def before_response(self, context, status_code, headers):
        self.responses.append(context)


def _hooks() -> dict[str, list]:
    tracking = build_request_tracking_hooks()
    custom = build_http_hooks(provider="openai", model="model-test")
    return {
        "request": [*tracking["request"], *custom["request"]],
        "response": [*tracking["response"], *custom["response"]],
    }


@pytest.mark.parametrize("turn_id", ["turn-real", None])
async def test_request_and_response_context_from_real_tracking_extensions(turn_id: str | None) -> None:
    policy = CaptureContext()
    set_http_policy(policy)
    context, sink = trajectory(turn_id=turn_id)
    tracker = RequestTracking(context)

    async def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle), event_hooks=_hooks()) as client:
        with tracker.scope():
            await client.post("http://llm.test", headers={"X-Session-ID": "derived-route"}, content=b"{}")

    assert len(policy.requests) == len(policy.responses) == 1
    for captured in (policy.requests[0], policy.responses[0]):
        assert captured.session_id == "session-real"
        assert captured.turn_id == turn_id
        assert captured.cycle_operation_id == "cycle-1"
        assert captured.exchange_operation_id == "exchange-1"
        assert captured.request_attempt_id == tracker.request_attempt_id
        assert captured.actor.kind == "agent"
        assert captured.actor.role == "main"
        assert captured.provider == "openai"
        assert captured.model == "model-test"
        assert captured.session_id != "derived-route"
    assert len(sink.drafts) == 2


async def test_route_session_header_does_not_replace_trajectory_session() -> None:
    policy = CaptureContext()
    set_http_policy(policy)
    context, _ = trajectory(session_id="trajectory-session")
    tracker = RequestTracking(context)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200)), event_hooks=_hooks()
    ) as client:
        with tracker.scope():
            await client.get("http://llm.test", headers={"Chrys-Session-Id": "route-only"})

    assert policy.requests[0].session_id == "trajectory-session"


async def test_redirect_attempt_ids_and_cycle_correlation() -> None:
    policy = CaptureContext()
    set_http_policy(policy)
    context, _ = trajectory()
    tracker = RequestTracking(context)

    async def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/start":
            return httpx.Response(307, headers={"Location": "/end"})
        return httpx.Response(200, json={"ok": True})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handle), event_hooks=_hooks(), follow_redirects=True
    ) as client:
        with tracker.scope():
            await client.get("http://llm.test/start")

    assert len(policy.requests) == 2
    assert len({item.request_attempt_id for item in policy.requests}) == 2
    assert {item.cycle_operation_id for item in policy.requests} == {"cycle-1"}
    assert {item.exchange_operation_id for item in policy.requests} == {"exchange-1"}
    assert [item.request_attempt_id for item in policy.responses] == [
        item.request_attempt_id for item in policy.requests
    ]


async def test_concurrent_contexts_and_profiles_do_not_cross_talk() -> None:
    policy = CaptureContext()
    set_http_policy(policy)
    contexts = [trajectory(session_id=f"session-{index}")[0] for index in range(2)]
    arrived = asyncio.Event()
    count = 0

    async def handle(request: httpx.Request) -> httpx.Response:
        nonlocal count
        count += 1
        if count == 2:
            arrived.set()
        await arrived.wait()
        return httpx.Response(200, json={"ok": True})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle), event_hooks=_hooks()) as client:

        async def send(index: int) -> None:
            with RequestTracking(contexts[index]).scope():
                await client.get(f"http://llm.test/{index}")

        await asyncio.gather(send(0), send(1))

    assert {item.session_id for item in policy.requests} == {"session-0", "session-1"}
    assert len({item.request_attempt_id for item in policy.requests}) == 2
    assert all(item.provider == "openai" and item.model == "model-test" for item in policy.requests)
