# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Core data types for the AIxCoding device-code login."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum

#: How long a stored credential stays valid. The token is opaque (never a
#: decoded JWT), so the client stamps its own local expiry; a stale value
#: surfaces as an HTTP failure on the next silent check and forces a re-login.
CREDENTIAL_TTL_SECONDS = 365 * 24 * 60 * 60

#: Schema version written inside the encrypted envelope's plaintext payload.
PAYLOAD_SCHEMA_VERSION = 2

#: Schema version written on the encrypted envelope itself.
ENVELOPE_SCHEMA_VERSION = 1

#: Purpose tag shared by the envelope and its payload.
PURPOSE = "account_auth"


class Environment(StrEnum):
    """Deployment the client talks to."""

    LOCAL = "local"
    DEV = "dev"
    PROD = "prod"


@dataclass(frozen=True, slots=True)
class DeviceCode:
    """A pending device authorization returned by ``/auth/device/code``."""

    device_code: str
    user_code: str
    verification_uri: str
    verification_uri_complete: str
    interval: int
    expires_in: int

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> DeviceCode:
        """Build one from the ``result`` object of a device/code response."""
        return cls(
            device_code=str(payload.get("device_code") or ""),
            user_code=str(payload.get("user_code") or ""),
            verification_uri=str(payload.get("verification_uri") or ""),
            verification_uri_complete=str(payload.get("verification_uri_complete") or ""),
            interval=int(payload.get("interval") or 0),
            expires_in=int(payload.get("expires_in") or 0),
        )


@dataclass(frozen=True, slots=True)
class TokenResult:
    """The token triple returned by ``/auth/device/token`` on success."""

    token: str
    refresh_token: str = ""
    token_type: str = ""
    expires_in: int = 0

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> TokenResult:
        """Build one from the ``result`` object of a device/token response.

        The wire contract offers both ``token`` and ``access_token``; the
        reference client prefers ``token`` (``WorkOsAuthProvider.ts:791``).
        """
        token = str(payload.get("token") or payload.get("access_token") or "")
        return cls(
            token=token,
            refresh_token=str(payload.get("refresh_token") or ""),
            token_type=str(payload.get("token_type") or ""),
            expires_in=int(payload.get("expires_in") or 0),
        )


@dataclass(frozen=True, slots=True)
class AccountInfo:
    """User identity fields returned by ``/user/info``."""

    ehr: str = ""
    name: str = ""
    region: str = ""
    dept_name: str = ""
    dept_id: str = ""
    is_st_wg: int = 0
    user_type: int = 0

    @property
    def display_name(self) -> str:
        """What the status surface shows: the name, falling back to the ehr."""
        return self.name or self.ehr

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> AccountInfo:
        """Build one from the ``data`` object of a user/info response."""
        return cls(
            ehr=str(payload.get("ehr") or ""),
            name=str(payload.get("name") or ""),
            region=str(payload.get("region") or ""),
            dept_name=str(payload.get("deptName") or ""),
            dept_id=str(payload.get("deptId") or ""),
            is_st_wg=int(payload.get("isStWg") or 0),
            user_type=int(payload.get("userType") or 0),
        )


@dataclass(frozen=True, slots=True)
class StoredCredential:
    """The plaintext payload that lives inside the encrypted envelope."""

    environment_id: str
    user_id: str
    token: str
    refresh_token: str = ""
    ehr: str = ""
    expires_at: float = 0.0
    schema_version: int = PAYLOAD_SCHEMA_VERSION
    purpose: str = field(default=PURPOSE)

    @property
    def is_expired(self) -> bool:
        """Whether the locally stamped TTL has elapsed."""
        return self.expires_at > 0 and time.time() >= self.expires_at

    @classmethod
    def issued_now(
        cls,
        environment_id: str,
        user_id: str,
        token: str,
        refresh_token: str = "",
        ehr: str = "",
        ttl_seconds: int = CREDENTIAL_TTL_SECONDS,
    ) -> StoredCredential:
        """Build a fresh credential stamped to expire ``ttl_seconds`` from now."""
        return cls(
            environment_id=environment_id,
            user_id=user_id,
            token=token,
            refresh_token=refresh_token,
            ehr=ehr,
            expires_at=time.time() + ttl_seconds,
        )

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> StoredCredential:
        """Rebuild one from a decrypted envelope payload (tolerating gaps)."""
        return cls(
            environment_id=str(payload.get("environmentId") or ""),
            user_id=str(payload.get("userId") or ""),
            token=str(payload.get("token") or ""),
            refresh_token=str(payload.get("refresh_token") or ""),
            ehr=str(payload.get("ehr") or ""),
            expires_at=float(payload.get("expiresAt") or 0.0),
            schema_version=int(payload.get("schemaVersion") or PAYLOAD_SCHEMA_VERSION),
            purpose=str(payload.get("purpose") or PURPOSE),
        )

    def to_payload(self) -> dict[str, object]:
        """Serialize to the JSON shape stored inside the envelope."""
        return {
            "schemaVersion": self.schema_version,
            "environmentId": self.environment_id,
            "userId": self.user_id,
            "ehr": self.ehr,
            "purpose": self.purpose,
            "token": self.token,
            "refresh_token": self.refresh_token,
            "expiresAt": self.expires_at,
        }
