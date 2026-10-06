# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Defensive JSON read helpers shared by the analysis core (TS ``util.ts``).

Session guide §1.3 compatibility rules: distinguish missing/null/0/empty;
never mutate the input objects.
"""

from __future__ import annotations

from typing import Any

JsonObject = dict[str, Any]


def as_object(value: object) -> JsonObject | None:
    if isinstance(value, dict):
        return value
    return None


def read_string(source: JsonObject, key: str) -> str | None:
    """Empty strings read as None, like missing (the engine writes '' for
    "no value")."""
    value = source.get(key)
    if isinstance(value, str) and value:
        return value
    return None


def read_number(source: JsonObject, key: str) -> float | None:
    value = source.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    number = float(value)
    return number if number == number and number not in (float("inf"), float("-inf")) else None


def read_positive_integer(source: JsonObject, key: str) -> int | None:
    value = read_number(source, key)
    if value is None or value != int(value) or value <= 0:
        return None
    return int(value)
