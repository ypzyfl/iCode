# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Runner tests: wrapper command construction per OS, mirror derivation, and the
detached wait-execute-relaunch order end-to-end (POSIX only — the Windows
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


def _point_at(monkeypatch: pytest.MonkeyPatch, base_url: str) -> None:
    monkeypatch.setattr(commands_module, "resolve_check_base", lambda: base_url)


def test_mirror_root_derives_from_the_check_base(monkeypatch: pytest.MonkeyPatch) -> None:
    _point_at(monkeypatch, "http://82.187.34.98/csas")

    assert commands_module.mirror_root() == "http://82.187.34.98/aixcoding/file/aixcoding"


def test_mirror_root_follows_a_base_url_override(monkeypatch: pytest.MonkeyPatch) -> None:
    _point_at(monkeypatch, "http://10.0.0.9/csas")

    assert commands_module.mirror_root() == "http://10.0.0.9/aixcoding/file/aixcoding"


def test_mirror_root_empty_on_an_unparseable_base(monkeypatch: pytest.MonkeyPatch) -> None:
    _point_at(monkeypatch, "not-a-url")

    assert commands_module.mirror_root() == ""


def test_install_script_url_uses_the_platform_script(monkeypatch: pytest.MonkeyPatch) -> None:
    _point_at(monkeypatch, "http://82.187.34.98/csas")

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
    assert "exec /bin/aixcoding-cli -s s1" in script
    assert ">> " in script and "update-failures" in script, "a failure appends one tally line"
    assert "如未出现命令提示符" in script, "the failure prints the conditional prompt hint (revision 10)"
    assert "update-skip-today" not in script, "the wrapper never deletes the flow's state files (design D2)"


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


def test_relaunch_argv_prefers_the_path_absolute_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner_module.shutil, "which", lambda _: "/usr/local/bin/aixcoding-cli")

    assert relaunch_argv(None) == ["/usr/local/bin/aixcoding-cli"]
    assert relaunch_argv("sess-1") == ["/usr/local/bin/aixcoding-cli", "-s", "sess-1"]


def test_relaunch_argv_falls_back_to_argv0(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner_module.shutil, "which", lambda _: None)

    argv = relaunch_argv(None)
    assert len(argv) == 1 and Path(argv[0]).is_absolute()


@pytest.mark.skipif(WIN32, reason="the POSIX wrapper order needs sh; the Windows twin runs on Windows CI")
def test_wrapper_runs_wait_execute_relaunch_in_order(tmp_path: Path) -> None:
    """End-to-end with a stand-in install script: wait, download, run, relaunch."""
    done = tmp_path / "done"
    relaunched = tmp_path / "relaunched"
    install = tmp_path / "install.sh"
    install.write_text(f"echo ok > {shlex.quote(str(done))}\n", encoding="utf-8")
    relaunch = f"sh -c 'echo ok > {relaunched}'"  # the wrapper prefixes exec itself

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


@pytest.mark.skipif(WIN32, reason="the POSIX wrapper order needs sh; the Windows twin runs on Windows CI")
def test_wrapper_script_failure_tallies_and_stops(tmp_path: Path) -> None:
    """A failing install script appends one tally line and does not relaunch (design Q4/D2)."""
    relaunched = tmp_path / "relaunched"
    tally = tmp_path / "update-failures"
    install = tmp_path / "install.sh"
    install.write_text("exit 1\n", encoding="utf-8")
    relaunch = f"sh -c 'echo bad > {relaunched}'"  # the wrapper prefixes exec itself

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


@pytest.mark.skipif(WIN32, reason="the POSIX wrapper order needs sh; the Windows twin runs on Windows CI")
def test_wrapper_download_failure_tallies_and_stops(tmp_path: Path) -> None:
    """A failed download must not masquerade as success (first manual smoke, design §3.4 revision 8)."""
    relaunched = tmp_path / "relaunched"
    tally = tmp_path / "update-failures"
    install_url = (tmp_path / "missing" / "install.sh").as_uri()  # never exists
    relaunch = f"sh -c 'echo bad > {relaunched}'"  # the wrapper prefixes exec itself

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
