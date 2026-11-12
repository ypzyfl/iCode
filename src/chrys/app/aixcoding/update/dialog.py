# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""The update confirmation dialog (design §3.3).

A normal release offers three answers — update now, remind on the next
launch, skip this version — with Escape and a backdrop click counting as
"remind" (the dialog shows again on the next start).  A
``forceUpgrade`` release offers update now only and cannot be dismissed
any other way (design Q5): the check runs at startup, so there is no
unsaved work to protect.

Text follows the aixcoding TUI house style (``login.py``): plain string
constants, no i18n pipeline.

Design: aixcoding/docs/batches/auto-update/design.md
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual import events, on
from textual.binding import Binding
from textual.containers import VerticalGroup
from textual.widgets import Button, Static

from chrys.app.tui.screens.dialogs.base import BaseDialog
from chrys.app.tui.widgets import DialogButtonRow, DialogButtonSpec
from chrys.service.aixcoding.update.client import AppUpdate

if TYPE_CHECKING:
    from collections.abc import Callable

    from textual.app import ComposeResult

_TITLE = "发现新版本"
_BODY = "更新将关闭当前窗口。\n请确认当前工作是否已保存，如未保存请先保存后再更新。"
_FORCE_BODY = "此版本为强制更新，更新将关闭当前窗口。"
_UPDATE_NOW = "立即更新"
_REMIND_LATER = "下次提醒"
_SKIP_VERSION = "跳过此版本"
_BUTTON_IDS = frozenset({"update-now", "update-later", "update-skip"})

#: Dialog answers: CONFIRM (update now), LATER (remind on the next launch), SKIP (this version).
CONFIRM = "confirm"
LATER = "later"
SKIP = "skip"


class UpdateConfirmDialog(BaseDialog[str]):
    """Ask what to do about ``update``; every dismissal delivers one answer."""

    DEFAULT_CSS = """
    UpdateConfirmDialog {
        align: center middle;
    }
    #update-dialog-container {
        width: 64;
        max-width: 90%;
        height: auto;
        border: round $primary;
        border-title-color: $primary;
        border-title-style: bold;
        background: $surface;
        padding: 1 2;
    }
    #update-dialog-body {
        color: $text-secondary;
        margin-bottom: 1;
        width: auto;
    }
    """

    BINDINGS: ClassVar[list] = [
        # Escape is the dialog's own channel so the force variant can hold it
        # shut (ask_user's noop-pattern); the normal variant answers "later".
        Binding("escape", "answer_escape", show=False, priority=True),
        # Button-to-button keyboard switching rides the ConfirmDialog house
        # pattern (confirm.py): left/right move the focus directly — Tab does
        # not reach the buttons reliably in this TUI.
        Binding("left", "switch_focus('left')", show=False),
        Binding("right", "switch_focus('right')", show=False),
    ]

    def __init__(self, update: AppUpdate, on_result: Callable[[str], None]) -> None:
        super().__init__(dismiss_on_backdrop=not update.force_upgrade)
        self._update = update
        self._on_result = on_result
        self._answered = False

    def compose(self) -> ComposeResult:
        body = _FORCE_BODY if self._update.force_upgrade else _BODY
        with VerticalGroup(id="update-dialog-container") as container:
            container.border_title = f"{_TITLE}: v{self._update.version}"
            yield Static(body, id="update-dialog-body")
            # All buttons rest dark: the primary-variant fill is the *focus*
            # highlight (applied inline on DescendantFocus), so it visibly
            # moves with Tab instead of one button staying accent-filled
            # while another is focused (revision 12, owner feedback).
            buttons = [DialogButtonSpec(_UPDATE_NOW, id="update-now", variant="default")]
            if not self._update.force_upgrade:
                buttons.append(DialogButtonSpec(_REMIND_LATER, id="update-later", variant="default"))
                buttons.append(DialogButtonSpec(_SKIP_VERSION, id="update-skip", variant="default"))
            yield DialogButtonRow(*buttons, id="update-dialog-buttons")

    def on_mount(self) -> None:
        """Start the keyboard on the primary action (AUTO_FOCUS can lose the
        race when the dialog is pushed while the main screen still mounts)."""
        self.query_one("#update-now", Button).focus()

    def _on_descendant_focus(self, event: events.DescendantFocus) -> None:
        """Make the focused button visibly highlighted (design §3.3, revision 12).

        Inline styles are the only channel that wins here: widget-level
        ``DEFAULT_CSS`` loses to the app's ``chrys.tcss`` flat-button rules
        regardless of specificity (verified 2026-11-11), and the app's own
        focus marker for flat buttons is only a 70% label-opacity dim, which
        reads as "Tab does not switch".
        """
        if isinstance(event.widget, Button) and event.widget.id in _BUTTON_IDS:
            # The focused button borrows the whole primary-variant look
            # (theme.py pre-computes fill, border and readable ink for it):
            # the highlight reads as "the 立即更新 style moved here" — the
            # owner's ask — with no bespoke colors to keep in sync.
            variables = self.app.get_css_variables()
            background = variables.get("tui-button-primary-background", "")
            ink = variables.get("tui-button-primary-foreground", "")
            border = variables.get("tui-border-button-primary", background)
            if background:
                event.widget.styles.background = background
                event.widget.styles.border = ("block", border or background)
            if ink:
                event.widget.styles.color = ink

    def _on_descendant_blur(self, event: events.DescendantBlur) -> None:
        """Drop the inline focus override so the CSS defaults take over again."""
        if isinstance(event.widget, Button) and event.widget.id in _BUTTON_IDS:
            event.widget.styles.background = None
            event.widget.styles.border = None
            event.widget.styles.color = None

    def action_switch_focus(self, direction: str = "right") -> None:
        """Move the focus one button left or right, wrapping (ConfirmDialog's house pattern)."""
        buttons = list(self.query(Button))
        if not buttons:
            return
        try:
            index = next(i for i, button in enumerate(buttons) if button.has_focus)
        except StopIteration:
            buttons[0].focus()
            return
        step = -1 if direction == "left" else 1
        buttons[(index + step) % len(buttons)].focus()

    def action_answer_escape(self) -> None:
        """Escape answers "later" — except on a force upgrade, which stays shut."""
        if not self._update.force_upgrade:
            self.dismiss_when_topmost(LATER)

    def _before_dismiss(self, _result: object | None = None) -> None:
        """Deliver the answer exactly once, on every dismissal path (design §3.3).

        ``BaseDialog.dismiss`` funnels backdrop clicks and button presses
        through here, so a None result (an untaken path) still counts as
        "later" — the dialog never leaves the flow without an answer.
        """
        if self._answered:
            return
        self._answered = True
        answer = _result if isinstance(_result, str) else LATER
        self._on_result(answer)

    @on(Button.Pressed, "#update-now")
    def _confirm(self) -> None:
        self.dismiss_when_topmost(CONFIRM)

    @on(Button.Pressed, "#update-later")
    def _later(self) -> None:
        self.dismiss_when_topmost(LATER)

    @on(Button.Pressed, "#update-skip")
    def _skip(self) -> None:
        self.dismiss_when_topmost(SKIP)
