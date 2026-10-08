# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Credential store tests: envelope shape, atomicity, corruption, isolation."""

from __future__ import annotations

import base64
import hashlib
import json

import pytest
from aixcoding.auth import Environment, StoredCredential
from aixcoding.auth.crypto import LABEL, MemoryBackend, PlaintextBackend
from aixcoding.auth.storage import POINTER_PREFIX, CredentialStore


@pytest.fixture
def store(tmp_path: pytest.TempPathFactory) -> CredentialStore:
    return CredentialStore(tmp_path, PlaintextBackend())


def make_credential(environment: Environment, token: str = "tok-1") -> StoredCredential:
    return StoredCredential.issued_now(
        environment_id=environment.value,
        user_id="8769092",
        token=token,
        refresh_token="ref-1",
        ehr="8769092",
    )


def test_round_trip(store: CredentialStore, tmp_path: pytest.TempPathFactory) -> None:
    store.store(Environment.PROD, make_credential(Environment.PROD))
    loaded = store.load(Environment.PROD)
    assert loaded is not None
    assert loaded.token == "tok-1"
    assert loaded.ehr == "8769092"
    assert not loaded.is_expired


def test_pointer_file_holds_no_token(store: CredentialStore) -> None:
    store.store(Environment.PROD, make_credential(Environment.PROD, token="sekrit"))
    pointer = (store._pointer_path(Environment.PROD)).read_text(encoding="utf-8").strip()
    assert pointer.startswith(POINTER_PREFIX)
    assert len(pointer.removeprefix(POINTER_PREFIX)) == 32
    assert "sekrit" not in pointer


def test_envelope_is_ciphertext_not_plaintext(store: CredentialStore) -> None:
    store.store(Environment.PROD, make_credential(Environment.PROD, token="sekrit"))
    secret_id = store._read_pointer(Environment.PROD)
    envelope_path = store._secrets_dir(Environment.PROD) / f"{secret_id}.json"
    raw = envelope_path.read_text(encoding="utf-8")
    assert "sekrit" not in raw
    envelope = json.loads(raw)
    assert envelope["schemaVersion"] == 1
    assert envelope["purpose"] == "account_auth"
    # Plaintext backend means the ciphertext decodes to the payload JSON.
    payload = base64.b64decode(envelope["ciphertext"]).decode("utf-8")
    assert json.loads(payload)["token"] == "sekrit"


def test_sha256_stamp_matches_ciphertext(store: CredentialStore) -> None:
    store.store(Environment.PROD, make_credential(Environment.PROD))
    secret_id = store._read_pointer(Environment.PROD)
    envelope = json.loads((store._secrets_dir(Environment.PROD) / f"{secret_id}.json").read_text(encoding="utf-8"))
    assert envelope["ciphertextSha256"] == hashlib.sha256(base64.b64decode(envelope["ciphertext"])).hexdigest()


def test_tampered_envelope_resolves_to_none_and_cleans_pointer(store: CredentialStore) -> None:
    store.store(Environment.PROD, make_credential(Environment.PROD))
    secret_id = store._read_pointer(Environment.PROD)
    envelope_path = store._secrets_dir(Environment.PROD) / f"{secret_id}.json"
    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    envelope["ciphertext"] = base64.b64encode(b"tampered-bytes").decode("ascii")
    envelope_path.write_text(json.dumps(envelope), encoding="utf-8")

    assert store.load(Environment.PROD) is None
    assert store._read_pointer(Environment.PROD) is None
    assert not envelope_path.exists()


def test_unprotect_failure_resolves_to_none(tmp_path: pytest.TempPathFactory) -> None:
    class DeadBackend(PlaintextBackend):
        def unprotect(self, ciphertext: bytes, label: str = LABEL) -> bytes:
            raise OSError("keychain locked mid-read")

    store = CredentialStore(tmp_path, DeadBackend())
    store.store(Environment.PROD, make_credential(Environment.PROD))
    assert store.load(Environment.PROD) is None
    assert store._read_pointer(Environment.PROD) is None


def test_environments_are_isolated(store: CredentialStore) -> None:
    store.store(Environment.PROD, make_credential(Environment.PROD, token="prod-tok"))
    store.store(Environment.LOCAL, make_credential(Environment.LOCAL, token="local-tok"))
    assert store.load(Environment.PROD) is not None and store.load(Environment.PROD).token == "prod-tok"
    assert store.load(Environment.LOCAL) is not None and store.load(Environment.LOCAL).token == "local-tok"


def test_clear_removes_everything(store: CredentialStore) -> None:
    store.store(Environment.PROD, make_credential(Environment.PROD))
    secret_id = store._read_pointer(Environment.PROD)
    store.clear(Environment.PROD)
    assert store.load(Environment.PROD) is None
    assert not (store._secrets_dir(Environment.PROD) / f"{secret_id}.json").exists()
    assert not store._pointer_path(Environment.PROD).exists()


def test_clear_without_credential_is_a_noop(store: CredentialStore) -> None:
    store.clear(Environment.DEV)
    assert store.load(Environment.DEV) is None


def test_load_without_pointer_returns_none(store: CredentialStore) -> None:
    assert store.load(Environment.PROD) is None


def test_no_temp_files_left_behind(store: CredentialStore) -> None:
    store.store(Environment.PROD, make_credential(Environment.PROD))
    leftovers = [p.name for p in store._secrets_dir(Environment.PROD).iterdir() if p.name.endswith(".tmp")]
    assert leftovers == []


def test_memory_backend_never_touches_disk(tmp_path: pytest.TempPathFactory) -> None:
    store = CredentialStore(tmp_path, MemoryBackend())
    store.store(Environment.PROD, make_credential(Environment.PROD))
    assert store.load(Environment.PROD).token == "tok-1"
    assert not (tmp_path / "users").exists()
    store.clear(Environment.PROD)
    assert store.load(Environment.PROD) is None


def test_purpose_mismatch_rejects_payload(store: CredentialStore) -> None:
    store.store(Environment.PROD, make_credential(Environment.PROD))
    secret_id = store._read_pointer(Environment.PROD)
    envelope_path = store._secrets_dir(Environment.PROD) / f"{secret_id}.json"
    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    payload = json.loads(base64.b64decode(envelope["ciphertext"]).decode("utf-8"))
    payload["purpose"] = "something-else"
    forged = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    envelope["ciphertext"] = base64.b64encode(forged).decode("ascii")
    envelope["ciphertextSha256"] = hashlib.sha256(forged).hexdigest()
    envelope_path.write_text(json.dumps(envelope), encoding="utf-8")

    assert store.load(Environment.PROD) is None
