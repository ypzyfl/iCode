# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""MainScreen wiring for /login and /logout: dialog push and result toasts."""

from __future__ import annotations

from types import SimpleNamespace

import aixcoding.auth.session as auth_session
from aixcoding.auth import LoginSession
from aixcoding.auth.crypto import MemoryBackend
from aixcoding.auth.delegation import DelegatedCredential
from aixcoding.auth.types import Environment, StoredCredential

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


def _host(pushed: list, notifications: list) -> SimpleNamespace:
    return SimpleNamespace(
        app=SimpleNamespace(push_screen=lambda dialog, callback: pushed.append((dialog, callback))),
        notify=lambda message, **_kwargs: notifications.append(str(message)),
        _language_localizer=lambda: Localizer("en"),
    )


def test_main_screen_logout_warns_when_not_logged_in(monkeypatch, tmp_path) -> None:
    session = _make_session(tmp_path)
    monkeypatch.setattr(auth_session, "_default_session", session)
    notifications: list[str] = []

    MainScreen._perform_logout(_host([], notifications))

    assert notifications == ["Not logged in yet"]
    assert session.stored_token is None


def test_main_screen_logout_clears_credential_and_toasts(monkeypatch, tmp_path) -> None:
    session = _make_session(tmp_path)
    monkeypatch.setattr(auth_session, "_default_session", session)
    session.store.store(
        Environment.LOCAL,
        StoredCredential.issued_now(environment_id="local", user_id="8769092", token="tok"),
    )
    notifications: list[str] = []

    MainScreen._perform_logout(_host([], notifications))

    assert notifications == ["Logged out"]
    assert session.stored_token is None


def test_main_screen_login_pushes_dialog_and_toasts_on_account(monkeypatch, tmp_path) -> None:
    session = _make_session(tmp_path)
    monkeypatch.setattr(auth_session, "_default_session", session)
    pushed: list[tuple[object, object]] = []
    notifications: list[str] = []
    host = _host(pushed, notifications)

    MainScreen._open_login_dialog(host)

    assert len(pushed) == 1
    dialog, dismiss_callback = pushed[0]
    assert type(dialog).__name__ == "LoginDialog"

    dismiss_callback(SimpleNamespace(display_name="大熊猫"))
    assert notifications == ["Logged in as 大熊猫"]

    dismiss_callback(None)  # cancelled login: no toast
    assert notifications == ["Logged in as 大熊猫"]


def test_main_screen_login_reports_desktop_managed_session(monkeypatch, tmp_path) -> None:
    session = _make_session(tmp_path, delegated=DelegatedCredential(token="parent-token"))
    monkeypatch.setattr(auth_session, "_default_session", session)
    pushed: list[tuple[object, object]] = []
    notifications: list[str] = []

    MainScreen._open_login_dialog(_host(pushed, notifications))

    assert pushed == []  # no device-code dialog: the desktop owns the login
    assert notifications == ["Login is managed by the desktop app"]


def test_main_screen_logout_reports_desktop_managed_session(monkeypatch, tmp_path) -> None:
    session = _make_session(tmp_path, delegated=DelegatedCredential(token="parent-token"))
    session.store.store(
        Environment.LOCAL,
        StoredCredential.issued_now(environment_id="local", user_id="8769092", token="own-token"),
    )
    monkeypatch.setattr(auth_session, "_default_session", session)
    notifications: list[str] = []

    MainScreen._perform_logout(_host([], notifications))

    assert notifications == ["Logout is managed by the desktop app"]
    assert session.stored_token == "parent-token"  # nothing was cleared
    assert session.store.load(Environment.LOCAL) is not None
