# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Expected-turn reader: record-level facts for one (logical turn, pass).

V1-V3 probe conclusions baked in (verification 2026-11-20):

- ownership is decided by ids (exchange/pass), never by turn numbers — a
  rollback rewrites the transcript and resets numbering while events.jsonl
  stays append-only (V1-b);
- the trajectory is the authoritative source: ``scan_turn_trace`` projects
  logical turn → passes → model calls (each with its ordered attempts; the
  successful call's LAST attempt is A-final, M1 evidence), and tool
  operations carry their parent exchange plus their pass (V3: Phase-4
  compaction may drop transcript content, the log keeps the facts);
- only the CURRENT pass's fresh executions are reported; prior-pass sources
  are listed, never re-reported; retries that merely replay are not new
  executions (F2 ruling).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from chrys.foundation.trajectory.event_types import EventType
from chrys.foundation.trajectory.reader import read_trajectory
from chrys.service.analytics.turn_trace import scan_turn_trace
from chrys.service.trajectory.session import trajectory_events_path

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class LlmFact:
    request_attempt_id: str  # A-final of the successful call, raw 32hex
    model_call_id: str  # exchange operation id (E)
    request_model: str | None  # model id (diagnostics)
    model_profile: str | None  # model profile id — the filtering key (catalog filename)


@dataclass(slots=True)
class ToolFact:
    tool_op_id: str  # T
    model_call_id: str | None  # parent exchange (E); None = orphan
    call_item_id: str | None  # transcript join key (function_call item)
    outcome: str | None  # success/... from the finished event


@dataclass
class TurnFacts:
    session_id: str
    logical_turn_id: str
    pass_id: str
    llm: list[LlmFact] = field(default_factory=list)
    tools: list[ToolFact] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def read_turn_facts(session_dir: Path, *, session_id: str, logical_turn_id: str, pass_id: str) -> TurnFacts | None:
    """Collect the turn's reportable facts; None when the turn is unknown."""
    events_path = trajectory_events_path(Path(session_dir))
    if not events_path.is_file():
        logger.debug("telemetry reader: no trajectory log at %s", events_path)
        return None
    trace = scan_turn_trace(events_path)
    turn = next((entry for entry in trace.turns if entry.turn_id == logical_turn_id), None)
    if turn is None:
        logger.debug("telemetry reader: logical turn %s not in trace", logical_turn_id)
        return None

    facts = TurnFacts(session_id=session_id, logical_turn_id=logical_turn_id, pass_id=pass_id)
    profiles: dict[str, str] = {}
    result = read_trajectory(events_path)
    for event in result.events:
        operation_id = event.operation_id
        if (
            event.event_type == EventType.MODEL_EXCHANGE_STARTED
            and event.turn_id == pass_id
            and operation_id is not None
            and event.payload.get("model_profile_id")
        ):
            profiles[operation_id] = str(event.payload["model_profile_id"])
    for call in turn.model_calls:
        if call.pass_id != pass_id:
            facts.skipped.append(f"llm-prior-pass:{call.model_call_id}")
            continue
        if call.outcome != "success" or not call.attempts:
            facts.skipped.append(f"llm-not-success:{call.model_call_id}")
            continue
        facts.llm.append(
            LlmFact(
                request_attempt_id=call.attempts[-1].request_attempt_id,
                model_call_id=call.model_call_id,
                request_model=call.request_model,
                model_profile=profiles.get(call.model_call_id),
            )
        )

    tools: dict[str, ToolFact] = {}
    for event in result.events:
        if event.turn_id != pass_id:
            continue  # V2: only this pass's executions; prior passes keep theirs
        if event.event_type == EventType.TOOL_OPERATION_STARTED:
            operation_id = event.operation_id
            if operation_id is None:
                continue
            tools[operation_id] = ToolFact(
                tool_op_id=operation_id,
                model_call_id=event.parent_operation_id,
                call_item_id=str(event.payload.get("call_item_id") or "") or None,
                outcome=None,
            )
        elif event.event_type == EventType.TOOL_OPERATION_FINISHED:
            operation_id = event.operation_id
            if operation_id is not None and operation_id in tools:
                tools[operation_id].outcome = str(event.payload.get("outcome") or "")
    for tool in tools.values():
        if tool.outcome == "success":
            facts.tools.append(tool)
        else:
            facts.skipped.append(f"tool-no-success:{tool.tool_op_id}")
    return facts
