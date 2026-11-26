# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""The waiting row's cancel affordance: leave the gateway queue by giving up the turn.

A queued request is never admitted once it leaves the queue, so cancelling the
wait ends the turn: the button floats over the waiting row's note line and asks
the main screen to interrupt — the same path ``Escape`` takes. The interrupt
closes the stream, and the close leaves the gateway queue through the client
batch's cancel call, so the click needs no channel of its own. It posts
:class:`QueueCancelRequested`, which bubbles from the waiting row through the
chat panel to the main screen.

Text lives here as a Chinese-only constant by design (ADR-0010): queue prose is
customization-facing and never enters the i18n catalogs.

Design: ``aixcoding/docs/batches/model-queue-progress/design.md`` (v1.8).
"""

from __future__ import annotations

from typing import Final

from textual.content import Content
from textual.message import Message

from chrys.app.tui.widgets.click_affordance import ClickAffordance

QUEUE_CANCEL_LABEL: Final = "取消排队"
"""The affordance's label, shown beside the queue note."""

QUEUE_CANCELLED_NOTICE: Final = "用户已取消排队"
"""What the main screen toasts once the cancel is on its way (owner ruling, 2026-11-26)."""


class QueueCancelRequested(Message):
    """The user clicked the waiting row's cancel-queue affordance."""


class QueueCancelButton(ClickAffordance):
    """A one-row pseudo-button floated over the waiting row's note line."""

    # It floats over the row the transcript's next entry takes; it must never join selections.
    ALLOW_SELECT = False

    CLICK_MESSAGE = QueueCancelRequested

    DEFAULT_CSS = """
    QueueCancelButton {
        position: absolute;
        bottom: 0;
        right: 1;
        height: 1;
        width: auto;
        min-width: 10;
        padding: 0 1;
        background: $foreground 8%;
        color: $text-muted;
        content-align: center middle;
        pointer: pointer;
    }
    QueueCancelButton:hover {
        background: $foreground 15%;
        color: $accent;
    }
    """

    def __init__(self) -> None:
        super().__init__(Content.from_text(QUEUE_CANCEL_LABEL, markup=False))
        # Hidden beside the bare dot; ``WaitingRow.set_queue_note`` shows it with a note.
        self.display = False
