# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Local mocks of the AIxCoding internal backends (dev assets, never shipped).

One subpackage per backend service (``auth`` / ``update`` / ``model_catalog``;
``telemetry`` joins with its migration). Each subpackage's ``server.py``
exposes ``create_server(...)`` for tests plus a CLI for manual runs
(``python aixcoding/mock/<name>/server.py`` or
``python -m aixcoding.mock.<name>.server``).

``python -m aixcoding.mock`` starts the base combo for manual TUI runs
(model_catalog :7777 with the auth mock mounted on the same port, plus
update :7778).

The registry, conventions and the new-mock checklist live in ``README.md``
(DIRECTORY.md §6); contract tests live in ``aixcoding/tests/mock/``.
"""

from __future__ import annotations
