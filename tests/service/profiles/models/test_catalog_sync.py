# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Tests for the periodic model catalog sync.

The sync itself is exercised against a stubbed fetch: what these cover is the
clock, the stop signal, and the in-memory replacement a sync triggers — the
parts that decide whether a server-side change reaches a running session.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from chrys.service.profiles.models import catalog as catalog_module
from chrys.service.profiles.models.catalog import (
    CatalogSyncResult,
    start_periodic_sync,
)
from chrys.service.profiles.models.registry import ModelProfileRegistry
from tests.support.waiting import wait_until

_POLL_INTERVAL = 0.01


def _result(*profile_ids: str) -> CatalogSyncResult:
    return CatalogSyncResult(
        replaced=True,
        version="v1",
        profile_ids=profile_ids,
        default_profile_id=profile_ids[0] if profile_ids else "",
    )


@pytest.fixture(autouse=True)
def _credentialed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Assume a login: these tests are about the clock, not the credential gate."""
    monkeypatch.setattr(catalog_module, "has_catalog_credential", lambda: True)


async def test_syncs_on_the_clock_and_stops_when_signalled(monkeypatch: pytest.MonkeyPatch) -> None:
    """One fetch per interval, and setting the event ends the loop."""
    monkeypatch.setattr(catalog_module, "catalog_url", lambda: "http://127.0.0.1:1/base")
    monkeypatch.setattr(catalog_module, "sync_catalog_blocking", lambda **_kwargs: _result("a"))

    seen: list[CatalogSyncResult] = []
    stop = start_periodic_sync(interval=_POLL_INTERVAL, on_applied=seen.append)
    try:
        assert stop is not None, "a configured source must start the loop"
        assert await wait_until(lambda: len(seen) >= 2), f"expected repeated syncs, got {len(seen)}"
        assert seen[0].profile_ids == ("a",)
    finally:
        stop.set()

    await asyncio.sleep(5 * _POLL_INTERVAL)
    settled = len(seen)
    await asyncio.sleep(20 * _POLL_INTERVAL)
    assert len(seen) == settled, "a stopped loop must not keep fetching"


def test_no_credential_means_no_thread(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unauthenticated, every sync would be refused: no thread, no traffic."""

    def _must_not_sync(**_kwargs: object) -> CatalogSyncResult:
        raise AssertionError("a sync without a credential must not be attempted")

    monkeypatch.setattr(catalog_module, "catalog_url", lambda: "http://127.0.0.1:1/base")
    monkeypatch.setattr(catalog_module, "has_catalog_credential", lambda: False)
    monkeypatch.setattr(catalog_module, "sync_catalog_blocking", _must_not_sync)
    assert start_periodic_sync(interval=_POLL_INTERVAL) is None


async def test_immediate_syncs_before_the_first_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """A login starts the loop mid-session: the list arrives now, not in a minute."""
    monkeypatch.setattr(catalog_module, "catalog_url", lambda: "http://127.0.0.1:1/base")
    monkeypatch.setattr(catalog_module, "has_catalog_credential", lambda: True)
    monkeypatch.setattr(catalog_module, "sync_catalog_blocking", lambda **_kwargs: _result("a"))

    seen: list[CatalogSyncResult] = []
    stop = start_periodic_sync(interval=60, immediate=True, on_applied=seen.append)
    try:
        assert stop is not None, "a credentialed source must start the loop"
        assert await wait_until(lambda: len(seen) >= 1, timeout=2.0), "immediate never synced"
        assert len(seen) == 1, "the first wait is a whole interval, so a second sync is too early"
    finally:
        stop.set()


