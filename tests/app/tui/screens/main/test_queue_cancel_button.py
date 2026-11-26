# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Clicking the waiting row's cancel-queue affordance toasts the user and interrupts the turn."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from chrys.app.aixcoding.tui.queue_cancel_button import QUEUE_CANCELLED_NOTICE, QueueCancelButton
from chrys.app.tui.screens.main.screen import MainScreen
from chrys.app.tui.widgets.chat.panel import ChatPanel
from chrys.app.tui.widgets.chat.waiting_row import WaitingRow
from chrys.kernel.aixcoding.queue_progress import queue_note
from tests.support.tui_app_harness import make_chrys_app
from tests.support.tui_helpers import click_when_settled
from tests.support.waiting import wait_for


async def test_clicking_cancel_queue_toasts_and_interrupts_the_turn(tmp_path: Path) -> None:
    app = make_chrys_app(tmp_path)
    async with app.run_test() as pilot:
        screen = app.screen
        assert isinstance(screen, MainScreen)
        panel = screen.query_one(ChatPanel)
        panel.agent_running = True
        row = panel.query_one(WaitingRow)
        button = panel.query_one(QueueCancelButton)
        row.set_queue_note(queue_note(3, 10))
        await wait_for(
            lambda: row.display and button.display,
            pilot=pilot,
            description="the queued turn shows the waiting row with its cancel affordance",
        )
        with (
            patch.object(screen, "action_interrupt") as interrupt,
            patch.object(screen, "notify") as notify,
        ):
            await click_when_settled(pilot, button)
            await wait_for(interrupt.called, pilot=pilot, description="the click interrupted the turn")
        # The toast says the user left the queue; the interrupt is what leaves it (design v1.8).
        interrupt.assert_called_once_with()
        notify.assert_called_once_with(QUEUE_CANCELLED_NOTICE, markup=False)
