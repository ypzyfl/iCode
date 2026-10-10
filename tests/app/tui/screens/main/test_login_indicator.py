# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Tests for pure status-bar login indicator state computation."""

from __future__ import annotations

from pathlib import Path

from aixcoding.auth import LoginSession
from aixcoding.auth.crypto import MemoryBackend
from aixcoding.auth.delegation import DelegatedCredential
from aixcoding.auth.types import AccountInfo, Environment, StoredCredential

from chrys.app.tui.screens.main.login_indicator import compute_login_indicator_state
from chrys.foundation.i18n import Localizer

_EN = Localizer("en")
_ZH = Localizer("zh-Hans")


def _session(tmp_path: Path, **delegation: object) -> LoginSession:
    return LoginSession(
        environment=Environment.LOCAL,
        endpoints=("http://127.0.0.1:1/api/v1", "http://127.0.0.1:1/api/v1"),
        config_dir=tmp_path,
        backend=MemoryBackend(),
        **delegation,  # type: ignore[arg-type]
    )


def _store_credential(session: LoginSession, *, ehr: str = "8769092") -> None:
    session.store.store(
        Environment.LOCAL,
        StoredCredential.issued_now(environment_id="local", user_id=ehr, token="tok", ehr=ehr),
    )


def test_no_credential_and_no_delegation_is_logged_out(tmp_path: Path) -> None:
    state = compute_login_indicator_state(_session(tmp_path), _EN)

    assert state.label == "Not logged in"
    assert state.tooltip == "Not logged in — run /login to sign in"
    assert state.logged_in is False
    assert state.managed is False


def test_logged_out_label_localizes(tmp_path: Path) -> None:
    state = compute_login_indicator_state(_session(tmp_path), _ZH)

    assert state.label == "未登录"
    assert state.tooltip == "未登录 — 输入 /login 登录"


def test_stored_credential_without_account_falls_back_to_ehr(tmp_path: Path) -> None:
    session = _session(tmp_path)
    _store_credential(session)

    state = compute_login_indicator_state(session, _EN)

    assert state.label == "8769092"
    assert state.tooltip == "Signed in as 8769092"
    assert state.logged_in is True
    assert state.managed is False


def test_account_result_wins_over_stored_ehr(tmp_path: Path) -> None:
    session = _session(tmp_path)
    _store_credential(session)
    account = AccountInfo(ehr="8769092", name="大熊猫")

    state = compute_login_indicator_state(session, _EN, account=account)

    assert state.label == "大熊猫"
    assert state.tooltip == "Signed in as 大熊猫 (8769092)"
    assert state.logged_in is True


def test_account_name_matching_ehr_dedupes_tooltip(tmp_path: Path) -> None:
    session = _session(tmp_path)
    _store_credential(session)
    account = AccountInfo(ehr="8769092", name="8769092")

    state = compute_login_indicator_state(session, _EN, account=account)

    assert state.tooltip == "Signed in as 8769092"


def test_delegated_credential_reports_managed_identity(tmp_path: Path) -> None:
    session = _session(
        tmp_path,
        delegated=DelegatedCredential(token="parent-token", ehr="10086", display_name="桌面用户"),
    )

    state = compute_login_indicator_state(session, _EN)

    assert state.label == "桌面用户"
    assert state.tooltip == "桌面用户 — login managed by the desktop app"
    assert state.logged_in is True
    assert state.managed is True


def test_delegated_credential_falls_back_to_ehr_hint(tmp_path: Path) -> None:
    session = _session(tmp_path, delegated=DelegatedCredential(token="parent-token", ehr="10086"))

    state = compute_login_indicator_state(session, _EN)

    assert state.label == "10086"
    assert state.tooltip == "10086 — login managed by the desktop app"
    assert state.managed is True


def test_delegated_credential_without_hints_shows_generic_signed_in(tmp_path: Path) -> None:
    session = _session(tmp_path, delegated=DelegatedCredential(token="parent-token"))

    state = compute_login_indicator_state(session, _EN)

    assert state.label == "Signed in"
    assert state.logged_in is True
    assert state.managed is True


def test_delegated_account_result_beats_environment_hints(tmp_path: Path) -> None:
    session = _session(
        tmp_path,
        delegated=DelegatedCredential(token="parent-token", ehr="10086", display_name="桌面用户"),
    )
    account = AccountInfo(ehr="10086", name="真实姓名")

    state = compute_login_indicator_state(session, _EN, account=account)

    assert state.label == "真实姓名"


def test_rejected_delegation_falls_back_to_stored_credential(tmp_path: Path) -> None:
    session = _session(
        tmp_path,
        delegated=DelegatedCredential(token="parent-token", ehr="10086"),
    )
    _store_credential(session, ehr="8769092")
    session._delegated_rejected = True  # what a server-side rejection leaves behind

    state = compute_login_indicator_state(session, _EN)

    assert state.label == "8769092"
    assert state.managed is False
    assert state.logged_in is True
