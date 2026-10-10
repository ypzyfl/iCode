# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Chrys session reporting mock server (local debug tool, never shipped).

Simulates the Chrys `/csas/telemetry/api/v1/...` receiving endpoints with
SQLite-backed inspection, fault injection, and a zero-dependency debug view
page. The package is intentionally independent of ``src/chrys/`` so it stays
a dev-only asset and never enters the production wheel.

The receiving side validates through
:mod:`chrys.foundation.reporting.schemas` (the single source of truth shared
with the sending side), so the mock cannot drift from the real Chrys
contract.

Public API lives in :mod:`mock_server.chrys_telemetry.server`; the canonical
entry point is :func:`mock_server.chrys_telemetry.server.start`.

Layout::

    mock_server/
        chrys_telemetry/        # this subpackage
            __init__.py         # this file
            server.py           # HTTP server, SQLite store, fault injection
            conftest.py         # pytest fixtures (loopback-safe transport)
            test_server.py      # integration tests
            README.md           # endpoints, fault modes, usage
"""

from __future__ import annotations
