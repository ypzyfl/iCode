# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Mutations ledger ↔ session-message call ownership matching (TS
``mutation-matching.ts``; shared by tool-events line-count columns and
ai-code-events requestId derivation).

The provider call_id (session messages) and the Chrys short
tool_call_id (ledger) are two disconnected ID systems — the short id
never lands in session messages. On an exact-match miss, ownership falls
back to "unique write call / unique mutation within the turn" or a
unique hit inside the timing window (never guessing: ambiguity gives
up). Once the engine stamps the short id into messages (e.g.
_chrys_call_id) this fallback can retire. Background and evidence:
Chrys-会话ID体系断层问题反馈.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from chrys.aixcoding.telemetry.collector.analysis.exchanges import ToolTriple
from chrys.aixcoding.telemetry.collector.analysis.util import as_object, read_number, read_string

# Engine file tools (tool_names.py _FILE_TOOLS) producing write_file /
# edit_file mutations.
FILE_TOOL_NAMES = frozenset({"write_file", "edit_file"})


def turn_write_mutations(mutations_ledger: Any, turn_index: int) -> list[dict[str, Any]]:
    """This turn's write-class mutations (source in write_file/edit_file,
    provenance not foreign), in order."""
    ledger = as_object(mutations_ledger)
    turns = ledger.get("turns") if ledger is not None else None
    if not isinstance(turns, list):
        turns = []
    output: list[dict[str, Any]] = []
    for raw in turns:
        turn_entry = as_object(raw)
        if turn_entry is None or read_number(turn_entry, "turn_id") != turn_index:
            continue
        mutations = turn_entry.get("mutations")
        if not isinstance(mutations, list):
            mutations = []
        for entry in mutations:
            mutation = as_object(entry)
            if mutation is None:
                continue
            source = read_string(mutation, "source")
            if source != "write_file" and source != "edit_file":
                continue
            # provenance missing falls back by source: write/edit are
            # proven (guide §11.1).
            if read_string(mutation, "provenance") == "foreign":
                continue
            output.append(mutation)
    return output


@dataclass
class MutationMatching:
    """Mutation matching context: matching state plus this turn's write
    call / write mutation counts.

    Identifiers are indices into ``write_mutations`` (stable within the
    matching's lifetime) — the TS version keys sets/maps by object
    identity, which Python dicts do not hash.
    """

    write_mutations: list[dict[str, Any]]
    write_call_count: int
    by_call_id: dict[str, list[int]] = field(default_factory=dict)
    claimed: set[int] = field(default_factory=set)


def build_mutation_matching(triples: list[ToolTriple], mutations_ledger: Any, turn_index: int) -> MutationMatching:
    write_mutations = turn_write_mutations(mutations_ledger, turn_index)
    by_call_id: dict[str, list[int]] = {}
    for index, mutation in enumerate(write_mutations):
        tool_call_id = read_string(mutation, "tool_call_id")
        if tool_call_id is None:
            continue
        by_call_id.setdefault(tool_call_id, []).append(index)
    write_call_count = sum(
        1 for triple in triples if isinstance(triple.call.get("name"), str) and triple.call["name"] in FILE_TOOL_NAMES
    )
    return MutationMatching(
        write_mutations=write_mutations,
        write_call_count=write_call_count,
        by_call_id=by_call_id,
    )


def _iso_to_epoch_seconds(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        # JS Date.parse reads naive stamps as local time; the engine
        # always writes offsets, so this branch only serves handwritten
        # data and pins to UTC for cross-platform determinism.
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.timestamp()


def _call_timing_window(call: dict[str, Any]) -> tuple[float, float] | None:
    """Call timing window (additional_properties._chrys_timing, epoch
    seconds)."""
    properties = as_object(call.get("additional_properties"))
    timing = as_object(properties.get("_chrys_timing")) if properties is not None else None
    if timing is None:
        return None
    start = _iso_to_epoch_seconds(read_string(timing, "started_at"))
    end = _iso_to_epoch_seconds(read_string(timing, "finished_at"))
    if start is None or end is None:
        return None
    return start, end


def _mutation_timestamp(mutation: dict[str, Any]) -> float | None:
    value = read_number(mutation, "t_start")
    if value is None:
        value = read_number(mutation, "timestamp")
    return value


def _within_timing_window(mutation: dict[str, Any], window: tuple[float, float]) -> bool:
    """A mutation recorded inside the call timing window (±2s
    tolerance) counts as a time hit."""
    timestamp = _mutation_timestamp(mutation)
    return timestamp is not None and window[0] - 2 <= timestamp <= window[1] + 2


def match_mutations(triple: ToolTriple, matching: MutationMatching) -> list[dict[str, Any]] | None:
    """Match this call's write-class mutations: exact call_id first, then
    the uniqueness/timing-window fallbacks."""
    call_id = read_string(triple.call, "call_id")
    exact = matching.by_call_id.get(call_id) if call_id is not None else None
    if exact is not None:
        matching.claimed.update(exact)
        return [matching.write_mutations[index] for index in exact]
    candidate_indices = [index for index in range(len(matching.write_mutations)) if index not in matching.claimed]
    if not candidate_indices:
        return None
    name = triple.call.get("name")
    is_write_tool = isinstance(name, str) and name in FILE_TOOL_NAMES
    if is_write_tool and matching.write_call_count == 1 and len(candidate_indices) == 1:
        matching.claimed.add(candidate_indices[0])
        return [matching.write_mutations[candidate_indices[0]]]
    window = _call_timing_window(triple.call)
    if window is None:
        return None
    hits = [index for index in candidate_indices if _within_timing_window(matching.write_mutations[index], window)]
    if len(hits) == 1:
        matching.claimed.add(hits[0])
        return [matching.write_mutations[hits[0]]]
    return None


def build_mutation_ownership(
    triples: list[ToolTriple],
    matching: MutationMatching,
) -> dict[int, ToolTriple]:
    """Mutation → owning call reverse view: run matchMutations in
    triples order (the same ownership basis as the tool-events line
    count columns), recording the carrying call for every owned
    mutation. Only calls with results participate (no result = not
    finished executing, ownership is never guessed). Keys are
    ``id(mutation)`` — the Python stand-in for the TS reference-identity
    map keys; the ledger keeps the objects alive for the matching's
    lifetime."""
    ownership: dict[int, ToolTriple] = {}
    for triple in triples:
        if triple.result is None:
            continue
        mutations = match_mutations(triple, matching)
        if mutations is None:
            continue
        for mutation in mutations:
            ownership[id(mutation)] = triple
    return ownership
