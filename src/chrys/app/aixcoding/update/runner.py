# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Exit-update-relaunch orchestration (design §3.4).

"Update now" hands the work to a detached wrapper process and exits the
TUI: the package installer refuses to run while a Chrys instance is alive,
so the wrapper first waits for this process to disappear, then runs the
internal install command, and on success relaunches the TUI with the
current session restored.  A failure appends one line to the tally file,
prints the error, and stops (design Q4) — the user relaunches by hand.

The wrapper's only file operation is that failure append (design D2):
consuming and resetting the tally is the flow's job on the next start.

Design: aixcoding/docs/batches/auto-update/design.md
"""

from __future__ import annotations

import logging
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from chrys.foundation.branding import APP_COMMAND

from .commands import install_script_url

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from collections.abc import Callable

_FAILURE_MESSAGE = "Update failed - see the output above."
# The wrapper outlives the TUI detached, so whether this hint lands before or
# after the shell's prompt is a race: phrase it conditionally (the prompt may
# already be on screen) — owner decision, design revision 10.
_PROMPT_HINT = "如未出现命令提示符，请按回车返回命令行。"
_MANUAL_RELAUNCH_HINT = "更新完成。当前环境无法打开新终端窗口，请手动运行 aixcoding-cli 启动。"


def relaunch_argv(session_id: str | None) -> list[str]:
    """The argv that restarts the TUI, restoring ``session_id`` when known.

    Resolved *before* the TUI exits (design D3).  The installer puts the
    product command on the user's PATH, so the relaunch launches by the bare
    command name — the new-window launchers resolve it through the wrapper's
    inherited PATH.  The bare name is trusted only after ``which`` proves it
    resolves in this process's environment; otherwise the resolved
    ``sys.argv[0]`` is the fallback — the entry script PyApp runs this
    process with, whose offline-flavor shebang names a build-machine
    interpreter that does not exist on the user machine (found in the first
    real update, 2026-11-19).
    """
    executable = APP_COMMAND if shutil.which(APP_COMMAND) else str(Path(sys.argv[0]).resolve())
    argv = [executable]
    if session_id:
        argv += ["-s", session_id]
    return argv


def _posix_relaunch_snippet(argv: list[str]) -> str:
    """A sh snippet that launches ``argv`` in a NEW terminal window.

    The wrapper shares the terminal the TUI just left: an in-place relaunch
    interleaves the TUI with the user's shell (seen in the first real update,
    2026-11-19).  macOS opens a Terminal.app window via osascript; Linux walks
    the common terminal emulators (x-terminal-emulator covers the Debian
    alternatives system, then gnome-terminal/konsole/xterm); a windowless
    environment (SSH, headless) prints the manual-relaunch hint instead.  The
    update itself is already complete by this point, so no branch here can
    change the update's outcome — the design revision 21 decision is comfort,
    not correctness.
    """
    command = " ".join(shlex.quote(part) for part in argv)
    if sys.platform == "darwin":
        apple = command.replace("\\", "\\\\").replace('"', '\\"')
        return (
            f'osascript -e \'tell application "Terminal" to do script "{apple}"\' '
            f">/dev/null || echo {_MANUAL_RELAUNCH_HINT!r} >&2"
        )
    quoted = shlex.quote(command)
    return (
        f"cmd={quoted}; "
        "if command -v x-terminal-emulator >/dev/null 2>&1; then "
        'x-terminal-emulator -e sh -c "$cmd" & '
        "elif command -v gnome-terminal >/dev/null 2>&1; then "
        'gnome-terminal -- sh -c "$cmd" & '
        "elif command -v konsole >/dev/null 2>&1; then "
        'konsole -e sh -c "$cmd" & '
        "elif command -v xterm >/dev/null 2>&1; then "
        'xterm -e sh -c "$cmd" & '
        f"else echo {_MANUAL_RELAUNCH_HINT!r} >&2; fi"
    )


def _windows_relaunch_snippet(argv: list[str]) -> str:
    """A PowerShell snippet that launches ``argv`` in a NEW console window.

    ``Start-Process`` resolves a bare command name through PATH (+PATHEXT) and
    opens its own console, so the relaunched TUI never shares the window with
    the user's shell.
    """
    exe, *args = argv

    def ps_quote(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    snippet = f"Start-Process -FilePath {ps_quote(exe)}"
    if args:
        snippet += f" -ArgumentList {', '.join(ps_quote(arg) for arg in args)}"
    return snippet


def build_posix_wrapper(install_url: str, relaunch: str, parent_pid: int, failures: Path) -> list[str]:
    """The sh wrapper: wait for the parent, install, relaunch — or tally and stop.

    Downloads the install script to a temp file and runs that, never a
    ``curl | bash`` pipeline: the pipeline's status is bash's (empty input
    exits 0), so a failed download would masquerade as success and relaunch
    (found in the first manual smoke — design §3.4, revision 8).
    """
    tally = shlex.quote(str(failures))
    script = (
        f"while kill -0 {parent_pid} 2>/dev/null; do sleep 0.2; done; "
        f"tmp=$(mktemp) || exit 1; "
        f'if curl -fsSL {shlex.quote(install_url)} -o "$tmp" && bash "$tmp"; then '
        # No exec: the relaunch opens a NEW terminal window (revision 21) and
        # must never take over the wrapper's terminal — the user's shell keeps
        # it.  The relaunch snippet is a complete command list, so it sits
        # inside the then-branch as-is.
        f'rm -f "$tmp"; {relaunch}; '
        f'else rm -f "$tmp"; date +%s >> {tally}; echo {_FAILURE_MESSAGE!r} >&2; '
        f"echo {_PROMPT_HINT!r} >&2; exit 1; fi"
    )
    return ["sh", "-c", script]


def build_windows_wrapper(install_url: str, relaunch: str, parent_pid: int, failures: Path) -> list[str]:
    """The PowerShell wrapper: wait for the parent, install, relaunch — or tally and stop.

    ``-ErrorAction Stop`` must sit on ``Invoke-RestMethod`` itself (not the
    trailing ``Invoke-Expression``): a 404 then becomes a terminating error
    the catch block tallies, instead of a silent non-terminating one that
    falls through into the relaunch.

    The mirrored install script must signal failure with ``throw``, never
    ``exit 1``: an ``exit`` inside ``Invoke-Expression`` terminates the whole
    PowerShell process before the catch block can append the failure tally.
    The shipped ``aixcoding/release/install-internal-mirror.ps1`` follows that
    contract on every failure path (design §3.4, revision 19).
    """
    script = (
        f"while (Get-Process -Id {parent_pid} -ErrorAction SilentlyContinue) "
        f"{{ Start-Sleep -Milliseconds 200 }}; "
        f"try {{ Invoke-RestMethod -Uri {install_url} -ErrorAction Stop | Invoke-Expression; {relaunch} }} "
        f"catch {{ Add-Content -Path '{failures}' -Value (Get-Date -Format o); "
        f"Write-Error '{_FAILURE_MESSAGE}'; Write-Host '{_PROMPT_HINT}'; exit 1 }}"
    )
    return ["powershell", "-NoProfile", "-Command", script]


def build_wrapper(session_id: str | None, parent_pid: int, config_dir: Path) -> list[str]:
    """The detached wrapper's argv for this platform (design §3.4, revision 21)."""
    argv = relaunch_argv(session_id)
    from chrys.service.aixcoding.update.state import failures_path

    if sys.platform == "win32":
        return build_windows_wrapper(
            install_script_url(), _windows_relaunch_snippet(argv), parent_pid, failures_path(config_dir)
        )
    return build_posix_wrapper(
        install_script_url(), _posix_relaunch_snippet(argv), parent_pid, failures_path(config_dir)
    )


