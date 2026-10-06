# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""attribution.json reading with degradation (TS ``attribution.ts``).

Attribution is independent of report-config and written by the engine-side
installer: static per account HOME in the ACP scene, refreshed from the
engine login state in the TUI scene. Missing/corrupt files never fail the
run (P1: collect with degraded attribution rather than not at all) — the
caller logs ``outcome=attribution_missing`` and continues with
``account_id: "unknown"``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

_ACCOUNT_ID_MAX = 256

UNKNOWN_ACCOUNT_ID = "unknown"


@dataclass(frozen=True, slots=True)
class Attribution:
    account_id: str


@dataclass(frozen=True, slots=True)
class MissingAttribution:
    pass


def read_attribution(path: str) -> Attribution | MissingAttribution:
    """Load ``{"version": 1, "account_id": …}``; degrade on any defect."""
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError:
        return MissingAttribution()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return MissingAttribution()
    if not isinstance(data, dict):
        return MissingAttribution()
    if data.get("version") != 1:
        return MissingAttribution()
    account_id = data.get("account_id")
    if not isinstance(account_id, str) or not 1 <= len(account_id) <= _ACCOUNT_ID_MAX:
        return MissingAttribution()
    return Attribution(account_id=account_id)
