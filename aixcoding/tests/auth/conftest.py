"""Shared fixtures for the auth tests (migrated + wiring).

Design: aixcoding/docs/batches/auth/design.md (signed off 2026-10-26).
"""

from __future__ import annotations

import pytest

import chrys.kernel.aixcoding.auth.session as auth_session


def pytest_configure(config: pytest.Config) -> None:
    """Register the opt-out marker locally (pyproject is upstream-owned)."""
    config.addinivalue_line(
        "markers",
        "allow_delegation_detect: this test exercises delegation auto-detection itself",
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
