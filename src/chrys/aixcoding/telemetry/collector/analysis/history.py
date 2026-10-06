# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""① History expansion with occurrence dedup (TS ``history.ts``).

Compressed blocks first (stably sorted by turn_range lower bound), live tail
after; summary message texts never enter the body (their originals are
already expanded from the archive — counting them again would inflate the
content); archive/live twins sharing one valid message-level
``_chrys_analytics_item_id`` merge into the first occurrence (archive wins).
Same-text different-occurrence entries are NOT deduped. The analyser never
mutates input objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from chrys.aixcoding.telemetry.collector.analysis.util import as_object, read_string

type _Origin = str  # "archive" | "live"


@dataclass(frozen=True, slots=True)
class HistoryEntry:
    message: dict[str, Any]
    origin: _Origin


def _turn_range_lower_bound(block: dict[str, Any]) -> int:
    """Invalid/missing turn_range lower bounds sort as -1 (storage order first)."""
    turn_range = block.get("turn_range")
    if not isinstance(turn_range, list) or not turn_range:
        return -1
    lower = turn_range[0]
    if isinstance(lower, bool) or not isinstance(lower, int | float) or lower < 0:
        return -1
    return int(lower)


def expand_history(state: dict[str, Any]) -> list[HistoryEntry]:
    seen_occurrences: set[str] = set()
    entries: list[HistoryEntry] = []

    def append_message(raw: object, origin: str) -> None:
        message = as_object(raw)
        if message is None:
            return
        properties = as_object(message.get("additional_properties"))
        if properties is not None and properties.get("_chrys_kind") == "summary":
            return
        analytics_id = None if properties is None else read_string(properties, "_chrys_analytics_item_id")
        if analytics_id is not None:
            if analytics_id in seen_occurrences:
                return
            seen_occurrences.add(analytics_id)
        entries.append(HistoryEntry(message=message, origin=origin))

    raw_blocks = state.get("compressed_msgs")
    blocks: list[tuple[dict[str, Any], int]] = []
    if isinstance(raw_blocks, list):
        for raw in raw_blocks:
            block = as_object(raw)
            if block is not None:
                blocks.append((block, _turn_range_lower_bound(block)))
    # Python's sort is stable: equal lower bounds keep storage order.
    blocks.sort(key=lambda item: item[1])
    for block, _bound in blocks:
        messages = block.get("messages")
        if isinstance(messages, list):
            for raw in messages:
                append_message(raw, "archive")

    live_messages = state.get("messages")
    if isinstance(live_messages, list):
        for raw in live_messages:
            append_message(raw, "live")
    return entries
