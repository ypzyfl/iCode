# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Deterministic JSON encoder (Session guide §19.4; TS ``canonical.ts``).

Object keys are sorted lexicographically (recursively); arrays keep order;
missing/null/0/false/empty-string each keep a distinct encoding. Inputs come
from ``json.loads`` of session.json, so undefined-like values cannot occur —
anything unsupported raises (fast failure over silent rewriting).
"""

from __future__ import annotations

import math
from typing import Any

_SEPARATOR = ", "
_ITEM_SEPARATOR = ":"


def canonical_json_encode(value: Any) -> str:
    return _encode(value)


def _encode(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            msg = "The canonical encoder received a non-finite number."
            raise TypeError(msg)
        # JSON numbers: JS JSON.stringify prints 1.0 as "1"; mirror that so
        # hashes match the TS baseline for integral floats.
        if value == int(value) and abs(value) < 1e21:
            return str(int(value))
        return repr(value)
    if isinstance(value, str):
        import json

        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return "[" + ",".join(_encode(entry) for entry in value) + "]"
    if isinstance(value, dict):
        keys = sorted(value.keys())
        return "{" + ",".join(f"{_encode(key)}{_ITEM_SEPARATOR}{_encode(value[key])}" for key in keys) + "}"
    msg = f"The canonical encoder received an unsupported value of type {type(value).__name__}."
    raise TypeError(msg)
