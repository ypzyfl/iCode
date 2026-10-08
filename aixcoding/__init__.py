# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""AIxCoding enterprise login -- iCode incremental module.

This package carries every new line of the iCode TUI device-code login
(OAuth2 Device Authorization Grant), kept physically separate from the
``src/chrys`` main package so the change stays reviewable as one unit:

- ``auth/``   -- protocol client, credential storage, OS-level crypto backends
- ``mock/``   -- loopback mock login server (the intranet auth service is
  unreachable while developing off-site)
- ``tui/``    -- the Textual login dialog

Edits under ``src/chrys`` are wiring only (registering the ``/login`` slash
command, the ``on_mount`` silent check); all business logic lives here.
"""

__version__ = "0.1.0"