async def test_sync_now_pulls_one_catalog_ahead_of_the_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    """A login wakes a loop that is already running: the list arrives now, not at the next tick."""
    monkeypatch.setattr(catalog_module, "catalog_url", lambda: "http://127.0.0.1:1/base")
    monkeypatch.setattr(catalog_module, "sync_catalog_blocking", lambda **_kwargs: _result("a"))

    seen: list[CatalogSyncResult] = []
    stop = start_periodic_sync(interval=60, on_applied=seen.append)
    try:
        assert stop is not None, "a credentialed source must start the loop"
        # The interval is a minute: on the clock alone nothing arrives in time.
        await asyncio.sleep(5 * _POLL_INTERVAL)
        assert not seen, "an untouched interval must not sync early"
        stop.sync_now()
        assert await wait_until(lambda: len(seen) >= 1, timeout=2.0), "sync_now never synced"
        assert len(seen) == 1, "one request is one sync, not a loop restart"
    finally:
        stop.set()


def test_the_interval_is_the_environments_or_the_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """The variable shortens the wait for debugging; a bad value must not."""
    monkeypatch.delenv(catalog_module.SYNC_INTERVAL_ENV, raising=False)
    assert catalog_module.sync_interval_seconds() == catalog_module.SYNC_INTERVAL_SECONDS == 15 * 60

    monkeypatch.setenv(catalog_module.SYNC_INTERVAL_ENV, "30")
    assert catalog_module.sync_interval_seconds() == 30.0

    for unusable in ("soon", "", "   ", "0", "-1"):
        monkeypatch.setenv(catalog_module.SYNC_INTERVAL_ENV, unusable)
        assert catalog_module.sync_interval_seconds() == catalog_module.SYNC_INTERVAL_SECONDS, (
            f"{unusable!r} must fall back to the default, not stop or hot-loop the poll"
        )


async def test_the_loop_polls_at_the_environments_interval(monkeypatch: pytest.MonkeyPatch) -> None:
    """The override reaches the loop: ``interval`` is resolved at start, not import."""
    monkeypatch.setattr(catalog_module, "catalog_url", lambda: "http://127.0.0.1:1/base")
    monkeypatch.setattr(catalog_module, "sync_catalog_blocking", lambda **_kwargs: _result("a"))
    monkeypatch.setenv(catalog_module.SYNC_INTERVAL_ENV, str(_POLL_INTERVAL))

    seen: list[CatalogSyncResult] = []
    stop = start_periodic_sync(on_applied=seen.append)
    try:
        assert stop is not None, "a configured source must start the loop"
        assert await wait_until(lambda: len(seen) >= 2), f"the override never took effect: {len(seen)} sync(s)"
    finally:
        stop.set()


def test_without_a_source_there_is_nothing_to_poll(monkeypatch: pytest.MonkeyPatch) -> None:
    """No catalog configured means no thread — the directory stays the user's."""
    monkeypatch.setattr(catalog_module, "catalog_url", lambda: "")
    assert start_periodic_sync() is None


async def test_a_failing_callback_does_not_kill_the_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    """The callback refreshes a registry; its failure must not end the clock."""
    monkeypatch.setattr(catalog_module, "catalog_url", lambda: "http://127.0.0.1:1/base")
    monkeypatch.setattr(catalog_module, "sync_catalog_blocking", lambda **_kwargs: _result("a"))

    calls: list[int] = []

    def _boom_once(result: CatalogSyncResult) -> None:
        calls.append(len(calls))
        if len(calls) == 1:
            raise RuntimeError("callback blew up")

    stop = start_periodic_sync(interval=_POLL_INTERVAL, on_applied=_boom_once)
    try:
        assert await wait_until(lambda: len(calls) >= 2), f"loop died after {len(calls)} call(s)"
    finally:
        if stop is not None:
            stop.set()


