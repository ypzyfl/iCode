# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Reusable app header widget with app title and optional subtitle."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.cells import cell_len
from textual.content import Content
from textual.css.scalar import Scalar
from textual.events import Click
from textual.geometry import Spacing
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from chrys.app.tui.i18n import render_str
from chrys.app.tui.util.spinner import SPINNER_FRAMES
from chrys.app.tui.util.visibility import (
    is_widget_shown_on_active_screen,
    resync_compositor_regions,
    set_widget_visibility_without_layout,
)
from chrys.app.tui.widgets.selection import NonSelectableStatic
from chrys.app.tui.widgets.workflow import text as workflow_text
from chrys.foundation.branding import format_app_version_title
from chrys.foundation.i18n import MessageRef, msg
from chrys.foundation.i18n.formatting import format_message
from chrys.service.approval.policy import ApprovalMode

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.timer import Timer

    from chrys.app.aixcoding.tui.login_indicator import LoginIndicatorState
    from chrys.app.tui.i18n import LocaleController
    from chrys.foundation.i18n import Localizer

_APPROVAL_BADGE = msg(
    "tui.chrome.approval_mode.badge",
    fallback=" APPROVAL MODE: {mode} ",
)
_APPROVAL_MODE_MANUAL = msg("tui.chrome.approval_mode.manual", fallback="MANUAL")
_APPROVAL_MODE_AUTO = msg("tui.chrome.approval_mode.auto", fallback="AUTO")
_APPROVAL_MODE_BYPASS = msg("tui.chrome.approval_mode.bypass", fallback="BYPASS")
_APPROVAL_REVIEWING = msg("tui.chrome.approval_mode.reviewing", fallback="Reviewing")
_REVIEW_SPIN_SECONDS = 0.12

_APPROVAL_CLASSES = {
    ApprovalMode.MANUAL: "approval-manual",
    ApprovalMode.AUTO: "approval-auto",
    ApprovalMode.BYPASS: "approval-bypass",
}

APPROVAL_MODE_MESSAGES = {
    ApprovalMode.MANUAL: _APPROVAL_MODE_MANUAL,
    ApprovalMode.AUTO: _APPROVAL_MODE_AUTO,
    ApprovalMode.BYPASS: _APPROVAL_MODE_BYPASS,
}


class _HeaderBadge(NonSelectableStatic):
    """Clickable header chip excluded from drag selection and copy."""


