# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Own the enterprise subscriptions for one engine event bus."""

from __future__ import annotations

from typing import TYPE_CHECKING
from weakref import WeakKeyDictionary

from chrys.foundation.events.types import (
    ApprovalCancelled,
    ApprovalModeUpdated,
    ApprovalRequest,
    ApprovalResponse,
    InvocationToolCallResult,
    InvocationToolCallStart,
    SessionReady,
)
from chrys.service.aixcoding.telemetry.context import forget_session_sources, load_settings, telemetry_token
from chrys.service.aixcoding.telemetry.delivery import TelemetryDelivery
from chrys.service.aixcoding.telemetry.events import TelemetryEvents

if TYPE_CHECKING:
    from chrys.foundation.events.bus import EventBus

_buses: WeakKeyDictionary[EventBus, TelemetryEvents] = WeakKeyDictionary()


def _handlers(events: TelemetryEvents):
    return (
        (SessionReady, events.session_ready),
        (ApprovalModeUpdated, events.mode_changed),
        (ApprovalRequest, events.approval_requested),
        (ApprovalResponse, events.approval_answered),
        (ApprovalCancelled, events.approval_cancelled),
        (InvocationToolCallStart, events.tool_start),
        (InvocationToolCallResult, events.tool_result),
    )


async def attach(bus: EventBus) -> None:
    if bus in _buses:
        return
    settings = load_settings()
    if not settings.enabled:
        return
    events = TelemetryEvents(
        TelemetryDelivery(settings.base_url, token_provider=lambda: telemetry_token(settings)), settings
    )
    _buses[bus] = events
    try:
        for event_type, handler in _handlers(events):
            await bus.subscribe(event_type, handler)
    except Exception:
        await detach(bus)
        raise


async def detach(bus: EventBus) -> None:
    if (events := _buses.pop(bus, None)) is None:
        return
    try:
        for event_type, handler in _handlers(events):
            await bus.unsubscribe(event_type, handler)
    finally:
        if events.session_id:
            forget_session_sources(events.session_id)
        events.unregister()
        await events.delivery.aclose()
