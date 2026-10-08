# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""AIxCoding device-code login: protocol client, storage, and crypto backends.

Public API -- import from :mod:`aixcoding.auth` rather than the submodules::

    from aixcoding.auth import AuthClient, CredentialStore, Environment, get_backend
    from aixcoding.auth import LoginSession, get_login_session
"""

from aixcoding.auth.client import AuthClient
from aixcoding.auth.crypto import get_backend
from aixcoding.auth.errors import (
    AuthError,
    AuthNetworkError,
    AuthServerError,
    DevicePollCancelled,
    DevicePollDenied,
    DevicePollTimeout,
    ProtectUnavailable,
)
from aixcoding.auth.session import LoginSession, get_login_session
from aixcoding.auth.storage import CredentialStore, default_config_dir
from aixcoding.auth.types import (
    CREDENTIAL_TTL_SECONDS,
    AccountInfo,
    DeviceCode,
    Environment,
    StoredCredential,
    TokenResult,
)

__all__ = [
    "CREDENTIAL_TTL_SECONDS",
    "AccountInfo",
    "AuthClient",
    "AuthError",
    "AuthNetworkError",
    "AuthServerError",
    "CredentialStore",
    "DeviceCode",
    "DevicePollCancelled",
    "DevicePollDenied",
    "DevicePollTimeout",
    "Environment",
    "LoginSession",
    "ProtectUnavailable",
    "StoredCredential",
    "TokenResult",
    "default_config_dir",
    "get_backend",
    "get_login_session",
]
