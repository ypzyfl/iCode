"""Shared fixtures for the auth tests (migrated + wiring).

Design: aixcoding/docs/batches/auth/design.md (signed off 2026-10-26).
"""

from __future__ import annotations

from pathlib import Path

import pytest

import chrys.kernel.aixcoding.auth.session as auth_session
from chrys.kernel.aixcoding.auth.crypto import MemoryBackend


def pytest_configure(config: pytest.Config) -> None:
    """Register the opt-out markers locally (pyproject is upstream-owned)."""
    config.addinivalue_line(
        "markers",
        "allow_delegation_detect: this test exercises delegation auto-detection itself",
    )
    config.addinivalue_line(
        "markers",
        "real_platform_backend: this test needs the real OS crypto backend probe",
    )


@pytest.fixture(autouse=True)
def _no_delegated_credential(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin delegation detection off for every auth test.

    The compat channel reads the real process environment (the
    ``OPENAI_API_KEY`` + ``AIXCODING_USER_EHR`` pair), which a developer shell
    may legitimately export -- without this pin, tests that build a
    ``LoginSession`` without an explicit ``delegated=`` would branch on the
    machine's environment instead of the code under test. Tests that exercise
    the detection itself opt out with ``@pytest.mark.allow_delegation_detect``.
    """
    if request.node.get_closest_marker("allow_delegation_detect") is not None:
        return
    monkeypatch.setattr(auth_session, "detect_delegation", lambda: None)


@pytest.fixture(autouse=True)
def _isolated_default_construction(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Pin default ``LoginSession()`` construction to a tmp dir and MemoryBackend.

    The defaults (``config_dir=None``, ``backend=None``) resolve to the real
    user config dir and a real OS-backend probe: on macOS the probe writes a
    Keychain item via ``security add-generic-password`` (never cleaned up), on
    Windows it round-trips real DPAPI. Tests that build a session without
    explicit arguments get the isolated defaults instead; the crypto backend
    tests construct platform backends directly and never pass through
    ``_default_backend``, so they are unaffected. A test that needs the real
    default probe opts out with ``@pytest.mark.real_platform_backend``.
    """
    if request.node.get_closest_marker("real_platform_backend") is not None:
        return
    monkeypatch.setattr(auth_session, "default_config_dir", lambda: tmp_path)
    monkeypatch.setattr(auth_session, "_default_backend", MemoryBackend)
