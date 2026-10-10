# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""MainScreen wiring for /login and /logout: dialog push, result toasts, indicator refresh."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import aixcoding.auth.session as auth_session
from aixcoding.auth import LoginSession
from aixcoding.auth.crypto import MemoryBackend
from aixcoding.auth.delegation import DelegatedCredential
from aixcoding.auth.types import AccountInfo, Environment, StoredCredential

from chrys.app.tui.app import ChrysApp
from chrys.app.tui.screens.main.login_indicator import LoginIndicatorState
from chrys.app.tui.screens.main.screen import MainScreen
from chrys.foundation.i18n import Localizer


def _make_session(tmp_path, **delegation: object) -> LoginSession:
    return LoginSession(
        environment=Environment.LOCAL,
        endpoints=("http://127.0.0.1:1/api/v1", "http://127.0.0.1:1/api/v1"),
        config_dir=tmp_path,
        backend=MemoryBackend(),
        **delegation,  # type: ignore[arg-type]
    )


def _store_credential(session: LoginSession) -> None:
    session.store.store(
        Environment.LOCAL,
        StoredCredential.issued_now(environment_id="local", user_id="8769092", token="tok", ehr="8769092"),
    )


def _host(pushed: list, notifications: list, refreshes: list) -> SimpleNamespace:
    return SimpleNamespace(
        app=SimpleNamespace(push_screen=lambda dialog, callback: pushed.append((dialog, callback))),
        notify=lambda message, **_kwargs: notifications.append(str(message)),
        _language_localizer=lambda: Localizer("en"),
        refresh_login_indicator=lambda **kwargs: refreshes.append(kwargs),
    )


def _screen_host(refreshes: list) -> SimpleNamespace:
    return SimpleNamespace(refresh_login_indicator=lambda **kwargs: refreshes.append(kwargs))


def test_main_screen_logout_warns_when_not_logged_in(monkeypatch, tmp_path) -> None:
    session = _make_session(tmp_path)
    monkeypatch.setattr(auth_session, "_default_session", session)
    notifications: list[str] = []

    MainScreen._perform_logout(_host([], notifications, []))

    assert notifications == ["Not logged in yet"]
    assert session.stored_token is None


def test_main_screen_logout_clears_credential_toasts_and_refreshes_indicator(monkeypatch, tmp_path) -> None:
    session = _make_session(tmp_path)
    monkeypatch.setattr(auth_session, "_default_session", session)
    _store_credential(session)
    notifications: list[str] = []
    refreshes: list[dict] = []

    MainScreen._perform_logout(_host([], notifications, refreshes))

    assert notifications == ["Logged out"]
    assert session.stored_token is None
    assert refreshes == [{}]


def test_main_screen_logout_managed_branch_skips_indicator_refresh(monkeypatch, tmp_path) -> None:
    session = _make_session(tmp_path, delegated=DelegatedCredential(token="parent-token"))
    _store_credential(session)
    monkeypatch.setattr(auth_session, "_default_session", session)
    refreshes: list[dict] = []

    MainScreen._perform_logout(_host([], [], refreshes))

    assert refreshes == []


def test_main_screen_logout_not_logged_in_branch_skips_indicator_refresh(monkeypatch, tmp_path) -> None:
    session = _make_session(tmp_path)
    monkeypatch.setattr(auth_session, "_default_session", session)
    refreshes: list[dict] = []

    MainScreen._perform_logout(_host([], [], refreshes))

    assert refreshes == []


def test_main_screen_login_pushes_dialog_toasts_and_refreshes_on_account(monkeypatch, tmp_path) -> None:
    session = _make_session(tmp_path)
    monkeypatch.setattr(auth_session, "_default_session", session)
    pushed: list[tuple[object, object]] = []
    notifications: list[str] = []
    refreshes: list[dict] = []
    host = _host(pushed, notifications, refreshes)

    MainScreen._open_login_dialog(host)

    assert len(pushed) == 1
    dialog, dismiss_callback = pushed[0]
    assert type(dialog).__name__ == "LoginDialog"

    account = AccountInfo(ehr="8769092", name="大熊猫")
    dismiss_callback(account)
    assert notifications == ["Logged in as 大熊猫"]
    assert refreshes == [{"account": account}]

    dismiss_callback(None)  # cancelled login: no toast, no second refresh
    assert notifications == ["Logged in as 大熊猫"]
    assert refreshes == [{"account": account}]


def test_main_screen_login_reports_desktop_managed_session(monkeypatch, tmp_path) -> None:
    session = _make_session(tmp_path, delegated=DelegatedCredential(token="parent-token"))
    monkeypatch.setattr(auth_session, "_default_session", session)
    pushed: list[tuple[object, object]] = []
    notifications: list[str] = []

    MainScreen._open_login_dialog(_host(pushed, notifications, []))

    assert pushed == []  # no device-code dialog: the desktop owns the login
    assert notifications == ["Login is managed by the desktop app"]


def test_main_screen_logout_reports_desktop_managed_session(monkeypatch, tmp_path) -> None:
    session = _make_session(tmp_path, delegated=DelegatedCredential(token="parent-token"))
    _store_credential(session)
    monkeypatch.setattr(auth_session, "_default_session", session)
    notifications: list[str] = []

    MainScreen._perform_logout(_host([], notifications, []))

    assert notifications == ["Logout is managed by the desktop app"]
    assert session.stored_token == "parent-token"  # nothing was cleared
    assert session.store.load(Environment.LOCAL) is not None


def test_main_screen_refresh_login_indicator_pushes_state_to_status_bar(monkeypatch, tmp_path) -> None:
    session = _make_session(tmp_path)
    monkeypatch.setattr(auth_session, "_default_session", session)
    _store_credential(session)
    recorded: list[LoginIndicatorState] = []
    host = SimpleNamespace(
        _language_localizer=lambda: Localizer("en"),
        query_one=lambda _widget_type: SimpleNamespace(set_account=recorded.append),
    )

    MainScreen.refresh_login_indicator(host)

    assert len(recorded) == 1
    state = recorded[0]
    assert state.label == "8769092"
    assert state.logged_in is True
    assert state.managed is False


def test_silent_login_check_refreshes_indicator_without_account_when_offline(monkeypatch, tmp_path) -> None:
    """An unreachable check keeps the credential; the refresh re-reads the session, not the result."""
    session = _make_session(tmp_path)
    monkeypatch.setattr(auth_session, "_default_session", session)
    refreshes: list[dict] = []

    asyncio.run(ChrysApp._silent_login_check(SimpleNamespace(_main_screen=_screen_host(refreshes))))

    assert refreshes == [{"account": None}]


def test_silent_login_check_passes_account_result_to_indicator_refresh(monkeypatch, tmp_path) -> None:
    account = AccountInfo(ehr="8769092", name="大熊猫")

    async def _check_silent() -> AccountInfo:
        return account

    monkeypatch.setattr(
        auth_session,
        "_default_session",
        SimpleNamespace(check_silent=_check_silent),
    )
    refreshes: list[dict] = []

    asyncio.run(ChrysApp._silent_login_check(SimpleNamespace(_main_screen=_screen_host(refreshes))))

    assert refreshes == [{"account": account}]


def test_silent_login_check_tolerates_missing_main_screen(monkeypatch, tmp_path) -> None:
    async def _check_silent():
        return None

    monkeypatch.setattr(
        auth_session,
        "_default_session",
        SimpleNamespace(check_silent=_check_silent),
    )

    asyncio.run(ChrysApp._silent_login_check(SimpleNamespace(_main_screen=None)))  # no refresh, no crash
