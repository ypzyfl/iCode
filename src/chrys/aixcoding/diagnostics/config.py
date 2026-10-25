# ruff: noqa: T201
# (stderr notes are the observable-degradation channel, DEVELOPMENT.md §9)
"""Reader for ``~/.chrys/aixcoding.toml`` — the customization-layer config base.

Design: aixcoding/docs/diagnostics/design.md (signed off 2026-10-25).

Read-only via :mod:`tomllib`; a missing file, missing keys or invalid syntax
all fall back to built-in defaults — the diagnostics layer must never break
startup (fail-safe, DEVELOPMENT.md §9). This file is the *shared* config
infrastructure for the whole customization layer: future features with
"editable before start, applied on restart" settings extend this file rather
than adding new config files.
"""

from __future__ import annotations

import logging
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

CONFIG_FILE_NAME = "aixcoding.toml"
DEFAULT_LEVEL = "INFO"
DEFAULT_PANEL = False
VALID_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


@dataclass(frozen=True)
class LoggingConfig:
    """``[logging]`` section: file level and F6-panel bubble switch."""

    level: int
    panel: bool


@dataclass(frozen=True)
class DiagnosticsConfig:
    """Parsed customization config; ``source`` names the file actually read."""

    logging: LoggingConfig
    source: Path | None


def _default_logging() -> LoggingConfig:
    return LoggingConfig(level=logging.INFO, panel=DEFAULT_PANEL)


def resolve_config_dir(config_dir: Path | None) -> Path | None:
    """Use the caller's dir; else the upstream platform dir, lazily."""
    if config_dir is not None:
        return config_dir
    try:  # lazy + fully degraded: config is optional (R9: foundation tier)
        from chrys.foundation.platform import get_platform

        return get_platform().config_dir
    except Exception:
        print("aixcoding.config: platform config_dir unavailable, using ~/.chrys", file=sys.stderr)
        return Path.home() / ".chrys"


_LEVEL_BY_NAME = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def _coerce_level(value: object) -> int:
    if isinstance(value, str):
        return _LEVEL_BY_NAME.get(value.strip().upper(), logging.INFO)
    return logging.INFO


def load_config(config_dir: Path | None = None) -> DiagnosticsConfig:
    """Load the customization config; never raises (fail-safe defaults)."""
    resolved = resolve_config_dir(config_dir)
    path = resolved / CONFIG_FILE_NAME if resolved is not None else None
    if path is None or not path.is_file():
        return DiagnosticsConfig(logging=_default_logging(), source=None)
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        # Observable degradation (§9): named on stderr, defaults keep working.
        print(f"aixcoding.config: cannot parse {path} ({exc}); using defaults", file=sys.stderr)
        return DiagnosticsConfig(logging=_default_logging(), source=path)
    section = data.get("logging")
    if not isinstance(section, dict):
        section = {}
    panel_value = section.get("panel", DEFAULT_PANEL)
    logging_cfg = LoggingConfig(
        level=_coerce_level(section.get("level", DEFAULT_LEVEL)),
        panel=panel_value if isinstance(panel_value, bool) else DEFAULT_PANEL,
    )
    return DiagnosticsConfig(logging=logging_cfg, source=path)
