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
