# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Error taxonomy for the AIxCoding device-code login.

Every failure the login flow can raise derives from :class:`AuthError`, so
wiring code in ``src/chrys`` needs a single ``except AuthError`` to surface a
 readable message without leaking internals.
"""

from __future__ import annotations


class AuthError(Exception):
    """Base class for every login failure."""


class AuthNetworkError(AuthError):
    """A transport-level failure (DNS, connect, timeout, malformed JSON)."""


class AuthServerError(AuthError):
    """The backend answered with an unusable envelope (missing result/token)."""


class DevicePollDenied(AuthError):
    """The user denied the authorization, or the device code expired.

    Carries the OAuth device-flow error string (``access_denied`` or
    ``expired_token``) so callers can render a precise message.
    """

    def __init__(self, error: str) -> None:
        super().__init__(f"device authorization ended: {error}")
        self.error = error


class DevicePollTimeout(AuthError):
    """The 15-minute overall polling budget elapsed without a decision."""


class DevicePollCancelled(AuthError):
    """The caller cancelled the poll (dialog closed, app shutting down)."""


class ProtectUnavailable(AuthError):
    """No usable OS-level encryption backend exists on this machine.

    Storage degrades to an in-memory backend instead of raising this; the
    error exists for callers that must refuse to continue without at-rest
    protection.
    """
