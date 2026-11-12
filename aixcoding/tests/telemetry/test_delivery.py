# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Delivery contract at the HTTP boundary."""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest


async def test_failed_post_does_not_reorder_or_retry_following_reports() -> None:
    from chrys.service.aixcoding.telemetry.delivery import TelemetryDelivery
    from chrys.service.aixcoding.telemetry.reporters import Report

    received = []
    tokens = iter(("first", "second"))

    def receive(request: httpx.Request) -> httpx.Response:
        received.append((request.url.path, request.headers["token"], json.loads(request.content)))
        return httpx.Response(503 if len(received) == 1 else 200)

    client = httpx.AsyncClient(transport=httpx.MockTransport(receive))
    delivery = TelemetryDelivery("https://telemetry.invalid/csas", token_provider=lambda: next(tokens), client=client)
    delivery.submit(Report("tool-detail/save", {"funcId": "x"}))
    delivery.submit(Report("tool-detail/update", {"funcId": "x", "codeStatus": 3}))
    await delivery.aclose()
    assert client.is_closed
    assert received == [
        ("/csas/telemetry/api/v1/tool-detail/save", "first", {"funcId": "x"}),
        ("/csas/telemetry/api/v1/tool-detail/update", "second", {"funcId": "x", "codeStatus": 3}),
    ]
    assert (delivery.sent, delivery.failed, delivery.dropped) == (1, 1, 0)


async def test_queue_counts_overflow_and_rejects_submissions_after_close() -> None:
    from chrys.service.aixcoding.telemetry.delivery import TelemetryDelivery
    from chrys.service.aixcoding.telemetry.reporters import Report

    received = []

    def receive(request: httpx.Request) -> httpx.Response:
        received.append(json.loads(request.content))
        return httpx.Response(200)

    delivery = TelemetryDelivery(
        "https://telemetry.invalid",
        token_provider=lambda: None,
        capacity=1,
        client=httpx.AsyncClient(transport=httpx.MockTransport(receive)),
    )
    assert delivery.submit(Report("tool-detail/save", {"funcId": "first"}))
    assert not delivery.submit(Report("tool-detail/save", {"funcId": "overflow"}))
    await delivery.aclose()
    assert not delivery.submit(Report("tool-detail/save", {"funcId": "closed"}))
    assert received == [{"funcId": "first"}]
    assert (delivery.sent, delivery.failed, delivery.dropped) == (1, 0, 2)


