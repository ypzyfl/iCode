# ruff: noqa: T201
# (stderr notes are the observable-degradation channel, DEVELOPMENT.md §9)
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Read and cache ``~/.chrys/aixcoding.toml`` for AIxCoding features."""

from __future__ import annotations

import logging
import os
import sys
import tomllib
from functools import cache
from pathlib import Path

from chrys.kernel.aixcoding.diagnostics.config import (
    DEFAULT_LEVEL,
    DEFAULT_PANEL,
    DiagnosticsConfig,
    LoggingConfig,
)

from .types import AixcodingConfig, ModelCatalogConfig, UpdateConfig

CONFIG_FILE_NAME = "aixcoding.toml"
ENVIRONMENT_VARIABLE = "AIXCODING_ENVIRONMENT"
VALID_ENVIRONMENTS = ("local", "dev", "prod")
DEFAULT_ENVIRONMENT = "prod"

# AIxCoding logging (batches/logging-coverage): config errors are
# user-actionable -- stderr stays (logging may not be up yet), and the
# same Chinese message double-writes onto the aixcoding tree (ADR-0017,
# DEVELOPMENT.md §9). Before the sink exists the WARNING rides stdlib
# lastResort to stderr, which is today's behavior.
_log = logging.getLogger("aixcoding.config")
_detail_log = logging.getLogger("aixcoding.detail.config")
_DETAIL_LEVEL = 5  # mirrors diagnostics.logging_support (session.py precedent)

_LEVEL_BY_NAME = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def _warn(message: str) -> None:
    print(f"aixcoding.config: {message}", file=sys.stderr)
    _log.warning("%s", message)
    _detail_log.log(_DETAIL_LEVEL, "%s", message)


def _resolve_config_dir(config_dir: Path | None) -> Path:
    if config_dir is not None:
        return config_dir
    try:
        from chrys.foundation.platform import get_platform

        return get_platform().config_dir
    except Exception:
        _warn("无法确定配置目录，改用 ~/.chrys。")
        return Path.home() / ".chrys"


def _resolve_environment(data: dict) -> str:
    if ENVIRONMENT_VARIABLE in os.environ:
        raw: object = os.environ[ENVIRONMENT_VARIABLE]
        origin = ENVIRONMENT_VARIABLE
    elif "environment" in data:
        raw = data["environment"]
        # Literal, never the source path: the main volume's WARNING must not
        # carry the absolute path (and the username inside it) -- PII stays
        # off the public channel (batches/logging-coverage review F1).
        origin = "配置文件 aixcoding.toml"
    else:
        return DEFAULT_ENVIRONMENT
    if not isinstance(raw, str):
        _warn(f"环境配置无效（{origin}），已回退默认环境 {DEFAULT_ENVIRONMENT}。")
        return DEFAULT_ENVIRONMENT
    value = raw.strip().lower()
    if value not in VALID_ENVIRONMENTS:
        _warn(f"环境配置无效（{origin}），已回退默认环境 {DEFAULT_ENVIRONMENT}。")
        return DEFAULT_ENVIRONMENT
    return value


def _coerce_level(value: object) -> int:
    if isinstance(value, str):
        return _LEVEL_BY_NAME.get(value.strip().upper(), logging.INFO)
    return logging.INFO


def _load_diagnostics(data: dict, source: Path | None) -> DiagnosticsConfig:
    section = data.get("logging")
    if not isinstance(section, dict):
        section = {}
    panel_value = section.get("panel", DEFAULT_PANEL)
    return DiagnosticsConfig(
        logging=LoggingConfig(
            level=_coerce_level(section.get("level", DEFAULT_LEVEL)),
            panel=panel_value if isinstance(panel_value, bool) else DEFAULT_PANEL,
        ),
        source=source,
    )


def _load_model_catalog(data: dict) -> ModelCatalogConfig:
    section = data.get("model_catalog", {})
    if not isinstance(section, dict):
        _warn("配置项 [model_catalog] 无效，已回退部署层默认。")
        return ModelCatalogConfig()
    # Per-field degrade: one bad key must not discard the other — a bad
    # base_url dropping an explicit auto_sync would silently fall back to
    # the tier default (catalog-auto-sync design).
    base_url = section.get("base_url", "")
    if not isinstance(base_url, str):
        _warn("配置项 model_catalog.base_url 无效，已回退部署层默认。")
        base_url = ""
    auto_sync = section.get("auto_sync")
    if auto_sync is not None and not isinstance(auto_sync, bool):
        _warn("配置项 model_catalog.auto_sync 无效，已回退默认。")
        auto_sync = None
    return ModelCatalogConfig(base_url=base_url.strip(), auto_sync=auto_sync)


def _load_update(data: dict) -> UpdateConfig:
    section = data.get("update", {})
    if not isinstance(section, dict):
        _warn("配置项 [update] 无效，已回退部署层默认。")
        return UpdateConfig()
    base_url = section.get("base_url", "")
    if not isinstance(base_url, str):
        _warn("配置项 update.base_url 无效，已回退部署层默认。")
        base_url = ""
    return UpdateConfig(base_url=base_url.strip())


@cache
def load_config(config_dir: Path | None = None) -> AixcodingConfig:
    """Return one fail-safe snapshot; environment variables override TOML."""
    path = _resolve_config_dir(config_dir) / CONFIG_FILE_NAME
    source: Path | None = path
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        data = {}
        source = None
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        _warn(f"配置文件无法解析（{exc}），已回退全部默认。")
        data = {}
    return AixcodingConfig(
        environment=_resolve_environment(data),
        diagnostics=_load_diagnostics(data, source),
        model_catalog=_load_model_catalog(data),
        update=_load_update(data),
    )
