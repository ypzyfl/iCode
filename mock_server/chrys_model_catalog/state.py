# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Runtime state and the fault switch.

The counterpart of the reference mock's ``helpers/sessionExpired.js``: one
module owns the mutable switch, exposes a setter used by the control endpoint,
and reports its own snapshot. The extra piece here is ``revision``, because the
catalog carries a ``version`` — bumping it is what makes the client treat the
next response as new.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mock_server.chrys_model_catalog.modes import DEFAULT_DELAY, MODES


class UnknownModeError(ValueError):
    """Raised when a control request asks for a mode that does not exist."""


@dataclass
class CatalogMockState:
    """Mode, revision and counters for one running mock."""

    mode: str = "ok"
    delay: float = DEFAULT_DELAY
    revision: int = 1
    requests: int = 0
    #: Version pinned while in ``stale`` mode, so polling sees no new version.
    stale_version: str = field(default="")

    def __post_init__(self) -> None:
        if self.mode not in MODES:
            raise UnknownModeError(f"unknown mode {self.mode!r}; expected one of {', '.join(MODES)}")
        if self.mode == "stale":
            self.stale_version = f"mock-{self.revision}"

    @property
    def version(self) -> str:
        """Version served right now; ``stale`` keeps repeating one value."""
        return self.stale_version if self.mode == "stale" else f"mock-{self.revision}"

    def set_mode(self, mode: str, delay: float | None = None) -> None:
        """Switch mode at runtime; every switch is a new revision."""
        if mode not in MODES:
            raise UnknownModeError(f"unknown mode {mode!r}; expected one of {', '.join(MODES)}")
        self.mode = mode
        if delay is not None:
            self.delay = float(delay)
        self.revision += 1
        if mode == "stale":
            self.stale_version = f"mock-{self.revision}"

    def snapshot(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "revision": self.revision,
            "version": self.version,
            "requests": self.requests,
            "delay": self.delay,
        }
