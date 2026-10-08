# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Failure modes of the model catalog mock.

Each mode exists because it maps to one client rule in the catalog sync: a
failed sync must leave ``~/.chrys/models`` untouched. The table below is the
whole point of this mock — every row is something a developer has to be able
to trigger by hand.

=========  ==========================================  ==============================
mode       response                                    what it proves
=========  ==========================================  ==============================
``ok``     file content, as the server serves it       wholesale replacement works
``empty``  ``models: []``                              an empty catalog is refused
``invalid`` entries with no usable ``model``           validation rejects the payload
``error``  HTTP 500                                    transport/HTTP failure is inert
``slow``   sleeps past the client's 3s timeout         startup sync times out safely
``stale``  drifting ``title``, stable derived ids      polling skips the rewrite
=========  ==========================================  ==============================
"""

from __future__ import annotations

import copy
from typing import Any

#: ``slow`` must outlast the client's 3s startup fetch timeout.
DEFAULT_DELAY = 8.0

MODES = ("ok", "empty", "invalid", "error", "slow", "stale")

#: Rejected by the client on translation: the profile id is derived from
#: ``model`` (docs/model-catalog-sync-details.md §1.1), so an entry without one
#: has nothing to be stored under.
INVALID_PROFILES: list[dict[str, Any]] = [
    {"title": "Unusable Profile", "provider": "openrouter"},
    {"title": "Blank Model", "provider": "openrouter", "model": "   "},
]


def status_for(mode: str) -> int:
    """HTTP status the mode answers with."""
    return 500 if mode == "error" else 200


def delay_for(mode: str, delay: float) -> float:
    """Seconds the mode sleeps before answering (only ``slow`` stalls)."""
    return delay if mode == "slow" else 0.0


def build_payload(
    mode: str,
    *,
    payload: dict[str, Any],
    requests: int,
) -> dict[str, Any]:
    """Build the catalog body for *mode*, mutating only ``payload["models"]``.

    The served payload is the reference server's own object. ``ok`` returns it
    verbatim; the other modes replace ``models`` with whatever the test lane
    needs, leaving every other top-level key (``tabAutocompleteModel`` and
    friends) untouched. There is no ``version`` field, so the client
    fingerprints the id list instead — which is why ``stale`` drifts ``title``.
    """
    if mode == "error":
        return {"error": "simulated catalog outage", "mode": mode}

    served = copy.deepcopy(payload)
    if mode == "empty":
        served["models"] = []
    elif mode == "invalid":
        served["models"] = copy.deepcopy(INVALID_PROFILES)
    elif mode == "stale":
        for entry in served.get("models", []):
            entry["title"] = f"{entry.get('title', '')} ·req{requests}"
    return served
