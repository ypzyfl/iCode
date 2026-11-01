# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""LoginSession tests: silent check, complete login, logout, hand-off token."""

from __future__ import annotations

import threading

from aixcoding.mock.auth.server import MockAuthConfig, create_server

from chrys.kernel.aixcoding.auth import Environment, LoginSession, StoredCredential, get_login_session
from chrys.kernel.aixcoding.auth.crypto import MemoryBackend


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


async def test_check_silent_returns_none_with_nothing_stored(tmp_path) -> None:
    with MockServer(mode="auto") as mock:
        session = make_session(tmp_path, mock.base_url)
        assert await session.check_silent() is None


async def test_complete_login_stores_credential_and_returns_account(tmp_path) -> None:
    with MockServer(mode="auto", interval=0) as mock:
        session = make_session(tmp_path, mock.base_url)
        code = await session.request_device_code()
        account = await session.complete_login(code)
        assert account.ehr == "1234567"
        assert account.display_name == "测试员"
        token = session.stored_token
        assert token is not None and token.startswith("mock-token-")
        stored = session.store.load(Environment.LOCAL)
        assert stored is not None
        assert stored.token == token
        assert stored.environment_id == "local"
        assert stored.ehr == "1234567"
        assert session.stored_user_id == "1234567"


async def test_check_silent_round_trips_after_login(tmp_path) -> None:
    with MockServer(mode="auto", interval=0) as mock:
        session = make_session(tmp_path, mock.base_url)
        code = await session.request_device_code()
        logged_in = await session.complete_login(code)
        silent = await session.check_silent()
        assert silent is not None
        assert silent.ehr == logged_in.ehr
        assert silent.display_name == "测试员"


async def test_check_silent_clears_credential_the_server_rejects(tmp_path) -> None:
    with MockServer(mode="auto") as mock:
        session = make_session(tmp_path, mock.base_url)
        session.store.store(
            Environment.LOCAL,
            StoredCredential.issued_now(environment_id="local", user_id="8769092", token="bogus-token"),
        )
        assert await session.check_silent() is None
        # The dead credential is gone: the next login starts clean.
        assert session.store.load(Environment.LOCAL) is None
        assert session.stored_token is None


async def test_check_silent_keeps_credential_when_offline(tmp_path) -> None:
    session = make_session(tmp_path, "http://127.0.0.1:1/api/v1")
    session.store.store(
        Environment.LOCAL,
        StoredCredential.issued_now(environment_id="local", user_id="8769092", token="tok-keep"),
    )
    assert await session.check_silent() is None
    # Being offline is not a logout: the credential survives for the next start.
    assert session.stored_token == "tok-keep"


async def test_stored_token_none_when_expired(tmp_path) -> None:
    with MockServer(mode="auto") as mock:
        session = make_session(tmp_path, mock.base_url)
        session.store.store(
            Environment.LOCAL,
            StoredCredential.issued_now(environment_id="local", user_id="8769092", token="tok-old", ttl_seconds=-10),
        )
        assert session.stored_token is None
        assert session.stored_user_id is None  # same liveness predicate as the token
        assert await session.check_silent() is None


async def test_logout_clears_everything(tmp_path) -> None:
    with MockServer(mode="auto", interval=0) as mock:
        session = make_session(tmp_path, mock.base_url)
        code = await session.request_device_code()
        await session.complete_login(code)
        assert session.stored_token is not None
        session.logout()
        assert session.stored_token is None
        assert session.store.load(Environment.LOCAL) is None
        # Logout is idempotent.
        session.logout()
        assert session.stored_token is None


async def test_get_login_session_is_a_singleton(monkeypatch) -> None:
    import chrys.kernel.aixcoding.auth.session as session_module

    monkeypatch.setattr(session_module, "_default_session", None)
    first = get_login_session()
    second = get_login_session()
    assert first is second
    # Leave no cached real-backend session behind for other tests.
    monkeypatch.setattr(session_module, "_default_session", None)


def test_default_construction_is_isolated_by_conftest(tmp_path) -> None:
    """The conftest autouse pins both defaults of a bare ``LoginSession()``.

    A bare ``LoginSession()`` used to reach the real OS-backend probe (a
    Keychain write on macOS) and the real config dir; this anchor fails if
    the fixture stops patching ``_default_backend`` or ``default_config_dir``
    — e.g. after an upstream rename — so the isolation cannot silently rot.
    (``tmp_path`` here is the same instance the autouse fixture patched in.)
    """
    import chrys.kernel.aixcoding.auth.session as auth_session

    session = LoginSession()
    assert isinstance(session.store.backend, MemoryBackend)
    assert auth_session.default_config_dir() == tmp_path
