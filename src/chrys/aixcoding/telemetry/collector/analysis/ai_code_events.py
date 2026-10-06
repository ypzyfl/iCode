# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""④ Net-change events ai-code/save (TS ``ai-code-events.ts``; M5 plan
§6.3; contract §2.5/§3.5).

For every incremental turn, process the ``state.chrys_mutations.turns[]``
entries whose turn_id matches: provenance=foreign excluded; same-path
mutations merge into a net change (earliest snapshot vs final
after_hash; identical → net-zero, not counted; snapshot missing falls
back to the first before_hash; both missing → create semantics);
delete produces nothing (no generated-code-into-repository meaning).
``reportId`` derives deterministically (analysis_version included) —
revision-level retries recompute the same value. Scale caps (blob 2MB /
blocks 64 / files 256): deterministic truncation, lossy but
successful; truncated paths surface via truncatedPaths (the
orchestration layer logs them; the ledger still writes).
``filepath``/``blocks[].snippet`` are registration-focus fields and do
not enter the payload.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

from chrys.aixcoding.telemetry.collector.analysis.attachments import MutationBlobReader, split_lines
from chrys.aixcoding.telemetry.collector.analysis.context import EventCommonContext, build_event_common
from chrys.aixcoding.telemetry.collector.analysis.exchanges import ToolTriple, build_tool_triples
from chrys.aixcoding.telemetry.collector.analysis.git_context import GitContextResolver
from chrys.aixcoding.telemetry.collector.analysis.line_diff import compute_line_diff
from chrys.aixcoding.telemetry.collector.analysis.mutation_matching import (
    build_mutation_matching,
    build_mutation_ownership,
)
from chrys.aixcoding.telemetry.collector.analysis.turns import TurnSegment
from chrys.aixcoding.telemetry.collector.analysis.util import as_object, read_number, read_string

# Contracts schema cap: blocks per file.
MAX_BLOCKS_PER_FILE = 64
# Per-turn cap on files producing ai-code events (deterministic
# truncation beyond, lexicographic by path).
MAX_FILES_PER_TURN = 256

# kind "ai-code-saved" (AiCodeSavedEvent in the TS contracts package);
# AiCodeSavedBlock is {"rangeStart": int, "rangeEnd": int}.
AiCodeEvent = dict[str, Any]

# Language inference (extension → language; copied from the desktop
# CODE_LANGUAGE_MAP — both ends of ai-code/save share the backend
# table).
_CODE_LANGUAGE_MAP = {
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".vue": "xml",
    ".css": "css",
    ".scss": "scss",
    ".sass": "scss",
    ".less": "less",
    ".json": "json",
    ".jsonc": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".ym": "yaml",
    ".toml": "ini",
    ".ini": "ini",
    ".cfg": "ini",
    ".xml": "xml",
    ".py": "python",
    ".java": "java",
    ".c": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".cs": "csharp",
    ".vb": "vbnet",
    ".fs": "fsharp",
    ".fsx": "fsharp",
    ".sql": "sql",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".ps1": "powershell",
    ".bat": "dos",
    ".cmd": "dos",
    ".pl": "perl",
    ".lua": "lua",
    ".r": "r",
    ".mm": "objectivec",
    ".cob": "cobol",
    ".txt": "plaintext",
    ".log": "plaintext",
}

_BACKSLASH = re.compile(r"\\")
_DRIVE = re.compile(r"^([A-Za-z]):/")


@dataclass(frozen=True, slots=True)
class _NetChange:
    """Net-change merge result (one group per path)."""

    path: str
    # Earliest snapshot hash; None means create semantics.
    initial_hash: str | None
    # Final after_hash; None when the last mutation is a delete.
    final_after_hash: str | None
    # The group's last raw mutation (the requestId ownership fallback
    # association object).
    last_mutation: dict[str, Any]
    last_operation: str | None
    last_tool_call_id: str | None


@dataclass(frozen=True, slots=True)
class AiCodeEventInputs:
    segment: TurnSegment
    session_id: str
    analysis_version: int
    context: EventCommonContext
    mutations_ledger: Any
    blob_reader: MutationBlobReader
    git_context: GitContextResolver


@dataclass(frozen=True, slots=True)
class AiCodeEventResult:
    events: list[AiCodeEvent]
    # Paths deterministically truncated by the per-turn file cap (the
    # orchestration layer logs them).
    truncated_paths: list[str]


def _extract_turn_mutations(mutations_ledger: Any, turn_index: int) -> list[dict[str, Any]]:
    ledger = as_object(mutations_ledger)
    turns = ledger.get("turns") if ledger is not None else None
    if not isinstance(turns, list):
        turns = []
    for raw in turns:
        entry = as_object(raw)
        if entry is not None and read_number(entry, "turn_id") == turn_index:
            mutations = entry.get("mutations")
            if not isinstance(mutations, list):
                mutations = []
            return [mutation for mutation in (as_object(item) for item in mutations) if mutation is not None]
    return []


