# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""AIxCoding device-code login: protocol client, storage, and crypto backends.

Public API -- import from :mod:`chrys.aixcoding.auth` rather than the submodules::

    from chrys.aixcoding.auth import AuthClient, CredentialStore, Environment, get_backend
    from chrys.aixcoding.auth import LoginSession, get_login_session
    from chrys.aixcoding.auth import DelegatedCredential, detect_delegation
"""

from chrys.aixcoding.auth.client import AuthClient
from chrys.aixcoding.auth.crypto import get_backend
from chrys.aixcoding.auth.delegation import (
    COMPAT_EHR_VARIABLE,
    COMPAT_TOKEN_VARIABLE,
    DELEGATED_EHR_VARIABLE,
    DELEGATED_NAME_VARIABLE,
    DELEGATED_TOKEN_VARIABLE,
    DelegatedCredential,
    detect_delegation,
)
from chrys.aixcoding.auth.errors import (
    AuthError,
    AuthNetworkError,
    AuthServerError,
    DevicePollCancelled,
    DevicePollDenied,
    DevicePollTimeout,
    ProtectUnavailable,
)
from chrys.aixcoding.auth.session import LoginSession, get_login_session
from chrys.aixcoding.auth.storage import CredentialStore, default_config_dir
from chrys.aixcoding.auth.types import (
    CREDENTIAL_TTL_SECONDS,
    AccountInfo,
    DeviceCode,
    Environment,
    StoredCredential,
    TokenResult,
)

__all__ = [
    "COMPAT_EHR_VARIABLE",
    "COMPAT_TOKEN_VARIABLE",
    "CREDENTIAL_TTL_SECONDS",
    "DELEGATED_EHR_VARIABLE",
    "DELEGATED_NAME_VARIABLE",
    "DELEGATED_TOKEN_VARIABLE",
    "AccountInfo",
    "AuthClient",
    "AuthError",
    "AuthNetworkError",
    "AuthServerError",
    "CredentialStore",
    "DelegatedCredential",
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
    "detect_delegation",
    "get_backend",
    "get_login_session",
]
