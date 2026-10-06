# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Exit codes (TS behavioural baseline ``exit-codes.ts``; C11 semantics).

Detach + durable hook jobs are terminalised by the engine's detached worker:
0 → ``done/``, anything else → ``failed/`` (observable, never requeued —
recovery is the next hook firing plus the ledger's content-hash idempotency).
"""

from __future__ import annotations

EXIT_OK = 0
"""Success / idempotent idle run."""
EXIT_USAGE = 2
"""Argument error; never retried."""
EXIT_SESSION_NOT_FOUND = 20
"""Session file could not be located (root override included); never retried."""
EXIT_ROOT_UNREADABLE = 21
"""Sessions root is not an accessible directory; never retried."""
EXIT_CONFIG_INVALID = 22
"""report-config missing/corrupt/invalid; never retried (next firing recovers
after the config is fixed)."""
EXIT_MALFORMED = 30
"""JSON/structure parse failure; never retried."""
EXIT_REPORT_FAILED = 40
"""Analysis succeeded but reporting failed (in-process retries exhausted);
ledger does not advance — terminal in ``failed/``, next firing re-reports."""
EXIT_TIMEOUT = 41
"""Forced self-exit timeout; ledger did not advance."""
EXIT_DEFERRED = 42
"""Lock held by a concurrent instance; deferred. Value is observability, not
requeue: 0 would mark the outbox job ``done/`` silently and the freshest
revision of that window would be lost with no trace, while 42 lands in
``failed/`` for the desktop D3 alert to aggregate."""
