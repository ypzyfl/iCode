# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Fork-owned snapshot types for the shared AIxCoding configuration."""

from __future__ import annotations

from dataclasses import dataclass, field

from chrys.kernel.aixcoding.diagnostics.config import DiagnosticsConfig


@dataclass(frozen=True)
class ModelCatalogConfig:
    """``[model_catalog]`` section: service base URL and the auto-sync switch."""

    base_url: str = ""
    #: ``None`` = unset: the tier default applies (local off, dev/prod on).
    auto_sync: bool | None = None


@dataclass(frozen=True)
class UpdateConfig:
    """``[update]`` section: the release-check base URL (ADR-0022 reserved key)."""

    base_url: str = ""


@dataclass(frozen=True)
class AixcodingConfig:
    """One process-wide configuration snapshot."""

    environment: str
    diagnostics: DiagnosticsConfig
    model_catalog: ModelCatalogConfig
    update: UpdateConfig = field(default_factory=UpdateConfig)
