# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# ruff: noqa: S101, S106, RUF001

"""MainScreen wiring for /login and /logout: dialog push, result toasts, startup hook."""

from __future__ import annotations

import inspect
from types import SimpleNamespace

from chrys.app.aixcoding.tui import login_actions
from chrys.app.tui.screens.main.screen import MainScreen
from chrys.kernel.aixcoding.auth import LoginSession
from chrys.kernel.aixcoding.auth import session as auth_session
from chrys.kernel.aixcoding.auth.crypto import MemoryBackend
from chrys.kernel.aixcoding.auth.delegation import DelegatedCredential
from chrys.kernel.aixcoding.auth.types import AccountInfo, Environment, StoredCredential


def _make_session(tmp_path, **delegation: object) -> LoginSession:
    return LoginSession(
        environment=Environment.LOCAL,
        endpoints=("http://127.0.0.1:1/api/v1", "http://127.0.0.1:1/api/v1"),
        config_dir=tmp_path,
        backend=MemoryBackend(),
        **delegation,  # type: ignore[arg-type]
    )


def _host(pushed: list, notifications: list, refreshed: list | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        app=SimpleNamespace(
            push_screen=lambda dialog, callback: pushed.append((dialog, callback)),
        ),
        notify=lambda message, **_kwargs: notifications.append(str(message)),
        refresh_login_indicator=lambda **account: refreshed.append(account),
    )


def test_main_screen_logout_warns_when_not_logged_in(monkeypatch, tmp_path) -> None:
    session = _make_session(tmp_path)
    monkeypatch.setattr(auth_session, "_default_session", session)
    notifications: list[str] = []

    login_actions.perform_logout(_host([], notifications))

    assert notifications == ["尚未登录"]
    assert session.stored_token is None


def test_main_screen_logout_clears_credential_and_toasts(monkeypatch, tmp_path) -> None:
    session = _make_session(tmp_path)
    monkeypatch.setattr(auth_session, "_default_session", session)
    session.store.store(
        Environment.LOCAL,
        StoredCredential.issued_now(environment_id="local", user_id="8769092", token="tok"),
    )
    notifications: list[str] = []
    refreshed: list[dict] = []

    login_actions.perform_logout(_host([], notifications, refreshed))

    assert notifications == ["已登出"]
    assert refreshed == [{}]
    assert session.stored_token is None


def test_main_screen_login_pushes_dialog_and_toasts_on_account(monkeypatch, tmp_path) -> None:
    session = _make_session(tmp_path)
    monkeypatch.setattr(auth_session, "_default_session", session)
    pushed: list[tuple[object, object]] = []
    notifications: list[str] = []
    refreshed: list[dict] = []
    host = _host(pushed, notifications, refreshed)

    login_actions.open_login_dialog(host)

    assert len(pushed) == 1
    dialog, dismiss_callback = pushed[0]
    assert type(dialog).__name__ == "LoginDialog"

    dismiss_callback(AccountInfo(ehr="8769092", name="大熊猫"))
    assert notifications == ["已登录：大熊猫"]
    assert len(refreshed) == 1

    dismiss_callback(None)  # cancelled login: no toast
    assert notifications == ["已登录：大熊猫"]


def test_main_screen_login_reports_desktop_managed_session(monkeypatch, tmp_path) -> None:
    session = _make_session(tmp_path, delegated=DelegatedCredential(token="parent-token"))
    monkeypatch.setattr(auth_session, "_default_session", session)
    pushed: list[tuple[object, object]] = []
    notifications: list[str] = []

    login_actions.open_login_dialog(_host(pushed, notifications))

    assert pushed == []  # no device-code dialog: the desktop owns the login
    assert notifications == ["登录由桌面端管理"]


def test_main_screen_logout_reports_desktop_managed_session(monkeypatch, tmp_path) -> None:
    session = _make_session(tmp_path, delegated=DelegatedCredential(token="parent-token"))
    session.store.store(
        Environment.LOCAL,
        StoredCredential.issued_now(environment_id="local", user_id="8769092", token="own-token"),
    )
    monkeypatch.setattr(auth_session, "_default_session", session)
    notifications: list[str] = []

    login_actions.perform_logout(_host([], notifications))

    assert notifications == ["登出由桌面端管理"]
    assert session.stored_token == "parent-token"  # nothing was cleared
    assert session.store.load(Environment.LOCAL) is not None


def test_main_screen_mounts_silent_login_check() -> None:
    """The startup silent check hangs off MainScreen.on_mount (design, change 9)."""
    on_mount = inspect.getsource(MainScreen.on_mount)
    assert "from chrys.app.aixcoding.tui.login_actions import silent_login_check" in on_mount
    assert "asyncio.create_task(silent_login_check(self))" in on_mount


def test_main_screen_teardown_cancels_silent_login_check() -> None:
    """on_unmount cancels the task so app exit never leaks it (5-line pattern)."""
    on_unmount = inspect.getsource(MainScreen.on_unmount)
    assert "_login_silent_check_task" in on_unmount
    assert ".cancel()" in on_unmount
    assert "await self._login_silent_check_task" in on_unmount  # peer review C4: the 5-line floor, fully anchored
