# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Credential storage: encrypted envelope plus a plaintext pointer file.

Layout under ``<config_dir>/users/<environment>/`` (the host app's config dir:
``%APPDATA%/chrys`` on Windows, ``~/.chrys`` elsewhere)::

    current                      # pointer: "secret:v1:<32hex>" -- never the token
    private/secrets/<32hex>.json # {"schemaVersion": 1, "purpose": "account_auth",
                                 #  "ciphertext": "<b64>", "ciphertextSha256": "<hex64>"}

Design points (mirroring the reference app's ``safeStorage`` scheme):

* the plaintext token exists only inside the encrypted envelope
* writes are atomic (temp file + ``os.replace``) and integrity-stamped
* corruption (sha256 mismatch, unprotect failure, torn JSON) resolves to
  "no credential": the pointer is cleared and the user simply logs in again
* a non-persistent backend (:class:`~aixcoding.auth.crypto.MemoryBackend`)
  keeps the credential in RAM only -- nothing touches disk
* POSIX-only hardening: 0700 dirs, 0600 files, ``O_NOFOLLOW`` opens
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import json
import os
import secrets
import sys
from pathlib import Path

from aixcoding.auth.crypto import LABEL, MemoryBackend, ProtectBackend
from aixcoding.auth.types import (
    ENVELOPE_SCHEMA_VERSION,
    PURPOSE,
    Environment,
    StoredCredential,
)

POINTER_PREFIX = "secret:v1:"


def default_config_dir() -> Path:
    """The host app's config dir, falling back to ``~/.chrys``.

    ``chrys.foundation.platform`` owns the canonical location; the lazy
    import keeps this module usable even when the host app is absent.
    """
    try:
        from chrys.foundation.platform import get_platform

        return Path(get_platform().config_dir)
    except Exception:
        return Path.home() / ".chrys"


class CredentialStore:
    """Store, load, and clear one credential per environment."""

    def __init__(self, config_dir: Path, backend: ProtectBackend) -> None:
        self._config_dir = Path(config_dir)
        self._backend = backend
        self._ram: dict[Environment, StoredCredential] = {}

    @property
    def backend(self) -> ProtectBackend:
        """The encryption backend this store writes through."""
        return self._backend

    def _user_dir(self, environment: Environment) -> Path:
        return self._config_dir / "users" / environment.value

    def _pointer_path(self, environment: Environment) -> Path:
        return self._user_dir(environment) / "current"

    def _secrets_dir(self, environment: Environment) -> Path:
        return self._user_dir(environment) / "private" / "secrets"

    def store(self, environment: Environment, credential: StoredCredential) -> None:
        """Persist ``credential`` for ``environment`` (RAM-only if degraded)."""
        if isinstance(self._backend, MemoryBackend):
            self._ram[environment] = credential
            return
        user_dir = self._user_dir(environment)
        secrets_dir = self._secrets_dir(environment)
        _ensure_private_tree(user_dir, secrets_dir)
        secret_id = secrets.token_hex(16)
        payload = json.dumps(credential.to_payload(), ensure_ascii=False).encode("utf-8")
        ciphertext = self._backend.protect(payload, label=LABEL)
        envelope = {
            "schemaVersion": ENVELOPE_SCHEMA_VERSION,
            "purpose": PURPOSE,
            "ciphertext": _b64encode(ciphertext),
            "ciphertextSha256": hashlib.sha256(ciphertext).hexdigest(),
        }
        _atomic_write_json(secrets_dir / f"{secret_id}.json", envelope)
        _atomic_write_text(self._pointer_path(environment), f"{POINTER_PREFIX}{secret_id}")

    def load(self, environment: Environment) -> StoredCredential | None:
        """Return the stored credential, or ``None`` for absent/corrupt/expunged.

        Corruption cleans up after itself: the pointer is removed so the next
        login starts fresh instead of hitting the same dead envelope forever.
        """
        if isinstance(self._backend, MemoryBackend):
            return self._ram.get(environment)
        secret_id = self._read_pointer(environment)
        if secret_id is None:
            return None
        envelope_path = self._secrets_dir(environment) / f"{secret_id}.json"
        try:
            envelope = json.loads(_open_no_follow(envelope_path).decode("utf-8"))
            ciphertext = _b64decode(str(envelope.get("ciphertext") or ""))
            if hashlib.sha256(ciphertext).hexdigest() != envelope.get("ciphertextSha256"):
                raise ValueError("ciphertext sha256 mismatch")
            payload = json.loads(self._backend.unprotect(ciphertext, label=LABEL).decode("utf-8"))
        except OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError:
            self.clear(environment)
            return None
        if payload.get("purpose") != PURPOSE or payload.get("environmentId") != environment.value:
            self.clear(environment)
            return None
        return StoredCredential.from_payload(payload)

    def clear(self, environment: Environment) -> None:
        """Remove the credential for ``environment`` (absent is fine)."""
        self._ram.pop(environment, None)
        secret_id = self._read_pointer(environment)
        if secret_id is not None:
            envelope = self._secrets_dir(environment) / f"{secret_id}.json"
            _silent_unlink(envelope)
        _silent_unlink(self._pointer_path(environment))

    def _read_pointer(self, environment: Environment) -> str | None:
        try:
            raw = _open_no_follow(self._pointer_path(environment)).decode("utf-8").strip()
        except OSError, UnicodeDecodeError:
            return None
        if not raw.startswith(POINTER_PREFIX):
            return None
        secret_id = raw.removeprefix(POINTER_PREFIX)
        return secret_id or None


def _ensure_private_tree(user_dir: Path, secrets_dir: Path) -> None:
    secrets_dir.mkdir(parents=True, exist_ok=True)
    if sys.platform != "win32":
        os.chmod(user_dir, 0o700)
        os.chmod(secrets_dir, 0o700)


def _atomic_write_bytes(path: Path, data: bytes, mode: int) -> None:
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(tmp, flags, mode)
    try:
        os.write(fd, data)
    finally:
        os.close(fd)
    if sys.platform != "win32":
        os.chmod(tmp, mode)
    os.replace(tmp, path)


def _atomic_write_json(path: Path, payload: dict[str, object]) -> None:
    mode = 0o600 if sys.platform != "win32" else 0o666
    _atomic_write_bytes(path, json.dumps(payload, ensure_ascii=False).encode("utf-8"), mode)


def _atomic_write_text(path: Path, text: str) -> None:
    mode = 0o600 if sys.platform != "win32" else 0o666
    _atomic_write_bytes(path, text.encode("utf-8"), mode)


def _open_no_follow(path: Path) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        chunks: list[bytes] = []
        while chunk := os.read(fd, 65536):
            chunks.append(chunk)
    finally:
        os.close(fd)
    return b"".join(chunks)


def _silent_unlink(path: Path) -> None:
    with contextlib.suppress(OSError):
        os.unlink(path)


def _b64encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _b64decode(text: str) -> bytes:
    return base64.b64decode(text, validate=True)
