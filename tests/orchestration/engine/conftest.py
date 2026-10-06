# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Shared fixtures for engine tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from chrys.foundation.platform import get_platform


@pytest.fixture
def _isolate_hook_config_dir(_isolate_platform_config_dir: None) -> Path:
    """Expose the already isolated platform directory to hook-writing tests."""
    return get_platform().config_dir


@pytest.fixture
def _no_aixcoding_telemetry_install(monkeypatch: pytest.MonkeyPatch) -> None:
    # [AIxCoding M-005] Tests that assert the engine's own empty-hooks
    # contract (no manager / no runtime dirs / exactly the user's entries)
    # must opt out of the fork's per-session-start collector installer
    # (M-001), which otherwise always injects the two aixcoding-collector
    # entries into the isolated config dir.
    from chrys.aixcoding.telemetry import install as install_module

    monkeypatch.setattr(install_module, "ensure_telemetry_hooks", lambda: None)


@pytest.fixture(autouse=True)
def _workspace_change_notice_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable advisory scans for engine tests that load settings from the env.

    These tests build real engines whose workspace is the developer
    checkout; the default-enabled notice would capture and diff it with
    Git subprocesses on every turn — pure overhead that pushes slow CI
    hosts past fixed polling timeouts. Direct ``Settings(...)`` construction
    does not read this environment variable: mock factories must explicitly
    pass ``workspace_change_notice=False``. Notice tests use explicit
    ``Settings(workspace_change_notice=True)``.
    """
    monkeypatch.setenv("CHRYS_WORKSPACE_CHANGE_NOTICE", "0")
