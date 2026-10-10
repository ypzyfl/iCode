# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Crypto backend tests.

DPAPI round trips run for real on Windows (this dev box); the macOS backend
exercises its CLI plumbing through a monkeypatched ``subprocess.run``; the
degradation path is driven by injecting failing factories.
"""

from __future__ import annotations

import subprocess
import sys

import pytest
from aixcoding.auth import crypto
from aixcoding.auth.crypto import (
    LABEL,
    MacOSSecurity,
    MemoryBackend,
    PlaintextBackend,
    get_backend,
)

PROBE = b"secret-token-bytes"


def test_memory_backend_round_trip_and_degraded() -> None:
    backend = MemoryBackend()
    assert backend.degraded
    token = backend.protect(PROBE)
    assert backend.unprotect(token) == PROBE


def test_memory_backend_rejects_unknown_token() -> None:
    backend = MemoryBackend()
    with pytest.raises(ValueError, match="not found"):
        backend.unprotect(b"never-issued")


def test_plaintext_backend_is_identity_and_degraded() -> None:
    backend = PlaintextBackend()
    assert backend.degraded
    assert backend.protect(PROBE) == PROBE
    assert backend.unprotect(PROBE) == PROBE


@pytest.mark.skipif(sys.platform != "win32", reason="DPAPI is Windows-only")
class TestWindowsDPAPI:
    def test_round_trip(self) -> None:
        from aixcoding.auth.crypto import WindowsDPAPI

        backend = WindowsDPAPI()
        assert not backend.degraded
        ciphertext = backend.protect(PROBE)
        assert ciphertext != PROBE
        assert backend.unprotect(ciphertext) == PROBE

    def test_wrong_label_fails(self) -> None:
        from aixcoding.auth.crypto import WindowsDPAPI

        backend = WindowsDPAPI()
        ciphertext = backend.protect(PROBE, label="other-purpose")
        with pytest.raises(OSError, match="DPAPI call failed"):
            backend.unprotect(ciphertext, label=LABEL)


class TestMacOSSecurity:
    def test_add_and_find_use_expected_cli_args(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[list[str]] = []

        def fake_run(args, **kwargs):
            calls.append(args)
            assert kwargs["timeout"] == 2
            if args[1] == "add-generic-password":
                return subprocess.CompletedProcess(args, 0, "", "")
            return subprocess.CompletedProcess(args, 0, "c2VjcmV0LXRva2VuLWJ5dGVz\n", "")

        monkeypatch.setattr(crypto.subprocess, "run", fake_run)
        backend = MacOSSecurity()
        account = backend.protect(PROBE)
        assert calls[0][:2] == ["/usr/bin/security", "add-generic-password"]
        assert backend.unprotect(account) == PROBE
        assert calls[1][:2] == ["/usr/bin/security", "find-generic-password"]

    def test_cli_failure_raises_oserror(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_run(args, **kwargs):
            return subprocess.CompletedProcess(args, 45, "", "keychain locked")

        monkeypatch.setattr(crypto.subprocess, "run", fake_run)
        backend = MacOSSecurity()
        with pytest.raises(OSError, match="keychain locked"):
            backend.protect(PROBE)


class TestGetBackend:
    def _with_factories(self, monkeypatch: pytest.MonkeyPatch, factories: list) -> None:
        monkeypatch.setattr(crypto, "_platform_factories", lambda: factories)

    def test_healthy_backend_wins(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._with_factories(monkeypatch, [PlaintextBackend])
        assert isinstance(get_backend(), PlaintextBackend)

    def test_failing_backend_degrades_to_memory(self, monkeypatch: pytest.MonkeyPatch) -> None:
        class Exploding:
            def __init__(self) -> None:
                raise OSError("headless session")

        self._with_factories(monkeypatch, [Exploding, MemoryBackend])
        assert isinstance(get_backend(), MemoryBackend)

    def test_corrupt_backend_degrades_to_memory(self, monkeypatch: pytest.MonkeyPatch) -> None:
        class Garbage:
            degraded = False

            def protect(self, plaintext: bytes, label: str = LABEL) -> bytes:
                return b"corrupted"

            def unprotect(self, ciphertext: bytes, label: str = LABEL) -> bytes:
                return b"not-the-original"

        self._with_factories(monkeypatch, [Garbage])
        assert isinstance(get_backend(), MemoryBackend)

    @pytest.mark.skipif(sys.platform != "win32", reason="probe targets the real DPAPI")
    def test_real_windows_probe_returns_dpapi(self) -> None:
        backend = get_backend()
        assert isinstance(backend, crypto.WindowsDPAPI)
        assert not backend.degraded
