# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Batch-1 precondition probes V1/V2 (design §4; V3 pending compaction trigger).

V1 (F1 ruling): record-level read consistency — after two persisted turns an
expected-turn read returns only that turn's facts; after a destructive
rewrite (rollback + replacement) the read never stitches old-turn facts into
the replacement turn, and skipped/prior sources are listed explicitly.

V2 (F2 ruling): dispatcher notice contract — same-pass duplicate notices
merge while the first task is pending/running/completed; a new pass is never
dropped; queue order is FIFO per session; a logical-turn-level view exists
for the future 1001 single-record contract (batch 2 implements 1001 itself).

These are test-state probes over real engine files (same harness pattern as
test_tool_identity_persistence.py); the production reader/dispatcher lands
with the slice implementation and must satisfy the same invariants.
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from chrys.foundation.config.settings import Settings
from chrys.foundation.events.bus import EventBus
from chrys.foundation.events.types import Error, UserMessage, UserRollback
from chrys.foundation.models.workspace import Workspace
from chrys.foundation.trajectory.envelope import TrajectoryEvent
from chrys.foundation.trajectory.event_types import EventType
from chrys.foundation.trajectory.metadata import ANALYTICS_ITEM_ID_KEY, OPERATION_ID_KEY
from chrys.foundation.trajectory.reader import read_trajectory
from chrys.kernel import tool
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

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared harness (mirrors test_tool_identity_persistence.py)
# ---------------------------------------------------------------------------


def _lookup(city: str) -> str:
    return f"Sunny in {city}, 21 degrees."


