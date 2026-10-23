# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Tests for installing the bundled security guard hooks."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

from chrys.app import guard_install
from chrys.app.guard_install import (
    GUARD_PAYLOAD_FILES,
    GUARD_SUBDIR,
    MANAGED_HOOK_IDS,
    install_guard_hooks,
    installed_guard_hooks,
)


def _hook_ids(hooks_file: Path) -> list[str]:
    document = yaml.safe_load(hooks_file.read_text(encoding="utf-8-sig"))
    return [str(entry["id"]) for entry in document["hooks"]]


def test_fresh_install_writes_template_and_payload(tmp_path: Path) -> None:
    hooks_dir = tmp_path / "hooks"

    report = install_guard_hooks(hooks_dir=hooks_dir)

    assert report.merged_into_existing is False
    assert report.backup is None
    assert report.hooks_file == hooks_dir / "hooks.yaml"
    assert _hook_ids(report.hooks_file) == list(MANAGED_HOOK_IDS)
    for name in GUARD_PAYLOAD_FILES:
        assert (hooks_dir / GUARD_SUBDIR / name).is_file()
    assert installed_guard_hooks(hooks_dir) == (True, [])


def test_reinstall_is_idempotent_and_overwrites_payload(tmp_path: Path) -> None:
    hooks_dir = tmp_path / "hooks"
    install_guard_hooks(hooks_dir=hooks_dir)
    first = yaml.safe_load((hooks_dir / "hooks.yaml").read_text(encoding="utf-8"))
    stale = hooks_dir / GUARD_SUBDIR / "rules.json"
    stale.write_text("{}", encoding="utf-8")

    install_guard_hooks(hooks_dir=hooks_dir)
    install_guard_hooks(hooks_dir=hooks_dir)

    reloaded = yaml.safe_load((hooks_dir / "hooks.yaml").read_text(encoding="utf-8"))
    assert reloaded["hooks"] == first["hooks"]
    assert stale.read_text(encoding="utf-8") != "{}"


def test_existing_hooks_and_settings_survive_merge(tmp_path: Path) -> None:
    hooks_dir = tmp_path / "hooks"
    hooks_dir.mkdir(parents=True)
    (hooks_dir / "hooks.yaml").write_text(
        "# hand written\n"
        "version: 1\n"
        "settings:\n"
        "  max_parallel_hooks: 2\n"
        "hooks:\n"
        "  - id: telemetry\n"
        "    event: after_turn\n"
        "    run:\n"
        "      type: command\n"
        "      argv: [echo, hi]\n",
        encoding="utf-8",
    )

    report = install_guard_hooks(hooks_dir=hooks_dir)

    text = report.hooks_file.read_text(encoding="utf-8")
    document = yaml.safe_load(text)
    assert report.merged_into_existing is True
    assert report.backup is not None and report.backup.is_file()
    assert "# hand written" in text
    assert document["settings"]["max_parallel_hooks"] == 2
    assert document["hooks"][0]["id"] == "telemetry"
    assert [entry["id"] for entry in document["hooks"]] == ["telemetry", *MANAGED_HOOK_IDS]


def test_stale_guard_entries_are_replaced_not_duplicated(tmp_path: Path) -> None:
    hooks_dir = tmp_path / "hooks"
    hooks_dir.mkdir(parents=True)
    (hooks_dir / "hooks.yaml").write_text(
        "version: 1\n"
        "hooks:\n"
        "  - id: security-prompt-guard\n"
        "    event: user_prompt_submit\n"
        "    run:\n"
        "      type: script\n"
        "      path: old/prompt_guard.py\n"
        "  - id: telemetry\n"
        "    event: after_turn\n"
        "    run:\n"
        "      type: command\n"
        "      argv: [echo, hi]\n",
        encoding="utf-8",
    )

    install_guard_hooks(hooks_dir=hooks_dir)

    document = yaml.safe_load((hooks_dir / "hooks.yaml").read_text(encoding="utf-8"))
    runs = {entry["id"]: entry["run"] for entry in document["hooks"]}
    assert list(runs) == ["telemetry", *MANAGED_HOOK_IDS]
    if sys.platform == "win32":
        # Template entries are the PowerShell launcher form, merged verbatim on Windows.
        launcher_run = runs["security-prompt-guard"]
        assert launcher_run["type"] == "command"
        assert any("_launcher.ps1" in argument for argument in launcher_run["argv"])
        assert launcher_run["env"]["GUARD_SCRIPT"].endswith("_prompt_guard.py")
    else:
        # POSIX: the engine rewrites the launcher form back to type: script.
        assert runs["security-prompt-guard"] == {"type": "script", "path": "guard/_prompt_guard.py"}


def test_unparsable_configuration_is_backed_up_and_replaced(tmp_path: Path) -> None:
    hooks_dir = tmp_path / "hooks"
    hooks_dir.mkdir(parents=True)
    broken = hooks_dir / "hooks.yaml"
    broken.write_text("hooks: [unclosed\n", encoding="utf-8")

    report = install_guard_hooks(hooks_dir=hooks_dir)

    assert report.replaced_unparsable_config is True
    assert report.backup is not None
    assert report.backup.read_text(encoding="utf-8") == "hooks: [unclosed\n"
    assert _hook_ids(broken) == list(MANAGED_HOOK_IDS)


def test_configuration_without_hooks_section_gains_one(tmp_path: Path) -> None:
    hooks_dir = tmp_path / "hooks"
    hooks_dir.mkdir(parents=True)
    (hooks_dir / "hooks.yaml").write_text("version: 1\nsettings:\n  max_parallel_hooks: 3\n", encoding="utf-8")

    install_guard_hooks(hooks_dir=hooks_dir)

    document = yaml.safe_load((hooks_dir / "hooks.yaml").read_text(encoding="utf-8"))
    assert document["settings"]["max_parallel_hooks"] == 3
    assert [entry["id"] for entry in document["hooks"]] == list(MANAGED_HOOK_IDS)


def test_missing_assets_are_reported(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        install_guard_hooks(hooks_dir=tmp_path / "hooks", asset_dir=tmp_path / "empty")


def test_installed_report_flags_missing_payload(tmp_path: Path) -> None:
    hooks_dir = tmp_path / "hooks"
    install_guard_hooks(hooks_dir=hooks_dir)
    (hooks_dir / GUARD_SUBDIR / "rules.json").unlink()

    listed, missing = installed_guard_hooks(hooks_dir)

    assert listed is True
    assert missing == [str(hooks_dir / GUARD_SUBDIR / "rules.json")]


def test_first_run_installs_guard_hooks_and_survives_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``cli.app._ensure_guard_hooks`` is the real wiring (called from main)."""

    def missing_assets() -> None:
        raise FileNotFoundError("guard hooks missing")

    monkeypatch.setattr(guard_install, "install_guard_hooks", missing_assets)

    from chrys.app.cli import app as cli_app

    cli_app._ensure_guard_hooks()

    err = capsys.readouterr().err
    assert "security guard hooks not installed" in err
    assert "guard hooks missing" in err


def test_startup_reinstalls_unconditionally(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every start reinstalls, so upgraded machines can never run stale scripts."""

    install_calls: list[bool] = []
    monkeypatch.setattr(guard_install, "install_guard_hooks", lambda: install_calls.append(True))

    from chrys.app.cli import app as cli_app

    cli_app._ensure_guard_hooks()

    assert install_calls == [True]
