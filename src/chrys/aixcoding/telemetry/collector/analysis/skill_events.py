# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""④ Skill trigger events → tool-detail/batch-save (TS ``skill-events.ts``;
M5 plan §6.2; contract §3.4).

Two-level corroboration (D-M5-1: in-session evidence only until the
engine's external skill directory layout is confirmed): (1) the turn
opener text matches the engine's own pattern
``^[/\uff0f](token)(?:[ \\t]|$)`` (``input_refs.py::parse_skill_reference``);
(2) this turn's ToolTriples contain a ``_chrys_tool_kind='skill'`` call
whose ``skill_name`` argument equals the token (truncated non-JSON
arguments give no evidence — never guess). A hit yields an
InputTriggeredUseEvent (funcType=0); non-skill ``/xxx`` (local commands
never enter messages; hand-typed without corroboration) is not
reported; at most the first match per turn.
"""

from __future__ import annotations

import json
import re
from typing import Any

from chrys.aixcoding.telemetry.collector.analysis.context import EventCommonContext, build_event_common
from chrys.aixcoding.telemetry.collector.analysis.exchanges import build_tool_triples
from chrys.aixcoding.telemetry.collector.analysis.turns import TurnSegment
from chrys.aixcoding.telemetry.collector.analysis.util import as_object

# The engine's parse_skill_reference pattern (full-width \uff0f included).
# ``\\Z`` is the TS parity of JavaScript's bare ``$``: an absolute
# string end, without Python's end-of-string-newline leniency.
_SKILL_REFERENCE_PATTERN = re.compile(r"^[/\uff0f]([A-Za-z][A-Za-z0-9_-]*)(?:[ \t]|\Z)")

# kind "input-triggered-use" (InputTriggeredUseEvent in the TS
# contracts package).
SkillEvent = dict[str, Any]


def _message_properties(message: dict[str, Any]) -> dict[str, Any]:
    properties = as_object(message.get("additional_properties"))
    return properties if properties is not None else {}


def _opener_text(segment: TurnSegment) -> str | None:
    """Turn opener text: the first real user input's type=text bodies
    joined with the engine's own spacing."""
    for entry in segment.entries:
        message = entry.message
        if message.get("role") != "user":
            continue
        properties = _message_properties(message)
        if properties.get("_injected") is True or properties.get("_continuation") is True:
            continue
        contents = message.get("contents")
        if not isinstance(contents, list):
            contents = []
        texts: list[str] = []
        for raw in contents:
            content = as_object(raw)
            if content is not None and content.get("type") == "text" and isinstance(content.get("text"), str):
                texts.append(content["text"])
        return " ".join(texts)
    return None


def _corroborated_by_skill_call(segment: TurnSegment, token: str) -> bool:
    """Corroboration: a skill-kind call (``_chrys_tool_kind='skill'``) in
    this turn whose skill_name argument equals the token."""
    for triple in build_tool_triples(segment):
        if _message_properties(triple.call).get("_chrys_tool_kind") != "skill":
            continue
        raw_arguments = triple.call.get("arguments")
        # arguments may be a JSON string (possibly truncated into
        # invalid JSON) or an object; a parse failure gives no evidence.
        parsed: Any = raw_arguments
        if isinstance(raw_arguments, str):
            try:
                parsed = json.loads(raw_arguments)
            except ValueError:
                continue
        arguments = as_object(parsed)
        if arguments is not None and arguments.get("skill_name") == token:
            return True
    return False


def build_skill_events(segment: TurnSegment, context: EventCommonContext) -> list[SkillEvent]:
    text = _opener_text(segment)
    if text is None:
        return []
    match = _SKILL_REFERENCE_PATTERN.match(text)
    token = match.group(1) if match is not None else ""
    if token == "" or not _corroborated_by_skill_call(segment, token):
        return []
    return [
        {
            "kind": "input-triggered-use",
            **build_event_common(context, segment.turn_id),
            "funcType": 0,
            "funcName": token,
        }
    ]
