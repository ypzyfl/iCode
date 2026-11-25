# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Public HTTP interception values and trajectory-derived call context."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from chrys.foundation.trajectory.context import TrajectoryContext

if TYPE_CHECKING:
    from collections.abc import Mapping

    import httpx

    from chrys.foundation.trajectory.envelope import Actor


@dataclass(frozen=True, slots=True)
class HttpChange:
    """Replace the complete headers mapping and/or raw body bytes."""

    headers: Mapping[str, str] | None = None
    body: bytes | None = None


@dataclass(frozen=True, slots=True)
class Block:
    """Deliberately terminate the current model call with a detail-only reason."""

    reason: str


@dataclass(frozen=True, slots=True)
class HttpCallContext:
    """Stable HTTP call identity; missing trajectory fields stay missing."""

    session_id: str | None
    turn_id: str | None
    cycle_operation_id: str | None
    exchange_operation_id: str | None
    request_attempt_id: str | None
    actor: Actor | None
    provider: str
    model: str

    @classmethod
    def from_request(cls, request: httpx.Request, *, provider: str, model: str) -> HttpCallContext:
        from chrys.service.llm.request_tracking import _CONTEXT_EXTENSION, REQUEST_ATTEMPT_ID_EXTENSION

        trajectory = request.extensions.get(_CONTEXT_EXTENSION)
        if not isinstance(trajectory, TrajectoryContext):
            trajectory = None
        attempt_id = request.extensions.get(REQUEST_ATTEMPT_ID_EXTENSION)
        return cls(
            session_id=trajectory.session_id if trajectory is not None else None,
            turn_id=trajectory.turn_id if trajectory is not None else None,
            cycle_operation_id=trajectory.cycle_operation_id if trajectory is not None else None,
            exchange_operation_id=trajectory.exchange_operation_id if trajectory is not None else None,
            request_attempt_id=attempt_id if isinstance(attempt_id, str) else None,
            actor=trajectory.actor if trajectory is not None else None,
            provider=provider,
            model=model,
        )
