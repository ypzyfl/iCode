# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""AIxCoding TUI widgets: the device-code login dialog.

Text lives here rather than in the host i18n catalog by design (the plan's
constraint #5): ``scripts/i18n.py`` only scans ``src/chrys``, so aixcoding
ships its copy inline and the host app only registers the ``/login`` and
``/logout`` command descriptions.
"""

from aixcoding.tui.login import LoginDialog

__all__ = ["LoginDialog"]
