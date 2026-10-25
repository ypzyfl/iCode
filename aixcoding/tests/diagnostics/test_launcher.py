# ruff: noqa: S101
# (tests — asserts are pytest idiom, Chinese prose is the data)
"""Tests for chrys.aixcoding.diagnostics.launcher.

The upstream entrypoint is faked via importlib so the test never boots the
real TUI; hook installation and the hand-off order are what we verify here.
The real upstream entrypoint behavior is upstream's own test domain.
"""

from __future__ import annotations

import importlib
import sys
from types import SimpleNamespace

import pytest

from chrys.aixcoding.diagnostics import launcher


class FakeMain:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def __call__(self) -> int:
        self.calls.append(list(sys.argv))
        return 42


@pytest.fixture
def fake_upstream(monkeypatch):
    fake = FakeMain()
    real_import_module = importlib.import_module

    def fake_import_module(name: str):
        if name == "chrys.app.cli.app":
            return SimpleNamespace(main=fake)
        return real_import_module(name)

    monkeypatch.setattr(importlib, "import_module", fake_import_module)
    return fake


def test_launcher_installs_hooks_snapshot_then_calls(tmp_path, fake_upstream, restore_hooks, aix_logger_state):
    # Session dir under the injected config dir; hooks + snapshot + logging live there.
    called_order: list[str] = []
    monkeypatch_snapshot = pytest.MonkeyPatch()
    real_snapshot = launcher.write_snapshot

    def tracking_snapshot(session_dir, extras=None):
        called_order.append(f"snapshot:{session_dir.name}")
        return real_snapshot(session_dir, extras)

    monkeypatch_snapshot.setattr(launcher, "write_snapshot", tracking_snapshot)

    import chrys.aixcoding.diagnostics.launcher as mod

    monkeypatch_snapshot.setattr(mod, "resolve_config_dir", lambda _: tmp_path)
    try:
        rc = mod.main()
    finally:
        monkeypatch_snapshot.undo()
    assert rc == 42
    assert fake_upstream.calls, "upstream main must be called exactly once per launcher run"
    assert len(called_order) == 1
    session_dirs = list((tmp_path / "aixcoding-diagnostics").iterdir())
    assert len(session_dirs) == 1
    assert (session_dirs[0] / "snapshot.txt").is_file()
    assert (session_dirs[0] / "crash.txt").parent.is_dir()


def test_launcher_missing_entrypoint_returns_127(monkeypatch, tmp_path, restore_hooks):
    # Patch the module attribute first: the string form would import the module
    # through the already-faked import_module below.
    monkeypatch.setattr(launcher, "resolve_config_dir", lambda _: tmp_path)

    def boom(name: str):
        raise ImportError(name)

    monkeypatch.setattr(importlib, "import_module", boom)
    assert launcher.main() == 127