async def test_code_buffer_flushes_on_threshold_timer_and_shutdown() -> None:
    from chrys.service.aixcoding.telemetry.delivery import TelemetryDelivery
    from chrys.service.aixcoding.telemetry.reporters import Report

    received = asyncio.Queue[str]()

    def receive(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/telemetry/api/v1/ai-code/save"
        received.put_nowait(json.loads(request.content)["reportId"])
        return httpx.Response(200)

    delivery = TelemetryDelivery(
        "https://telemetry.invalid",
        token_provider=lambda: None,
        client=httpx.AsyncClient(transport=httpx.MockTransport(receive)),
        code_flush_size=2,
        code_flush_interval=0.05,
    )
    try:
        delivery.submit_code(Report("ai-code/save", {"reportId": "first"}))
        delivery.submit_code(Report("ai-code/save", {"reportId": "threshold"}))
        assert await asyncio.wait_for(received.get(), 1) == "first"
        assert await asyncio.wait_for(received.get(), 1) == "threshold"
        delivery.submit_code(Report("ai-code/save", {"reportId": "timer"}))
        assert await asyncio.wait_for(received.get(), 1) == "timer"
        delivery.submit_code(Report("ai-code/save", {"reportId": "close"}))
    finally:
        await delivery.aclose()
    assert received.get_nowait() == "close"


@pytest.mark.parametrize("disabled_by", ["environment", "config"])
async def test_disabled_telemetry_keeps_the_engine_turn_working(
    monkeypatch, telemetry_engine, telemetry_provider, telemetry_capture, disabled_by
) -> None:
    from chrys.foundation.events.types import InvocationMessage, UserMessage
    from chrys.foundation.platform import get_platform

    if disabled_by == "environment":
        monkeypatch.setenv("AIXCODING_TELEMETRY_DISABLED", "1")
    else:
        config = get_platform().config_dir
        config.mkdir(parents=True)
        (config / "aixcoding.yaml").write_text("telemetryEnabled: false\n", encoding="utf-8")
    engine = telemetry_engine.build()
    results = []

    async def record(event: InvocationMessage) -> None:
        if event.is_final:
            results.append(event.text)

    await engine.event_bus.subscribe(InvocationMessage, record)
    try:
        await engine.start(telemetry_engine.profile)
        await engine.event_bus.publish(UserMessage(text="Finish normally."), raise_handler_errors=True)
        await asyncio.wait_for(engine.wait_for_run_task(), 10)
    finally:
        await engine.shutdown()
    assert results == ["Finished."]
    (request,) = telemetry_provider.requests
    assert "telemetry" not in json.loads(request.content)
    assert telemetry_capture.requests == []
    assert telemetry_capture.clients == []


async def test_repeated_attach_and_detach_report_once_and_allow_reattach(telemetry_capture) -> None:
    from chrys.foundation.events.bus import EventBus
    from chrys.foundation.events.types import InvocationToolCallStart
    from chrys.foundation.models.invocations import InvocationOrigin
    from chrys.orchestration.aixcoding.telemetry.lifecycle import attach, detach

    bus = EventBus()
    origin = InvocationOrigin("turn", "lifecycle-session", "turn-one", None)

    async def publish(call_id: str) -> None:
        await bus.publish(
            InvocationToolCallStart(origin=origin, call_id=call_id, tool_name="read_file"),
            raise_handler_errors=True,
        )

    try:
        await asyncio.gather(attach(bus), attach(bus))
        await publish("first")
        await detach(bus)
        await detach(bus)
        assert [json.loads(request.content)["funcId"] for request in telemetry_capture.requests] == ["first", "first"]
        (client,) = telemetry_capture.clients
        assert client.is_closed
        await publish("detached")
        await attach(bus)
        await publish("reattached")
    finally:
        await detach(bus)
    assert [json.loads(request.content)["funcId"] for request in telemetry_capture.requests] == [
        "first",
        "first",
        "reattached",
        "reattached",
    ]
    assert len(telemetry_capture.clients) == 2
    assert all(client.is_closed for client in telemetry_capture.clients)


@pytest.mark.parametrize("times_out", [False, True])
async def test_slow_http_does_not_block_events_and_close_has_a_deadline(
    monkeypatch,
    telemetry_capture,
    times_out,
) -> None:
    from chrys.foundation.events.bus import EventBus
    from chrys.foundation.events.types import InvocationToolCallStart
    from chrys.foundation.models.invocations import InvocationOrigin
    from chrys.orchestration.aixcoding.telemetry import lifecycle
    from chrys.service.aixcoding.telemetry.delivery import TelemetryDelivery

    bus = EventBus()
    entered = asyncio.Event()
    release = asyncio.Event()
    cancelled = asyncio.Event()
    observed = []

    async def slow(request: httpx.Request) -> httpx.Response:
        observed.append(request.url.path.rsplit("/", 1)[-1])
        entered.set()
        try:
            await release.wait()
        except asyncio.CancelledError:
            cancelled.set()
            raise
        return httpx.Response(200)

    client = httpx.AsyncClient(transport=httpx.MockTransport(slow))
    delivery = TelemetryDelivery(
        "https://telemetry.invalid",
        token_provider=lambda: None,
        client=client,
        drain_timeout=0.05 if times_out else 2,
    )
    monkeypatch.setattr(lifecycle, "TelemetryDelivery", lambda *_args, **_kwargs: delivery)
    origin = InvocationOrigin("turn", "slow-session", "turn-one", None)
    event = InvocationToolCallStart(origin=origin, call_id="slow", tool_name="read_file")

    await lifecycle.attach(bus)
    try:
        await asyncio.wait_for(bus.publish(event, raise_handler_errors=True), 1)
        await asyncio.wait_for(entered.wait(), 1)
        assert observed == ["save"]
        assert not release.is_set()
        if not times_out:
            release.set()
        await asyncio.wait_for(lifecycle.detach(bus), 1)
    finally:
        release.set()
        await delivery.aclose()
    assert client.is_closed
    if times_out:
        assert cancelled.is_set()
        assert observed == ["save"]
        assert (delivery.sent, delivery.failed, delivery.dropped) == (0, 0, 2)
    else:
        assert not cancelled.is_set()
        assert observed == ["save", "update"]
        assert (delivery.sent, delivery.failed, delivery.dropped) == (2, 0, 0)
