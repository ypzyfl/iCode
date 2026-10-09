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

When iCode runs as a child of the AIxCoding desktop, the parent's login is
detected as a :class:`~aixcoding.auth.delegation.DelegatedCredential` and
shadows the store -- see :mod:`aixcoding.auth.delegation` for the contract.

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
from aixcoding.auth.delegation import DelegatedCredential, detect_delegation
from aixcoding.auth.environments import resolve_endpoints, resolve_environment
from aixcoding.auth.errors import AuthError, AuthServerError
from aixcoding.auth.storage import CredentialStore, default_config_dir
from aixcoding.auth.types import (
    AccountInfo,
    DeviceCode,
    Environment,
    StoredCredential,
)

#: Fixed poll cadence: the production reference ignores the server-sent
#: ``result.interval`` and repolls every second.
DEFAULT_POLL_INTERVAL = 1.0


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
        delegated: DelegatedCredential | None = None,
    ) -> None:
        """Build a session; every argument is optional (tests inject fakes).

        ``endpoints`` overrides environment-based URL resolution with an
        explicit ``(auth_url, data_url)`` -- used by tests against the loopback
        mock and by any deployment with unusual addressing.  ``delegated``
        pins a parent-provided credential; ``None`` (the default) auto-detects
        one from the frozen process environment.
        """
        self.environment = environment or resolve_environment()
        self._endpoints = endpoints
        self._store = CredentialStore(
            config_dir if config_dir is not None else default_config_dir(),
            backend if backend is not None else _default_backend(),
        )
        self._http = http
        self._delegated = delegated if delegated is not None else detect_delegation()
        self._delegated_rejected = False

    @property
    def store(self) -> CredentialStore:
        """The credential store -- exposed for tests and migrations."""
        return self._store

    @property
    def _active_delegated(self) -> DelegatedCredential | None:
        if self._delegated is None or self._delegated_rejected:
            return None
        return self._delegated

    @property
    def delegated_credential(self) -> DelegatedCredential | None:
        """The parent-provided credential while it shadows the store.

        ``None`` covers both "standalone process" and "the parent's token was
        rejected server-side" -- after a rejection the session falls back to
        the stored credential, if any, instead of reporting a login that no
        longer works.
        """
        return self._active_delegated

    @property
    def stored_token(self) -> str | None:
        """The live token, or ``None`` when absent/expired/corrupt.

        A delegation (desktop parent) wins over the store; after the server
        rejects the delegated token the store answers again.  This is the
        hand-off point for downstream consumers (post-login features attach
        it to their requests); it never performs network I/O.
        """
        delegated = self._active_delegated
        if delegated is not None:
            return delegated.token
        credential = self._store.load(self.environment)
        if credential is None or credential.is_expired or not credential.token:
            return None
        return credential.token

    @property
    def stored_user_id(self) -> str | None:
        """The logged-in user's id (``ehr``), or ``None`` without a live credential.

        The counterpart of :attr:`stored_token`: same source, same precedence
        (a delegation shadows the store), no network I/O. It exists because a
        request may need to *name* the user and not just authenticate as them
        — the remote model config is served per user, and falls back to a
        public default for an empty one.
        """
        delegated = self._active_delegated
        if delegated is not None:
            return delegated.ehr or None
        credential = self._store.load(self.environment)
        if credential is None or credential.is_expired:
            return None
        return credential.user_id or credential.ehr or None

    def _make_client(self) -> AuthClient:
        if self._endpoints is not None:
            auth_url, data_url = self._endpoints
        else:
            auth_url, data_url = resolve_endpoints(self.environment)
        return AuthClient(auth_url, data_url, http=self._http)

    async def check_silent(self) -> AccountInfo | None:
        """Startup check: the live credential validated against ``user/info``.

        ``None`` means "needs a login": nothing live, TTL elapsed, or the
        server could not be reached.  A stored credential the server rejects
        (``用户不存在``) is cleared so the next login starts clean, while a
        network failure keeps it -- being offline is not a logout.  A
        delegated credential follows the same split with one difference: the
        parent owns it, so a rejection only stops it from shadowing the store
        (nothing local is destroyed; the parent's re-login respawns us).
        """
        delegated = self._active_delegated
        if delegated is not None:
            try:
                return await self._make_client().fetch_user_info(delegated.token)
            except AuthServerError:
                self._delegated_rejected = True
                return None
            except AuthError:
                return None
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
        family); nothing is stored unless the full chain succeeds.  Under an
        active delegation the store write still happens but stays shadowed
        until the delegated token is rejected -- the parent's session wins.
        """
        client = self._make_client()
        token = await client.poll_token(
            device_code.device_code,
            interval=DEFAULT_POLL_INTERVAL,
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
        """Remove the credential for this environment (idempotent).

        A no-op while a delegation is active: the parent app owns that
        session, and only its own logout (or expiry) can end it -- the child
        cannot revoke the token server-side anyway.
        """
        if self._active_delegated is not None:
            return
        self._store.clear(self.environment)


_default_session: LoginSession | None = None


def get_login_session() -> LoginSession:
    """The process-wide session (see the module docstring for why it's one)."""
    global _default_session
    if _default_session is None:
        _default_session = LoginSession()
    return _default_session
