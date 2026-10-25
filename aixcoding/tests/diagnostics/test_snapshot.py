# ruff: noqa: S101
# (tests — asserts are pytest idiom, Chinese prose is the data)
"""Tests for chrys.aixcoding.diagnostics.snapshot."""

from __future__ import annotations

from pathlib import Path

from chrys.aixcoding.diagnostics.snapshot import take_snapshot, write_snapshot


def test_fields_present():
    text = take_snapshot()
    for key in ("python =", "implementation =", "platform =", "machine =", "os ="):
        assert key in text


def test_extras_rendered():
    text = take_snapshot({"diagnostics_panel": False})
    assert "diagnostics_panel = False" in text


def test_never_dumps_environ(monkeypatch):
    monkeypatch.setenv("AIXCODING_SECRET_CANARY", "hunter2-no-leak")
    text = take_snapshot()
    assert "AIXCODING_SECRET_CANARY" not in text
    assert "hunter2-no-leak" not in text
    assert "PATH" not in text  # no incidental env leakage either


def test_write_snapshot_returns_path(tmp_path: Path):
    path = write_snapshot(tmp_path, {"k": "v"})
    assert path is not None and path.is_file()
    assert "k = v" in path.read_text(encoding="utf-8")


def test_write_failure_degrades(tmp_path: Path, capsys):
    blocker = tmp_path / "blocker"
    blocker.write_text("file", encoding="utf-8")
    assert write_snapshot(blocker) is None
    assert "cannot write" in capsys.readouterr().err
