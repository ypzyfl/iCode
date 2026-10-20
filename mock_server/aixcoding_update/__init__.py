# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""AIxCoding TUI update-detection mock server (local debug tool, never shipped).

Simulates ``GET /csas/api/v1/releases/check`` — the release-check contract the
TUI update-detection feature will call at startup. The real backend does not
exist yet; this mock freezes the wire contract so client work and manual runs
can proceed: strict query validation
(unknown/missing/invalid → ``400 invalid_app_release_query``), v2 manifest
answers with ``ETag``/``304`` support, ``204`` for "no applicable release",
plus fault modes (``error`` / ``garbage`` / slow) covering the client's
silent-failure paths.

Public API lives in :mod:`mock_server.aixcoding_update.server`; the canonical
entry points are :func:`mock_server.aixcoding_update.server.create_server`
(tests, ephemeral port) and ``python mock_server/aixcoding_update/server.py``
(CLI, port 7778). Point the TUI at it with
``AIXCODING_EXTENSION_BASE_URL=http://127.0.0.1:7778/csas``.

Layout::

    mock_server/
        aixcoding_update/     # this subpackage
            __init__.py      # this file
            server.py        # HTTP server, strict validation, modes, debug endpoints
            test_server.py   # contract tests (stdlib urllib, no fixtures needed)
            README.md        # endpoints, modes, CLI usage

The TUI client (``src/chrys/aixcoding/update_detection.py``) ships alongside
this mock: its end-to-end tests live in ``tests/app/aixcoding/``, while the
contract tests here keep guarding the mock itself.
"""

from __future__ import annotations
