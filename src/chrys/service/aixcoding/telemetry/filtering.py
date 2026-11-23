# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Model-source filtering: report only catalog-dispatched models (fail-closed).

The probe reuses the catalog's own ``synced_from_server`` marker semantics
(``service/aixcoding/models/catalog.py``, commit 659b56ef). Ruling 2026-11-20
(requirements §2.5): a non-dispatched or undeterminable profile skips the
whole batch with a detail log — never a partial report, never a guess.

Implementation details pinned in design §3.4: same-stem ``.yaml`` wins over
``.yml``; a profile with no file is undeterminable (skip); results are read
per call in this slice — the in-process cache lands with the sync-invality
hook, not by guesswork.
"""

from __future__ import annotations

import logging

from chrys.service.aixcoding.models.catalog import _is_server_synced, catalog_directory

logger = logging.getLogger(__name__)


def is_server_dispatched_model(profile_name: str | None) -> bool:
    """True only when the profile file carries the server marker (fail-closed)."""
    if not profile_name:
        return False
    directory = catalog_directory()
    for suffix in (".yaml", ".yml"):
        candidate = directory / f"{profile_name}{suffix}"
        if candidate.exists():
            return _is_server_synced(candidate)
    logger.debug("telemetry filtering: profile %s has no file — undeterminable, skipping", profile_name)
    return False
