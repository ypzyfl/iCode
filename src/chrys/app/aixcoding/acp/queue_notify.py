# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""ACP queue-status notification: per-session dedupe for ``chrys/queue_status``.

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
review finding). ``requestId`` names the queued request (D1: the release
carries it too) and is omitted from both payloads when unknown.

Design: ``aixcoding/docs/batches/model-queue-progress/design.md`` (v1.3 C, v1.4).
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


def queue_status_payload(
    server: Any, session_key: str, position: int, queue_size: int, request_id: str | None = None
) -> dict[str, Any] | None:
    """The ``chrys/queue_status`` payload to send now, or ``None`` to send nothing.

    A negative position is the release: the session's dedupe entry is dropped
    and the release is announced. A repeated ``(request_id, position)`` pair is
    suppressed — the gateway's heartbeat repeats a position, and a new request
    on the same position is a fresh fact. ``request_id`` is omitted when
    unknown (no tracker armed the request). The caller confirms a landed
    position notification with :func:`confirm_queue_status`, so a failed send
    retries.
    """
    states = _STATES.setdefault(server, {})
    if position < 0:
        # The queue let the request through: tell the client once, per session.
        states.pop(session_key, None)
        payload: dict[str, Any] = {"sessionId": session_key}
        if request_id:
            payload["requestId"] = request_id
        payload["released"] = True
        return payload
    if states.get(session_key) == (request_id, position):
        return None
    payload = {"sessionId": session_key}
    if request_id:
        payload["requestId"] = request_id
    payload["position"] = position
    payload["queueSize"] = queue_size
    return payload


def confirm_queue_status(server: Any, session_key: str, position: int, request_id: str | None = None) -> None:
    """Record a landed position notification: a failed send must retry."""
    states = _STATES.get(server)
    if states is not None and position >= 0:
        states[session_key] = (request_id, position)
