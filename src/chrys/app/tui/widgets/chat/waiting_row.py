# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""The dot a running turn shows breathing where its next row will appear, while nothing in it moves.

Between what the turn shows, the model may be thinking where it cannot be read, writing a tool call's arguments,
or not answering yet: the transcript would sit still with no sign the turn goes on. The row says it does, with no
words, as nothing tells which of these it is.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, ClassVar

from rich.text import Text
from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget

# AIxCoding queue-progress: waiting row cancel button (floated over the queue note's line)
from chrys.app.aixcoding.tui.queue_cancel_button import QueueCancelButton, pin_queue_cancel_button
from chrys.app.tui.util.shimmer import FRAME_SECONDS, breathing_dot
from chrys.app.tui.widgets.chat.compaction_card import CompactionCard
from chrys.app.tui.widgets.chat.context_fold import ContextFoldWidget
from chrys.app.tui.widgets.chat.fold_gap import FOLD_GAP_ROWS, FoldGap
from chrys.app.tui.widgets.chat.messages import AgentMessage, SystemMessage, ThinkingMessage, UserMessage
from chrys.app.tui.widgets.chat.tool_call import ToolGroup
from chrys.app.tui.widgets.loading import GatedAnimation

if TYPE_CHECKING:
    from textual._arrange import DockArrangeResult
    from textual.geometry import Size


class QueueNoteChanged(Message):
    """The queue note came or went; the chat panel owns whether the row then shows."""


class WaitingRow(GatedAnimation, FoldGap, Widget):
    """A dot that grows and brightens, then shrinks and dims, at the turn's fold arrow column, under its guide.

    It stays in the chat panel under the transcript, hidden until a running turn waits: transcript entries mount
    above it, so new output takes its place as it hides. Not part of the transcript, it is never selected or copied.
    Below a folded row it keeps the gap the next fold row would, so the dot is where that row's arrow appears.
    """

    ALLOW_SELECT = False

    # AIxCoding queue-progress: waiting row note
    _queue_note: str = ""
    """Shown beside the dot while the gateway queues this turn; empty otherwise."""

    COMPONENT_CLASSES: ClassVar[set[str]] = {"waitingrow--lit"}

    DEFAULT_CSS = """
    WaitingRow {
        height: auto;
        padding: 0 1;
        border-left: solid $tui-border-neutral-gray $border-opacity;
        color: $text-muted;
    }
    /* What the dot brightens to at its largest. */
    WaitingRow > .waitingrow--lit {
        color: $text;
        text-style: not bold;
    }
    """

    def on_mount(self) -> None:
        self.auto_refresh = FRAME_SECONDS

    def takes_fold_gap(self) -> bool:
        return True

    def get_content_height(self, container: Size, viewport: Size, width: int) -> int:
        # Not the rendered text's, which Textual keeps per width: the gap comes and goes at any width.
        return 1 + (FOLD_GAP_ROWS if self.gap_above else 0)

    def _size_updated(self, size: Size, virtual_size: Size, container_size: Size, layout: bool = True) -> bool:
        # The layout calling this placed it already, and it shows no scrollbar: Textual's reactive virtual size would
        # lay the whole transcript out again as its gap comes and goes.
        return super()._size_updated(size, virtual_size, container_size, layout=False)

    # AIxCoding queue-progress: waiting row cancel button (floated over the note line)
    _cancel_button: QueueCancelButton | None = None
    """The affordance over the note line; ``compose`` sets it, ``None`` before the row mounts."""

    def compose(self) -> ComposeResult:
        self._cancel_button = QueueCancelButton()
        yield self._cancel_button

    def arrange(self, size: Size, optimal: bool = False) -> DockArrangeResult:
        """Pin the cancel affordance to the note line's right edge, out of the row's flow."""
        result = super().arrange(size, optimal=optimal)
        pin_queue_cancel_button(result, self._cancel_button, size)
        return result

    @property
    def queue_note(self) -> str:
        """The queue note beside the dot; empty when the turn is not queued."""
        return self._queue_note

    def set_queue_note(self, note: str) -> None:
        """Show *note* beside the dot; an empty note restores the bare dot.

        The note shares the dot's line, so it never changes the row's height,
        and the cancel affordance comes with it: floated in place, it takes no
        flow space of its own.
        """
        if note == self._queue_note:
            return
        self._queue_note = note
        if self._cancel_button is not None:
            self._cancel_button.display = bool(note)
        self.refresh()
        # The note changes outside any transcript move the panel already syncs on, so it hears.
        self.post_message(QueueNoteChanged())

    def render(self) -> Text:
        if self.app.animation_level == "none":
            dot = breathing_dot(None, None, 0.0)
        else:
            lit = self.text_style_of("waitingrow--lit")
            dot = breathing_dot(self.rich_style.color, lit.color, time.monotonic())
        line = Text.assemble(dot, f"  {self._queue_note}") if self._queue_note else dot
        return Text.assemble(self.gap_text(), "\n", line) if self.gap_above else line


def waits_after(entry: Widget | None) -> bool:
    """Whether a running turn whose last transcript entry is *entry* waits with nothing on screen moving.

    It does after its prompt, complete thinking or text between tool calls, a compaction that ended, and notices.
    Streaming text, a folded thinking row showing progress, an answer that may be the last, and a tool group whose
    title still runs show it is moving; errors, retries and interruptions say why it waits themselves.
    """
    if isinstance(entry, (UserMessage, SystemMessage, ContextFoldWidget)):
        return True
    if isinstance(entry, (ThinkingMessage, AgentMessage)):
        # Complete thinking, and complete text between tool calls; never an answer, which may end the turn.
        return entry.foldable
    if isinstance(entry, ToolGroup):
        return not entry.shows_running
    if isinstance(entry, CompactionCard):
        return entry.status != "running"
    return False
