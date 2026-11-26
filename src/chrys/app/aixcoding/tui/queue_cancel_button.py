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

from typing import TYPE_CHECKING, Final

from textual.content import Content
from textual.geometry import Region, Size
from textual.message import Message

from chrys.app.tui.util.placement import pin_fixed_placement
from chrys.app.tui.widgets.click_affordance import ClickAffordance

if TYPE_CHECKING:
    from textual._arrange import DockArrangeResult

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

    # Textual has no ``right``/``bottom`` CSS: ``position: absolute`` only keeps
    # the button out of the row's flow, and the row's arrange pins its region to
    # the note line's right edge (``pin_queue_cancel_button``).
    DEFAULT_CSS = """
    QueueCancelButton {
        position: absolute;
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


def pin_queue_cancel_button(result: DockArrangeResult, button: QueueCancelButton | None, size: Size) -> None:
    """Show *button* on the row's trailing line, right-aligned, whatever the row's height.

    The row's last content line is the dot's, where the queue note sits; the row
    is one line tall, or two under a fold gap. Runs on every arrange, so it
    leaves an already-pinned placement untouched (``pin_fixed_placement``).
    """
    if button is None:
        return

    def trailing_line(arranged: Region) -> Region:
        width = min(max(1, arranged.width), max(1, size.width))
        height = min(max(1, arranged.height), max(1, size.height))
        return Region(max(0, size.width - width), max(0, size.height - height), width, height)

    pin_fixed_placement(result, button, trailing_line)
