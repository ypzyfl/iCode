# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Bind an explicit invocation and pass for telemetry consumers."""

from __future__ import annotations

import logging
from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from chrys.foundation.models.invocations import InvocationOrigin

logger = logging.getLogger("aixcoding.detail.telemetry")


@dataclass(frozen=True, slots=True)
class PassScope:
    origin: InvocationOrigin
    pass_id: str


_current_pass: ContextVar[PassScope | None] = ContextVar("aixcoding_telemetry_pass", default=None)


def current_pass() -> PassScope | None:
    return _current_pass.get()


def bind_pass(origin: InvocationOrigin, pass_id: str) -> Callable[[], None]:
    token = _current_pass.set(PassScope(origin, pass_id))

    def reset() -> None:
        try:
            _current_pass.reset(token)
        except RuntimeError, ValueError:
            logger.debug("Telemetry pass scope was already reset or belongs to another context.")

    return reset