def spawn_wrapper(argv: list[str]) -> subprocess.Popen[bytes]:
    """Detach the wrapper so it outlives the TUI, keeping this terminal for its output."""
    if sys.platform == "win32":
        # Same console (the output stays visible after the TUI exits), own
        # process group (Ctrl+C in the terminal does not cut the update short).
        return subprocess.Popen(argv, stdin=subprocess.DEVNULL, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    # New session: survives the TUI's death, keeps the inherited stdout.
    # The argv is built in this module, never from user input (the directory-level
    # S603 exemption in pyproject.toml is registered as C173).
    return subprocess.Popen(argv, stdin=subprocess.DEVNULL, start_new_session=True)


def start_update_and_exit(
    session_id: str | None,
    config_dir: Path,
    exit_app: Callable[[], object],
    *,
    parent_pid: int | None = None,
) -> bool:
    """Spawn the detached wrapper and exit the TUI; False when the wrapper could not start.

    ``exit_app`` is expected to be ``ChrysApp.exit``; it runs only after the
    wrapper is alive, so a spawn failure leaves the session untouched.
    """
    pid = os.getpid() if parent_pid is None else parent_pid
    try:
        argv = build_wrapper(session_id, pid, config_dir)
        process = spawn_wrapper(argv)
    except Exception:
        logger.warning("auto-update: could not start the update wrapper", exc_info=True)
        return False
    logger.debug("auto-update: wrapper started (pid %s): %s", process.pid, argv)
    exit_app()
    return True
