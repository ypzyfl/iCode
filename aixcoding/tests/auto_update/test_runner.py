# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Runner tests: wrapper command construction per OS, the pinned mirror root, and
the detached wait-execute-relaunch order end-to-end (POSIX only — the Windows
sequence depends on real console behaviour; R13 skip, design §10).

Design: aixcoding/docs/batches/auto-update/design.md §3.4, §3.6
"""

from __future__ import annotations

import shlex
import subprocess
import sys
import time
from pathlib import Path

import pytest

from chrys.app.aixcoding.update import commands as commands_module
from chrys.app.aixcoding.update import runner as runner_module
from chrys.app.aixcoding.update.runner import (
    build_posix_wrapper,
    build_windows_wrapper,
    relaunch_argv,
    spawn_wrapper,
)

WIN32 = sys.platform == "win32"


def test_mirror_root_is_pinned_to_the_production_origin() -> None:
    # Temporary pin (design revision 20): the dev gateway has not published the
    # bare-origin file mirror, so a derived install URL answers 400 there and
    # every dev update would fail at the download step.  The origin comes from
    # the tier table's prod entry, so an IP change touches client.py only.
    assert commands_module.mirror_root() == "http://82.187.34.98/aixcoding/file/aixcoding"


def test_install_script_url_uses_the_platform_script() -> None:
    url = commands_module.install_script_url()
    expected_script = "install.ps1" if WIN32 else "install.sh"
    assert url == f"http://82.187.34.98/aixcoding/file/aixcoding/{expected_script}"


def test_posix_wrapper_shape(tmp_path: Path) -> None:
    argv = build_posix_wrapper("http://m/install.sh", "/bin/aixcoding-cli -s s1", 4242, tmp_path / "update-failures")

    assert argv[0:2] == ["sh", "-c"]
    script = argv[2]
    assert "while kill -0 4242 2>/dev/null" in script, "wait for the parent first (installer blocks otherwise)"
    assert 'curl -fsSL http://m/install.sh -o "$tmp"' in script, "download the install script to a temp file first"
    assert 'bash "$tmp"' in script, "run the downloaded script, never a pipeline"
    assert "| bash" not in script, (
        "a pipeline's status is bash's, not curl's — a failed download would pass (revision 8)"
    )
    assert "mktemp" in script
    assert script.count('rm -f "$tmp"') == 2, "the temp file is cleaned in both branches"
    assert "/bin/aixcoding-cli -s s1" in script
    assert "exec" not in script, "the relaunch never takes over the wrapper's terminal (revision 20)"
    assert ">> " in script and "update-failures" in script, "a failure appends one tally line"
    assert "如未出现命令提示符" in script, "the failure prints the conditional prompt hint (revision 10)"
    assert "update-skip-today" not in script, "the wrapper never deletes the flow's state files (design D2)"


def test_posix_relaunch_snippet_opens_a_new_terminal_window(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    snippet = runner_module._posix_relaunch_snippet(["aixcoding-cli", "-s", "sess-1"])

    assert 'if [ -z "$DISPLAY$WAYLAND_DISPLAY" ]' in snippet, (
        "command -v alone cannot prove a window can open (SSH into a GNOME box, WSL)"
    )
    assert "x-terminal-emulator -e sh -c" in snippet, "Debian alternatives first (Ubuntu default)"
    assert "gnome-terminal -- sh -c" in snippet
    assert "konsole -e sh -c" in snippet
    assert "xterm -e sh -c" in snippet
    assert "aixcoding-cli" in snippet and "sess-1" in snippet
    assert "手动运行" in snippet, "every no-window path prints the manual hint"


def test_posix_relaunch_snippet_on_macos_uses_osascript(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")

    snippet = runner_module._posix_relaunch_snippet(["aixcoding-cli"])

    assert snippet.startswith("( osascript") and snippet.endswith(") &"), (
        "backgrounded: a first-time Terminal automation prompt must not hang the wrapper"
    )
    assert "do script" in snippet, "Terminal.app opens the new window"
    assert "aixcoding-cli" in snippet
    assert "手动运行" in snippet, "osascript failure still tells the user how to start"


def test_posix_relaunch_snippet_without_a_launcher_is_only_the_hint() -> None:
    snippet = runner_module._posix_relaunch_snippet(None)

    assert snippet == f"echo {runner_module._MANUAL_RELAUNCH_HINT!r} >&2", (
        "no launcher — the hint alone, never an execution of a known-bad argv"
    )


def test_windows_relaunch_snippet_uses_start_process() -> None:
    snippet = runner_module._windows_relaunch_snippet(["aixcoding-cli", "-s", "sess-1"])

    assert snippet == "Start-Process -FilePath 'aixcoding-cli' -ArgumentList '-s', 'sess-1'", (
        "Start-Process resolves PATH (+PATHEXT) and opens its own console window"
    )


def test_windows_relaunch_snippet_escapes_embedded_quotes() -> None:
    snippet = runner_module._windows_relaunch_snippet(["aixcoding-cli", "-s", "it's"])

    assert "it''s" in snippet, "PowerShell single-quoted literals double embedded quotes"


def test_windows_relaunch_snippet_without_a_launcher_is_only_the_hint() -> None:
    snippet = runner_module._windows_relaunch_snippet(None)

    assert snippet.startswith("Write-Host '") and snippet.endswith("'"), (
        "no launcher — the hint alone, never an execution of a known-bad argv"
    )


@pytest.mark.skipif(WIN32, reason="sh -n needs a POSIX shell")
@pytest.mark.parametrize("platform_hint", ["linux", "darwin"])
def test_posix_wrapper_scripts_are_valid_shell(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, platform_hint: str
) -> None:
    """Cheap regression against quote/nesting breakage in the generated script (review 9)."""
    monkeypatch.setattr(sys, "platform", platform_hint)
    script = build_posix_wrapper(
        "http://m/install.sh",
        runner_module._posix_relaunch_snippet(["aixcoding-cli", "-s", "sess-1"]),
        4242,
        tmp_path / "update-failures",
    )[2]
    target = tmp_path / f"wrapper-{platform_hint}.sh"
    target.write_text(script, encoding="utf-8")

    subprocess.run(["sh", "-n", str(target)], check=True, capture_output=True)


def test_windows_wrapper_shape(tmp_path: Path) -> None:
    argv = build_windows_wrapper(
        "http://m/install.ps1",
        '& "C:\\bin\\aixcoding-cli" -s s1',
        4242,
        tmp_path / "update-failures",
    )

    assert argv[0:3] == ["powershell", "-NoProfile", "-Command"]
    script = argv[3]
    assert "Get-Process -Id 4242" in script, "wait for the parent first"
    assert "Invoke-RestMethod -Uri http://m/install.ps1 -ErrorAction Stop" in script, (
        "the download failure must terminate the try block, not fall through (revision 8)"
    )
    assert "Invoke-Expression" in script
    assert "Add-Content" in script and "update-failures" in script, "a failure appends one tally line"
    assert "如未出现命令提示符" in script, "the failure prints the conditional prompt hint (revision 10)"
    assert "Remove-Item" not in script, "the wrapper never deletes the flow's state files (design D2)"


def test_relaunch_argv_launches_by_bare_command_when_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    # The installer puts the product command on PATH, so the relaunch uses the
    # bare name — the new-window launchers resolve it through the wrapper's
    # inherited PATH, and the bare name survives the install replacing version
    # directories behind any absolute path.
    monkeypatch.setattr(runner_module.shutil, "which", lambda _: "/usr/local/bin/aixcoding-cli")

    assert relaunch_argv(None) == [runner_module.APP_COMMAND]
    assert relaunch_argv("sess-1") == [runner_module.APP_COMMAND, "-s", "sess-1"]


def test_relaunch_argv_falls_back_to_the_installer_locations(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # This process's PATH and the login shell's can differ; the installer's
    # known directories are probed before giving up.
    monkeypatch.setattr(runner_module.shutil, "which", lambda _: None)
    monkeypatch.setattr(runner_module, "_launcher_fallback_dirs", lambda: (tmp_path / "bin",))
    (tmp_path / "bin").mkdir(parents=True)
    launcher = tmp_path / "bin" / runner_module.APP_COMMAND
    launcher.write_text("#!/bin/sh\n", encoding="utf-8")
    launcher.chmod(0o755)

    assert relaunch_argv(None) == [str(launcher)]
    assert relaunch_argv("sess-1") == [str(launcher), "-s", "sess-1"]


def test_relaunch_argv_is_none_when_no_launcher_exists(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # A None result becomes the manual-relaunch hint — never an execution of
    # the argv[0] entry script, whose offline shebang names a build-machine
    # interpreter that does not exist on the user machine (revision 20).
    monkeypatch.setattr(runner_module.shutil, "which", lambda _: None)
    monkeypatch.setattr(runner_module, "_launcher_fallback_dirs", lambda: (tmp_path / "empty",))

    assert relaunch_argv(None) is None
    assert relaunch_argv("sess-1") is None


@pytest.mark.skipif(
    WIN32,
    reason=(
        "POSIX wrapper e2e needs sh; Windows CI asserts the command string only, "
        "real-console e2e is manual smoke item 8"
    ),
)
def test_wrapper_runs_wait_execute_relaunch_in_order(tmp_path: Path) -> None:
    """End-to-end with a stand-in install script: wait, download, run, relaunch."""
    done = tmp_path / "done"
    relaunched = tmp_path / "relaunched"
    install = tmp_path / "install.sh"
    install.write_text(f"echo ok > {shlex.quote(str(done))}\n", encoding="utf-8")
    relaunch = f"sh -c 'echo ok > {relaunched}'"  # a stand-in relaunch command list

    # A short-lived stand-in for the TUI process the wrapper must outlive.
    parent = subprocess.Popen(["sleep", "30"])
    try:
        argv = build_posix_wrapper(install.as_uri(), relaunch, parent.pid, tmp_path / "update-failures")
        wrapper = spawn_wrapper(argv)

        assert not done.exists(), "the wrapper must not run before the parent exits"
        parent.terminate()
        parent.wait(timeout=10)
        wrapper.wait(timeout=15)

        assert done.exists(), "the install script ran"
        assert relaunched.exists(), "a success relaunches"
        assert not (tmp_path / "update-failures").exists(), "a success never tallies"
    finally:
        if parent.poll() is None:
            parent.kill()
        if wrapper.poll() is None:
            wrapper.kill()


@pytest.mark.skipif(
    WIN32,
    reason=(
        "POSIX wrapper e2e needs sh; Windows CI asserts the command string only, "
        "real-console e2e is manual smoke item 8"
    ),
)
def test_wrapper_script_failure_tallies_and_stops(tmp_path: Path) -> None:
    """A failing install script appends one tally line and does not relaunch (design Q4/D2)."""
    relaunched = tmp_path / "relaunched"
    tally = tmp_path / "update-failures"
    install = tmp_path / "install.sh"
    install.write_text("exit 1\n", encoding="utf-8")
    relaunch = f"sh -c 'echo bad > {relaunched}'"  # a stand-in relaunch command list

    parent = subprocess.Popen(["sleep", "30"])
    try:
        argv = build_posix_wrapper(install.as_uri(), relaunch, parent.pid, tally)
        wrapper = spawn_wrapper(argv)

        parent.terminate()
        parent.wait(timeout=10)
        exit_code = wrapper.wait(timeout=15)

        assert exit_code != 0, "the wrapper surfaces the update failure"
        assert tally.exists() and len(tally.read_text(encoding="utf-8").strip().splitlines()) == 1
        assert not relaunched.exists(), "a failure must not relaunch"
    finally:
        if parent.poll() is None:
            parent.kill()
        if wrapper.poll() is None:
            wrapper.kill()


@pytest.mark.skipif(
    WIN32,
    reason=(
        "POSIX wrapper e2e needs sh; Windows CI asserts the command string only, "
        "real-console e2e is manual smoke item 8"
    ),
)
def test_wrapper_download_failure_tallies_and_stops(tmp_path: Path) -> None:
    """A failed download must not masquerade as success (first manual smoke, design §3.4 revision 8)."""
    relaunched = tmp_path / "relaunched"
    tally = tmp_path / "update-failures"
    install_url = (tmp_path / "missing" / "install.sh").as_uri()  # never exists
    relaunch = f"sh -c 'echo bad > {relaunched}'"  # a stand-in relaunch command list

    parent = subprocess.Popen(["sleep", "30"])
    try:
        argv = build_posix_wrapper(install_url, relaunch, parent.pid, tally)
        wrapper = spawn_wrapper(argv)

        parent.terminate()
        parent.wait(timeout=10)
        exit_code = wrapper.wait(timeout=15)

        assert exit_code != 0, "a failed download is a failure, never a relaunch"
        assert tally.exists() and len(tally.read_text(encoding="utf-8").strip().splitlines()) == 1
        assert not relaunched.exists(), "a failed download must not relaunch"
    finally:
        if parent.poll() is None:
            parent.kill()
        if wrapper.poll() is None:
            wrapper.kill()


def test_spawn_wrapper_detaches_without_blocking(tmp_path: Path) -> None:
    marker = tmp_path / "touched"
    # A Python child, not `sh -c`: a POSIX shell eats the backslashes in a
    # Windows tmp_path (PR #119). The point under test is the detach itself.
    process = spawn_wrapper(
        [
            sys.executable,
            "-c",
            f"from pathlib import Path; Path({str(marker)!r}).write_text('ok', encoding='utf-8')",
        ]
    )
    try:
        assert process.pid > 0
        for _ in range(100):
            if marker.exists():
                break
            time.sleep(0.05)
        assert marker.exists(), "the detached wrapper keeps running to completion"
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
