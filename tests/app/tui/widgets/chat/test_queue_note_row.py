# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""The waiting row shows the gateway's queue note behind a status card, with a cancel affordance beside it."""

from __future__ import annotations

from chrys.app.aixcoding.tui.queue_cancel_button import QueueCancelButton, QueueCancelRequested
from chrys.app.tui.widgets.chat.panel import ChatPanel
from chrys.app.tui.widgets.chat.waiting_row import WaitingRow
from chrys.kernel.aixcoding.queue_progress import queue_note
from tests.support.tui_helpers import ChatPanelApp, click_when_settled
from tests.support.waiting import wait_for


class _QueueCancelRecorderApp(ChatPanelApp):
    """Records the cancel affordance's message where nothing between the panel and here stops it."""

    def __init__(self) -> None:
        self.cancel_requests: list[QueueCancelRequested] = []
        super().__init__()

    def on_queue_cancel_requested(self, message: QueueCancelRequested) -> None:
        self.cancel_requests.append(message)


def _row(panel: ChatPanel) -> WaitingRow:
    return panel.query_one(WaitingRow)


def _cancel_button(panel: ChatPanel) -> QueueCancelButton:
    return panel.query_one(QueueCancelButton)


async def test_the_row_shows_the_queue_note_behind_a_status_card_until_the_queue_lets_it_go() -> None:
    """A retry's notice stays the last entry while the retried request queues again; the position is the wait itself."""
    async with ChatPanelApp().run_test() as pilot:
        panel = pilot.app.query_one(ChatPanel)
        panel.agent_running = True
        await panel.add_user_message("prompt")
        await panel.add_retry("gateway queue timeout", attempt=2, max_attempts=10, delay_seconds=30)
        row = _row(panel)
        assert not row.display

        row.set_queue_note(queue_note(3, 10))
        await wait_for(lambda: row.display, pilot=pilot, description="the queued retry shows the waiting row")

        # The timeout's translated release frame clears the note; the notice again says the wait itself.
        row.set_queue_note("")
        await wait_for(
            lambda: not row.display and panel._waiting_row_timer is None,
            pilot=pilot,
            description="the row hides once the queue no longer holds the request",
        )


async def test_the_cancel_affordance_comes_with_the_note_and_leaves_with_it() -> None:
    async with ChatPanelApp().run_test() as pilot:
        panel = pilot.app.query_one(ChatPanel)
        panel.agent_running = True
        await panel.add_user_message("prompt")
        row = _row(panel)
        button = _cancel_button(panel)

        # The bare dot carries no affordance: there is no queue to leave.
        assert not button.display
        row.set_queue_note(queue_note(3, 10))
        assert row.queue_note == queue_note(3, 10)
        assert button.display
        row.set_queue_note("")
        assert not button.display


async def test_clicking_the_cancel_affordance_delivers_its_message_beyond_the_panel() -> None:
    async with _QueueCancelRecorderApp().run_test() as pilot:
        app = pilot.app
        assert isinstance(app, _QueueCancelRecorderApp)
        panel = app.query_one(ChatPanel)
        panel.agent_running = True
        await panel.add_user_message("prompt")
        row = _row(panel)
        row.set_queue_note(queue_note(3, 10))
        await wait_for(
            lambda: row.display and _cancel_button(panel).display,
            pilot=pilot,
            description="the queued turn shows the row with its cancel affordance",
        )
        await click_when_settled(pilot, _cancel_button(panel))
        await wait_for(
            lambda: len(app.cancel_requests) == 1,
            pilot=pilot,
            description="the click reaches beyond the chat panel as one request",
        )
