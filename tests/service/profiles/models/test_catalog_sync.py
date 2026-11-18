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


def test_translation_trims_title_and_gates_dirty_types(caplog: pytest.LogCaptureFixture) -> None:
    """The real payload's dirty scalars are cleaned, not written verbatim."""
    import logging

    from chrys.service.profiles.models.catalog import translate_models_payload

    with caplog.at_level(logging.WARNING):
        items = translate_models_payload(
            {
                "models": [
                    {
                        "title": "  GLM-5  ",
                        "model": "  GLM-5  ",
                        "apiBase": "  https://example.test/v1  ",
                        "contextLength": "256000",  # quoted number: coerced
                        "completionOptions": {"maxTokens": "16000"},  # quoted number: coerced
                        "capabilities": {"uploadImage": "true"},  # not a boolean: dropped
                        "requestOptions": {"verifySsl": "no"},  # not a boolean: dropped
                    },
                    {
                        "title": "No Context",
                        "model": "no-context",
                        "apiBase": "https://example.test/v1",
                        "contextLength": True,  # a misplaced flag: dropped
                    },
                ]
            }
        )["items"]

    assert items[0]["name"] == "GLM-5"
    assert items[0]["model_id"] == "GLM-5", "the alias must not restore the unpadded model"
    assert items[0]["base_url"] == "https://example.test/v1"
    assert items[0]["max_context_tokens"] == 256000
    assert items[0]["max_output_tokens"] == 16000
    assert "vision" not in items[0], "a non-boolean flag must be dropped, not guessed"
    assert "verify_ssl" not in items[0]
    assert "max_context_tokens" not in items[1], "a boolean is not a context length"
    assert "not a boolean" in caplog.text
    assert "not a positive integer" in caplog.text


def test_translation_warns_when_apiBase_is_absent(caplog: pytest.LogCaptureFixture) -> None:
    """A missing apiBase silently falls back to the OpenAI default: surface it."""
    import logging

    from chrys.service.profiles.models.catalog import translate_models_payload

    with caplog.at_level(logging.WARNING):
        translate_models_payload({"models": [{"title": "No Base", "model": "no-base"}]})

    assert "carries no apiBase" in caplog.text


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


def test_sync_preserves_custom_profiles_and_removes_only_stale_server_profiles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unmarked and explicitly-custom files survive; a dropped server model does not."""
    from chrys.service.profiles.models.catalog import ModelCatalog, apply_catalog
    from chrys.service.profiles.models.schema import ModelProfile

    monkeypatch.setattr(catalog_module, "catalog_directory", lambda: tmp_path)
    (tmp_path / "custom.yaml").write_text(
        "id: custom\nname: Custom\nmodel_id: my-model\nsynced_from_server: false\n", encoding="utf-8"
    )
    (tmp_path / "custom.yml").write_text(
        "id: custom-yml\nname: Custom Yml\nmodel_id: my-model\nsynced_from_server: false\n", encoding="utf-8"
    )
    # Hand-written without the marker: still the user's, never guessed away.
    (tmp_path / "legacy.yaml").write_text("id: legacy\nname: Legacy\nmodel_id: old\n", encoding="utf-8")
    (tmp_path / "legacy.yml").write_text("id: legacy-yml\nname: Legacy Yml\nmodel_id: old\n", encoding="utf-8")
    # A marker with the wrong type does not prove server ownership either.
    (tmp_path / "string-marker.yml").write_text(
        'id: string-marker\nname: String Marker\nmodel_id: old\nsynced_from_server: "false"\n', encoding="utf-8"
    )
    (tmp_path / "stale.yaml").write_text(
        "id: stale\nname: Stale\nmodel_id: old\nsynced_from_server: true\n", encoding="utf-8"
    )

    apply_catalog(ModelCatalog(items=(ModelProfile(id="server-a", name="Server A", model_id="a"),)))

    assert (tmp_path / "custom.yaml").is_file(), "a marked custom profile survives"
    assert (tmp_path / "custom.yml").is_file(), "a marked custom .yml survives too"
    assert (tmp_path / "legacy.yaml").is_file(), "an unmarked hand-written YAML survives"
    assert (tmp_path / "legacy.yml").is_file(), "an unmarked hand-written .yml survives"
    assert (tmp_path / "string-marker.yml").is_file(), "a non-boolean marker proves nothing, so it survives"
    assert not (tmp_path / "stale.yaml").exists(), "a dropped server model is removed"
    assert (tmp_path / "server-a.yaml").is_file()

    registry = ModelProfileRegistry()
    registry.load_profiles(tmp_path)
    assert "custom" in registry.list_ids(), "preserved profiles stay visible in the TUI"
    assert "custom-yml" in registry.list_ids()
    assert "legacy" in registry.list_ids()
    assert "legacy-yml" in registry.list_ids()
    assert "string-marker" in registry.list_ids()
    assert "stale" not in registry.list_ids()


def test_a_directory_without_a_single_marker_is_cleared_once_by_the_first_sync(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pre-marker catalog is replaced wholesale instead of kept as user profiles."""
    from chrys.service.profiles.models.catalog import ModelCatalog, apply_catalog
    from chrys.service.profiles.models.schema import ModelProfile

    monkeypatch.setattr(catalog_module, "catalog_directory", lambda: tmp_path)
    # What the baseline left behind: hand-written shapes, marker absent everywhere.
    (tmp_path / "retired.yaml").write_text("id: retired\nname: Retired\nmodel_id: old\n", encoding="utf-8")
    (tmp_path / "retired-yml.yml").write_text("id: retired-yml\nname: Retired Yml\nmodel_id: old\n", encoding="utf-8")

    apply_catalog(ModelCatalog(items=(ModelProfile(id="server-a", name="Server A", model_id="a"),)))

    assert not (tmp_path / "retired.yaml").exists(), "a pre-marker profile must not linger as the user's own"
    assert (tmp_path / "retired-yml.yml").is_file(), "a .yml is never written by a sync, so the clear leaves it"
    assert (tmp_path / "server-a.yaml").is_file()


