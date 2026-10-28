# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Shared fixtures and wait helper for the aixcoding TUI tests.

Mirrors the theme-variable fixture the upstream TUI tests use and carries a
local ``wait_until`` equivalent: ADR-0001 keeps this tree from sharing a
failure domain with ``tests/support``.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from typing import Any

import pytest
from textual.app import App

from chrys.app.tui.theme import TUI_VARIABLE_DEFAULTS, with_tui_css_variables


@pytest.fixture(autouse=True)
def provide_tui_variable_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make lightweight Textual test apps resolve Chrys-specific CSS slots.

    Production always hosts these widgets in ``ChrysApp``, which provides the
    same defaults. Focused widget tests intentionally use a bare ``App`` to
    avoid constructing the full application shell.
    """
    original = App.get_theme_variable_defaults
    original_get_css_variables = App.get_css_variables

    def _get_theme_variable_defaults(app: App) -> dict[str, str]:
        return {**original(app), **TUI_VARIABLE_DEFAULTS}

    def _get_css_variables(app: App) -> dict[str, str]:
        variables = with_tui_css_variables(app.current_theme, original_get_css_variables(app))
        app.theme_variables = variables
        return variables

    monkeypatch.setattr(App, "get_theme_variable_defaults", _get_theme_variable_defaults)
    monkeypatch.setattr(App, "get_css_variables", _get_css_variables)


async def wait_until(
    predicate: Callable[[], object],
    *,
    timeout: float = 10.0,
    interval: float = 0.02,
    pilot: Any | None = None,
) -> bool:
    """Return whether *predicate* became truthy before the deadline.

    With a ``pilot`` the loop pumps the Textual event loop (``pause()``);
    without one it sleeps, so plain-asyncio callers work too. Polling avoids
    scheduler races seen on loaded Windows CI workers, where a single
    ``asyncio.sleep(0)`` may return before a fire-and-forget task runs.
    """
    deadline = time.monotonic() + timeout
    while True:
        if predicate():
            return True
        if pilot is not None:
            await pilot.pause()
        else:
            await asyncio.sleep(interval)
        if time.monotonic() >= deadline:
            return False
