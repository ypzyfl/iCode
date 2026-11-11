# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""The auto-sync switch: LOCAL defaults off, explicit values override every tier.

Covers the two entry guards (startup blocking sync and poll start — the login
resume flows through the latter), the directory-ownership semantics of
``is_catalog_managed``, and the tier-default split
(aixcoding/docs/batches/catalog-auto-sync/design.md).
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from chrys.service.aixcoding.models import catalog as catalog_module
from chrys.service.aixcoding.models.catalog import (
    ModelCatalog,
    is_catalog_managed,
    sync_catalog_blocking,
)
from chrys.service.profiles.models.registry import ModelProfileRegistry
from chrys.service.profiles.models.schema import ModelProfile


def _configure(monkeypatch: pytest.MonkeyPatch, *, tier: str, auto_sync: bool | None) -> None:
    """Stub the config snapshot: tier and switch fixed without touching real HOME."""
    cfg = SimpleNamespace(
        environment=tier,
        model_catalog=SimpleNamespace(base_url="", auto_sync=auto_sync),
    )
    monkeypatch.setattr(catalog_module, "load_config", lambda: cfg)


def _must_not_fetch(*args: object, **kwargs: object) -> None:
    raise AssertionError("auto_sync off: no catalog request may be made")


@pytest.mark.parametrize("tier", ["local", "dev", "prod"])
@pytest.mark.parametrize("auto_sync", [None, True, False])
def test_auto_sync_enabled_matrix(monkeypatch: pytest.MonkeyPatch, tier: str, auto_sync: bool | None):
    _configure(monkeypatch, tier=tier, auto_sync=auto_sync)
    expected = auto_sync if auto_sync is not None else tier != "local"
    assert catalog_module.auto_sync_enabled() is expected


def test_local_default_disables_blocking_sync(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    _configure(monkeypatch, tier="local", auto_sync=None)
    monkeypatch.setattr(catalog_module, "fetch_catalog", _must_not_fetch)
    monkeypatch.setattr(catalog_module, "catalog_directory", lambda: tmp_path)
    (tmp_path / "mine.yaml").write_text("id: mine\n", encoding="utf-8")

    assert sync_catalog_blocking() is None
    assert (tmp_path / "mine.yaml").read_text(encoding="utf-8") == "id: mine\n"


def test_local_default_disables_poll_start(monkeypatch: pytest.MonkeyPatch):
    _configure(monkeypatch, tier="local", auto_sync=None)
    assert catalog_module.start_sync_runtime(ModelProfileRegistry(), lambda _r: None) is False
    assert catalog_module._runtime is None


def test_resume_after_login_is_blocked(monkeypatch: pytest.MonkeyPatch):
    _configure(monkeypatch, tier="local", auto_sync=None)
    registry = ModelProfileRegistry()
    assert catalog_module.start_sync_runtime(registry, lambda _r: None) is False
    assert catalog_module._last_wiring is not None, "wiring is still remembered for resume, as before"
    assert catalog_module.resume_sync_runtime() is False
    assert catalog_module._runtime is None


@pytest.mark.parametrize("tier", ["dev", "prod"])
def test_dev_prod_defaults_unchanged(monkeypatch: pytest.MonkeyPatch, tier: str):
    _configure(monkeypatch, tier=tier, auto_sync=None)
    monkeypatch.setattr(catalog_module, "catalog_url", lambda: "http://127.0.0.1:1/base")
    monkeypatch.setattr(catalog_module, "has_catalog_credential", lambda: True)
    monkeypatch.setattr(catalog_module, "sync_interval_seconds", lambda: 60.0)
    assert catalog_module.start_sync_runtime(ModelProfileRegistry(), lambda _r: None) is True
    assert catalog_module._runtime is not None and catalog_module._runtime.is_running()


@pytest.mark.parametrize("tier", ["local", "dev", "prod"])
def test_explicit_false_blocks_any_tier(monkeypatch: pytest.MonkeyPatch, tier: str):
    _configure(monkeypatch, tier=tier, auto_sync=False)
    monkeypatch.setattr(catalog_module, "fetch_catalog", _must_not_fetch)
    assert sync_catalog_blocking() is None
    assert catalog_module.start_sync_runtime(ModelProfileRegistry(), lambda _r: None) is False
    assert catalog_module._runtime is None


def test_explicit_true_enables_local(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    _configure(monkeypatch, tier="local", auto_sync=True)
    monkeypatch.setattr(catalog_module, "catalog_directory", lambda: tmp_path)

    async def _fetch(url: str | None = None, *, timeout: float = 3.0) -> ModelCatalog:
        return ModelCatalog(
            items=(ModelProfile(id="a", name="a", provider="openai", model_id="a-m"),),
            version="v1",
        )

    monkeypatch.setattr(catalog_module, "fetch_catalog", _fetch)
    result = sync_catalog_blocking()
    assert result is not None and result.profile_ids == ("a",)
    assert (tmp_path / "a.yaml").exists()


def test_catalog_managed_semantics(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr(catalog_module, "catalog_directory", lambda: tmp_path)

    # auto-sync off, no state: the directory is the user's own.
    _configure(monkeypatch, tier="local", auto_sync=None)
    assert is_catalog_managed() is False

    # auto-sync on (explicit or by tier): a named source manages it, as before.
    _configure(monkeypatch, tier="local", auto_sync=True)
    assert is_catalog_managed() is True
    _configure(monkeypatch, tier="prod", auto_sync=None)
    assert is_catalog_managed() is True

    # A successful sync sticks: server-owned whatever the switch says now.
    _configure(monkeypatch, tier="local", auto_sync=False)
    catalog_module.write_catalog_state(catalog_module.CatalogState(version="v1", source="remote", profile_ids=("a",)))
    assert is_catalog_managed() is True
