# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Built-in update commands: the mirror root derived from the check base.

The mirror root is the *origin* (scheme + host) of the same base the
release check resolves to (design D4, second revision): one
``[update].base_url`` override moves both the check endpoint and the update
command.  The path is the file mirror's directory layout — the same root
the internal install scripts default to (``aixcoding/release/``).

Design: aixcoding/docs/batches/auto-update/design.md
"""

from __future__ import annotations

import sys
from urllib.parse import urlsplit

from chrys.service.aixcoding.update.client import resolve_check_base

MIRROR_PATH = "/aixcoding/file/aixcoding"


def mirror_root() -> str:
    """The file-mirror root derived from the release-check base's origin.

    Empty when the configured base does not parse.  ``install_script_url()``
    then yields a relative ``/install.sh`` (or ``/install.ps1``); there is no
    flow-level "command unavailable" check — the wrapper's download fails, and
    its failure branch tallies the attempt and stops instead of relaunching
    (design §3.4/§3.6).
    """
    split = urlsplit(resolve_check_base())
    if not split.scheme or not split.netloc:
        return ""
    return f"{split.scheme}://{split.netloc}{MIRROR_PATH}"


def install_script_url() -> str:
    """The internal install script URL for this platform."""
    script = "install.ps1" if sys.platform == "win32" else "install.sh"
    return f"{mirror_root().rstrip('/')}/{script}"
