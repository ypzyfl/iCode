# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# ruff: noqa: S101

"""/login and /logout registration in the slash command table."""

from __future__ import annotations

from unittest.mock import MagicMock

from chrys.app.tui.screens.main.buddy_command import BuddyCommandController
from chrys.app.tui.screens.main.commands import MainSlashCommandRegistry
from chrys.foundation.i18n import Localizer


def _build() -> tuple[list, MagicMock]:
    localizer = Localizer("zh-Hans")
    actions = MagicMock()
    registry = MainSlashCommandRegistry(
        actions=actions,
        buddy=BuddyCommandController(MagicMock(), render_message=localizer.render),
        render_message=localizer.render,
    )
    registry.build()
    return registry.commands, actions


def test_login_and_logout_are_registered() -> None:
    commands, _actions = _build()
    names = [command.name for command in commands]

    assert "login" in names
    assert "logout" in names


def test_login_logout_stay_usable_while_running() -> None:
    commands, _actions = _build()
    login = next(command for command in commands if command.name == "login")
    logout = next(command for command in commands if command.name == "logout")

    assert login.allow_while_running
    assert logout.allow_while_running


def test_login_logout_actions_forward_to_the_port() -> None:
    commands, actions = _build()
    login = next(command for command in commands if command.name == "login")
    logout = next(command for command in commands if command.name == "logout")

    login.action("")
    login.action("ignored")
    logout.action("")

    assert actions.open_login_dialog.call_count == 2
    assert actions.perform_logout.call_count == 1


def test_login_logout_man_pages_auto_indexed() -> None:
    commands, _actions = _build()
    login = next(command for command in commands if command.name == "login")
    logout = next(command for command in commands if command.name == "logout")
    man = next(command for command in commands if command.name == "man")

    assert login.man_page is not None
    assert logout.man_page is not None
    # /man subcommand completion sweeps the registry automatically.
    assert man.subcommands is not None
    indexed = [value for value, _label in man.subcommands()]
    assert "login" in indexed
    assert "logout" in indexed
