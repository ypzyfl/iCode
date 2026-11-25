# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Status copy and event plumbing for a gateway queue position, shared by every frontend.

Customization-facing prose stays a plain Chinese constant rather than an i18n
catalog entry (ADR-0010). The TUI and the CLI render it; the ACP path forwards
only the raw position, so a client draws its own text. The session-scoped
``GatewayQueueStatus`` event and its bus publisher live here too: the event
subclasses the foundation ``Event`` (a legal kernel-tier dependency), and the
event declaration guard only constrains classes defined in
``foundation/events/types.py``.

Design: ``aixcoding/docs/batches/model-queue-progress/design.md``.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from chrys.foundation.events.types import Event


def queue_note(position: int, queue_size: int = 0) -> str:
    """The status text for *position* requests ahead among *queue_size* waiting.

    ``position == 0`` means this request is next, not that it holds a slot: the
    gateway admits it only when a concurrency slot frees, and ``max_wait_time``
    can still expire first (``QUEUE_TIMEOUT``). The note therefore never claims
    the model resource. A negative position means the queue released it (no note
    at all). ``queue_size`` is still accepted so the frontends keep one call
    shape, but the copy speaks about the position only: the total queue length
    is not shown.

    Kept on one line on purpose: the TUI renders it beside the waiting dot, and
    the CLI writes it as a single appended line.
    """
    if position < 0:
        return ""
    if position == 0:
        # Still queued: only the first data chunk proves the queue released it.
        return "已排到队首，当前为队列第一位"  # noqa: RUF001
    # The full-width comma is the wording the owner asked for; the exemption stays line-level.
    return f"当前模型请求量大，请求排队约 {position} 人"  # noqa: RUF001


@dataclass
class GatewayQueueStatus(Event):
    """The gateway queued the request; ``position`` counts the requests ahead of it.

    Session-scoped by design: a queued request has no invocation identity when
    the client that will send it is built, so this carries the envelope's
    session id rather than an :class:`chrys.foundation.events.types.InvocationOrigin`.
    ``request_id`` names the queued request (the per-attempt
    ``Chrys-Request-Attempt-Id``, filled by the tracker); ``None`` when no
    tracker armed the request (design v1.4).
    """

    position: int = 0
    queue_size: int = 0
    request_id: str | None = None


def make_queue_status_publisher(bus: Any, session_id: str | None) -> Callable[[Any], Awaitable[None]]:
    """Build the wire callback that republishes queue positions on the session's event bus.

    *status* is the queue package's ``QueueStatus``; reading its fields keeps
    this module decoupled from the service tier. ``bus`` is duck-typed on
    ``publish`` only, so the factory stays importable from the lowest tier.
    """

    async def publish(status: Any) -> None:
        await bus.publish(
            GatewayQueueStatus(
                session_id=session_id,
                position=status.position,
                queue_size=status.queue_size,
                request_id=status.request_id,
            )
        )

    return publish
