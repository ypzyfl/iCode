# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Directional after-turn joins over real session and trajectory files."""

from __future__ import annotations

import asyncio
import functools
import inspect
import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from time import perf_counter
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import httpx
import pytest

from chrys.app.acp.bridge import with_chrys_metadata
from chrys.foundation.config.settings import Settings
from chrys.foundation.events.bus import EventBus
from chrys.foundation.events.types import Error, SessionReady, UserMessage, UserRollback
from chrys.foundation.models.history_markers import HistoryMarkerKind
from chrys.foundation.models.turns import turn_slices
from chrys.foundation.models.workspace import Workspace
from chrys.foundation.trajectory.envelope import TrajectoryEvent
from chrys.foundation.trajectory.event_types import EventType
from chrys.foundation.trajectory.metadata import ANALYTICS_ITEM_ID_KEY, OPERATION_ID_KEY
from chrys.foundation.trajectory.reader import read_trajectory, verify_accounted_prefix
from chrys.foundation.util.chrys_headers import REQUEST_ATTEMPT_ID_HEADER
from chrys.kernel import Message, tool
from chrys.orchestration.engine.assembly import assemble_agent_engine
from chrys.service.mutations.store import SnapshotStore
from chrys.service.mutations.types import FileMutation
from chrys.service.profiles.agents.registry import AgentProfileRegistry
from chrys.service.profiles.agents.schema import (
    AgentProfile,
    ApprovalConfig,
    CompactionConfig,
    SkillsConfig,
    ToolsConfig,
)
from chrys.service.profiles.models.registry import ModelProfileRegistry
from chrys.service.profiles.models.schema import API_STYLE_CHAT_COMPLETIONS, ModelProfile
from chrys.service.state.store import JsonFileStateStore
from chrys.service.tools import packs as tool_packs
from chrys.service.tools.builtins.filesystem import FilesystemTools
from chrys.service.trajectory.session import trajectory_events_path
from chrys.service.trajectory.state import TurnRecord

logger = logging.getLogger(__name__)


def _lookup(city: str) -> str:
    return f"Sunny in {city}, 21 degrees."


