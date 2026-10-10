# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Manual local verification: pop the real LoginDialog (TUI) in a live terminal.

No ``src/chrys`` wiring needed (the ``/login`` command is not implemented yet):
this file is a minimal Textual host for the dialog.

Usage (two terminals, both in the repository root):

    terminal 1:  uv run python mock_server/aixcoding_auth/server.py   # mock auth service :7777
    terminal 2:  uv run python verify_login_dialog.py                 # this file must sit in the root

Flow:
    1. the dialog shows the user code (e.g. ABCD-EFGH) and opens the verify
       page in the browser automatically;
    2. click "Confirm authorization" in the browser;
    3. the dialog closes itself and the terminal prints the login result
       (dayanmao / Shanghai branch tech platform R&D dept).

Other branches:
    * press Esc or click the cancel button -> aborts, nothing is stored;
    * terminal 1 not running the mock     -> the dialog shows the
      "cannot obtain the login code" error message;
    * click "Deny" on the verify page     -> the dialog shows "login unfinished".

The credential is really written to %APPDATA%/chrys/users/local/ (DPAPI
encrypted). See codingExplan/启动与登录人工验证指南.md section 6 for logout
and storage inspection.
"""

from __future__ import annotations

from textual.app import App

from aixcoding.auth import AccountInfo, LoginSession
from aixcoding.auth.types import Environment
from aixcoding.tui import LoginDialog
from chrys.app.tui.theme import TUI_VARIABLE_DEFAULTS, with_tui_css_variables


def _install_tui_css_variables() -> None:
    """Let a bare ``App`` resolve the ``$tui-*`` variables used by login.tcss.

    Production hosts these widgets inside ``ChrysApp``, which provides the
    variables; the focused tests (tests/app/aixcoding/conftest.py) inject the
    same defaults onto a bare ``App``. This script mirrors that injection so it
    stays isomorphic to the tested path.
    """
    original_defaults = App.get_theme_variable_defaults
    original_variables = App.get_css_variables

    def _defaults(app: App) -> dict[str, str]:
        return {**original_defaults(app), **TUI_VARIABLE_DEFAULTS}

    def _variables(app: App) -> dict[str, str]:
        merged = with_tui_css_variables(app.current_theme, original_variables(app))
        app.theme_variables = merged
        return merged

    App.get_theme_variable_defaults = _defaults  # type: ignore[method-assign]
    App.get_css_variables = _variables  # type: ignore[method-assign]


class LoginProbeApp(App):
    """Minimal host: mount the LoginDialog, bring the dismiss result back."""

    def on_mount(self) -> None:
        # The LOCAL tier points at http://localhost:7777/api/v1 -- the aixcoding_auth mock default.
        session = LoginSession(environment=Environment.LOCAL)
        self.push_screen(LoginDialog(session=session), self._on_dialog_done)

    def _on_dialog_done(self, account: AccountInfo | None) -> None:
        self.exit(account)


def main() -> None:
    _install_tui_css_variables()
    result = LoginProbeApp().run()
    if result is None:
        print("已取消登录（未存储任何凭据）。")
        return
    print(f"登录成功：{result.display_name} / {result.dept_name}（ehr={result.ehr}）")


if __name__ == "__main__":
    main()
