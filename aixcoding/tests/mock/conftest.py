# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""pytest fixtures for the mock contract tests (``aixcoding/tests/mock/``).

These fixtures are duplicated from ``tests/conftest.py`` (``direct_route`` and
its dependency ``clear_proxy_env``) rather than imported: upstream test
internals carry no stability promise, and the checker must not share a failure
domain with the checked (ADR-0001). If the upstream definitions in
``tests/conftest.py`` change, mirror the change here.

Only the minimum needed by the mock contract tests is exposed. The full suite
of repository-wide fixtures (textual dispatch, platform isolation, prompt
history, etc.) lives in ``tests/conftest.py`` and is intentionally **not**
applied here — this folder is a dev tool, not part of the product's test
surface.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest


@pytest.fixture
def clear_proxy_env(monkeypatch: pytest.MonkeyPatch) -> Callable[[], None]:
    """Return a helper that clears proxy-related env vars.

    Kept in sync with ``tests/conftest.py::clear_proxy_env``.
    """

    def _clear() -> None:
        for key in (
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "ALL_PROXY",
            "NO_PROXY",
            "http_proxy",
            "https_proxy",
            "all_proxy",
            "no_proxy",
        ):
            monkeypatch.delenv(key, raising=False)

    return _clear


@pytest.fixture
def direct_route(monkeypatch: pytest.MonkeyPatch, clear_proxy_env: Callable[[], None]) -> None:
    """Send HTTP straight to its host, as a loopback stub or an injected fault needs.

    With no proxy env at all, httpx falls back to the macOS/Windows system
    proxy. ``NO_PROXY='*'`` forces every request to bypass it.

    Kept in sync with ``tests/conftest.py::direct_route``.
    """
    clear_proxy_env()
    monkeypatch.setenv("NO_PROXY", "*")
