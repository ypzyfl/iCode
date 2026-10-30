# ruff: noqa: T201
# (stderr notes are the observable-degradation channel, DEVELOPMENT.md §9)
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Startup aggregation entry for AIxCoding customizations.

Design: aixcoding/docs/auth-logging/design.md (signed off 2026-10-30).

``app/aixcoding`` is the host-seam package (``tui`` sibling, ADR-0011
placement): startup wiring is a seam with the host CLI, and the app tier is
the only tier that can aggregate startup tasks from every lower tier without
a ceiling. ``chrys.app.cli.app:main`` is the sole caller — one upstream
touch, frozen: new startup tasks are appended to ``_TASKS`` below instead of
re-wiring upstream.

Contract: each task is idempotent and fail-safe on its own; this entry only
adds per-task containment (§9 observable degradation — stderr note, never
propagate) so adding a task can never break CLI startup.
"""

from __future__ import annotations

import sys


def _ensure_file_sink() -> None:
    """Attach the ``aixcoding`` rotating file sink (kernel diagnostics)."""
    from chrys.kernel.aixcoding.diagnostics.logging_support import ensure_file_sink

    ensure_file_sink()


# Startup tasks in order; each must stay idempotent + individually fail-safe.
_TASKS = (_ensure_file_sink,)


def aixcoding_startup() -> None:
    """Run every customization startup task; per-task fail-safe, idempotent."""
    for task in _TASKS:
        try:
            task()
        except Exception as exc:
            # Degraded but observable (§9): a failing task must not break startup.
            print(f"aixcoding.startup: task {task.__name__} failed ({exc}); skipped", file=sys.stderr)
