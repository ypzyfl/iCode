# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""ACP queue-status notification: per-session dedupe for ``chrys/queue_status``.

The dedupe and the payload decision live here so ``app/acp/server.py`` keeps a
small hook that still owns the literal ``ext_notification`` call (the upstream
capability pin test scans the server module for the notification literals it
declares). The state is keyed by the server instance (weakly, so closed servers
do not leak entries) and by session within it. A ``TurnStarted`` must reset the
session's entry, or an interrupted queued turn swallows the next turn's first
notification when the position repeats (PR #151 review finding).

Design: ``aixcoding/docs/batches/model-queue-progress/design.md`` (v1.3 C).
"""

from __future__ import annotations

from typing import Any
from weakref import WeakKeyDictionary

_STATES: WeakKeyDictionary[Any, dict[str, int]] = WeakKeyDictionary()
"""Per-server dedupe of the last notified position, keyed by session id."""


def reset_queue_session(server: Any, session_key: str) -> None:
    """Drop the dedupe entry for *session_key*: a new turn began on *server*."""
    states = _STATES.get(server)
    if states is not None:
        states.pop(session_key, None)


def queue_status_payload(server: Any, session_key: str, position: int, queue_size: int) -> dict[str, Any] | None:
    """The ``chrys/queue_status`` payload to send now, or ``None`` to send nothing.

    A negative position is the release: the session's dedupe entry is dropped
    and the release is announced. A repeated position is suppressed — the
    gateway's heartbeat repeats it. The caller confirms a landed position
    notification with :func:`confirm_queue_status`, so a failed send retries.
    """
    states = _STATES.setdefault(server, {})
    if position < 0:
        # The queue let the request through: tell the client once, per session.
        states.pop(session_key, None)
        return {"sessionId": session_key, "released": True}
    if states.get(session_key) == position:
        return None
    return {"sessionId": session_key, "position": position, "queueSize": queue_size}


def confirm_queue_status(server: Any, session_key: str, position: int) -> None:
    """Record a landed position notification: a failed send must retry."""
    states = _STATES.get(server)
    if states is not None and position >= 0:
        states[session_key] = position