def test_a_yml_only_directory_is_left_alone(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``.yml`` is not a profile file for the sync, so such a directory is not an upgrade."""
    from chrys.service.profiles.models.catalog import ModelCatalog, apply_catalog
    from chrys.service.profiles.models.schema import ModelProfile

    monkeypatch.setattr(catalog_module, "catalog_directory", lambda: tmp_path)
    (tmp_path / "mine.yml").write_text("id: mine\nname: Mine\nmodel_id: mine\n", encoding="utf-8")

    apply_catalog(ModelCatalog(items=(ModelProfile(id="server-a", name="Server A", model_id="a"),)))

    assert (tmp_path / "mine.yml").is_file(), "a .yml-only directory has no .yaml to migrate"
    assert (tmp_path / "server-a.yaml").is_file()


def test_a_yml_never_counts_as_a_server_profile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Only ``.yaml`` is read: a marked ``.yml`` is the user's file, not a sync product."""
    from chrys.service.profiles.models.catalog import ModelCatalog, apply_catalog
    from chrys.service.profiles.models.schema import ModelProfile

    monkeypatch.setattr(catalog_module, "catalog_directory", lambda: tmp_path)
    (tmp_path / "copied.yml").write_text(
        "id: copied\nname: Copied\nmodel_id: old\nsynced_from_server: true\n", encoding="utf-8"
    )
    (tmp_path / "hand-written.yaml").write_text("id: hand\nname: Hand\nmodel_id: mine\n", encoding="utf-8")

    apply_catalog(ModelCatalog(items=(ModelProfile(id="server-a", name="Server A", model_id="a"),)))

    assert (tmp_path / "copied.yml").is_file(), "a .yml is never deleted, whatever marker it carries"
    assert not (tmp_path / "hand-written.yaml").exists(), "a marker on a .yml does not make the .yaml side post-marker"
    assert (tmp_path / "server-a.yaml").is_file()


def test_the_first_upgrade_clear_spares_the_same_id_file_the_sync_just_wrote(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pre-marker file the server now serves is replaced, never deleted afterwards."""
    from chrys.service.profiles.models.catalog import ModelCatalog, apply_catalog
    from chrys.service.profiles.models.loader import load_profile_from_yaml
    from chrys.service.profiles.models.schema import ModelProfile

    monkeypatch.setattr(catalog_module, "catalog_directory", lambda: tmp_path)
    (tmp_path / "server-a.yaml").write_text("id: server-a\nname: Old Name\nmodel_id: old\n", encoding="utf-8")

    apply_catalog(ModelCatalog(items=(ModelProfile(id="server-a", name="Server A", model_id="a"),)))

    assert (tmp_path / "server-a.yaml").is_file(), "the served profile must survive the clear that follows it"
    assert load_profile_from_yaml(tmp_path / "server-a.yaml").name == "Server A"
    assert "synced_from_server: true" in (tmp_path / "server-a.yaml").read_text(encoding="utf-8")


def test_one_marked_file_stops_the_upgrade_clear(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A mixed directory is a synced catalog with user files: unmarked ones stay."""
    from chrys.service.profiles.models.catalog import ModelCatalog, apply_catalog
    from chrys.service.profiles.models.schema import ModelProfile

    monkeypatch.setattr(catalog_module, "catalog_directory", lambda: tmp_path)
    (tmp_path / "stale.yaml").write_text(
        "id: stale\nname: Stale\nmodel_id: old\nsynced_from_server: true\n", encoding="utf-8"
    )
    (tmp_path / "mine.yaml").write_text("id: mine\nname: Mine\nmodel_id: mine\n", encoding="utf-8")

    apply_catalog(ModelCatalog(items=(ModelProfile(id="server-a", name="Server A", model_id="a"),)))

    assert not (tmp_path / "stale.yaml").exists(), "a dropped server profile is stale cleanup, not upgrade cleanup"
    assert (tmp_path / "mine.yaml").is_file(), "one marker proves the directory is post-marker, so nothing is cleared"


def test_an_unreadable_profile_vetoes_the_upgrade_clear(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A directory that cannot be judged is preserved, never wiped blind."""
    import logging

    from chrys.service.profiles.models.catalog import ModelCatalog, apply_catalog
    from chrys.service.profiles.models.schema import ModelProfile

    monkeypatch.setattr(catalog_module, "catalog_directory", lambda: tmp_path)
    (tmp_path / "broken.yaml").write_text("name: [unclosed\n", encoding="utf-8")
    (tmp_path / "hand-written.yaml").write_text("id: hand\nname: Hand\nmodel_id: mine\n", encoding="utf-8")

    with caplog.at_level(logging.WARNING):
        apply_catalog(ModelCatalog(items=(ModelProfile(id="server-a", name="Server A", model_id="a"),)))

    assert (tmp_path / "broken.yaml").is_file(), "an unreadable file is no proof of anything"
    assert (tmp_path / "hand-written.yaml").is_file(), "cannot prove all-unmarked, so nothing is cleared"
    assert "skipping the first-upgrade clear" in caplog.text


def test_an_empty_profile_file_does_not_veto_the_upgrade_clear(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A 0-byte leftover cannot be a server profile, so it must not block the convergence."""
    from chrys.service.profiles.models.catalog import ModelCatalog, apply_catalog
    from chrys.service.profiles.models.schema import ModelProfile

    monkeypatch.setattr(catalog_module, "catalog_directory", lambda: tmp_path)
    (tmp_path / "empty.yaml").write_text("", encoding="utf-8")
    (tmp_path / "hand-written.yaml").write_text("id: hand\nname: Hand\nmodel_id: mine\n", encoding="utf-8")

    apply_catalog(ModelCatalog(items=(ModelProfile(id="server-a", name="Server A", model_id="a"),)))

    assert not (tmp_path / "empty.yaml").exists(), "readable but not a mapping is 'no marker', not 'unknown'"
    assert not (tmp_path / "hand-written.yaml").exists()
    assert (tmp_path / "server-a.yaml").is_file()


def test_a_corrupt_file_does_not_veto_the_clear_when_the_sync_rewrites_that_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A served id is overwritten anyway, so its unreadable marker cannot block the clear."""
    from chrys.service.profiles.models.catalog import ModelCatalog, apply_catalog
    from chrys.service.profiles.models.schema import ModelProfile

    monkeypatch.setattr(catalog_module, "catalog_directory", lambda: tmp_path)
    (tmp_path / "server-a.yaml").write_text("name: [unclosed\n", encoding="utf-8")
    (tmp_path / "hand-written.yaml").write_text("id: hand\nname: Hand\nmodel_id: mine\n", encoding="utf-8")

    apply_catalog(ModelCatalog(items=(ModelProfile(id="server-a", name="Server A", model_id="a"),)))

    assert not (tmp_path / "hand-written.yaml").exists(), "the unreadable file is being replaced, so it is no veto"
    assert "synced_from_server: true" in (tmp_path / "server-a.yaml").read_text(encoding="utf-8")


def test_a_saved_custom_profile_survives_a_later_sync(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Once the directory carries markers, an unmarked save joins it and survives."""
    from chrys.service.profiles.models.catalog import ModelCatalog, apply_catalog
    from chrys.service.profiles.models.schema import ModelProfile
    from chrys.service.profiles.models.serializer import save_profile

    fake_platform = type("P", (), {"config_dir": tmp_path})()
    monkeypatch.setattr("chrys.foundation.platform.get_platform", lambda: fake_platform)
    monkeypatch.setattr(catalog_module, "catalog_directory", lambda: tmp_path / "models")

    # The first sync over an empty directory is a fresh install, not an upgrade.
    apply_catalog(ModelCatalog(items=(ModelProfile(id="server-a", name="Server A", model_id="a"),)))
    save_profile(ModelProfile(id="my-custom", name="My Custom", model_id="mine"))
    apply_catalog(ModelCatalog(items=(ModelProfile(id="server-a", name="Server A", model_id="a"),)))

    assert (tmp_path / "models" / "my-custom.yaml").is_file(), "a saved profile outlives the next sync"
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
    assert "overwrote same-id profiles" in caplog.text


def test_a_failed_publish_leaves_the_previous_catalog_and_no_staged_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every profile is staged before the first rename, so a write failure changes nothing."""
    from chrys.service.profiles.models.catalog import ModelCatalog, ModelCatalogError, apply_catalog
    from chrys.service.profiles.models.schema import ModelProfile

    monkeypatch.setattr(catalog_module, "catalog_directory", lambda: tmp_path)
    previous = tmp_path / "server-a.yaml"
    previous.write_text("id: server-a\nname: Previous\nmodel_id: old\nsynced_from_server: true\n", encoding="utf-8")

    real_write = catalog_module._write_profile
    calls = 0

    def flaky(path: Path, profile: ModelProfile) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("disk full")
        real_write(path, profile)

    monkeypatch.setattr(catalog_module, "_write_profile", flaky)

    with pytest.raises(ModelCatalogError, match="Cannot publish"):
        apply_catalog(
            ModelCatalog(
                items=(
                    ModelProfile(id="server-a", name="Server A", model_id="a"),
                    ModelProfile(id="server-b", name="Server B", model_id="b"),
                )
            )
        )

    assert "name: Previous" in previous.read_text(encoding="utf-8"), "nothing was renamed, so the old file stands"
    assert not list(tmp_path.glob("*.tmp")), "a failed publish must not leave staged files"


def test_staged_files_from_an_interrupted_publish_are_removed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A leftover ``*.yaml.tmp`` is never loaded, and the next publish clears it."""
    from chrys.service.profiles.models.catalog import ModelCatalog, apply_catalog
    from chrys.service.profiles.models.schema import ModelProfile

    monkeypatch.setattr(catalog_module, "catalog_directory", lambda: tmp_path)
    (tmp_path / "server-a.yaml.tmp").write_text("half-written: [\n", encoding="utf-8")

    apply_catalog(ModelCatalog(items=(ModelProfile(id="server-a", name="Server A", model_id="a"),)))

    assert not list(tmp_path.glob("*.tmp")), "a successful publish leaves no staging files"
    assert (tmp_path / "server-a.yaml").is_file()


def test_sync_warns_when_a_custom_yml_shadows_a_served_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A user .yml is never overwritten, but it shadows the server model after reload."""
    import logging

    from chrys.service.profiles.models.catalog import ModelCatalog, apply_catalog
    from chrys.service.profiles.models.schema import ModelProfile

    monkeypatch.setattr(catalog_module, "catalog_directory", lambda: tmp_path)
    # A marker-bearing directory first: this .yml is a user file inside a synced
    # catalog, not a leftover of the pre-marker era the upgrade clear targets.
    apply_catalog(ModelCatalog(items=(ModelProfile(id="server-b", name="Server B", model_id="b"),)))
    (tmp_path / "server-a.yml").write_text(
        "id: server-a\nname: Custom Shadow\nmodel_id: mine\nsynced_from_server: false\n", encoding="utf-8"
    )

    with caplog.at_level(logging.WARNING):
        apply_catalog(
            ModelCatalog(
                items=(
                    ModelProfile(id="server-a", name="Server A", model_id="a"),
                    ModelProfile(id="server-b", name="Server B", model_id="b"),
                )
            )
        )

    assert (tmp_path / "server-a.yaml").is_file(), "the server file is still written"
    assert (tmp_path / "server-a.yml").is_file(), "a user .yml is never overwritten"
    assert "will shadow it after reload" in caplog.text