def _resolve_initial_hash(
    path: str,
    turn_index: int,
    mutations_ledger: Any,
    first_mutation: dict[str, Any] | None,
) -> str | None:
    """Earliest snapshot (guide §11.1: snapshot keys are
    ``path::period_index`` — never split the key, match by the value
    fields): the content_hash of this path's snapshot for this turn
    (period_index === turnIndex); missing falls back to the group's
    first mutation's before_hash; still missing (create, no before) →
    None (create semantics)."""
    ledger = as_object(mutations_ledger)
    snapshots = as_object(ledger.get("snapshots")) if ledger is not None else None
    if snapshots is not None:
        best_hash: str | None = None
        best_index = float("inf")
        for raw in snapshots.values():
            snapshot = as_object(raw)
            if snapshot is None or snapshot.get("path") != path:
                continue
            period_index = read_number(snapshot, "period_index")
            if period_index != turn_index or period_index >= best_index:
                continue
            best_index = period_index
            best_hash = read_string(snapshot, "content_hash")
        if best_hash is not None:
            return best_hash
    if first_mutation is None:
        return None
    return read_string(first_mutation, "before_hash")


def _group_net_changes(
    mutations: list[dict[str, Any]],
    turn_index: int,
    mutations_ledger: Any,
) -> list[_NetChange]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for mutation in mutations:
        # provenance=foreign leaves the net change (kept for audit
        # expansion, produces no event).
        if read_string(mutation, "provenance") == "foreign":
            continue
        path = read_string(mutation, "path")
        if path is None:
            continue
        groups.setdefault(path, []).append(mutation)
    changes: list[_NetChange] = []
    for path, bucket in groups.items():
        first = bucket[0]
        last = bucket[-1]
        initial_hash = _resolve_initial_hash(path, turn_index, mutations_ledger, first)
        final_after_hash = read_string(last, "after_hash")
        # Net-zero: the earliest snapshot equals the final state → not
        # counted (the path's content returned to this turn's start).
        if initial_hash is not None and final_after_hash is not None and initial_hash == final_after_hash:
            continue
        changes.append(
            _NetChange(
                path=path,
                initial_hash=initial_hash,
                final_after_hash=final_after_hash,
                last_mutation=last,
                last_operation=read_string(last, "operation"),
                last_tool_call_id=read_string(last, "tool_call_id"),
            )
        )
    return changes


def _diff_blocks(before_text: str, after_text: str) -> list[dict[str, int]]:
    """Diff op sequence → changed line ranges (1-based, contiguous edit
    runs merged)."""
    before_lines = split_lines(before_text)
    after_lines = split_lines(after_text)
    ops = compute_line_diff(before_lines, after_lines)
    if ops is None:
        return []
    blocks: list[dict[str, int]] = []
    index = 0
    while index < len(ops):
        if ops[index] not in ("+", "-"):
            index += 1
            continue
        end = index
        while end < len(ops) and ops[end] in ("+", "-"):
            end += 1
        blocks.append({"rangeStart": index + 1, "rangeEnd": end})
        index = end
    return blocks[:MAX_BLOCKS_PER_FILE]


def _derive_language(path: str) -> str | None:
    dot = path.rfind(".")
    if dot < 0:
        return None
    return _CODE_LANGUAGE_MAP.get(path[dot:].lower())


def _derive_report_id(
    session_id: str,
    turn_id: str,
    content_hash: str,
    analysis_version: int,
    filepath: str,
) -> str:
    """reportId deterministic derivation (contract §2.5): sha256(
    session_id + ':' + turn_id + ':' + content_hash + ':' +
    analysis_version + ':' + filepath) first 32 hex digits formatted
    as a UUID (8-4-4-4-12). filepath takes the K5 relativized form:
    inside a git repository → relative to the repository root;
    otherwise relative to primary_cwd; neither available → the raw
    path with unified '/' separators (absolute paths breaking
    cross-copy idempotence is a known limitation)."""
    hex_digest = hashlib.sha256(
        f"{session_id}:{turn_id}:{content_hash}:{analysis_version}:{filepath}".encode()
    ).hexdigest()[:32]
    return f"{hex_digest[:8]}-{hex_digest[8:12]}-{hex_digest[12:16]}-{hex_digest[16:20]}-{hex_digest[20:]}"


def _relative_path_within(base: str, file_path: str) -> str | None:
    """Windows case-insensitive path prefix relativization (borrowed
    from the adapters-node logic of the same purpose)."""

    def normalize(value: str) -> list[str]:
        return [part for part in _BACKSLASH.sub("/", value).split("/") if part]

    base_drive = _DRIVE.search(_BACKSLASH.sub("/", base))
    file_drive = _DRIVE.search(_BACKSLASH.sub("/", file_path))
    if (base_drive.group(1).lower() if base_drive else "") != (file_drive.group(1).lower() if file_drive else ""):
        return None
    base_parts = normalize(base)
    file_parts = normalize(file_path)
    if len(base_parts) > len(file_parts):
        return None
    for index in range(len(base_parts)):
        if base_parts[index].lower() != file_parts[index].lower():
            return None
    remaining = file_parts[len(base_parts) :]
    return "/".join(remaining) if remaining else None


