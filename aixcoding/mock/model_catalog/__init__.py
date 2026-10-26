# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Chrys model catalog mock server (local debug tool, never shipped).

Simulates the backend that publishes the server-owned catalog consumed by the
model sync (fetch -> validate -> replace ``~/.chrys/models`` wholesale). Its
job is to make every failure lane reachable by hand: an empty catalog, an
invalid one, an HTTP 500, a timeout, and content that drifts under a version
that never changes.

Data comes from :mod:`aixcoding.mock.model_catalog.source` (a JSON file
whose content is the response, re-read per request — ``config_new.json`` by
default);
behaviour comes from :mod:`aixcoding.mock.model_catalog.modes`; the runtime
switch lives in :mod:`aixcoding.mock.model_catalog.state`. The HTTP layer in
:mod:`aixcoding.mock.model_catalog.server` only assembles them.

Public API lives in :mod:`aixcoding.mock.model_catalog.server`; the canonical
entry point is :func:`aixcoding.mock.model_catalog.server.start`.

Endpoints::

    GET  /llm/api/v1/continue-config/dispatch   catalog payload for the current mode
    POST /mock/control   {"mode": ..., "delay": N}

Only these two: a second catalog route serving the same payload was redundant,
and the mode/revision/version/request counters ride back in the control
response instead of a separate read-only endpoint.

Layout::

    aixcoding/mock/
        model_catalog/          # this subpackage
            __init__.py         # this file
            server.py           # HTTP layer, routing, CLI
            source.py           # catalog payload source (config_new.json, or --catalog)
            modes.py            # failure modes and payload construction
            state.py            # runtime mode/revision switch
            README.md           # endpoints, modes, usage

    aixcoding/tests/mock/
        conftest.py                  # pytest fixtures (loopback-safe transport)
        test_model_catalog_server.py # contract tests
"""

from __future__ import annotations
