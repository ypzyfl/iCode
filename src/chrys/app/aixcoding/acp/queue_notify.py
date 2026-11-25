# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""ACP queue-status notification: per-session dedupe for ``queue_status``.

The dedupe and the payload decision live here so ``app/acp/server.py`` keeps a
small hook that still owns the literal ``ext_notification`` call (the upstream
capability pin test scans the server module for the notification literals it
declares). The state is keyed by the server instance (weakly, so closed servers
do not leak entries) and by session within it; within a session a
``(request_id, position)`` pair is announced once — the gateway's heartbeat
repeats a position, while a *new* request landing on the same position must be
announced, because its id is now the live one (design v1.4 D2). A
``TurnStarted`` must reset the session's entry, or an interrupted queued turn
swallows the next turn's first notification when the position repeats (PR #151
review finding). Three frame shapes share one method (design v1.5/v1.6): the
phase booleans ``released``/``rejected`` ride every frame, ``requestId`` is
omitted when unknown, and a rejection (``reason``/``message``/``traceId``) is
terminal — it passes once and is not deduped. On the wire the method name is
``_queue_status``: the Python ACP SDK prepends the underscore.

Design: ``aixcoding/docs/batches/model-queue-progress/design.md`` (v1.3 C, v1.4 to v1.6).
"""

from __future__ import annotations

from typing import Any
from weakref import WeakKeyDictionary

_STATES: WeakKeyDictionary[Any, dict[str, tuple[str | None, int]]] = WeakKeyDictionary()
"""Per-server dedupe of the last notified (request_id, position), keyed by session id."""


def reset_queue_session(server: Any, session_key: str) -> None:
    """Drop the dedupe entry for *session_key*: a new turn began on *server*."""
    states = _STATES.get(server)
    if states is not None:
        states.pop(session_key, None)


def queue_status_payload(server: Any, session_key: str, event: Any) -> dict[str, Any] | None:
    """The ``queue_status`` payload to send now, or ``None`` to send nothing.

    *event* is the kernel ``GatewayQueueStatus`` (read duck-typed, so this
    module stays decoupled from the kernel tier). A rejection is terminal and
    announced once — it also ends any queued view, so the session's dedupe
    entry is dropped. A negative position is the release: same drop, announced
    once. Otherwise a repeated ``(request_id, position)`` pair is suppressed —
    the gateway's heartbeat repeats a position, and a new request on the same
    position is a fresh fact. ``requestId`` is omitted when unknown (no tracker
    armed the request). The caller confirms a landed position notification with
    :func:`confirm_queue_status`, so a failed send retries.
    """
    states = _STATES.setdefault(server, {})
    if event.rejected is not None:
        # The queue finally refused this turn: pass it through, undeduped.
        states.pop(session_key, None)
        payload: dict[str, Any] = {"sessionId": session_key}
        if event.request_id:
            payload["requestId"] = event.request_id
        payload["released"] = False
        payload["rejected"] = True
        payload["reason"] = event.rejected
        if event.reject_message:
            payload["message"] = event.reject_message
        if event.trace_id:
            payload["traceId"] = event.trace_id
        return payload
    if event.position < 0:
        # The queue let the request through: tell the client once, per session.
        states.pop(session_key, None)
        payload = {"sessionId": session_key}
        if event.request_id:
            payload["requestId"] = event.request_id
        payload["released"] = True
        payload["rejected"] = False
        return payload
    if states.get(session_key) == (event.request_id, event.position):
        return None
    payload = {"sessionId": session_key}
    if event.request_id:
        payload["requestId"] = event.request_id
    payload["released"] = False
    payload["rejected"] = False
    payload["position"] = event.position
    payload["queueSize"] = event.queue_size
    return payload


def confirm_queue_status(server: Any, session_key: str, event: Any) -> None:
    """Record a landed position notification: a failed send must retry."""
    states = _STATES.get(server)
    if states is not None and event.position >= 0 and event.rejected is None:
        states[session_key] = (event.request_id, event.position)
