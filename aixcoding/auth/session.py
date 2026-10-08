# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Login session: the boundary between the login feature and everything after.

The device-code flow itself lives in :class:`~aixcoding.auth.client.AuthClient`
and persistence in :class:`~aixcoding.auth.storage.CredentialStore`; this module
binds them into the single object the rest of the app talks to::

    session = get_login_session()

    account = await session.check_silent()      # startup: None => not logged in
    if account is None:
        code = await session.request_device_code()
        ...                                     # UI shows the code, opens browser
        account = await session.complete_login(code)
    token = session.stored_token                # downstream consumers attach this
    session.logout()                            # /logout

The module-level :func:`get_login_session` is a process-wide singleton on
purpose: when the crypto backend degrades to :class:`~aixcoding.auth.crypto.MemoryBackend`
the credential lives inside the backend instance, so every caller must share
one session or "logged in" state would fragment.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import httpx

from aixcoding.auth.client import AuthClient
from aixcoding.auth.crypto import ProtectBackend
from aixcoding.auth.environments import resolve_endpoints, resolve_environment
from aixcoding.auth.errors import AuthError, AuthServerError
from aixcoding.auth.storage import CredentialStore, default_config_dir
from aixcoding.auth.types import (
    AccountInfo,
    DeviceCode,
    Environment,
    StoredCredential,
)

#: Seed interval when the server did not send one.
DEFAULT_POLL_INTERVAL = 5.0


def _default_backend() -> ProtectBackend:
    """Resolve the OS crypto backend lazily (probe runs only when needed)."""
    from aixcoding.auth.crypto import get_backend

    return get_backend()


class LoginSession:
    """One environment's login state: silent check, login flow, logout."""

    def __init__(
        self,
        *,
        environment: Environment | None = None,
        endpoints: tuple[str, str] | None = None,
        config_dir: Path | None = None,
        backend: ProtectBackend | None = None,
        http: httpx.AsyncClient | None = None,
    ) -> None:
        """Build a session; every argument is optional (tests inject fakes).

        ``endpoints`` overrides environment-based URL resolution with an
        explicit ``(auth_url, data_url)`` -- used by tests against the loopback
        mock and by any deployment with unusual addressing.
        """
        self.environment = environment or resolve_environment()
        self._endpoints = endpoints
        self._store = CredentialStore(
            config_dir if config_dir is not None else default_config_dir(),
            backend if backend is not None else _default_backend(),
        )
        self._http = http

    @property
    def store(self) -> CredentialStore:
        """The credential store -- exposed for tests and migrations."""
        return self._store

    @property
    def stored_token(self) -> str | None:
        """The live token, or ``None`` when absent/expired/corrupt.

        This is the hand-off point for downstream consumers (post-login
        features attach it to their requests); it never performs network I/O.
        """
        credential = self._store.load(self.environment)
        if credential is None or credential.is_expired or not credential.token:
            return None
        return credential.token

    def _make_client(self) -> AuthClient:
        if self._endpoints is not None:
            auth_url, data_url = self._endpoints
        else:
            auth_url, data_url = resolve_endpoints(self.environment)
        return AuthClient(auth_url, data_url, http=self._http)

    async def check_silent(self) -> AccountInfo | None:
        """Startup check: a stored credential validated against ``user/info``.

        ``None`` means "needs a login": nothing stored, TTL elapsed, or the
        server could not be reached. A server-side rejection (``用户不存在``)
        additionally clears the dead credential so the next login starts
        clean; a network failure keeps it -- being offline is not a logout.
        """
        credential = self._store.load(self.environment)
        if credential is None or credential.is_expired or not credential.token:
            return None
        try:
            return await self._make_client().fetch_user_info(credential.token)
        except AuthServerError:
            self._store.clear(self.environment)
            return None
        except AuthError:
            return None

    async def request_device_code(self) -> DeviceCode:
        """Start a device authorization (the UI shows the returned code)."""
        return await self._make_client().request_device_code()

    async def complete_login(
        self,
        device_code: DeviceCode,
        *,
        cancel_event: asyncio.Event | None = None,
    ) -> AccountInfo:
        """Poll the grant to its end, store the credential, return the user.

        Raises on every non-happy path (:class:`~aixcoding.auth.errors.AuthError`
        family); nothing is stored unless the full chain succeeds.
        """
        client = self._make_client()
        token = await client.poll_token(
            device_code.device_code,
            interval=device_code.interval if device_code.interval > 0 else DEFAULT_POLL_INTERVAL,
            cancel_event=cancel_event,
        )
        account = await client.fetch_user_info(token.token)
        self._store.store(
            self.environment,
            StoredCredential.issued_now(
                environment_id=self.environment.value,
                user_id=account.ehr,
                token=token.token,
                refresh_token=token.refresh_token,
                ehr=account.ehr,
            ),
        )
        return account

    def logout(self) -> None:
        """Remove the credential for this environment (idempotent)."""
        self._store.clear(self.environment)


_default_session: LoginSession | None = None


def get_login_session() -> LoginSession:
    """The process-wide session (see the module docstring for why it's one)."""
    global _default_session
    if _default_session is None:
        _default_session = LoginSession()
    return _default_session
