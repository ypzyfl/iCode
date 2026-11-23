# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Built-in update commands: the pinned file-mirror root.

The mirror root is temporarily pinned to the production origin (design
revision 20): the dev gateway has not published the bare-origin file mirror,
so a D4-derived install URL answers 400 there and every dev update would
fail at the download step.  ``[update].base_url`` still moves the
release-check endpoint; only the mirror stays pinned until the dev mirror
ships, when the D4 derivation (origin of the check base + ``MIRROR_PATH``)
returns.  The path is the file mirror's directory layout — the same root
the internal install scripts default to (``aixcoding/release/``).

Design: aixcoding/docs/batches/auto-update/design.md
"""

from __future__ import annotations

import sys
from urllib.parse import urlsplit

from chrys.service.aixcoding.update.client import _TIER_BASES

MIRROR_PATH = "/aixcoding/file/aixcoding"

# The origin is reused from the tier table so a prod IP change touches one
# place (update/client.py owns it) instead of a fourth hardcoded copy.
_prod = urlsplit(_TIER_BASES["prod"])
_PINNED_MIRROR_ORIGIN = f"{_prod.scheme}://{_prod.netloc}"


def mirror_root() -> str:
    """The file-mirror root, pinned to the production origin (design revision 20).

    Environment-independent by decision: the known consequence is that a
    dev-environment check installs the production artifact (cross-tier mix)
    until the dev mirror ships.  When it does, restore the D4 derivation
    here — the origin of the check base (``urlsplit(resolve_check_base())``,
    empty when the base does not parse) plus ``MIRROR_PATH``; there is no
    flow-level "command unavailable" check — the wrapper's download fails,
    and its failure branch tallies the attempt and stops instead of
    relaunching (design §3.4/§3.6).
    """
    return _PINNED_MIRROR_ORIGIN + MIRROR_PATH


def install_script_url() -> str:
    """The internal install script URL for this platform."""
    script = "install.ps1" if sys.platform == "win32" else "install.sh"
    return f"{mirror_root().rstrip('/')}/{script}"
