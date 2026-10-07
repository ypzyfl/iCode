# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Analysis orchestration: session-level facts (M1) + turn slicing and
increments (M5.1) (TS ``index.ts``).

Extract session-level fields from session.json's meta/state (M1
definitions preserved as-is), then per M5 plan §1/§2: expand history →
slice turns → compute increments; event projection (④) filled in by
M5.2+. Parsing follows the Chrys-Session guide §1.3 compatibility
rules: distinguish missing/null/0/empty, keep unknown fields.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, replace
from typing import Any

from chrys.aixcoding.telemetry.collector.analysis.ai_code_events import AiCodeEventInputs, build_ai_code_events
from chrys.aixcoding.telemetry.collector.analysis.attachments import (
    NULL_BLOB_READER,
    MutationBlobReader,
)
from chrys.aixcoding.telemetry.collector.analysis.context import (
    EventCommonContext,
    ReportAttribution,
    derive_project_name,
    first_working_dir,
)
from chrys.aixcoding.telemetry.collector.analysis.git_context import (
    NULL_GIT_CONTEXT,
    GitContextResolver,
    GitRepositoryInfo,
)
from chrys.aixcoding.telemetry.collector.analysis.history import expand_history
from chrys.aixcoding.telemetry.collector.analysis.skill_events import build_skill_events
from chrys.aixcoding.telemetry.collector.analysis.tool_events import build_tool_events
from chrys.aixcoding.telemetry.collector.analysis.turns import (
    PriorTurnRef,
    compute_incremental,
    slice_turn_segments,
    to_turn_fact,
)
from chrys.aixcoding.telemetry.collector.analysis.util import as_object, read_number, read_string

__all__ = [
    "ANALYSIS_VERSION",
    "MalformedSessionError",
    "SessionRevisionInput",
    "analyze_session_revision",
]

# Compile-time built-in analysis version; upgrade re-analysis triggers
# via the ledger's analysis_version comparison.
# v2 (M4): the K2 channelName/channelVersion columns entered the remote
# payload (proceed-by-default); already-reported sessions re-report under
# this version so the backend records the new columns (idempotency key
# includes the version).
ANALYSIS_VERSION = 2

_TITLE_MAX_LENGTH = 200
_PATH_SPLIT = re.compile(r"[\\/]")


class MalformedSessionError(Exception):
    def __init__(self, json_path: str, message: str) -> None:
        super().__init__(message)
        self.json_path = json_path


@dataclass(frozen=True, slots=True)
class SessionRevisionInput:
    session_id: str
    revision_hash: str
    envelope: Any
    source_path: str
    # Read-only projection of the ledger's already-reported turns
    # (increment input); default treats the history as empty.
    prior_turns: list[PriorTurnRef] | None = None
    # Reporting configuration such as the channel quartet (event
    # common-field assembly input).
    attribution: ReportAttribution | None = None
    # Controlled mutations blob accessor; default is the null accessor
    # (line-count columns omitted).
    blob_reader: MutationBlobReader | None = None
    # Git context resolver (built and injected by the orchestration
    # layer); default is the null resolver (git fields omitted).
    git_context: GitContextResolver | None = None
    # Analysis version (ai-code reportId derivation input); default is
    # the compile-time built-in.
    analysis_version: int | None = None


def _read_surface(meta: dict[str, Any]) -> str | None:
    value = meta.get("last_surface")
    return value if value in ("acp", "tui", "cli") else None


def _truncate_title(title: str | None) -> str | None:
    if title is None:
        return None
    return title[:_TITLE_MAX_LENGTH] if len(title) > _TITLE_MAX_LENGTH else title


def _chat_turn_count(state: dict[str, Any]) -> int:
    """Recoverable-history turn-count projection (Session guide §9.2):
    the maximum of the positive turn_counter, the live turn markers'
    max ``_turn``, the live marker count, and the compressed blocks'
    turn_range upper bounds."""
    turn_count = 0
    turn_counter = read_number(state, "turn_counter")
    if turn_counter is not None and turn_counter > 0:
        turn_count = max(turn_count, math.trunc(turn_counter))
    messages = state.get("messages")
    if not isinstance(messages, list):
        messages = []
    marker_count = 0
    max_turn = 0
    for message in messages:
        record = as_object(message)
        properties = as_object(record.get("additional_properties")) if record is not None else None
        if properties is None or properties.get("_chrys_kind") != "turn":
            continue
        marker_count += 1
        turn = read_number(properties, "_turn")
        if turn is not None and turn > 0:
            max_turn = max(max_turn, math.trunc(turn))
    turn_count = max(turn_count, marker_count, max_turn)
    compressed = state.get("compressed_msgs")
    if not isinstance(compressed, list):
        compressed = []
    for block in compressed:
        record = as_object(block)
        turn_range = record.get("turn_range") if record is not None else None
        if not isinstance(turn_range, list) or len(turn_range) < 2:
            continue
        upper = turn_range[1]
        if isinstance(upper, int | float) and math.isfinite(upper) and upper > 0:
            turn_count = max(turn_count, math.trunc(upper))
    return turn_count


