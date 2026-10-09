# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Desktop-delegated login: detection, precedence, and rejection semantics."""

from __future__ import annotations

import threading

import aixcoding.auth.session as auth_session
from aixcoding.auth import (
    DELEGATED_TOKEN_VARIABLE,
    Environment,
    LoginSession,
    StoredCredential,
    detect_delegation,
    get_login_session,
)
from aixcoding.auth.crypto import MemoryBackend
from aixcoding.auth.delegation import (
    COMPAT_EHR_VARIABLE,
    COMPAT_TOKEN_VARIABLE,
    DELEGATED_EHR_VARIABLE,
    DELEGATED_NAME_VARIABLE,
    DelegatedCredential,
)
from aixcoding.auth.types import AccountInfo
from mock_server.aixcoding_auth.server import MockAuthConfig, create_server


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


def make_session(tmp_path, base_url: str, **delegation: object) -> LoginSession:
    return LoginSession(
        environment=Environment.LOCAL,
        endpoints=(base_url, base_url),
        config_dir=tmp_path,
        backend=MemoryBackend(),
        **delegation,  # type: ignore[arg-type]
    )


# --------------------------------------------------------------- detection #


def test_detect_primary_token_variable() -> None:
    delegated = detect_delegation({DELEGATED_TOKEN_VARIABLE: " parent-token \n"})
    assert delegated == DelegatedCredential(
        token="parent-token",
        ehr="",
        display_name="",
        source=DELEGATED_TOKEN_VARIABLE,
    )


def test_detect_primary_with_identity_hints() -> None:
    delegated = detect_delegation(
        {
            DELEGATED_TOKEN_VARIABLE: "parent-token",
            DELEGATED_EHR_VARIABLE: "8769092",
            DELEGATED_NAME_VARIABLE: "大熊猫",
        }
    )
    assert delegated is not None
    assert delegated.token == "parent-token"
    assert delegated.ehr == "8769092"
    assert delegated.display_name == "大熊猫"


def test_detect_primary_wins_over_compat_pair() -> None:
    delegated = detect_delegation(
        {
            DELEGATED_TOKEN_VARIABLE: "parent-token",
            COMPAT_EHR_VARIABLE: "8769092",
            COMPAT_TOKEN_VARIABLE: "model-key",
        }
    )
    assert delegated is not None
    assert delegated.token == "parent-token"
    assert delegated.source == DELEGATED_TOKEN_VARIABLE


def test_detect_compat_pair_used_when_primary_absent() -> None:
    delegated = detect_delegation(
        {
            COMPAT_EHR_VARIABLE: "8769092",
            COMPAT_TOKEN_VARIABLE: "model-key",
        }
    )
    assert delegated == DelegatedCredential(token="model-key", ehr="8769092", source=COMPAT_TOKEN_VARIABLE)


def test_detect_requires_both_compat_variables() -> None:
    # A standalone shell exporting only a provider key, or only the desktop's
    # identity stamp, is not a delegation.
    assert detect_delegation({COMPAT_TOKEN_VARIABLE: "model-key"}) is None
    assert detect_delegation({COMPAT_EHR_VARIABLE: "8769092"}) is None


def test_detect_blank_values_are_absent() -> None:
    assert detect_delegation({DELEGATED_TOKEN_VARIABLE: "   "}) is None
    assert detect_delegation({COMPAT_EHR_VARIABLE: "8769092", COMPAT_TOKEN_VARIABLE: ""}) is None


def test_detect_reads_process_environment(monkeypatch) -> None:
    monkeypatch.setenv(DELEGATED_TOKEN_VARIABLE, "env-token")
    delegated = detect_delegation()
    assert delegated is not None
    assert delegated.token == "env-token"


def test_get_login_session_detects_delegation_from_environment(monkeypatch) -> None:
    monkeypatch.setattr(auth_session, "_default_session", None)
    monkeypatch.setenv(DELEGATED_TOKEN_VARIABLE, "env-token")
    try:
        session = get_login_session()
        assert session.delegated_credential is not None
        assert session.stored_token == "env-token"
    finally:
        # Leave no cached session behind for other tests.
        monkeypatch.setattr(auth_session, "_default_session", None)


# ---------------------------------------------------------------- session  #


async def test_delegation_shadows_the_store(tmp_path) -> None:
    session = make_session(tmp_path, "http://127.0.0.1:1/api/v1", delegated=DelegatedCredential(token="parent-token"))
    session.store.store(
        Environment.LOCAL,
        StoredCredential.issued_now(environment_id="local", user_id="8769092", token="own-token"),
    )
    assert session.stored_token == "parent-token"
    assert session.delegated_credential is not None


async def test_check_silent_validates_the_delegated_token(tmp_path) -> None:
    with MockServer(mode="auto", interval=0) as mock:
        # The "desktop" walks the device flow and owns the resulting token.
        parent = make_session(tmp_path, mock.base_url)
        code = await parent.request_device_code()
        account = await parent.complete_login(code)
        token = parent.stored_token
        assert token is not None

        child = make_session(
            tmp_path,
            mock.base_url,
            delegated=DelegatedCredential(token=token, ehr=account.ehr),
        )
        assert child.stored_token == token
        silent = await child.check_silent()
        assert silent is not None
        assert silent.ehr == account.ehr
        assert child.delegated_credential is not None


async def test_rejected_delegation_falls_back_to_the_store_without_destroying_it(tmp_path) -> None:
    with MockServer(mode="auto") as mock:
        session = make_session(
            tmp_path,
            mock.base_url,
            delegated=DelegatedCredential(token="bogus-parent-token"),
        )
        session.store.store(
            Environment.LOCAL,
            StoredCredential.issued_now(environment_id="local", user_id="8769092", token="own-token"),
        )
        assert await session.check_silent() is None
        # The parent's token is dead: it stops shadowing, the own credential
        # survives untouched, and the session stays usable.
        assert session.delegated_credential is None
        assert session.stored_token == "own-token"
        assert session.store.load(Environment.LOCAL) is not None
        # After the fallback, logout behaves like the standalone flow again.
        session.logout()
        assert session.store.load(Environment.LOCAL) is None


async def test_offline_delegation_is_kept(tmp_path) -> None:
    session = make_session(
        tmp_path,
        "http://127.0.0.1:1/api/v1",
        delegated=DelegatedCredential(token="parent-token"),
    )
    assert await session.check_silent() is None
    # Being offline is not a logout -- for either credential kind.
    assert session.stored_token == "parent-token"


async def test_logout_is_a_no_op_while_delegated(tmp_path) -> None:
    session = make_session(
        tmp_path,
        "http://127.0.0.1:1/api/v1",
        delegated=DelegatedCredential(token="parent-token"),
    )
    session.store.store(
        Environment.LOCAL,
        StoredCredential.issued_now(environment_id="local", user_id="8769092", token="own-token"),
    )
    session.logout()
    # The parent owns the session: nothing local changes.
    assert session.store.load(Environment.LOCAL) is not None
    assert session.stored_token == "parent-token"


async def test_complete_login_under_delegation_stores_but_stays_shadowed(tmp_path) -> None:
    with MockServer(mode="auto", interval=0) as mock:
        session = make_session(
            tmp_path,
            mock.base_url,
            delegated=DelegatedCredential(token="parent-token"),
        )
        code = await session.request_device_code()
        account = await session.complete_login(code)
        assert isinstance(account, AccountInfo)
        stored = session.store.load(Environment.LOCAL)
        assert stored is not None
        assert stored.token != "parent-token"
        assert session.stored_token == "parent-token"
