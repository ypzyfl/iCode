# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Headless CLI queue line: one appended line per queue-position change.

The dedupe lives here so ``app/cli/progress.py`` keeps two case hooks. The
state is per ``TurnProgress`` instance: a new turn resets it, and the gateway
position heartbeat repeating a position must not print twice.

Design: ``aixcoding/docs/batches/model-queue-progress/design.md`` (v1.3 D).
"""

from __future__ import annotations

from typing import Any

from chrys.kernel.aixcoding.queue_progress import queue_note


class QueueLineNote:
    """Dedupes queue positions for one CLI run and renders the appended line."""

    __slots__ = ("_last_position",)

    def __init__(self) -> None:
        self._last_position: int | None = None

    def reset(self) -> None:
        """A new turn started; the same position must print again."""
        self._last_position = None

    def render(self, writer: Any, accent_style: Any, position: int, queue_size: int = 0) -> None:
        """Write one queue line per position change: the heartbeat repeats a position."""
        if position < 0:
            self._last_position = None
            return
        if position == self._last_position:
            return
        self._last_position = position
        writer.line(("• ", accent_style), queue_note(position, queue_size))
