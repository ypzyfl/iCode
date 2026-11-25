# ruff: noqa: T201, RUF001
# (stderr notes are the observable-degradation channel, DEVELOPMENT.md §9;
#  Chinese messages use full-width punctuation -- file-level so a ruff format
#  reflow cannot strand a line-level noqa, PR #141 CI fix)
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Startup aggregation entry for AIxCoding customizations.

``app/aixcoding`` is the host-seam package: app is the only tier that can
aggregate startup tasks from every lower tier without a ceiling.
``chrys.app.cli.app:main`` is the sole caller; new tasks are appended to
``_TASKS`` instead of re-wiring upstream.

Each task is idempotent and fail-safe on its own. This entry adds per-task
containment so adding a task cannot break CLI startup.
"""

from __future__ import annotations

import logging
import sys

from .tasks import _configure_environment, _ensure_file_sink, _install_llm_http_interception

# AIxCoding logging (batches/logging-coverage): a failed startup task is a
# user-facing degrade -- stderr stays (the sink task itself may be the one
# that failed), the same Chinese message double-writes onto the aixcoding
# tree (ADR-0017, DEVELOPMENT.md §9); without a sink the WARNING rides
# stdlib lastResort to stderr. Chinese messages ride the file-level RUF001
# exemption at the top (batches/logging-coverage R13, PR #141 CI fix).
_log = logging.getLogger("aixcoding.startup")
_detail_log = logging.getLogger("aixcoding.detail.startup")
_DETAIL_LEVEL = 5  # mirrors diagnostics.logging_support (session.py precedent)

# Startup tasks in order; each must stay idempotent + individually fail-safe.
_TASKS = (_configure_environment, _ensure_file_sink, _install_llm_http_interception)


def aixcoding_startup() -> None:
    """Run every customization startup task; per-task fail-safe, idempotent."""
    for task in _TASKS:
        try:
            task()
        except Exception as exc:
            # The exception NAME only on both channels: the str of an OSError
            # carries the absolute path with the username -- the public channel
            # stays path-free; the full traceback rides detail's exc_info
            # (PR #141 review C1).
            message = f"启动任务 {task.__name__} 失败（{type(exc).__name__}）；已跳过。"
            print(f"aixcoding.startup: {message}", file=sys.stderr)
            _log.warning("%s", message)
            _detail_log.log(_DETAIL_LEVEL, "%s", message, exc_info=True)