class AppHeader(Widget):
    """Top-of-screen header bar showing the application title and optional subtitle.

    Uses a horizontal layout with a centered title (``1fr``) and a
    right-aligned approval mode badge when enabled.

    Usage::

        header = AppHeader()
        yield header

        # Later, update with profile/model info:
        header.set_subtitle("Code Agent", "claude-sonnet-4-6")
    """

    class ApprovalBadgeClicked(Message):
        """Posted when the approval mode badge is clicked."""

    class ModeClicked(Message):
        """Switch between chat and workflow presentation."""

    ALLOW_SELECT = False

    subtitle_parts: reactive[tuple[str, ...]] = reactive(())
    approval_mode: reactive[ApprovalMode] = reactive(ApprovalMode.MANUAL)

    def __init__(
        self,
        *,
        show_approval_badge: bool = True,
        show_login_badge: bool = True,  # AIxCoding tui: account badge toggle
        show_mode_badge: bool = False,
        locale_controller: LocaleController | None = None,
    ) -> None:
        super().__init__(id="app-header")
        self._show_approval_badge = show_approval_badge
        self._show_login_badge = show_login_badge
        self._show_mode_badge = show_mode_badge
        self._workflow_mode = False
        self._login_state: LoginIndicatorState | None = None
        self._locale_controller = locale_controller
        self._auto_review_count = 0
        self._review_frame = 0
        self._review_timer: Timer | None = None

    def compose(self) -> ComposeResult:
        yield Static(id="header-title")
        if self._show_mode_badge:
            yield _HeaderBadge(self._mode_content(), id="mode-badge")
        if self._show_approval_badge:
            yield NonSelectableStatic(id="approval-reviewing")
            yield _HeaderBadge(id="approval-badge")
        if self._show_login_badge:
            # AIxCoding tui: account badge -- a third overlay-docked sibling kept
            # left of the approval badge by the dynamic margin in
            # ``_refresh_login_badge`` (same pattern as ``#approval-reviewing``).
            login_badge = _HeaderBadge(id="login-badge")
            login_badge.display = False  # hidden until a login state is pushed
            yield login_badge

    def on_mount(self) -> None:
        if self._locale_controller is not None:
            self._locale_controller.register_surface(self)
        self._refresh_title()
        self._refresh_mode()
        self._refresh_login_badge()  # AIxCoding tui: initial badge paint
        if self._show_approval_badge:
            self._review_timer = self.set_interval(_REVIEW_SPIN_SECONDS, self._spin_review, pause=True)
            self._refresh_approval_badge(self.approval_mode)

    def on_unmount(self) -> None:
        if self._locale_controller is not None:
            self._locale_controller.unregister_surface(self)

    def refresh_localization(self) -> None:
        """Retranslate the approval badge without rebuilding the header."""
        self._refresh_mode()
        if self.is_mounted and self._show_approval_badge:
            self._refresh_approval_badge(self.approval_mode)

    def watch_subtitle_parts(self, _parts: tuple[str, ...]) -> None:
        if self.is_mounted:
            self._refresh_title()

    def watch_approval_mode(self, mode: ApprovalMode) -> None:
        if self.is_mounted:
            self._refresh_approval_badge(mode)

    def _refresh_title(self) -> None:
        """Rebuild the title text from the current subtitle parts."""
        from chrys import __version__

        title = Content(format_app_version_title(__version__))
        if self.subtitle_parts:
            sub_text = " \u2502 ".join(self.subtitle_parts)
            content = Content.assemble(title, (" \u2014 ", "dim"), Content(sub_text).stylize("dim"))
        else:
            content = title
        self.query_one("#header-title", Static).update(content)

    def set_auto_review_count(self, count: int) -> None:
        """Track the calls the approval judge is reviewing; the label left of the badge shows while any are."""
        if count == self._auto_review_count:
            return
        self._auto_review_count = count
        if self.is_mounted and self._show_approval_badge:
            self._refresh_review_count()

    def _refresh_approval_badge(self, mode: ApprovalMode) -> None:
        """Refresh the approval mode badge and the review count beside it.

        Neither ever relayouts the screen (``width: auto`` would lay out the
        whole transcript again): both widths are pinned to their text and only
        the header is remapped.
        """
        if not self._show_approval_badge:
            return
        badge = self.query_one("#approval-badge", Static)
        mode_text = self._render_message(APPROVAL_MODE_MESSAGES[mode].bind())
        badge_text = self._render_message(_APPROVAL_BADGE.bind(mode=mode_text))
        badge.update(Content.from_text(badge_text, markup=False), layout=False)
        # Swap CSS class for color
        for mode_key, cls in _APPROVAL_CLASSES.items():
            badge.set_class(mode_key == mode, cls)
        moved = badge.styles.set_rule("width", Scalar.from_number(cell_len(badge_text)))
        if self._show_login_badge:  # AIxCoding tui: keep the account badge left of ours
            login_badge = self.query_one("#login-badge", Static)
            moved = self._place_login_badge(login_badge) or moved
        if moved:
            self._clear_arrangement_cache()
            if not self._refresh_review_count():
                resync_compositor_regions(self)
        else:
            self._refresh_review_count()

    def _refresh_review_count(self) -> bool:
        """Place, size, show or hide the review count; return whether the header was remapped.

        It docks right like the badge, kept left of it by a right margin, and
        changes between turns' calls: its geometry is written as raw rules and
        only the header is remapped. Its timer spins only while it shows.
        """
        indicator = self.query_one("#approval-reviewing", Static)
        badge = self.query_one("#approval-badge", Static)
        count = self._auto_review_count
        moved = False
        if count:
            text = self._review_text()
            indicator.update(Content.from_text(text, markup=False), layout=False)
            moved = indicator.styles.set_rule("width", Scalar.from_number(cell_len(text)))
        badge_width = badge.styles.width
        right = badge.styles.margin.right + (int(badge_width.value) if badge_width is not None else 0)
        moved = indicator.styles.set_rule("margin", Spacing(0, right, 0, 0)) or moved
        if moved:
            self._clear_arrangement_cache()
        remapped = set_widget_visibility_without_layout(indicator, count > 0)
        if moved and not remapped:
            resync_compositor_regions(self)
            remapped = True
        timer = self._review_timer
        if timer is not None:
            if count:
                timer.resume()
            else:
                timer.pause()
        return remapped

    def _review_text(self) -> str:
        """The spinner frame and review label, padded on both sides.

        The padding keeps the centred title from showing next to the label or
        between it and the badge in a narrow window.
        """
        reviewing = self._render_message(_APPROVAL_REVIEWING.bind())
        return f" {SPINNER_FRAMES[self._review_frame]} {reviewing} "

    def _spin_review(self) -> None:
        """Advance the spinner: a repaint at a fixed width, only where it can be seen."""
        if not self._auto_review_count:
            return
        self._review_frame = (self._review_frame + 1) % len(SPINNER_FRAMES)
        indicator = self.query_one("#approval-reviewing", Static)
        if is_widget_shown_on_active_screen(indicator):
            indicator.update(Content.from_text(self._review_text(), markup=False), layout=False)

    def set_login_indicator(self, state: LoginIndicatorState) -> None:
        """Update the account badge (``None`` hides it) and repaint.

        AIxCoding tui: the state itself is computed in the aixcoding package;
        the header only holds and repaints it.
        """
        self._login_state = state
        self._refresh_login_badge()

    def _refresh_login_badge(self) -> None:
        """Repaint the account badge from the stored indicator state.

        AIxCoding tui: an overlay-docked sibling left of the approval badge,
        anchored by a dynamic right margin (the approval badge's width plus its
        margin) -- the same pattern ``_refresh_review_count`` uses for the
        reviewing label. Repaints are pinned-width (``layout=False``).
        """
        if not self._show_login_badge or not self.is_mounted:
            return
        badge = self.query_one("#login-badge", Static)
        state = self._login_state
        if state is None:
            if badge.display:
                badge.display = False
            return
        badge.display = True
        badge.set_class(not state.logged_in, "-logged-out")
        badge_text = f"\u25cf {state.label}"
        badge.update(Content.from_text(badge_text, markup=False), layout=False)
        badge.tooltip = Content.from_text(state.tooltip, markup=False) if state.tooltip else None
        moved = badge.styles.set_rule("width", Scalar.from_number(cell_len(badge_text)))
        moved = self._place_login_badge(badge) or moved
        if moved:
            self._clear_arrangement_cache()
            if not self._refresh_review_count():
                resync_compositor_regions(self)

    def _place_login_badge(self, badge: Static) -> bool:
        """Pin the account badge's right margin to the approval badge's left edge."""
        approval = self.query("#approval-badge")
        approval_width = approval[0].styles.width if approval else None
        right = 1  # the approval badge's own margin-right
        right += int(approval_width.value) if approval_width is not None else 0
        right += 1  # one gutter column between the two badges
        return badge.styles.set_rule("margin", Spacing(0, right, 0, 0))

    def _localizer(self) -> Localizer | None:
        controller = self._locale_controller
        if controller is None:
            return None
        return controller.localizer

    def _render_message(self, reference: MessageRef) -> str:
        localizer = self._localizer()
        if localizer is None:
            return format_message(reference)
        return render_str(localizer, reference)

    def on_click(self, event: Click) -> None:
        """Open approval mode picker when the badge is clicked."""
        if self._show_mode_badge and self.query_one("#mode-badge").region.contains(event.screen_x, event.screen_y):
            event.prevent_default()
            event.stop()
            self.post_message(self.ModeClicked())
            return
        if not self._show_approval_badge:
            return
        badge = self.query_one("#approval-badge", Static)
        if badge.region.contains(event.screen_x, event.screen_y):
            event.prevent_default()
            event.stop()
            self.post_message(self.ApprovalBadgeClicked())

    def set_subtitle(self, *parts: str) -> None:
        """Set subtitle parts (e.g. profile name, model id) and refresh."""
        self.subtitle_parts = tuple(p for p in parts if p)

    def set_workflow_mode(self, workflow: bool) -> None:
        if workflow == self._workflow_mode:
            return
        self._workflow_mode = workflow
        self._refresh_mode()

    def _mode_content(self) -> Content:
        reference = workflow_text.MODE_WORKFLOW if self._workflow_mode else workflow_text.MODE_CHAT
        label = self._render_message(reference.bind())
        badge = self._render_message(workflow_text.MODE_BADGE.bind(mode=label))
        return Content.from_text(badge, markup=False)

    def _refresh_mode(self) -> None:
        if not self._show_mode_badge:
            return
        self.query_one("#mode-badge", Static).update(self._mode_content())
