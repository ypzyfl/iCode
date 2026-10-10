# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Shared fixtures for aixcoding TUI tests (mirrors tests/app/tui/conftest.py)."""

from __future__ import annotations

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
