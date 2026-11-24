# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""After-turn telemetry notice and dispatch entry (design §3.1).

The finalizer constructs one immutable notice per run after save/checkpoint
and calls :func:`dispatch_telemetry_notice` (lazy import — the upstream
seam stays free of constructor injection). The synchronous path only
validates the notice, merges same-pass duplicates by the full
``(session_id, logical_turn_id, pass_id)`` key and enqueues into the
per-session worker; file analysis and network delivery live entirely in the
worker (N3 layering: notify ≠ analyzed ≠ delivered).

V2 probe evidence: the session dimension in the merge key is required —
dropping it merges distinct sessions' same-named turns.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TurnTelemetryNotice:
    """Immutable per-run telemetry notification payload (memory only)."""

    session_id: str
    session_dir: Path | None
    logical_turn_id: str
    pass_id: str
    turn_number: int
    is_retry: bool
    saved: bool
    """Whether this run's session save attempt persisted (False ⇒ skip, never read stale files)."""

    # Turn-outcome `status` removed by owner ruling (2026-11-23): the finalizer
    # outcome (failed/interrupted/ok) has no consumer in this batch, is absent
    # from the 0.28.0 baseline, and would need a new turn-level report interface
    # (batch 2's selected-Agent 1001). Deferred — record only, no implementation;
    # do not reintroduce without that batch's design re-checking the semantics.


def dispatch_telemetry_notice(notice: TurnTelemetryNotice) -> None:
    """Synchronous dispatch: validate, merge same-pass duplicates, enqueue.

    Ordinary exceptions are contained (logged at debug with traceback) so
    telemetry can never change a turn's outcome; ``CancelledError`` is a
    ``BaseException`` and propagates untouched by design.
    """
    from chrys.service.aixcoding.telemetry.owner import get_telemetry_owner

    try:
        get_telemetry_owner().dispatch(notice)
    except Exception:
        _logger.debug("telemetry notice dispatch contained an error", exc_info=True)
