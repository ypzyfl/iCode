# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""LoginDialog tests: success flow, cancel stops without storing, failure UI."""

from __future__ import annotations

import threading

import pytest
from aixcoding.auth import AccountInfo, Environment, LoginSession
from aixcoding.auth.crypto import MemoryBackend
from aixcoding.tui import LoginDialog
from textual.app import App
from textual.widgets import Static

from mock_server.aixcoding_auth.server import MockAuthConfig, create_server
from tests.support.waiting import wait_until

pytestmark = pytest.mark.asyncio


class _DialogApp(App):
    pass


class MockServer:
    """Loopback mock on an ephemeral port, usable as a context manager."""

    def __init__(self, **config: object) -> None:
        self.server = create_server(MockAuthConfig(**config), host="127.0.0.1", port=0)  # type: ignore[arg-type]
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}/api/v1"

    def __enter__(self) -> MockServer:
        self.thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.server.shutdown()
        self.server.server_close()


def make_session(tmp_path, base_url: str) -> LoginSession:
    return LoginSession(
        environment=Environment.LOCAL,
        endpoints=(base_url, base_url),
        config_dir=tmp_path,
        backend=MemoryBackend(),
    )


async def test_login_dialog_success_flow(tmp_path) -> None:
    with MockServer(mode="auto", interval=0) as mock:
        session = make_session(tmp_path, mock.base_url)
        opened: list[str] = []
        app = _DialogApp()
        async with app.run_test() as pilot:
            results: list[object] = []
            dialog = LoginDialog(session=session, open_browser=opened.append)
            app.push_screen(dialog, results.append)

            done = await wait_until(lambda: bool(results), pilot=pilot, timeout=10)
            assert done, "dialog should dismiss with the account after the mock grants"

            account = results[0]
            assert isinstance(account, AccountInfo)
            assert account.display_name == "大熊猫"
            # The browser was pointed at the pre-filled verification URL.
            assert opened and "user_code=" in opened[0]
            # The credential is stored for the next silent check.
            assert session.stored_token is not None
            assert session.stored_token.startswith("mock-token-")


async def test_login_dialog_cancel_stops_without_storing(tmp_path) -> None:
    # interval=1: a real (short) poll sleep, so the wait loop does not spin.
    with MockServer(mode="manual", interval=1) as mock:  # never confirms on its own
        session = make_session(tmp_path, mock.base_url)
        app = _DialogApp()
        async with app.run_test() as pilot:
            results: list[object] = []
            dialog = LoginDialog(session=session, open_browser=lambda url: None)
            app.push_screen(dialog, results.append)
            await pilot.pause()  # let the screen compose before querying widgets

            # Wait until the user code is on screen, then cancel. Content (not
            # display) is the signal: visibility is class-driven via the tcss.
            assert await wait_until(lambda: bool(dialog.children), pilot=pilot, timeout=10), (
                "dialog compose children should mount"
            )
            code_view = dialog.query_one("#login-code", Static)
            shown = await wait_until(lambda: bool(str(code_view.content).strip()), pilot=pilot, timeout=10)
            assert shown, "user code should appear once the device code arrives"

            await pilot.press("escape")
            assert await wait_until(lambda: results == [None], pilot=pilot, timeout=5), (
                "cancelling should dismiss the dialog with None"
            )
            assert session.stored_token is None


async def test_login_dialog_shows_error_when_unreachable(tmp_path) -> None:
    session = make_session(tmp_path, "http://127.0.0.1:1/api/v1")  # nothing listens here
    app = _DialogApp()
    async with app.run_test() as pilot:
        results: list[object] = []
        dialog = LoginDialog(session=session, open_browser=lambda url: None)
        app.push_screen(dialog, results.append)
        await pilot.pause()  # let the screen compose before querying widgets

        status = dialog.query_one("#login-status", Static)

        def failed() -> bool:
            return "无法获取登录码" in str(status.content)

        assert await wait_until(failed, pilot=pilot, timeout=10), (
            "unreachable server should surface as an error message"
        )

        await pilot.press("escape")
        await pilot.pause()
        assert results == [None]