def analyze_session_revision(input: SessionRevisionInput) -> dict[str, Any]:
    """Pure analysis of one session revision. Output shape mirrors the
    TS SessionAnalysisOutput (camelCase JSON keys): sessionFacts /
    turnFacts / incremental / reportEvents / aiCodeTruncatedPaths."""
    envelope = as_object(input.envelope)
    if envelope is None:
        raise MalformedSessionError("$", "The session envelope is not an object.")
    meta = as_object(envelope.get("meta"))
    if meta is None:
        raise MalformedSessionError("$.meta", "The session envelope has no meta object.")
    kind_value = meta.get("kind")
    if kind_value is None:
        kind = "chat"
    elif kind_value in ("chat", "workflow"):
        kind = kind_value
    else:
        raise MalformedSessionError("$.meta.kind", f"Unsupported session kind: {kind_value}.")
    stored_session_id = read_string(meta, "session_id")
    if stored_session_id is not None and stored_session_id != input.session_id:
        raise MalformedSessionError("$.meta.session_id", "The session file belongs to a different session id.")
    state = as_object(envelope.get("state"))
    if state is None:
        state = {}
    facts: dict[str, Any] = {
        "sessionId": input.session_id,
        "kind": kind,
        "schemaVersion": read_number(meta, "schema_version"),
        "createdAt": read_string(meta, "created_at"),
        "updatedAt": read_string(meta, "updated_at"),
        "title": _truncate_title(
            read_string(meta, "custom_title") or read_string(meta, "generated_title") or read_string(meta, "title")
        ),
        "surface": _read_surface(meta),
        "agentProfileId": read_string(meta, "agent_profile_id"),
        "agentDisplayName": read_string(meta, "agent_display_name"),
        "modelProvider": read_string(meta, "model_provider"),
        "modelId": read_string(meta, "model_id"),
        "turnCount": _chat_turn_count(state) if kind == "chat" else None,
        "totalSessionTokens": read_number(state, "total_session_tokens"),
        "totalSessionInputTokens": read_number(state, "total_session_input_tokens"),
        "totalSessionOutputTokens": read_number(state, "total_session_output_tokens"),
        "totalSessionCacheHitTokens": read_number(state, "total_session_cache_hit_tokens"),
        "parentSessionId": read_string(meta, "parent_session_id"),
        "appVersion": read_string(meta, "app_version"),
    }
    # Workflow sessions yield sessionFacts only (D-M5-2): no turn
    # slicing, no events.
    if kind == "workflow":
        return {
            "sessionFacts": facts,
            "turnFacts": [],
            "incremental": [],
            "reportEvents": [],
            "aiCodeTruncatedPaths": [],
        }
    history_entries = expand_history(state)
    segments = slice_turn_segments(history_entries)
    turn_facts = [to_turn_fact(segment) for segment in segments]
    incremental_segments = compute_incremental(segments, input.prior_turns or [])
    incremental = [to_turn_fact(segment) for segment in incremental_segments]
    # Events are produced for incremental turns only (M5 plan §2
    # pipeline ⑥); order within a turn: batch elements (skills,
    # logically the turn's opening) → save/update (tools) → ai-code
    # (contract §4.2: no business constraint between interfaces, only
    # save before the same funcId's update).
    primary_cwd = read_string(meta, "primary_cwd")
    git_context = input.git_context if input.git_context is not None else NULL_GIT_CONTEXT
    tool_detail_git: GitRepositoryInfo | None = (
        git_context.for_directory(primary_cwd) if primary_cwd is not None else None
    )
    # productName (contract §2.2): the git repository folder name, ''
    # outside git. The locator directory shares projectName's source
    # (K3: tool-detail uses the session's working_dirs[0], falling back
    # to primary_cwd); root resolution goes through forFile's per-run
    # cache, no extra spawn.
    product_name_directory = first_working_dir(meta) or primary_cwd
    product_root = git_context.for_file(product_name_directory).root if product_name_directory is not None else None
    if product_root is None:
        product_name = ""
    else:
        parts = [part for part in _PATH_SPLIT.split(product_root) if part]
        product_name = parts[-1] if parts else ""
    # Focus-field relativization basis (value/fileName): primary_cwd's
    # repository root (same per-run cache as the forDirectory call above
    # — no extra spawn).
    git_root = git_context.for_file(primary_cwd).root if primary_cwd is not None else None
    attribution = input.attribution
    # channelVersion fallback (K2 proceed-by-default): the engine
    # version (meta.app_version) when the run layer did not supply one —
    # the TUI default (--version output) equals it, and on ACP the
    # desktop build number is not obtainable engine-side (recorded
    # interim difference, corrected after the D1 review).
    if attribution is not None and attribution.channel_version is None and facts["appVersion"] is not None:
        attribution = replace(attribution, channel_version=facts["appVersion"])
    event_context = EventCommonContext(
        session_id=input.session_id,
        attribution=attribution,
        product_name=product_name,
        project_name=derive_project_name(meta),
        plugin_version=(
            facts["appVersion"]
            if facts["appVersion"] is not None
            else (attribution.plugin_version if attribution is not None else None)
        ),
        primary_cwd=primary_cwd,
        git=tool_detail_git,
        git_root=git_root,
    )
    blob_reader = input.blob_reader if input.blob_reader is not None else NULL_BLOB_READER
    analysis_version = input.analysis_version if input.analysis_version is not None else ANALYSIS_VERSION
    report_events: list[dict[str, Any]] = []
    truncated_paths: list[str] = []
    mutations_ledger = state.get("chrys_mutations")
    for segment in incremental_segments:
        report_events.extend(build_skill_events(segment, event_context))
        report_events.extend(build_tool_events(segment, event_context, mutations_ledger, blob_reader))
        ai_code = build_ai_code_events(
            AiCodeEventInputs(
                segment=segment,
                session_id=input.session_id,
                analysis_version=analysis_version,
                context=event_context,
                mutations_ledger=mutations_ledger,
                blob_reader=blob_reader,
                git_context=git_context,
            )
        )
        report_events.extend(ai_code.events)
        truncated_paths.extend(ai_code.truncated_paths)
    return {
        "sessionFacts": facts,
        "turnFacts": turn_facts,
        "incremental": incremental,
        "reportEvents": report_events,
        "aiCodeTruncatedPaths": truncated_paths,
    }