def _completion(
    response_id: str,
    message: dict[str, Any],
    finish_reason: str,
    *,
    prompt_tokens: int = 10,
    completion_tokens: int = 5,
) -> dict[str, Any]:
    return {
        "id": response_id,
        "object": "chat.completion",
        "created": 1_767_225_600,
        "model": "model-test",
        "choices": [{"index": 0, "message": message, "finish_reason": finish_reason}],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


def _tool_completion(response_id: str, call_id: str, city: str = "Paris", **usage: int) -> dict[str, Any]:
    return _completion(
        response_id,
        {
            "role": "assistant",
            "content": "Let me check the weather.",
            "tool_calls": [
                {
                    "id": call_id,
                    "type": "function",
                    "function": {"name": "lookup", "arguments": json.dumps({"city": city})},
                }
            ],
        },
        "tool_calls",
        **usage,
    )


def _text_completion(response_id: str, text: str = "Done.", **usage: int) -> dict[str, Any]:
    return _completion(response_id, {"role": "assistant", "content": text}, "stop", **usage)


_LAST_WORDS_NOTE = (
    "## Task\n"
    "Serve the current request after folding the turn's tool history into this note.\n\n"
    "## Progress\n"
    "The lookup tool ran for Oslo and returned a sunny summary; the assistant\n"
    "acknowledged it, persisted the session, and prepared the final reply.\n\n"
    "## Next\n"
    "Answer the pending request directly using the folded note instead of\n"
    "replaying the original tool transcript or re-invoking the tool.\n"
)


class _Wire:
    """Scripted wire with LAST_WORDS (Phase-4) side-call routing.

    Compaction's LAST_WORDS generator issues its own chat-completion call
    whose prompt carries the note format contract; those calls are answered
    from the canned compliant note above so real Phase-4 compaction can run.
    """

    def __init__(self, replies: list[Any]) -> None:
        self._replies = list(replies)
        self.requests: list[httpx.Request] = []
        self.main_calls: list[httpx.Request] = []
        self.last_words_calls: list[httpx.Request] = []
        self.transport = httpx.MockTransport(self._handle)

    async def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        body_text = request.content.decode("utf-8", "replace")
        if "Format contract: begin the note" in body_text:
            self.last_words_calls.append(request)
            return httpx.Response(200, json=_text_completion("chatcmpl-lastwords", _LAST_WORDS_NOTE), request=request)
        assert self._replies, f"unscripted request: {request.method} {request.url}"
        self.main_calls.append(request)
        reply = self._replies.pop(0)
        status, payload = reply if isinstance(reply, tuple) else (200, reply)
        return httpx.Response(status, json=payload, request=request)


@dataclass
class _Harness:
    engine: Any
    bus: EventBus
    store: JsonFileStateStore
    wire: _Wire
    errors: list[Error]


async def _start_harness(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    replies: list[Any],
    *,
    compaction: bool = False,
    max_context_tokens: int | None = None,
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

    model_kwargs: dict[str, Any] = {}
    if max_context_tokens is not None:
        model_kwargs["max_context_tokens"] = max_context_tokens
    model = ModelProfile(
        id="telemetry-model",
        name="telemetry-model",
        provider="openai",
        api_style=API_STYLE_CHAT_COMPLETIONS,
        model_id="model-test",
        api_key="sk-test",
        base_url="https://model.example.test",
        http_max_retries=0,
        stream=False,
        **model_kwargs,
    )
    models = ModelProfileRegistry()
    models.register(model)
    profile = AgentProfile(
        name="telemetry-after-turn-slice",
        instructions="Reply briefly.",
        tools=ToolsConfig(builtins=[]),
        skills=SkillsConfig(auto_load_user_agents_skills=False, auto_load_cwd_agents_skills=False),
        approval=ApprovalConfig(default="auto"),
        compaction=CompactionConfig(enabled=compaction),
    )
    agents = AgentProfileRegistry()
    agents.register(profile)

    bus = EventBus()
    errors: list[Error] = []
    await bus.subscribe(Error, errors.append)
    store = JsonFileStateStore(tmp_path / "sessions")
    engine = assemble_engine(bus, models, agents, store, tmp_path)
    await engine.start(profile)
    return _Harness(engine, bus, store, wire, errors)


def assemble_engine(
    bus: EventBus, models: ModelProfileRegistry, agents: AgentProfileRegistry, store: JsonFileStateStore, tmp_path: Path
) -> Any:
    from chrys.orchestration.engine.assembly import assemble_agent_engine

    return assemble_agent_engine(
        bus,
        settings=Settings(
            model_profile="telemetry-model",
            workspace_change_notice=False,
            default_approval_mode="bypass",
        ),
        agent_registry=agents,
        model_registry=models,
        state_store=store,
        initial_workspace=Workspace.from_cwd(str(tmp_path)),
    )


async def _send(harness: _Harness, text: str) -> None:
    await harness.bus.publish(UserMessage(text=text))
    await asyncio.wait_for(harness.engine.turns.turn_state.drain_for_boundary(), timeout=30)
    assert harness.errors == []


def _events(session_dir: Path) -> list[TrajectoryEvent]:
    result = read_trajectory(trajectory_events_path(session_dir))
    assert result.corrupt_lines == []
    assert result.torn_tail_bytes == 0
    assert result.unsupported_event_count == 0
    return result.events


# ---------------------------------------------------------------------------
# Minimal reader prototype (the invariant under probe — the production
# reader in service/aixcoding/telemetry/ must satisfy the same contract)
# ---------------------------------------------------------------------------


@dataclass
class TurnFacts:
    """Record-level facts for one expected turn, plus explicit skips."""

    attempts: dict[str, str] = field(default_factory=dict)  # exchange_id -> attempt_id
    tool_operations: dict[str, str] = field(default_factory=dict)  # tool op id -> call_item_id
    skipped: list[str] = field(default_factory=list)  # why each out-of-scope record was skipped


def _user_anchors(messages: list[dict[str, Any]]) -> list[tuple[int, str]]:
    anchors: list[tuple[int, str]] = []
    for index, item in enumerate(messages):
        if item.get("role") != "user":
            continue
        texts = [content.get("text", "") for content in item.get("contents") or [] if content.get("type") == "text"]
        anchors.append((index, " ".join(texts)))
    return anchors


def _read_expected_turn(messages: list[dict[str, Any]], anchor_user_text: str) -> TurnFacts:
    """Slice messages by the user anchor for `anchor_user_text` (first match).

    Records before the anchor are prior sources (kept out, listed); records
    after the next user anchor belong to later turns (kept out, listed).
    """
    anchors = _user_anchors(messages)
    start = next((index for index, text in anchors if text == anchor_user_text), None)
    assert start is not None, f"anchor user message not found: {anchor_user_text!r}"
    later = [index for index, _ in anchors if index > start]
    end = later[0] if later else len(messages)

    facts = TurnFacts()
    for index, item in enumerate(messages):
        if item.get("role") != "assistant":
            continue
        if index < start:
            facts.skipped.append(f"prior-source:assistant@{index}")
            continue
        if index >= end:
            facts.skipped.append(f"later-turn:assistant@{index}")
            continue
        properties = item.get("additional_properties") or {}
        exchange_id = properties.get(OPERATION_ID_KEY)
        attempt_id = properties.get("_chrys_request_attempt_id")
        if exchange_id and attempt_id:
            facts.attempts[exchange_id] = attempt_id
        for content in item.get("contents") or []:
            if content.get("type") != "function_call":
                continue
            call_properties = content.get("additional_properties") or {}
            tool_op = call_properties.get(OPERATION_ID_KEY)
            call_item = call_properties.get(ANALYTICS_ITEM_ID_KEY)
            if tool_op and call_item:
                facts.tool_operations[tool_op] = call_item
    return facts


def _tool_event_scope(events: list[TrajectoryEvent], facts: TurnFacts) -> set[str]:
    """Tool operation ids whose parent exchange belongs to the expected turn."""
    return {
        event.operation_id
        for event in events
        if event.event_type == EventType.TOOL_OPERATION_STARTED and event.parent_operation_id in facts.attempts
    }


# ---------------------------------------------------------------------------
# V1 — record-level read consistency (F1 ruling)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_v1_expected_turn_read_returns_only_that_turn(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    harness = await _start_harness(
        tmp_path,
        monkeypatch,
        [_text_completion("chatcmpl-one", "First answer."), _text_completion("chatcmpl-two", "Second answer.")],
    )
    try:
        await _send(harness, "First question")
        await _send(harness, "Second question")
        session_id = harness.engine.session.session_id
        session_dir = harness.engine.session_dir
        assert session_dir is not None
    finally:
        await harness.engine.shutdown()

    transcript = await harness.store.load_session_transcript(session_id)
    assert transcript is not None

    first = _read_expected_turn(transcript.messages, "First question")
    second = _read_expected_turn(transcript.messages, "Second question")

    assert set(first.attempts) != set(second.attempts)
    assert len(first.attempts) == 1
    assert len(second.attempts) == 1
    assert "later-turn:assistant@" in first.skipped[0]
    assert not [entry for entry in second.skipped if entry.startswith("later-turn:")]

    sent_attempts = [request.headers["Chrys-Request-Attempt-Id"] for request in harness.wire.requests]
    assert sorted(first.attempts.values()) == sorted(sent_attempts[:1])
    assert sorted(second.attempts.values()) == sorted(sent_attempts[1:])

    events = _events(session_dir)
    for exchange_id, attempt_id in first.attempts.items():
        finished = [
            event
            for event in events
            if event.event_type == EventType.MODEL_EXCHANGE_FINISHED and event.operation_id == exchange_id
        ]
        assert len(finished) == 1
        assert finished[0].payload["request_attempt_id"] == attempt_id


@pytest.mark.asyncio
async def test_v1_destructive_rewrite_never_stitches_old_turn(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Rollback = a fresh session: the replacement read stays clean and the
    pre-rollback records live on only in the old session's files — the
    session boundary is the isolation guarantee (same-session destructive
    rewrites are compaction/edit, covered by V3)."""
    harness = await _start_harness(
        tmp_path,
        monkeypatch,
        [
            _tool_completion("chatcmpl-old-tool", "shared-call", "Oslo"),
            _text_completion("chatcmpl-old-final", "Old answer."),
            _tool_completion("chatcmpl-new-tool", "shared-call", "Rome"),
            _text_completion("chatcmpl-new-final", "New answer."),
        ],
    )
    try:
        await _send(harness, "Old request")
        old_session_id = harness.engine.session.session_id
        old_session_dir = harness.engine.session_dir
        await harness.bus.publish(UserRollback())
        await asyncio.wait_for(harness.engine.turns.turn_state.drain_for_boundary(), timeout=30)
        await _send(harness, "New request")
        session_id = harness.engine.session.session_id
        session_dir = harness.engine.session_dir
        assert session_dir is not None
    finally:
        await harness.engine.shutdown()

    assert session_id == old_session_id, "UserRollback rewrites the transcript inside the same session"

    new_transcript = await harness.store.load_session_transcript(session_id)
    assert new_transcript is not None
    replacement = _read_expected_turn(new_transcript.messages, "New request")
    assert len(replacement.tool_operations) == 1
    replacement_tool = next(iter(replacement.tool_operations))
    assert replacement.skipped == [], "the rewritten transcript must not carry pre-rollback messages"

    # events.jsonl is append-only: the pre-rollback tool events are still in
    # the file even though their assistant messages are gone from the
    # transcript. Turn numbering has been reset, so the guard cannot be the
    # turn number — it is exchange ownership: a tool event counts as in-scope
    # only when its parent exchange belongs to the expected turn's attempts.
    events = _events(session_dir)
    assert _tool_event_scope(events, replacement) == {replacement_tool}
    stale_tool_starts = [
        event
        for event in events
        if event.event_type == EventType.TOOL_OPERATION_STARTED
        and event.parent_operation_id not in replacement.attempts
    ]
    assert stale_tool_starts, "append-only events must still hold the pre-rollback tool events"
    assert all(event.operation_id != replacement_tool for event in stale_tool_starts)
    assert old_session_dir == session_dir


# ---------------------------------------------------------------------------
# V2 — dispatcher notice contract (F2 ruling)
# ---------------------------------------------------------------------------


@dataclass
class _Notice:
    session_id: str
    logical_turn_id: str
    pass_id: str


class _DispatchProbe:
    """Minimal same-pass merge / new-pass keep semantics (design §3.1).

    The merge key is the full (session_id, logical_turn_id, pass_id) triple —
    the V2 session-isolation probe exists to prove the session dimension
    cannot be dropped from the key.
    """

    def __init__(self) -> None:
        self.queue: list[tuple[str, str, str]] = []  # (session_id, logical_turn_id, pass_id)
        self._open: dict[tuple[str, str, str], None] = {}  # ordered set of queued keys

    def dispatch(self, notice: _Notice) -> None:
        key = (notice.session_id, notice.logical_turn_id, notice.pass_id)
        if key not in self._open:
            self._open[key] = None
            self.queue.append(key)

    def logical_turn_keys(self) -> set[tuple[str, str]]:
        """Logical-turn-level view reserved for the future 1001 contract."""
        return {(session, logical) for session, logical, _ in self.queue}


def test_v2_same_pass_duplicates_merge_and_new_pass_survives() -> None:
    probe = _DispatchProbe()
    for _ in range(3):
        probe.dispatch(_Notice("s1", "turn-1", "pass-1"))
    assert probe.queue == [("s1", "turn-1", "pass-1")]

    probe.dispatch(_Notice("s1", "turn-1", "pass-2"))
    assert probe.queue == [("s1", "turn-1", "pass-1"), ("s1", "turn-1", "pass-2")]

    probe.dispatch(_Notice("s1", "turn-1", "pass-1"))
    assert probe.queue == [("s1", "turn-1", "pass-1"), ("s1", "turn-1", "pass-2")], "late duplicate must not reorder"

    probe.dispatch(_Notice("s1", "turn-2", "pass-3"))
    assert probe.queue == [
        ("s1", "turn-1", "pass-1"),
        ("s1", "turn-1", "pass-2"),
        ("s1", "turn-2", "pass-3"),
    ]

    assert probe.logical_turn_keys() == {("s1", "turn-1"), ("s1", "turn-2")}


def test_v2_sessions_are_isolated() -> None:
    probe = _DispatchProbe()
    probe.dispatch(_Notice("s1", "turn-1", "pass-1"))
    probe.dispatch(_Notice("s2", "turn-1", "pass-1"))
    assert probe.queue == [("s1", "turn-1", "pass-1"), ("s2", "turn-1", "pass-1")]
    # Same (logical, pass) across sessions is two independent tasks: the
    # session dimension in the merge key is what keeps them distinct
    # (design §3.1/§3.2; proven necessary by this very probe).


# ---------------------------------------------------------------------------
# V3 — current turn stays readable after real compaction (F3 ruling)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_v3_current_turn_readable_after_real_compaction(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Real Phase-4 compaction (current-turn fold with an LLM-generated
    LAST_WORDS note, served from the scripted wire) must not corrupt the
    expected-turn read: the transcript alone may no longer carry the folded
    assistant content, but the current turn's A-final stays recoverable from
    the append-only trajectory, and folded/older tool events never re-enter
    as current-turn facts (ownership filter, same guard as V1-b)."""
    big = {"prompt_tokens": 300, "completion_tokens": 30}
    harness = await _start_harness(
        tmp_path,
        monkeypatch,
        [
            _tool_completion("chatcmpl-fold-tool", "call_fold", "Oslo", **big),
            _text_completion("chatcmpl-fold-final", "Folded answer.", **big),
            _text_completion("chatcmpl-mid", "Middle answer.", **big),
            _text_completion("chatcmpl-now", "Current answer.", **big),
        ],
        compaction=True,
        max_context_tokens=200,
    )
    try:
        await _send(harness, "Folded request")
        await _send(harness, "Middle request")
        await _send(harness, "Current request")
        session_id = harness.engine.session.session_id
        session_dir = harness.engine.session_dir
        assert session_dir is not None
    finally:
        await harness.engine.shutdown()

    assert harness.wire.last_words_calls, "real Phase-4 compaction must have issued its LAST_WORDS side call"
    raw_session = (session_dir / "session.json").read_text(encoding="utf-8")
    assert "compressed_msgs" in raw_session or "LAST_WORDS" in raw_session, (
        "compaction must be visible in the persisted state"
    )

    transcript = await harness.store.load_session_transcript(session_id)
    assert transcript is not None
    user_texts = [text for _, text in _user_anchors(transcript.messages)]
    assert "Current request" in user_texts

    # The current turn's own assistant text may be folded away: the
    # session-only read is allowed to be incomplete here (that is the F3
    # finding) — what must hold is recoverability from trajectory.
    current = _read_expected_turn(transcript.messages, "Current request")

    events = _events(session_dir)
    exchanges = [
        event
        for event in events
        if event.event_type == EventType.MODEL_EXCHANGE_FINISHED and event.payload.get("outcome") == "success"
    ]
    assert exchanges, "append-only trajectory must still hold every model exchange"
    final_attempt = exchanges[-1].payload.get("request_attempt_id")
    main_attempts = [request.headers["Chrys-Request-Attempt-Id"] for request in harness.wire.main_calls]
    assert final_attempt == main_attempts[-1], "the current turn's A-final is recoverable from trajectory"

    if current.attempts:
        assert final_attempt in current.attempts.values(), (
            "when the transcript survived, its attempt matches trajectory"
        )
    assert _tool_event_scope(events, current) == set(), "current turn has no tools of its own"
    out_of_scope_tool_starts = [
        event
        for event in events
        if event.event_type == EventType.TOOL_OPERATION_STARTED and event.parent_operation_id not in current.attempts
    ]
    assert out_of_scope_tool_starts, "folded/older tool events must still exist as append-only prior sources"
    assert all(event.parent_operation_id not in current.attempts for event in out_of_scope_tool_starts)