def test_the_tier_is_auths_tier(monkeypatch: pytest.MonkeyPatch) -> None:
    """One deployment, one variable: the catalog must not name its own."""
    from aixcoding.auth import environments
    from aixcoding.auth.types import Environment

    from chrys.foundation.config import process_settings as process_settings_module

    assert catalog_module.ENVIRONMENT_ENV == environments.ENVIRONMENT_VARIABLE
    assert set(catalog_module._CATALOG_BASES) == {tier.value for tier in Environment}
    assert Environment.PROD.value == catalog_module.DEFAULT_ENVIRONMENT

    class _NoConfiguredBase:
        model_catalog_base_url = ""

    monkeypatch.setattr(process_settings_module, "process_settings", _NoConfiguredBase)

    for tier in Environment:
        monkeypatch.setenv(environments.ENVIRONMENT_VARIABLE, tier.value)
        assert catalog_module.catalog_base_url() == catalog_module._CATALOG_BASES[tier.value]

    monkeypatch.setenv(environments.ENVIRONMENT_VARIABLE, "staging")
    assert catalog_module.catalog_base_url() == catalog_module._CATALOG_BASES["prod"]


def test_replace_profiles_forgets_deleted_profiles(tmp_path: Path) -> None:
    """A catalog sync is a wholesale replacement, so the registry must drop too."""
    directory = tmp_path / "models"
    directory.mkdir()
    (directory / "a.yaml").write_text("name: A\n", encoding="utf-8")
    (directory / "b.yaml").write_text("name: B\n", encoding="utf-8")

    registry = ModelProfileRegistry()
    assert registry.load_profiles(directory) == 2

    (directory / "b.yaml").unlink()
    assert registry.replace_profiles(directory) == 1
    assert sorted(registry.list_ids()) == ["a"]


def test_translation_writes_only_fields_the_profile_consumes() -> None:
    """Server-only values must not be stored: no verbatim blocks, no reasoning."""
    from chrys.service.profiles.models.catalog import parse_catalog, translate_models_payload
    from chrys.service.profiles.models.serializer import profile_to_dict

    payload = {
        "models": [
            {
                "title": "GPT-4o mini",
                "provider": "openrouter",
                "model": "openai/gpt-4o-mini",
                "apiBase": "https://example.test/v1",
                "contextLength": 128000,
                # The server expresses vision only via capabilities.uploadImage.
                "completionOptions": {"maxTokens": 16000, "reasoning": True},
                "capabilities": {"uploadImage": True},
                "requestOptions": {"verifySsl": False},
                "apiKey": "never-stored",
            }
        ],
        # Deliberate top-level decoy: sync reads only ``models``, so this is ignored.
        "aa": {"test": "as"},
    }
    items = translate_models_payload(payload)["items"]
    assert items == [
        {
            "provider": "openai",
            "vision": True,
            "verify_ssl": False,
            "id": "openai-gpt-4o-mini",
            "model_id": "openai/gpt-4o-mini",
            "name": "GPT-4o mini",
            "base_url": "https://example.test/v1",
            "max_context_tokens": 128000,
            "max_output_tokens": 16000,
        }
    ]

    profile = parse_catalog({"items": items}).items[0]
    # ``provider`` is the dataclass default and is omitted by the serializer.
    assert profile_to_dict(profile) == {
        "id": "openai-gpt-4o-mini",
        "name": "GPT-4o mini",
        "model_id": "openai/gpt-4o-mini",
        "max_context_tokens": 128000,
        "max_output_tokens": 16000,
        "base_url": "https://example.test/v1",
        "vision": True,
        "verify_ssl": False,
    }


# ── synced profiles and custom profiles coexisting ───────────────────────


