# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""AIxCoding TUI widgets: the device-code login dialog.

Text lives here as Chinese-only constants by design (ADR-0010): the i18n
scanner covers ``src/chrys``, so the shell-wrapped ``msg(key, fallback=中文)``
constants for the ``/login``/``/logout`` command descriptions live in
``login_actions.py`` (inside the extract scope) and everything else ships
inline Chinese.

``LoginDialog`` resolves lazily (PEP 562): importing ``login_actions`` for
the startup silent check must not load the dialog's Textual widget tree.

Design: aixcoding/docs/tui/design.md
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chrys.app.aixcoding.tui.login import LoginDialog

__all__ = ["LoginDialog"]


def __getattr__(name: str) -> object:
    if name == "LoginDialog":
        from chrys.app.aixcoding.tui.login import LoginDialog

        return LoginDialog
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
