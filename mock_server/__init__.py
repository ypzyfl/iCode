# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Local mock servers for development, integration, and contract testing.

This package is a **registry of mocks** for the external services the iCode
agent platform depends on. Each mock is an isolated, self-contained
subpackage that simulates one real backend so product code can be exercised
end-to-end without hitting staging or production.

The umbrella is intentionally thin: there is no shared runtime — each
subpackage owns its own server, fixtures, tests, and README. New mocks are
added by creating a new subdirectory under ``mock_server/`` and following
the same shape.

Current subpackages:

- :mod:`mock_server.chrys_telemetry` — Chrys session reporting endpoints
  (``/csas/telemetry/api/v1/...``)
- :mod:`mock_server.aixcoding_auth` — AIxCoding device-code auth service
  (``/api/v1/auth/...``, ``/api/v1/user/info``)

Conventions for new subpackages:

- Name the directory after the **service or capability** it mocks, with a
  short product prefix where the namespace is shared (e.g. ``chrys_*`` for
  the Chrys agent platform, ``csas_*`` for CSAS backend). Avoid generic
  names like ``api`` or ``backend``.
- Always include: ``__init__.py`` (docstring), ``server.py`` (or a similarly
  descriptive module), ``conftest.py`` (loopback transport fixtures),
  ``test_server.py`` (integration tests), ``README.md`` (endpoints + usage).
- Bind only to loopback addresses. The starting helper must reject any
  non-loopback host at startup.
- Keep all imports from outside ``mock_server/`` strictly to the
  ``chrys.foundation.*`` shared contract module(s) — never reach into
  private modules of the product you are mocking. The mock must remain
  black-box with respect to the contract it pretends to speak.
- Tests must use ``direct_route`` (defined in each subpackage's
  ``conftest.py``) to bypass any system proxy. Bind port 0 and read back
  the kernel-assigned port through the listening socket — never probe for
  a free port.
- ``pyproject.toml``'s ``testpaths = ["tests", "mock_server"]`` already
  includes this directory; new subpackages are picked up automatically.
"""

from __future__ import annotations