def test_sync_marks_its_yaml_and_loader_ignores_the_marker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A synced YAML is identifiable, but the marker never reaches ModelProfile."""
    from chrys.service.profiles.models.catalog import ModelCatalog, apply_catalog
    from chrys.service.profiles.models.loader import load_profile_from_yaml
    from chrys.service.profiles.models.schema import ModelProfile

    monkeypatch.setattr(catalog_module, "catalog_directory", lambda: tmp_path)
    apply_catalog(ModelCatalog(items=(ModelProfile(id="server-a", name="Server A", model_id="a"),)))

    path = tmp_path / "server-a.yaml"
    assert "synced_from_server: true" in path.read_text(encoding="utf-8")
    loaded = load_profile_from_yaml(path)
    assert loaded.id == "server-a"
    assert not hasattr(loaded, "synced_from_server")


def test_sync_clears_old_configs_and_keeps_marked_custom_profiles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only marked new-version files coexist; unmarked old configs are cleared."""
    from chrys.service.profiles.models.catalog import ModelCatalog, apply_catalog
    from chrys.service.profiles.models.schema import ModelProfile

    monkeypatch.setattr(catalog_module, "catalog_directory", lambda: tmp_path)
    (tmp_path / "custom.yaml").write_text(
        "id: custom\nname: Custom\nmodel_id: my-model\nsynced_from_server: false\n", encoding="utf-8"
    )
    # Written before the marker existed: an old-version config, cleared outright.
    (tmp_path / "legacy.yaml").write_text("id: legacy\nname: Legacy\nmodel_id: old\n", encoding="utf-8")
    (tmp_path / "stale.yaml").write_text(
        "id: stale\nname: Stale\nmodel_id: old\nsynced_from_server: true\n", encoding="utf-8"
    )

    apply_catalog(ModelCatalog(items=(ModelProfile(id="server-a", name="Server A", model_id="a"),)))

    assert (tmp_path / "custom.yaml").is_file(), "a marked custom profile survives"
    assert not (tmp_path / "legacy.yaml").exists(), "an unmarked old config is cleared"
    assert not (tmp_path / "stale.yaml").exists(), "a dropped server model is removed"
    assert (tmp_path / "server-a.yaml").is_file()

    registry = ModelProfileRegistry()
    registry.load_profiles(tmp_path)
    assert "custom" in registry.list_ids(), "preserved profiles stay visible in the TUI"
    assert "legacy" not in registry.list_ids()
    assert "stale" not in registry.list_ids()


def test_a_saved_custom_profile_survives_a_later_sync(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The custom write path and the sync agree on the marker, so both coexist."""
    from chrys.service.profiles.models.catalog import ModelCatalog, apply_catalog
    from chrys.service.profiles.models.schema import ModelProfile
    from chrys.service.profiles.models.serializer import save_profile

    fake_platform = type("P", (), {"config_dir": tmp_path})()
    monkeypatch.setattr("chrys.foundation.platform.get_platform", lambda: fake_platform)
    monkeypatch.setattr(catalog_module, "catalog_directory", lambda: tmp_path / "models")

    save_profile(ModelProfile(id="my-custom", name="My Custom", model_id="mine"))
    apply_catalog(ModelCatalog(items=(ModelProfile(id="server-a", name="Server A", model_id="a"),)))

    assert (tmp_path / "models" / "my-custom.yaml").is_file(), "a saved profile outlives the sync"
    assert (tmp_path / "models" / "server-a.yaml").is_file()


def test_sync_overwrites_a_same_id_custom_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A server id wins over a user file with the same name, with a one-time warning."""
    import logging

    from chrys.service.profiles.models.catalog import ModelCatalog, apply_catalog
    from chrys.service.profiles.models.loader import load_profile_from_yaml
    from chrys.service.profiles.models.schema import ModelProfile

    monkeypatch.setattr(catalog_module, "catalog_directory", lambda: tmp_path)
    (tmp_path / "server-a.yaml").write_text(
        "id: server-a\nname: My Custom\nmodel_id: mine\nsynced_from_server: false\n", encoding="utf-8"
    )
    with caplog.at_level(logging.WARNING):
        apply_catalog(ModelCatalog(items=(ModelProfile(id="server-a", name="Server A", model_id="a"),)))

    loaded = load_profile_from_yaml(tmp_path / "server-a.yaml")
    assert loaded.name == "Server A"
    assert "synced_from_server: true" in (tmp_path / "server-a.yaml").read_text(encoding="utf-8")
    assert "overwrote same-id custom profiles" in caplog.text
