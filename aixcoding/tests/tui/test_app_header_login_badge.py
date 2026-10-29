# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# ruff: noqa: S101, RUF001

"""AppHeader login badge: visibility, state classes, tooltip."""

from __future__ import annotations

from textual.app import App
from textual.widgets import Static

from chrys.app.aixcoding.tui.login_indicator import LoginIndicatorState
from chrys.app.tui.widgets.chrome.app_header import AppHeader


class AppHeaderApp(App):
    def compose(self):
        yield AppHeader()


async def test_app_header_login_badge_states_and_visibility() -> None:
    async with AppHeaderApp().run_test() as pilot:
        header = pilot.app.query_one(AppHeader)
        badge = pilot.app.query_one("#login-badge", Static)

        # Hidden until the screen pushes a state.
        assert badge.display is False

        header.set_login_indicator(
            LoginIndicatorState(label="已登录", tooltip="已登录：alice", logged_in=True, managed=False)
        )
        await pilot.pause()
        assert badge.display is True
        assert badge.render().plain == "\u25cf 已登录"
        assert not badge.has_class("-logged-out")
        assert badge.tooltip is not None

        header.set_login_indicator(
            LoginIndicatorState(label="未登录", tooltip="未登录 — 运行 /login 登录", logged_in=False, managed=False)
        )
        await pilot.pause()
        assert badge.render().plain == "\u25cf 未登录"
        assert badge.has_class("-logged-out")


async def test_app_header_can_hide_login_badge() -> None:
    class AppHeaderWithoutLoginApp(App):
        def compose(self):
            yield AppHeader(show_login_badge=False)

    async with AppHeaderWithoutLoginApp().run_test() as pilot:
        assert list(pilot.app.query("#login-badge")) == []


async def test_login_badge_presence_re_pins_the_approval_badge_margin() -> None:
    """AIxCoding tui: peer review C3 -- the room-making margin is anchored.

    The approval badge's right margin is the stylesheet default (1) while the
    account badge is hidden, and login width + 2 while it shows; deleting the
    room-making call must fail here (it had zero automated coverage).
    """
    async with AppHeaderApp().run_test() as pilot:
        header = pilot.app.query_one(AppHeader)
        approval = pilot.app.query_one("#approval-badge", Static)
        assert approval.styles.margin.right == 1  # hidden: the stylesheet default

        header.set_login_indicator(
            LoginIndicatorState(label="已登录", tooltip="已登录：测试员", logged_in=True, managed=False)
        )
        await pilot.pause()
        login = pilot.app.query_one("#login-badge", Static)
        assert login.display is True
        login_width = login.styles.width
        assert login_width is not None
        expected = 1 + int(login_width.value) + 1  # default + badge + its own margin
        assert approval.styles.margin.right == expected

        header.set_login_indicator(None)  # hides the badge again
        await pilot.pause()
        assert approval.styles.margin.right == 1
