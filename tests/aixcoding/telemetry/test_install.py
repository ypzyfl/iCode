# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""AIxCoding telemetry hook installer (unified hook path, M2-C).

Drives ``chrys.aixcoding.telemetry.install`` with fully injected paths/env,
plus the SessionHookFactory wiring (upstream modification M-001) and the
loader-compatibility pin: every file the installer writes must parse through
the upstream ``load_hooks_file`` without errors.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pytest
import yaml
from pytest import MonkeyPatch

import chrys.aixcoding.telemetry.install as install_module
from chrys.aixcoding.telemetry.install import _install_into
from chrys.foundation.config.settings import resolve_sessions_dir
from chrys.service.hooks.loader import load_hooks_file

ACP_ENV = {
    "AIXCOLLECT_ACCOUNT_ID": "ehr-42",
    "AIXCOLLECT_TELEMETRY_TOKEN": "token-1",
    "AIXCOLLECT_TELEMETRY_URL": "https://backend.example/",
}

_COLLECTOR_MODULE_PREFIX = [
    install_module._collector_executable(),
    "-s",
    "-m",
    "chrys.aixcoding.telemetry.collector",
]


class TestCollectorExecutableResolution:
    """pythonw preference: the collector is spawned by the console-less
    detached worker, and any console creation there opens a visible
    Windows-Terminal window on default-terminal machines — so Windows
    resolves the GUI-subsystem sibling; other platforms (or a missing
    pythonw.exe) fall back to sys.executable."""

    def test_prefers_sibling_pythonw_on_windows(self, monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
        python = tmp_path / "python.exe"
        python.write_text("", encoding="utf-8")
        (tmp_path / "pythonw.exe").write_text("", encoding="utf-8")
        monkeypatch.setattr(install_module.sys, "platform", "win32")
        monkeypatch.setattr(install_module.sys, "executable", str(python))
        assert install_module._collector_executable() == str(tmp_path / "pythonw.exe")

    def test_falls_back_to_sys_executable_without_pythonw(self, monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
        python = tmp_path / "python.exe"
        python.write_text("", encoding="utf-8")
        monkeypatch.setattr(install_module.sys, "platform", "win32")
        monkeypatch.setattr(install_module.sys, "executable", str(python))
        assert install_module._collector_executable() == str(python)

    def test_non_windows_uses_sys_executable(self, monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
        python = tmp_path / "python.exe"
        (tmp_path / "pythonw.exe").write_text("", encoding="utf-8")
        monkeypatch.setattr(install_module.sys, "platform", "linux")
        monkeypatch.setattr(install_module.sys, "executable", str(python))
        assert install_module._collector_executable() == str(python)


def _read_hooks(config_dir: Path) -> dict[str, Any]:
    return yaml.safe_load((config_dir / "hooks" / "hooks.yaml").read_text(encoding="utf-8"))


def _owned(hooks: dict[str, Any]) -> list[dict[str, Any]]:
    return [h for h in hooks["hooks"] if str(h.get("id", "")).startswith("aixcoding-collector-")]


class TestFirstInstall:
    def test_installs_both_entries_attribution_and_report_config(self, tmp_path: Path) -> None:
        config_dir = tmp_path / "config"
        _install_into(config_dir, ACP_ENV)

        hooks = _read_hooks(config_dir)
        assert [h["id"] for h in _owned(hooks)] == [
            "aixcoding-collector-turn",
            "aixcoding-collector-session-end",
        ]
        turn, session_end = _owned(hooks)
        assert turn["event"] == "after_turn"
        assert session_end["event"] == "session_end"
        for entry in (turn, session_end):
            assert entry["run"]["argv"][:4] == _COLLECTOR_MODULE_PREFIX
            assert entry["run"]["argv"][4] == "run"
            assert entry["run"]["env"] == {"AIXCOLLECT_SESSION_ID": "${session_id}"}
            assert entry["execution"] == {
                "mode": "fire_and_forget",
                "detach": True,
                "delivery": "durable",
                "timeout_seconds": 60,
                "on_error": "ignore",
            }
        assert session_end["run"]["argv"][-1:] == ["--final"]
        assert turn["run"]["argv"].count("--final") == 0
        argv = turn["run"]["argv"]
        assert argv[argv.index("--scope") + 1] == "acp"
        assert argv[argv.index("--sessions-root") + 1] == str(resolve_sessions_dir(config_dir))
        assert argv[argv.index("--state-dir") + 1] == str(config_dir.parent / "collector-state")
        assert argv[argv.index("--attribution") + 1] == str(config_dir / "telemetry" / "attribution.json")
        assert argv[argv.index("--report-config") + 1] == str(
            config_dir.parent / "collector-state" / "config" / "report-config.json"
        )

        attribution = json.loads((config_dir / "telemetry" / "attribution.json").read_text(encoding="utf-8"))
        assert attribution == {"version": 1, "account_id": "ehr-42"}

        report_config = json.loads(
            (config_dir.parent / "collector-state" / "config" / "report-config.json").read_text(encoding="utf-8")
        )
        assert report_config == {
            "version": 2,
            "sink": "http",
            "endpoint": "https://backend.example/csas/telemetry/api/v1",
            "token": "token-1",
        }

    def test_written_hooks_file_parses_through_the_upstream_loader(
        self, monkeypatch: MonkeyPatch, tmp_path: Path
    ) -> None:
        config_dir = tmp_path / "config"
        _install_into(config_dir, ACP_ENV)

        loaded = load_hooks_file(config_dir / "hooks" / "hooks.yaml")
        assert [h.id for h in loaded.hooks] == [
            "aixcoding-collector-turn",
            "aixcoding-collector-session-end",
        ]

    def test_aligns_into_an_existing_json_hooks_file(self, monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
        config_dir = tmp_path / "config"
        hooks_dir = config_dir / "hooks"
        hooks_dir.mkdir(parents=True)
        (hooks_dir / "hooks.json").write_text(json.dumps({"version": 1, "hooks": []}), encoding="utf-8")
        _install_into(config_dir, ACP_ENV)
        data = json.loads((hooks_dir / "hooks.json").read_text(encoding="utf-8"))
        assert len(_owned(data)) == 2


class TestIdempotencyAndSelfHeal:
    def test_second_run_writes_nothing(self, monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
        config_dir = tmp_path / "config"
        _install_into(config_dir, ACP_ENV)

        writes: list[Path] = []
        real = install_module._write_atomic

        def counting(path: Path, data: Any, fmt: str) -> None:
            writes.append(path)
            real(path, data, fmt)

        monkeypatch.setattr(install_module, "_write_atomic", counting)
        _install_into(config_dir, ACP_ENV)
        assert writes == []

    def test_tampered_entry_is_restored_and_user_entries_survive(
        self, monkeypatch: MonkeyPatch, tmp_path: Path
    ) -> None:
        config_dir = tmp_path / "config"
        _install_into(config_dir, ACP_ENV)

        hooks = _read_hooks(config_dir)
        user_entry = {
            "id": "user-greeter",
            "event": "session_start",
            "run": {"type": "shell", "shell": "echo hi"},
        }
        hooks["settings"] = {"shutdown_grace_seconds": 9}
        for entry in _owned(hooks):
            entry["run"]["argv"] = ["/tampered"]  # simulate user edit
        hooks["hooks"] = [user_entry, *hooks["hooks"]]
        (config_dir / "hooks" / "hooks.yaml").write_text(yaml.safe_dump(hooks, sort_keys=False), encoding="utf-8")

        _install_into(config_dir, ACP_ENV)

        restored = _read_hooks(config_dir)
        assert user_entry in restored["hooks"]
        assert restored["settings"] == {"shutdown_grace_seconds": 9}
        owned = _owned(restored)
        assert len(owned) == 2
        assert all(entry["run"]["argv"][0] != "/tampered" for entry in owned)
        # User entries keep their position ahead of the aligned entries.
        assert restored["hooks"][0] == user_entry

    def test_unparsable_hooks_file_is_left_untouched(
        self, monkeypatch: MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        config_dir = tmp_path / "config"
        hooks_dir = config_dir / "hooks"
        hooks_dir.mkdir(parents=True)
        broken = "hooks: [ not: valid: yaml"
        (hooks_dir / "hooks.yaml").write_text(broken, encoding="utf-8")

        with caplog.at_level(logging.WARNING):
            _install_into(config_dir, ACP_ENV)

        assert (hooks_dir / "hooks.yaml").read_text(encoding="utf-8") == broken
        assert any("unparsable" in message for message in caplog.messages)


class TestScopeAndIdentity:
    def test_empty_identity_values_still_classify_as_acp(self, monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
        """Key PRESENCE decides scope; a logged-out ACP engine is not TUI."""
        config_dir = tmp_path / "config"
        _install_into(config_dir, {"AIXCOLLECT_ACCOUNT_ID": "", "AIXCOLLECT_TELEMETRY_TOKEN": ""})

        argv = _owned(_read_hooks(config_dir))[0]["run"]["argv"]
        assert argv[argv.index("--scope") + 1] == "acp"
        assert argv[argv.index("--state-dir") + 1] == str(config_dir.parent / "collector-state")

    def test_missing_keys_classify_as_tui_and_degrade_identity(
        self, monkeypatch: MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        config_dir = tmp_path / "config"
        with caplog.at_level(logging.WARNING):
            _install_into(config_dir, {})

        argv = _owned(_read_hooks(config_dir))[0]["run"]["argv"]
        assert argv[argv.index("--scope") + 1] == "tui"
        # TUI machine-level state default (D5 pending): inside the global config dir.
        assert argv[argv.index("--state-dir") + 1] == str(config_dir / "collector-state")
        # No desktop identity: attribution absent, file-sink template so the
        # collector stays observable on disk.
        assert not (config_dir / "telemetry" / "attribution.json").exists()
        report_config = json.loads(
            (config_dir / "collector-state" / "config" / "report-config.json").read_text(encoding="utf-8")
        )
        assert report_config == {"version": 2, "sink": "file"}
        assert any("attribution not refreshed" in message for message in caplog.messages)

    def test_report_config_refresh_preserves_existing_fields(self, monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
        config_dir = tmp_path / "config"
        _install_into(config_dir, ACP_ENV)

        env_later = dict(ACP_ENV)
        env_later["AIXCOLLECT_TELEMETRY_TOKEN"] = "token-2"
        env_later["AIXCOLLECT_TELEMETRY_URL"] = "https://other.example"
        _install_into(config_dir, env_later)

        report_config = json.loads(
            (config_dir.parent / "collector-state" / "config" / "report-config.json").read_text(encoding="utf-8")
        )
        assert report_config["token"] == "token-2"
        assert report_config["endpoint"] == "https://other.example/csas/telemetry/api/v1"


class TestFailClosed:
    def test_unimportable_collector_module_skips_hook_installation(
        self, monkeypatch: MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        monkeypatch.setattr(install_module, "_collector_module_available", lambda: False)
        config_dir = tmp_path / "config"
        with caplog.at_level(logging.WARNING):
            _install_into(config_dir, ACP_ENV)

        assert not (config_dir / "hooks").exists()
        assert any("hooks not installed" in message for message in caplog.messages)

    def test_importable_collector_module_is_detected(self) -> None:
        assert install_module._collector_module_available() is True


class TestIdentityEnvSource:
    def test_identity_env_prefers_the_frozen_snapshot(self, monkeypatch: MonkeyPatch) -> None:
        from chrys.foundation.config import env_layers

        frozen = env_layers.freeze_process_env()
        monkeypatch.setenv("AIXCOLLECT_ACCOUNT_ID", "live-injected")
        try:
            env = install_module._identity_env()
            assert env is frozen.values or dict(env) == dict(frozen.values)
            assert env.get("AIXCOLLECT_ACCOUNT_ID") == frozen.values.get("AIXCOLLECT_ACCOUNT_ID")
        finally:
            env_layers._reset_process_env_snapshot_for_tests()


class TestSessionHookFactoryWiring:
    async def test_factory_invokes_the_installer_before_loading_hooks(
        self, monkeypatch: MonkeyPatch, tmp_path: Path
    ) -> None:
        from chrys.foundation.events.bus import EventBus
        from chrys.orchestration.session_hooks import SessionHookFactory

        calls: list[str] = []
        monkeypatch.setattr(
            install_module,
            "ensure_telemetry_hooks",
            lambda: calls.append("install"),
        )
        factory = SessionHookFactory(EventBus())
        await factory(project_root=str(tmp_path), project_hooks_enabled=False, session_id=None)
        assert calls == ["install"]
