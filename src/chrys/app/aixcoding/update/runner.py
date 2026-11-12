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


def relaunch_argv(session_id: str | None) -> list[str]:
    """The argv that restarts the TUI, restoring ``session_id`` when known.

    Resolved *before* the TUI exits (design D3): the PATH absolute path of
    the product command survives the install replacing the version
    directories behind the old binary; ``sys.argv[0]`` resolved is the
    fallback when the alias is not on PATH.
    """
    executable = shutil.which(APP_COMMAND) or str(Path(sys.argv[0]).resolve())
    argv = [executable]
    if session_id:
        argv += ["-s", session_id]
    return argv


def _relaunch_shell_string(session_id: str | None) -> str:
    argv = relaunch_argv(session_id)
    if sys.platform == "win32":
        return "& " + " ".join(f'"{part}"' for part in argv)
    return " ".join(shlex.quote(part) for part in argv)


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
        f'rm -f "$tmp"; exec {relaunch}; '
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
    """The detached wrapper's argv for this platform (design §3.4)."""
    relaunch = _relaunch_shell_string(session_id)
    from chrys.service.aixcoding.update.state import failures_path

    if sys.platform == "win32":
        return build_windows_wrapper(install_script_url(), relaunch, parent_pid, failures_path(config_dir))
    return build_posix_wrapper(install_script_url(), relaunch, parent_pid, failures_path(config_dir))


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