def _completion(response_id: str, message: dict[str, Any], finish_reason: str) -> dict[str, Any]:
    return {
        "id": response_id,
        "object": "chat.completion",
        "created": 1_767_225_600,
        "model": "model-test",
        "choices": [{"index": 0, "message": message, "finish_reason": finish_reason}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }


def _tool_completion(response_id: str, call_id: str) -> dict[str, Any]:
    return _completion(
        response_id,
        {
            "role": "assistant",
            "content": "Let me check the weather.",
            "tool_calls": [
                {
                    "id": call_id,
                    "type": "function",
                    "function": {"name": "lookup", "arguments": json.dumps({"city": "Paris"})},
                }
            ],
        },
        "tool_calls",
    )


def _text_completion(response_id: str, text: str = "Done.") -> dict[str, Any]:
    return _completion(response_id, {"role": "assistant", "content": text}, "stop")


class _Wire:
    def __init__(self, replies: list[Any]) -> None:
        self._replies = list(replies)
        self.requests: list[httpx.Request] = []
        self.statuses: list[int] = []
        self.transport = httpx.MockTransport(self._handle)

    async def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        assert self._replies, f"unscripted request: {request.method} {request.url}"
        reply = self._replies.pop(0)
        status, payload = reply if isinstance(reply, tuple) else (200, reply)
        self.statuses.append(status)
        return httpx.Response(status, json=payload, request=request)


@dataclass
class _Harness:
    engine: Any
    bus: EventBus
    store: JsonFileStateStore
    wire: _Wire
    errors: list[Error]
    second_ready: asyncio.Event


async def _start_harness(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    replies: list[Any],
    *,
    http_max_retries: int = 0,
) -> _Harness:
    for key in list(os.environ):
        if key.startswith(("OPENAI_", "CHRYS_")) or key.upper() in {
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "ALL_PROXY",
            "NO_PROXY",
        }:
            monkeypatch.delenv(key)
    monkeypatch.setenv("NO_PROXY", "*")
    monkeypatch.setattr(
        "chrys.orchestration.session_hooks.get_platform",
        lambda: SimpleNamespace(config_dir=tmp_path / "empty-config"),
    )

    wire = _Wire(replies)
    import chrys.service.llm.clients as clients_module

    build = inspect.unwrap(clients_module._build_profile_http_client)

    @functools.wraps(build)
    def build_over(profile: ModelProfile, timeout: Any, **kwargs: Any) -> httpx.AsyncClient:
        return build(profile, timeout, **kwargs, transport=wire.transport)

    monkeypatch.setattr(clients_module, "_build_profile_http_client", build_over)

    def create_test_pack(build: tool_packs.ToolBuild, pack_ids: list[str]) -> list[tuple[str, list[Any]]]:
        return [
            (
                "telemetry-test",
                [
                    tool(name="lookup", description="Look up weather.")(_lookup),
                    FilesystemTools(build.runtime).write_file,
                ],
            )
        ]

    monkeypatch.setattr(tool_packs, "create_packs", create_test_pack)

    model = ModelProfile(
        id="telemetry-model",
        name="telemetry-model",
        provider="openai",
        api_style=API_STYLE_CHAT_COMPLETIONS,
        model_id="model-test",
        api_key="sk-test",
        base_url="https://model.example.test",
        http_max_retries=http_max_retries,
        stream=False,
    )
    models = ModelProfileRegistry()
    models.register(model)
    profile = AgentProfile(
        name="telemetry-exploration",
        instructions="Reply briefly.",
        tools=ToolsConfig(builtins=[]),
        skills=SkillsConfig(auto_load_user_agents_skills=False, auto_load_cwd_agents_skills=False),
        approval=ApprovalConfig(default="auto"),
        compaction=CompactionConfig(enabled=False),
    )
    agents = AgentProfileRegistry()
    agents.register(profile)

    bus = EventBus()
    errors: list[Error] = []
    ready: list[SessionReady] = []
    second_ready = asyncio.Event()

    async def collect_error(event: Error) -> None:
        errors.append(event)

    async def collect_ready(event: SessionReady) -> None:
        ready.append(event)
        if len(ready) >= 2:
            second_ready.set()

    await bus.subscribe(Error, collect_error)
    await bus.subscribe(SessionReady, collect_ready)
    store = JsonFileStateStore(tmp_path / "sessions")
    engine = assemble_agent_engine(
        bus,
        settings=Settings(
            model_profile=model.id,
            workspace_change_notice=False,
            default_approval_mode="bypass",
        ),
        agent_registry=agents,
        model_registry=models,
        state_store=store,
        initial_workspace=Workspace.from_cwd(str(tmp_path)),
    )
    await engine.start(profile)
    return _Harness(engine, bus, store, wire, errors, second_ready)


async def _send(harness: _Harness, text: str) -> None:
    await harness.bus.publish(UserMessage(text=text))
    await asyncio.wait_for(harness.engine.turns.turn_state.drain_for_boundary(), timeout=30)
    assert harness.errors == []


async def _wait_for_second_ready(harness: _Harness) -> None:
    await asyncio.wait_for(harness.second_ready.wait(), timeout=30)


def _events(session_dir: Path) -> list[TrajectoryEvent]:
    result = read_trajectory(trajectory_events_path(session_dir))
    assert result.corrupt_lines == []
    assert result.torn_tail_bytes == 0
    assert result.unsupported_event_count == 0
    return result.events


def _calls(messages: list[dict[str, Any]], provider_call_id: str) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    return [
        (message, content)
        for message in messages
        if message["role"] == "assistant"
        for content in message.get("contents") or []
        if content["type"] == "function_call" and content["call_id"] == provider_call_id
    ]


def _one_event(events: list[TrajectoryEvent], event_type: str, **payload: Any) -> TrajectoryEvent:
    matches = [
        event
        for event in events
        if event.event_type == event_type
        and all(
            (event.operation_id if key == "operation_id" else event.payload.get(key)) == value
            for key, value in payload.items()
        )
    ]
    assert len(matches) == 1, f"expected one {event_type} with {payload}, got {len(matches)}"
    return matches[0]


@pytest.mark.asyncio
async def test_tool_call_joins_its_message_and_producing_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    harness = await _start_harness(
        tmp_path,
        monkeypatch,
        [_tool_completion("chatcmpl-tool", "call_lookup_1"), _text_completion("chatcmpl-final")],
    )
    try:
        await _send(harness, "Check Paris")
        session_id = harness.engine.session.session_id
        session_dir = harness.engine.session_dir
        assert session_dir is not None
    finally:
        await harness.engine.shutdown()

    transcript = await harness.store.load_session_transcript(session_id)
    assert transcript is not None
    assert (session_dir / "session.json").is_file()
    assert trajectory_events_path(session_dir).is_file()
    calls = _calls(transcript.messages, "call_lookup_1")
    assert len(calls) == 1
    message, call = calls[0]
    message_properties = message["additional_properties"]
    call_properties = call["additional_properties"]
    call_item_id = call_properties[ANALYTICS_ITEM_ID_KEY]
    exchange_id = message_properties[OPERATION_ID_KEY]
    attempt_id = message_properties["_chrys_request_attempt_id"]

    events = _events(session_dir)
    started = _one_event(events, EventType.TOOL_OPERATION_STARTED)
    finished = _one_event(events, EventType.TOOL_OPERATION_FINISHED)
    exchange_finished = _one_event(
        events, EventType.MODEL_EXCHANGE_FINISHED, operation_id=exchange_id, outcome="success"
    )
    assert started.payload["call_item_id"] == call_item_id
    assert started.operation_id == finished.operation_id == call_properties[OPERATION_ID_KEY]
    assert started.parent_operation_id == started.payload["parent_model_operation_id"] == exchange_id
    assert finished.payload["outcome"] == "success"
    assert exchange_finished.payload["request_attempt_id"] == attempt_id

    result_contents = [
        content
        for item in transcript.messages
        for content in item.get("contents") or []
        if content["type"] == "function_result" and content["call_id"] == "call_lookup_1"
    ]
    assert len(result_contents) == 1
    assert result_contents[0]["additional_properties"][OPERATION_ID_KEY] == started.operation_id

    assert len(harness.wire.requests) == 2
    sent_attempts = [request.headers[REQUEST_ATTEMPT_ID_HEADER] for request in harness.wire.requests]
    assert attempt_id == sent_attempts[0]
    assert attempt_id != sent_attempts[1]


@pytest.mark.asyncio
async def test_rollback_orphan_tool_event_does_not_join_replacement_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    harness = await _start_harness(
        tmp_path,
        monkeypatch,
        [
            _tool_completion("chatcmpl-old-tool", "shared-call"),
            _text_completion("chatcmpl-old-final", "Old answer."),
            _tool_completion("chatcmpl-new-tool", "shared-call"),
            _text_completion("chatcmpl-new-final", "New answer."),
        ],
    )
    try:
        await _send(harness, "Old call")
        old_session_id = harness.engine.session.session_id
        old_transcript = await harness.store.load_session_transcript(old_session_id)
        assert old_transcript is not None
        old_calls = _calls(old_transcript.messages, "shared-call")
        assert len(old_calls) == 1
        old_call_item_id = old_calls[0][1]["additional_properties"][ANALYTICS_ITEM_ID_KEY]

        await harness.bus.publish(UserRollback(target_turn=0, revert_changes=False))
        await _wait_for_second_ready(harness)
        await _send(harness, "Replacement call")
        current_session_id = harness.engine.session.session_id
        session_dir = harness.engine.session_dir
        assert session_dir is not None
    finally:
        await harness.engine.shutdown()

    current_transcript = await harness.store.load_session_transcript(current_session_id)
    assert current_transcript is not None
    current_calls = _calls(current_transcript.messages, "shared-call")
    assert len(current_calls) == 1
    current_message, current_call = current_calls[0]
    current_call_item_id = current_call["additional_properties"][ANALYTICS_ITEM_ID_KEY]
    assert current_call_item_id != old_call_item_id

    current_by_item_id = {
        content["additional_properties"][ANALYTICS_ITEM_ID_KEY]: (message, content)
        for message, content in _calls(current_transcript.messages, "shared-call")
    }
    assert current_by_item_id.get(old_call_item_id) is None
    assert current_by_item_id[current_call_item_id] == (current_message, current_call)

    events = _events(session_dir)
    old_started = _one_event(events, EventType.TOOL_OPERATION_STARTED, call_item_id=old_call_item_id)
    new_started = _one_event(events, EventType.TOOL_OPERATION_STARTED, call_item_id=current_call_item_id)
    assert old_started.branch_id != new_started.branch_id
    assert new_started.parent_operation_id == current_message["additional_properties"][OPERATION_ID_KEY]
    _one_event(events, EventType.SESSION_ROLLBACK)


def _external_uuid(raw: str) -> str:
    if re.fullmatch(r"[0-9a-f]{32}", raw) is None:
        raise ValueError("expected raw lowercase 32hex identity")
    return str(UUID(hex=raw))


def _select_response_attempt(messages: list[Message], records: list[TurnRecord], turn_id: str) -> str | None:
    """Test-local copy of the directional ACP selector; this is not server wiring."""
    turn_by_opener = {
        record.opening_item_id: record.turn_id for record in records if record.opening_item_id is not None
    }
    last_response: Message | None = None
    for start, end in turn_slices(messages):
        opener = messages[start].additional_properties.get(ANALYTICS_ITEM_ID_KEY)
        if turn_by_opener.get(opener) != turn_id:
            continue
        for message in messages[start:end]:
            if message.role == "assistant" and HistoryMarkerKind.KEY not in message.additional_properties:
                last_response = message
    if last_response is None:
        return None
    attempt_id = last_response.additional_properties.get("_chrys_request_attempt_id")
    return attempt_id if isinstance(attempt_id, str) and attempt_id else None


@pytest.mark.asyncio
async def test_m0_five_record_target_contract(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Build test-local target DTOs from real A1 → write_file → A2 persistence."""
    write_completion = _completion(
        "chatcmpl-write",
        {
            "role": "assistant",
            "content": "Writing the file.",
            "tool_calls": [
                {
                    "id": "call_write_1",
                    "type": "function",
                    "function": {
                        "name": "write_file",
                        "arguments": json.dumps({"path": "m0.py", "content": "alpha\nbeta\n"}),
                    },
                }
            ],
        },
        "tool_calls",
    )
    harness = await _start_harness(
        tmp_path,
        monkeypatch,
        [write_completion, _text_completion("chatcmpl-final", "Created m0.py.")],
    )
    try:
        await _send(harness, "Create m0.py")
        session_id = harness.engine.session.session_id
        session_dir = harness.engine.session_dir
        assert session_dir is not None
    finally:
        await harness.engine.shutdown()

    transcript = await harness.store.load_session_transcript(session_id)
    state = await harness.store.load_session(session_id)
    assert transcript is not None
    assert state is not None
    assert len(transcript.turns) == 1
    turn = transcript.turns[0]

    calls = _calls(transcript.messages, "call_write_1")
    assert len(calls) == 1
    message, call = calls[0]
    raw_a1 = message["additional_properties"]["_chrys_request_attempt_id"]
    tool_operation_id = call["additional_properties"][OPERATION_ID_KEY]
    raw_a2 = _select_response_attempt(state["messages"], transcript.turns, turn.turn_id)
    assert raw_a2 is not None
    assert raw_a1 != raw_a2

    sent_attempts = [request.headers[REQUEST_ATTEMPT_ID_HEADER] for request in harness.wire.requests]
    assert sent_attempts == [raw_a1, raw_a2]
    events = _events(session_dir)
    finished = _one_event(
        events,
        EventType.TOOL_OPERATION_FINISHED,
        operation_id=tool_operation_id,
        outcome="success",
    )
    assert finished.payload["outcome"] == "success"

    mutations = [
        FileMutation.from_dict(item)
        for period in state["chrys_mutations"]["turns"]
        for item in period["mutations"]
        if item.get("tool_operation_id") == tool_operation_id
    ]
    assert len(mutations) == 1
    mutation = mutations[0]
    assert mutation.settled
    assert mutation.before_hash is None
    assert mutation.after_hash is not None
    snapshots = SnapshotStore(session_dir)
    after_bytes = snapshots.read_blob(mutation.after_hash)
    assert after_bytes == b"alpha\nbeta\n"
    assert SnapshotStore.content_hash(after_bytes) == mutation.after_hash
    assert (tmp_path / "m0.py").read_bytes() == after_bytes
    after_text = after_bytes.decode("utf-8")
    arguments = json.loads(call["arguments"])
    assert arguments == {"path": "m0.py", "content": after_text}

    original_model_records = [{"requestId": _external_uuid(raw)} for raw in sent_attempts]
    span_id = _external_uuid(turn.turn_id)
    independent_llm_records = [
        {
            "schemaVersion": 1,
            "sessionId": session_id,
            "eventType": "llm",
            "eventSubType": "success",
            "requestId": _external_uuid(raw),
            "spanId": span_id,
        }
        for raw in (raw_a1, raw_a2)
    ]
    tool_record = {
        "requestId": _external_uuid(raw_a1),
        "funcId": _external_uuid(tool_operation_id),
        "funcName": "write_file",
        "sessionId": session_id,
        "spanId": span_id,
        "funcType": 3,
        "codeStatus": 1,
        "value": arguments,
        "fileName": "m0.py",
    }
    ai_code_record = {
        "reportId": _external_uuid(tool_operation_id),
        "requestId": _external_uuid(raw_a1),
        "sessionId": session_id,
        "spanId": span_id,
        "filepath": "m0.py",
        "blocks": [{"snippet": after_text, "rangeStart": 1, "rangeEnd": 2}],
        "sourceType": "edit",
        "inputMethod": "ai_generated",
        "codeStatus": 1,
    }
    attribution_span = "3f2504e0-4f89-11d3-9a0c-0305e82c3301"
    identity = {
        "schemaVersion": 1,
        "spanId": attribution_span,
        "requestId": _external_uuid(raw_a2),
        "source": "model_request_id",
    }
    response_meta = with_chrys_metadata(
        {"agent-studio.dev/final-model-identity": identity},
        {"turnId": turn.turn_id, "turnNumber": turn.turn_number},
    )

    assert [record["requestId"] for record in original_model_records] == [
        _external_uuid(raw_a1),
        _external_uuid(raw_a2),
    ]
    assert [record["requestId"] for record in independent_llm_records] == [
        _external_uuid(raw_a1),
        _external_uuid(raw_a2),
    ]
    assert tool_record["requestId"] == ai_code_record["requestId"] == _external_uuid(raw_a1)
    assert tool_record["funcId"] == ai_code_record["reportId"] == _external_uuid(tool_operation_id)
    assert identity["requestId"] == _external_uuid(raw_a2)
    assert identity["requestId"] != tool_record["requestId"]
    assert identity["spanId"] != span_id
    assert response_meta["chrys"]["turnId"] == turn.turn_id
    assert response_meta["agent-studio.dev/final-model-identity"] == identity
    assert UUID(identity["requestId"]).hex == raw_a2
    assert UUID(tool_record["funcId"]).hex == tool_operation_id
    removed_timing_fields = {"executionStartedAt", "executionFinishedAt", "executionDurationMs"}
    assert removed_timing_fields.isdisjoint(tool_record)
    assert removed_timing_fields.isdisjoint(ai_code_record)


@pytest.mark.asyncio
async def test_m1_two_tools_share_producing_attempt_but_not_func_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    completion = _completion(
        "chatcmpl-two-tools",
        {
            "role": "assistant",
            "content": "Looking up weather and writing a file.",
            "tool_calls": [
                {
                    "id": "call_lookup_m1",
                    "type": "function",
                    "function": {"name": "lookup", "arguments": json.dumps({"city": "Paris"})},
                },
                {
                    "id": "call_write_m1",
                    "type": "function",
                    "function": {
                        "name": "write_file",
                        "arguments": json.dumps({"path": "m1.py", "content": "one\ntwo\n"}),
                    },
                },
            ],
        },
        "tool_calls",
    )
    harness = await _start_harness(
        tmp_path,
        monkeypatch,
        [completion, _text_completion("chatcmpl-two-tools-final")],
    )
    try:
        await _send(harness, "Run both tools")
        session_id = harness.engine.session.session_id
        session_dir = harness.engine.session_dir
        assert session_dir is not None
    finally:
        await harness.engine.shutdown()

    transcript = await harness.store.load_session_transcript(session_id)
    state = await harness.store.load_session(session_id)
    assert transcript is not None
    assert state is not None
    lookup_calls = _calls(transcript.messages, "call_lookup_m1")
    write_calls = _calls(transcript.messages, "call_write_m1")
    assert len(lookup_calls) == len(write_calls) == 1
    lookup_message, lookup_call = lookup_calls[0]
    write_message, write_call = write_calls[0]
    assert lookup_message == write_message
    raw_a1 = write_message["additional_properties"]["_chrys_request_attempt_id"]
    lookup_t = lookup_call["additional_properties"][OPERATION_ID_KEY]
    write_t = write_call["additional_properties"][OPERATION_ID_KEY]
    assert lookup_t != write_t

    events = _events(session_dir)
    for operation_id in (lookup_t, write_t):
        _one_event(
            events,
            EventType.TOOL_OPERATION_FINISHED,
            operation_id=operation_id,
            outcome="success",
        )
    mutations = [
        item
        for period in state["chrys_mutations"]["turns"]
        for item in period["mutations"]
        if item.get("tool_operation_id") in {lookup_t, write_t}
    ]
    assert len(mutations) == 1
    assert mutations[0]["tool_operation_id"] == write_t

    sent_attempts = [request.headers[REQUEST_ATTEMPT_ID_HEADER] for request in harness.wire.requests]
    assert sent_attempts[0] == raw_a1
    assert len(transcript.turns) == 1
    turn = transcript.turns[0]
    raw_a2 = _select_response_attempt(state["messages"], transcript.turns, turn.turn_id)
    assert raw_a2 == sent_attempts[1]
    assert raw_a1 != raw_a2

    request_id = _external_uuid(raw_a1)
    tool_records = [
        {"requestId": request_id, "funcId": _external_uuid(operation_id)} for operation_id in (lookup_t, write_t)
    ]
    ai_code_records = [{"requestId": request_id, "reportId": _external_uuid(write_t)}]
    assert {record["requestId"] for record in tool_records} == {request_id}
    assert len({record["funcId"] for record in tool_records}) == 2
    assert ai_code_records[0]["reportId"] == tool_records[1]["funcId"]
    assert ai_code_records[0]["reportId"] != tool_records[0]["funcId"]
    assert all(record["requestId"] != _external_uuid(raw_a2) for record in [*tool_records, *ai_code_records])


@pytest.mark.asyncio
async def test_m1_failed_turn_does_not_reuse_previous_success_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    harness = await _start_harness(
        tmp_path,
        monkeypatch,
        [
            _text_completion("chatcmpl-old-success", "Old answer."),
            (400, {"error": {"message": "current turn failed", "type": "invalid_request_error"}}),
        ],
    )
    try:
        await _send(harness, "Successful turn")
        await harness.bus.publish(UserMessage(text="Failed turn"))
        await asyncio.wait_for(harness.engine.turns.turn_state.drain_for_boundary(), timeout=30)
        session_id = harness.engine.session.session_id
    finally:
        await harness.engine.shutdown()

    transcript = await harness.store.load_session_transcript(session_id)
    state = await harness.store.load_session(session_id)
    assert transcript is not None
    assert state is not None
    assert len(transcript.turns) == 2
    old_turn, failed_turn = transcript.turns
    old_attempt = _select_response_attempt(state["messages"], transcript.turns, old_turn.turn_id)
    failed_attempt = _select_response_attempt(state["messages"], transcript.turns, failed_turn.turn_id)
    assert old_attempt is not None
    assert failed_attempt is None

    sent_attempts = [request.headers[REQUEST_ATTEMPT_ID_HEADER] for request in harness.wire.requests]
    assert sent_attempts[0] == old_attempt
    assert len(sent_attempts) >= 2
    assert all(attempt != old_attempt for attempt in sent_attempts[1:])
    current_turn_success_reports = [] if failed_attempt is None else [{"requestId": _external_uuid(failed_attempt)}]
    assert current_turn_success_reports == []


@pytest.mark.asyncio
async def test_m1_sdk_retry_only_success_attempt_forms_records(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    harness = await _start_harness(
        tmp_path,
        monkeypatch,
        [
            (429, {"error": {"message": "retry", "type": "rate_limit_error"}}),
            _tool_completion("chatcmpl-retry-tool", "call_retry_lookup"),
            _text_completion("chatcmpl-retry-final"),
        ],
        http_max_retries=1,
    )
    try:
        await _send(harness, "Retry and call lookup")
        session_id = harness.engine.session.session_id
    finally:
        await harness.engine.shutdown()

    transcript = await harness.store.load_session_transcript(session_id)
    state = await harness.store.load_session(session_id)
    assert transcript is not None
    assert state is not None
    calls = _calls(transcript.messages, "call_retry_lookup")
    assert len(calls) == 1
    message, _call = calls[0]
    raw_a1 = message["additional_properties"]["_chrys_request_attempt_id"]
    assert len(transcript.turns) == 1
    raw_a2 = _select_response_attempt(state["messages"], transcript.turns, transcript.turns[0].turn_id)
    assert raw_a2 is not None

    sent_attempts = [request.headers[REQUEST_ATTEMPT_ID_HEADER] for request in harness.wire.requests]
    assert harness.wire.statuses == [429, 200, 200]
    assert len(sent_attempts) == len(set(sent_attempts)) == 3
    assert raw_a1 == sent_attempts[1]
    assert raw_a2 == sent_attempts[2]
    assert raw_a1 != sent_attempts[0]
    original_success_records = [
        {"requestId": _external_uuid(attempt)}
        for attempt, status in zip(sent_attempts, harness.wire.statuses, strict=True)
        if status == 200
    ]
    assert original_success_records == [
        {"requestId": _external_uuid(raw_a1)},
        {"requestId": _external_uuid(raw_a2)},
    ]


async def _reconstruct_from_files(
    session_dir: Path, session_id: str, *, expected_turn_id: str | None = None
) -> dict[str, Any]:
    """Directional file-only reader; no live engine, expected A or known T inputs."""
    store = JsonFileStateStore(session_dir.parent)
    assert store.session_dir(session_id) == session_dir
    state = await store.load_session(session_id)
    transcript = await store.load_session_transcript(session_id)
    result: dict[str, Any] = {"llm": [], "tools": [], "aiCode": [], "skipped": []}
    if state is None or transcript is None:
        result["skipped"].append("session-unavailable")
        return result

    messages: list[Message] = state["messages"]
    turn_by_opener = {
        record.opening_item_id: record.turn_id
        for record in transcript.turns
        if record.opening_item_id is not None and record.origin_session_id is None
    }
    calls: dict[str, dict[str, Any]] = {}
    ambiguous_tools: set[str] = set()
    for start, end in turn_slices(messages):
        opener = messages[start].additional_properties.get(ANALYTICS_ITEM_ID_KEY)
        turn_id = turn_by_opener.get(opener)
        if turn_id is None or (expected_turn_id is not None and turn_id != expected_turn_id):
            continue
        span_id = _external_uuid(turn_id)
        for message in messages[start:end]:
            if message.role != "assistant" or HistoryMarkerKind.KEY in message.additional_properties:
                continue
            raw_a = message.additional_properties.get("_chrys_request_attempt_id")
            function_calls = [content for content in message.contents if content.type == "function_call"]
            if not isinstance(raw_a, str) or not raw_a:
                if function_calls:
                    result["skipped"].append(f"tool-without-a:{turn_id}")
                continue
            request_id = _external_uuid(raw_a)
            result["llm"].append(
                {
                    "sessionId": session_id,
                    "spanId": span_id,
                    "requestId": request_id,
                }
            )
            for content in function_calls:
                operation_id = content.additional_properties.get(OPERATION_ID_KEY)
                if not isinstance(operation_id, str) or not operation_id:
                    result["skipped"].append(f"tool-without-t:{request_id}")
                    continue
                if operation_id in calls:
                    ambiguous_tools.add(operation_id)
                    continue
                calls[operation_id] = {
                    "requestId": request_id,
                    "spanId": span_id,
                    "name": content.name,
                    "arguments": content.arguments,
                }

    trajectory_path = trajectory_events_path(session_dir)
    trajectory = read_trajectory(trajectory_path)
    events = trajectory.events
    if not trajectory_path.is_file():
        result["skipped"].append("trajectory-absent")
    if (
        trajectory.corrupt_lines
        or trajectory.torn_tail_bytes
        or trajectory.unsupported_event_count
        or verify_accounted_prefix(trajectory.slots)
    ):
        result["skipped"].append("trajectory-untrusted")
        events = []
    successful_tools = {
        event.operation_id
        for event in events
        if event.event_type == EventType.TOOL_OPERATION_FINISHED and event.payload.get("outcome") == "success"
    }
    for operation_id, call in calls.items():
        if operation_id in ambiguous_tools:
            result["skipped"].append(f"ambiguous-tool:{operation_id}")
        elif operation_id not in successful_tools:
            result["skipped"].append(f"tool-outcome-unknown:{operation_id}")
        else:
            result["tools"].append(
                {
                    "requestId": call["requestId"],
                    "spanId": call["spanId"],
                    "funcId": _external_uuid(operation_id),
                    "funcName": call["name"],
                    "value": call["arguments"],
                    "codeStatus": 1,
                }
            )

    mutations_by_tool: dict[str, list[FileMutation]] = {}
    for period in state["chrys_mutations"]["turns"]:
        for item in period["mutations"]:
            mutation = FileMutation.from_dict(item)
            if mutation.tool_operation_id is not None:
                mutations_by_tool.setdefault(mutation.tool_operation_id, []).append(mutation)
    snapshots = SnapshotStore(session_dir)
    for operation_id, mutations in mutations_by_tool.items():
        call = calls.get(operation_id)
        if call is None or operation_id not in successful_tools or operation_id in ambiguous_tools:
            continue
        if len(mutations) != 1:
            result["skipped"].append(f"ai-code-ambiguous-mutations:{operation_id}")
            continue
        mutation = mutations[0]
        if not mutation.settled or mutation.after_hash is None or call["name"] != "write_file":
            result["skipped"].append(f"ai-code-unavailable:{operation_id}")
            continue
        try:
            after_bytes = snapshots.read_blob(mutation.after_hash)
            if after_bytes is None:
                raise ValueError("missing mutation blob")
            after_text = after_bytes.decode("utf-8")
            arguments = json.loads(call["arguments"]) if isinstance(call["arguments"], str) else dict(call["arguments"])
        except FileNotFoundError, UnicodeDecodeError, ValueError, TypeError:
            result["skipped"].append(f"ai-code-blob-or-arguments:{operation_id}")
            continue
        if arguments.get("content") != after_text:
            result["skipped"].append(f"ai-code-arguments-mismatch:{operation_id}")
            continue
        result["aiCode"].append(
            {
                "requestId": call["requestId"],
                "spanId": call["spanId"],
                "reportId": _external_uuid(operation_id),
                "filepath": mutation.path,
                "blocks": [{"snippet": after_text, "rangeStart": 1, "rangeEnd": len(after_text.splitlines())}],
                "codeStatus": 1,
            }
        )
    if expected_turn_id is not None and not result["llm"]:
        result["skipped"].append(f"expected-turn-not-saved:{expected_turn_id}")
    return result


@pytest.mark.asyncio
async def test_file_only_reconstruction_is_exact_across_two_turns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_completion = _completion(
        "chatcmpl-reconstruct-write",
        {
            "role": "assistant",
            "content": "Writing.",
            "tool_calls": [
                {
                    "id": "call_reconstruct_write",
                    "type": "function",
                    "function": {
                        "name": "write_file",
                        "arguments": json.dumps({"path": "reconstructed.py", "content": "first\nsecond\n"}),
                    },
                }
            ],
        },
        "tool_calls",
    )
    harness = await _start_harness(
        tmp_path,
        monkeypatch,
        [
            _text_completion("chatcmpl-reconstruct-first", "First turn."),
            write_completion,
            _text_completion("chatcmpl-reconstruct-final", "Second turn."),
        ],
    )
    try:
        await _send(harness, "First turn")
        await _send(harness, "Second turn")
        session_id = harness.engine.session.session_id
        session_dir = harness.engine.session_dir
        assert session_dir is not None
    finally:
        await harness.engine.shutdown()

    reconstructed = await _reconstruct_from_files(session_dir, session_id)
    sent_attempts = [request.headers[REQUEST_ATTEMPT_ID_HEADER] for request in harness.wire.requests]
    assert [UUID(record["requestId"]).hex for record in reconstructed["llm"]] == sent_attempts
    assert len(reconstructed["llm"]) == 3
    assert len(reconstructed["tools"]) == 1
    assert len(reconstructed["aiCode"]) == 1
    assert reconstructed["skipped"] == []

    first_llm, producing_llm, final_llm = reconstructed["llm"]
    tool = reconstructed["tools"][0]
    ai_code = reconstructed["aiCode"][0]
    assert first_llm["spanId"] != producing_llm["spanId"]
    assert producing_llm["spanId"] == final_llm["spanId"] == tool["spanId"] == ai_code["spanId"]
    assert tool["requestId"] == ai_code["requestId"] == producing_llm["requestId"]
    assert tool["requestId"] != final_llm["requestId"]
    assert tool["funcId"] == ai_code["reportId"]
    assert ai_code["filepath"] == str(tmp_path / "reconstructed.py")
    assert ai_code["blocks"] == [{"snippet": "first\nsecond\n", "rangeStart": 1, "rangeEnd": 2}]
    assert await _reconstruct_from_files(session_dir, session_id) == reconstructed


async def _closed_write_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[_Harness, str, Path]:
    completion = _completion(
        "chatcmpl-degraded-write",
        {
            "role": "assistant",
            "content": "Writing.",
            "tool_calls": [
                {
                    "id": "call_degraded_write",
                    "type": "function",
                    "function": {
                        "name": "write_file",
                        "arguments": json.dumps({"path": "degraded.py", "content": "before\nafter\n"}),
                    },
                }
            ],
        },
        "tool_calls",
    )
    harness = await _start_harness(
        tmp_path,
        monkeypatch,
        [completion, _text_completion("chatcmpl-degraded-final", "Written.")],
    )
    try:
        await _send(harness, "Write the file")
        session_id = harness.engine.session.session_id
        session_dir = harness.engine.session_dir
        assert session_dir is not None
    finally:
        await harness.engine.shutdown()
    return harness, session_id, session_dir


@pytest.mark.asyncio
async def test_file_only_missing_blob_skips_only_ai_code(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _harness, session_id, session_dir = await _closed_write_session(tmp_path, monkeypatch)
    blobs = [path for path in (session_dir / "mutations").iterdir() if path.is_file()]
    assert len(blobs) == 1
    blobs[0].unlink()
    assert (tmp_path / "degraded.py").exists()

    reconstructed = await _reconstruct_from_files(session_dir, session_id)
    assert len(reconstructed["llm"]) == 2
    assert len(reconstructed["tools"]) == 1
    assert reconstructed["aiCode"] == []
    assert any(item.startswith("ai-code-blob-or-arguments:") for item in reconstructed["skipped"])


@pytest.mark.asyncio
async def test_file_only_missing_tool_terminal_skips_tool_and_ai_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _harness, session_id, session_dir = await _closed_write_session(tmp_path, monkeypatch)
    trajectory_path = trajectory_events_path(session_dir)
    lines = trajectory_path.read_text(encoding="utf-8").splitlines()
    kept = [line for line in lines if json.loads(line).get("event_type") != EventType.TOOL_OPERATION_FINISHED]
    assert len(kept) < len(lines)
    trajectory_path.write_text("\n".join(kept) + "\n", encoding="utf-8")

    reconstructed = await _reconstruct_from_files(session_dir, session_id)
    assert len(reconstructed["llm"]) == 2
    assert reconstructed["tools"] == []
    assert reconstructed["aiCode"] == []
    assert any(item.startswith("tool-outcome-unknown:") for item in reconstructed["skipped"])
    assert "trajectory-untrusted" in reconstructed["skipped"]


@pytest.mark.asyncio
async def test_file_only_fork_does_not_reemit_inherited_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _harness, session_id, session_dir = await _closed_write_session(tmp_path, monkeypatch)
    store = JsonFileStateStore(session_dir.parent)
    fork_id = store.fork_session(session_id)
    fork_dir = session_dir.parent / fork_id.replace("-", "")[:12]
    assert fork_dir.is_dir()

    original = await _reconstruct_from_files(session_dir, session_id)
    forked = await _reconstruct_from_files(fork_dir, fork_id)
    assert len(original["llm"]) == 2
    assert len(original["tools"]) == len(original["aiCode"]) == 1
    assert forked == {"llm": [], "tools": [], "aiCode": [], "skipped": ["trajectory-absent"]}


@pytest.mark.asyncio
async def test_file_only_save_suppressed_requires_expected_turn_guard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    harness = await _start_harness(
        tmp_path,
        monkeypatch,
        [
            _text_completion("chatcmpl-saved-old", "Old saved answer."),
            _text_completion("chatcmpl-unsaved-current", "Current unsaved answer."),
        ],
    )
    session_dir: Path | None = None
    try:
        await _send(harness, "Saved turn")
        session_id = harness.engine.session.session_id
        session_dir = harness.engine.session_dir
        assert session_dir is not None
        with harness.engine.session.saves_suppressed():
            await _send(harness, "Unsaved turn")
            turn_ids = [
                event.turn_id
                for event in _events(session_dir)
                if event.event_type == EventType.TURN_STARTED and event.turn_id is not None
            ]
            assert len(turn_ids) == 2
            current_turn_id = turn_ids[-1]
            guarded = await _reconstruct_from_files(session_dir, session_id, expected_turn_id=current_turn_id)
    finally:
        with harness.engine.session.saves_suppressed():
            await harness.engine.shutdown()

    assert guarded["llm"] == []
    assert guarded["tools"] == guarded["aiCode"] == []
    assert guarded["skipped"] == [f"expected-turn-not-saved:{current_turn_id}"]

    unguarded = await _reconstruct_from_files(session_dir, session_id)
    sent_attempts = [request.headers[REQUEST_ATTEMPT_ID_HEADER] for request in harness.wire.requests]
    assert len(sent_attempts) == 2
    assert [UUID(record["requestId"]).hex for record in unguarded["llm"]] == sent_attempts[:1]
    assert sent_attempts[1] not in {UUID(record["requestId"]).hex for record in unguarded["llm"]}


@pytest.mark.asyncio
@pytest.mark.timeout(180)
async def test_session_scan_benchmark_full_vs_expected_turn(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    replies: list[Any] = []
    tool_turns = 0
    write_turns = 0
    for turn_number in range(1, 31):
        if turn_number % 5 == 0:
            tool_turns += 1
            write_turns += 1
            replies.extend(
                [
                    _completion(
                        f"chatcmpl-bench-write-{turn_number}",
                        {
                            "role": "assistant",
                            "content": "Writing.",
                            "tool_calls": [
                                {
                                    "id": f"call_bench_write_{turn_number}",
                                    "type": "function",
                                    "function": {
                                        "name": "write_file",
                                        "arguments": json.dumps(
                                            {"path": f"benchmark-{turn_number}.py", "content": f"turn-{turn_number}\n"}
                                        ),
                                    },
                                }
                            ],
                        },
                        "tool_calls",
                    ),
                    _text_completion(f"chatcmpl-bench-final-{turn_number}"),
                ]
            )
        elif turn_number % 3 == 0:
            tool_turns += 1
            replies.extend(
                [
                    _tool_completion(f"chatcmpl-bench-tool-{turn_number}", f"call_bench_lookup_{turn_number}"),
                    _text_completion(f"chatcmpl-bench-final-{turn_number}"),
                ]
            )
        else:
            replies.append(_text_completion(f"chatcmpl-bench-text-{turn_number}"))

    harness = await _start_harness(tmp_path, monkeypatch, replies)
    samples: list[dict[str, Any]] = []
    full_total_ms = 0.0
    current_total_ms = 0.0
    final_full: dict[str, Any] = {}

    async def measure(session_id: str, session_dir: Path, turn_id: str | None) -> tuple[dict[str, Any], float]:
        started = perf_counter()
        if turn_id is None:
            result = await _reconstruct_from_files(session_dir, session_id)
        else:
            result = await _reconstruct_from_files(session_dir, session_id, expected_turn_id=turn_id)
        return result, (perf_counter() - started) * 1000

    try:
        session_id = harness.engine.session.session_id
        session_dir = harness.engine.session_dir
        assert session_dir is not None
        for turn_number in range(1, 31):
            await _send(harness, f"Benchmark turn {turn_number}")
            turn_ids = [
                event.turn_id
                for event in _events(session_dir)
                if event.event_type == EventType.TURN_STARTED and event.turn_id is not None
            ]
            assert len(turn_ids) == turn_number
            turn_id = turn_ids[-1]

            full, full_ms = await measure(session_id, session_dir, None)
            current, current_ms = await measure(session_id, session_dir, turn_id)
            full_total_ms += full_ms
            current_total_ms += current_ms
            failed_tool_payloads = [
                event.payload
                for event in _events(session_dir)
                if event.event_type == EventType.TOOL_OPERATION_FINISHED
                and event.payload.get("outcome") not in {"success", "skipped"}
            ]
            assert not failed_tool_payloads, json.dumps(failed_tool_payloads, default=str)
            assert full["skipped"] == current["skipped"] == [], {
                "turn": turn_number,
                "fullSkipped": full["skipped"],
                "currentSkipped": current["skipped"],
            }
            assert current["llm"]
            span_id = current["llm"][0]["spanId"]
            for key in ("llm", "tools", "aiCode"):
                assert current[key] == [record for record in full[key] if record["spanId"] == span_id]

            if turn_number in {5, 15, 30}:
                full_samples = [full_ms]
                current_samples = [current_ms]
                for _ in range(2):
                    _result, elapsed = await measure(session_id, session_dir, None)
                    full_samples.append(elapsed)
                    _result, elapsed = await measure(session_id, session_dir, turn_id)
                    current_samples.append(elapsed)
                sample = {
                    "turn": turn_number,
                    "sessionKiB": round((session_dir / "session.json").stat().st_size / 1024, 1),
                    "trajectoryKiB": round(trajectory_events_path(session_dir).stat().st_size / 1024, 1),
                    "mutationKiB": round(
                        sum(path.stat().st_size for path in (session_dir / "mutations").iterdir() if path.is_file())
                        / 1024,
                        1,
                    ),
                    "fullMedianMs": round(median(full_samples), 3),
                    "currentMedianMs": round(median(current_samples), 3),
                    "fullLlm": len(full["llm"]),
                    "fullTools": len(full["tools"]),
                    "fullAiCode": len(full["aiCode"]),
                }
                samples.append(sample)
                logger.info("SESSION_SCAN_SAMPLE " + json.dumps(sample, sort_keys=True))
            final_full = full
    finally:
        await harness.engine.shutdown()

    assert len(final_full["llm"]) == 30 + tool_turns
    assert len(final_full["tools"]) == tool_turns
    assert len(final_full["aiCode"]) == write_turns
    summary = {
        "turns": 30,
        "toolTurns": tool_turns,
        "writeTurns": write_turns,
        "fullCumulativeMs": round(full_total_ms, 3),
        "currentCumulativeMs": round(current_total_ms, 3),
        "samples": samples,
    }
    logger.info("SESSION_SCAN_SUMMARY " + json.dumps(summary, sort_keys=True))


def test_external_uuid_golden() -> None:
    assert _external_uuid("00112233445566778899aabbccddeeff") == "00112233-4455-6677-8899-aabbccddeeff"
    assert _external_uuid("10000000000000000000000000000002") == "10000000-0000-0000-0000-000000000002"


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "00112233445566778899aabbccddeef",
        "00112233445566778899aabbccddeefff",
        "00112233445566778899AABBCCDDEEF",
        "00112233-4455-6677-8899-aabbccddeeff",
    ],
)
def test_external_uuid_rejects_non_raw_identity(raw: str) -> None:
    with pytest.raises(ValueError, match="raw lowercase 32hex"):
        _external_uuid(raw)