def _derive_filepath(change: _NetChange, git_root: str | None, primary_cwd: str | None) -> str:
    if git_root is not None:
        relative = _relative_path_within(git_root, change.path)
        if relative is not None:
            return relative
    if primary_cwd is not None:
        relative = _relative_path_within(primary_cwd, change.path)
        if relative is not None:
            return relative
    # Fallback: unified '/' separators (plan §6.3 item 8) — filepath is
    # one of the reportId derivation inputs; the source data's '\'
    # converts here, the separator normalization is part of
    # determinism.
    return _BACKSLASH.sub("/", change.path)


def _message_operation_id(triple: ToolTriple) -> str | None:
    properties = as_object(triple.assistant_message.get("additional_properties"))
    return read_string(properties if properties is not None else {}, "_chrys_operation_id")


def _derive_request_id(
    triples: list[ToolTriple],
    ownership: dict[int, ToolTriple],
    change: _NetChange,
) -> str | None:
    """requestId (contract §3.5): the owning call's message-level
    ``_chrys_operation_id``. Exact matching (ledger tool_call_id ===
    call_id) is the deterministic channel, active once the engine
    stamps the short id; under the current ID-system break the
    mutation ownership map is the fallback (same basis as the
    tool-events line-count columns: uniqueness/timing window,
    ambiguity gives up). Both miss → omitted (K6)."""
    if change.last_tool_call_id is not None:
        for triple in triples:
            if read_string(triple.call, "call_id") == change.last_tool_call_id:
                return _message_operation_id(triple)
    owning_triple = ownership.get(id(change.last_mutation))
    return _message_operation_id(owning_triple) if owning_triple is not None else None


def build_ai_code_events(inputs: AiCodeEventInputs) -> AiCodeEventResult:
    segment = inputs.segment
    blob_reader = inputs.blob_reader
    mutations = _extract_turn_mutations(inputs.mutations_ledger, segment.turn_index)
    net_changes = _group_net_changes(mutations, segment.turn_index, inputs.mutations_ledger)
    if not net_changes:
        return AiCodeEventResult(events=[], truncated_paths=[])
    triples = build_tool_triples(segment)
    ownership = build_mutation_ownership(
        triples,
        build_mutation_matching(triples, inputs.mutations_ledger, segment.turn_index),
    )

    # Scale cap: the first MAX_FILES_PER_TURN in lexicographic path
    # order (two truncations of the same input yield identical sets).
    ordered = sorted(net_changes, key=lambda change: change.path)
    included = ordered[:MAX_FILES_PER_TURN]
    truncated_paths = [change.path for change in ordered[MAX_FILES_PER_TURN:]]

    events: list[AiCodeEvent] = []
    for change in included:
        if change.last_operation == "delete":
            # delete produces nothing (no generated-code-into-repository
            # meaning).
            continue
        # blocks: before/after blob line diff; blob missing/skipped/over
        # cap → blocks=[] (the event survives, only the ranges are
        # lost).
        blocks: list[dict[str, int]] = []
        if change.initial_hash is None:
            after_text = (
                blob_reader.read_blob_text(change.final_after_hash) if change.final_after_hash is not None else None
            )
            if after_text is not None:
                line_count = len(split_lines(after_text))
                if line_count > 0:
                    blocks = [{"rangeStart": 1, "rangeEnd": line_count}]
        elif change.final_after_hash is not None:
            before_text = blob_reader.read_blob_text(change.initial_hash)
            after_text = blob_reader.read_blob_text(change.final_after_hash)
            if before_text is not None and after_text is not None:
                blocks = _diff_blocks(before_text, after_text)

        git = inputs.git_context.for_file(change.path)
        filepath = _derive_filepath(change, git.root, inputs.context.primary_cwd)
        language = _derive_language(change.path)
        request_id = _derive_request_id(triples, ownership, change)
        report_id = _derive_report_id(
            inputs.session_id,
            segment.turn_id,
            segment.content_hash,
            inputs.analysis_version,
            filepath,
        )
        event: AiCodeEvent = {
            "kind": "ai-code-saved",
            **build_event_common(inputs.context, segment.turn_id),
            "reportId": report_id,
            "sourceType": "edit",
            "inputMethod": "agent",
            "blocks": blocks,
        }
        if request_id is not None:
            event["requestId"] = request_id
        if language is not None:
            event["language"] = language
        if git.remote_url is not None:
            event["remoteUrl"] = git.remote_url
        if git.branch is not None:
            event["branch"] = git.branch
        if git.user_name is not None:
            event["gitUserName"] = git.user_name
        if git.user_email is not None:
            event["gitUserEmail"] = git.user_email
        events.append(event)
    return AiCodeEventResult(events=events, truncated_paths=truncated_paths)
