# ruff: noqa: T201
# (stderr notes are the observable-degradation channel, DEVELOPMENT.md §9)
"""``aixcoding.*`` logger factory: rotating file sink always on, panel bubble opt-in.

Design: aixcoding/docs/diagnostics/design.md (signed off 2026-10-25).

Layout: handlers attach to the top-level ``aixcoding`` logger only — child
loggers (``aixcoding.telemetry``…) propagate to it by standard logging rules.
``propagate`` on the top-level logger is the F6-panel switch: ``panel=true``
lets records bubble further to the root logger where the upstream
``_TuiLogHandler`` picks them up (its whitelist derives from ``MODULE_ORDER``
in ``app/tui/screens/logs/screen.py``); ``panel=false`` keeps records off the
UI while the file sink stays active. Anyone importing this module gets the
feature; the launcher is not required.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .config import DiagnosticsConfig

ROOT_LOGGER_NAME = "aixcoding"
LOG_DIR_NAME = "aixcoding-logs"
LOG_FILE_NAME = "aixcoding.log"
MAX_BYTES = 1_000_000
BACKUP_COUNT = 3
FMT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


class _Marker(RotatingFileHandler):
    """Type tag so repeated setup calls can find and reuse our handler."""


def get_logger(child: str = "") -> logging.Logger:
    """Named logger inside the aixcoding subtree (e.g. ``get_logger("telemetry")``)."""
    name = ROOT_LOGGER_NAME if not child else f"{ROOT_LOGGER_NAME}.{child}"
    return logging.getLogger(name)


def _file_sink(logger: logging.Logger, config_dir: Path) -> Path | None:
    """Attach the rotating file handler; None (with a stderr note) on failure."""
    log_dir = config_dir / LOG_DIR_NAME
    log_path = log_dir / LOG_FILE_NAME
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        handler = _Marker(
            log_path,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
            delay=True,
        )
        handler.setFormatter(logging.Formatter(FMT))
        logger.addHandler(handler)
        return log_path
    except OSError as exc:
        # Degraded but observable (§9): sink unavailable → stderr note, no crash.
        print(f"aixcoding.logging: file sink unavailable at {log_path} ({exc}); logs off", file=sys.stderr)
        return None


def setup_logging(cfg: DiagnosticsConfig, config_dir: Path | None = None) -> Path | None:
    """Idempotently configure the aixcoding logging subtree.

    Returns the log file path, or None when the sink could not be created.
    Safe to call repeatedly (e.g. tests, re-entry): an existing sink is reused.
    """
    from .config import resolve_config_dir

    logger = logging.getLogger(ROOT_LOGGER_NAME)
    logger.setLevel(cfg.logging.level)
    logger.propagate = cfg.logging.panel
    for handler in logger.handlers:
        if isinstance(handler, _Marker):  # idempotent: reuse the existing sink
            return Path(handler.baseFilename)
    resolved = resolve_config_dir(config_dir)
    if resolved is None:
        print("aixcoding.logging: no config dir resolvable; file sink skipped", file=sys.stderr)
        return None
    return _file_sink(logger, resolved)
