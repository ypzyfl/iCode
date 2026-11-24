# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""End-to-end pipeline delivery: real engine turn -> finalizer notice ->
reader/filter/analyzer/reporter -> single-port mock, asserted via join.

The harness mirrors test_precondition_probe.py (scripted wire over the real
engine); the mock is the real single-port combo. Filtering runs against a
sandboxed catalog directory whose profile file carries (or lacks) the
``synced_from_server`` marker — both branches of the fail-closed ruling.
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import json
import os
import urllib.request
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from chrys.foundation.config.settings import Settings
from chrys.foundation.events.bus import EventBus
from chrys.foundation.events.types import Error, UserMessage
from chrys.foundation.models.workspace import Workspace
from chrys.foundation.trajectory.event_types import EventType
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

_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _lookup(city: str) -> str:
    return f"Sunny in {city}, 21 degrees."


def _tool_completion(response_id: str, call_id: str) -> dict[str, Any]:
    return {
        "id": response_id,
        "object": "chat.completion",
        "created": 1_767_225_600,
        "model": "model-test",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Let me check.",
                    "tool_calls": [
                        {
                            "id": call_id,
                            "type": "function",
                            "function": {"name": "lookup", "arguments": json.dumps({"city": "Paris"})},
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }


def _text_completion(response_id: str) -> dict[str, Any]:
    return {
        "id": response_id,
        "object": "chat.completion",
        "created": 1_767_225_600,
        "model": "model-test",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": "Done."}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }


class _Wire:
    def __init__(self, replies: list[dict[str, Any]]) -> None:
        self._replies = list(replies)
        self.main_attempts: list[str] = []
        self.transport = httpx.MockTransport(self._handle)

    async def _handle(self, request: httpx.Request) -> httpx.Response:
        self.main_attempts.append(request.headers["Chrys-Request-Attempt-Id"])
        reply = self._replies.pop(0)
        return httpx.Response(200, json=reply, request=request)


async def _run_turn(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    model_base_url: str | None = None,
    with_state_store: bool = True,
    suppress_save: bool = False,
) -> tuple[str, Path | None, _Wire | None, Any]:
    for key in list(os.environ):
        if key.startswith(("OPENAI_", "CHRYS_")) or key.upper() in {"HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"}:
            monkeypatch.delenv(key)
    monkeypatch.setenv("NO_PROXY", "*")
    monkeypatch.setattr(
        "chrys.orchestration.session_hooks.get_platform",
        lambda: SimpleNamespace(config_dir=tmp_path / "empty-config"),
    )
    if suppress_save:
        from chrys.orchestration.engine.state.session_writer import SessionWriter

        async def _unsaved(self: SessionWriter, **kwargs: Any) -> bool:
            return False

        monkeypatch.setattr(SessionWriter, "save_current_session", _unsaved)

    wire: _Wire | None = None
    if model_base_url is None:
        wire = _Wire([_tool_completion("chatcmpl-tool", "call_lookup_1"), _text_completion("chatcmpl-final")])
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
        base_url=model_base_url or "https://model.example.test",
        http_max_retries=0,
        stream=False,
    )
    models = ModelProfileRegistry()
    models.register(model)
    agents = AgentProfileRegistry()
    agents.register(
        AgentProfile(
            name="telemetry-after-turn-slice",
            instructions="Reply briefly.",
            tools=ToolsConfig(builtins=[]),
            skills=SkillsConfig(auto_load_user_agents_skills=False, auto_load_cwd_agents_skills=False),
            approval=ApprovalConfig(default="auto"),
            compaction=CompactionConfig(enabled=False),
        )
    )
    bus = EventBus()
    errors: list[Error] = []
    await bus.subscribe(Error, errors.append)
    store = JsonFileStateStore(tmp_path / "sessions") if with_state_store else None
    from chrys.orchestration.engine.assembly import assemble_agent_engine

    engine = assemble_agent_engine(
        bus,
        settings=Settings(model_profile=model.id, workspace_change_notice=False, default_approval_mode="bypass"),
        agent_registry=agents,
        model_registry=models,
        state_store=store,
        initial_workspace=Workspace.from_cwd(str(tmp_path)),
    )
    await engine.start(agents.get("telemetry-after-turn-slice"))
    await bus.publish(UserMessage(text="Check Paris"))
    await asyncio.wait_for(engine.turns.turn_state.drain_for_boundary(), timeout=30)
    assert errors == []
    session_id = engine.session.session_id
    session_dir = engine.session.session_dir
    await engine.shutdown()
    if not with_state_store:
        # Real semantics (verified here): without a state store the session dir
        # falls back to the process-global sessions directory — the notice's
        # saved=False (nothing to save into) is what skips the batch, not a
        # None dir. The global fallback must never receive telemetry files.
        assert session_dir is not None
    return session_id, session_dir, wire, store


def _join(origin: str, request_id: str) -> dict[str, Any]:
    with _OPENER.open(f"{origin}/csas/telemetry/_test/join?requestId={request_id}", timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))  # type: ignore[no-any-return]


def _tool_operation_ids(session_dir: Path) -> set[str]:
    result = read_trajectory(trajectory_events_path(session_dir))
    return {event.operation_id for event in result.events if event.event_type == EventType.TOOL_OPERATION_STARTED}


@pytest.mark.asyncio
async def test_pipeline_delivers_turn_to_mock_join(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from aixcoding.mock.combined import start_combined

    from chrys.service.aixcoding.telemetry.owner import get_telemetry_owner

    origin, server, _thread = start_combined(port=0, with_telemetry=True)
    monkeypatch.setenv("AIXCODING_TELEMETRY_BASE_URL", origin)
    catalog_dir = tmp_path / "models"
    catalog_dir.mkdir()
    (catalog_dir / "telemetry-model.yaml").write_text("synced_from_server: true\n", encoding="utf-8")
    monkeypatch.setattr("chrys.service.aixcoding.telemetry.filtering.catalog_directory", lambda: catalog_dir)

    session_id, session_dir, wire, _store = await _run_turn(tmp_path, monkeypatch)
    try:
        await asyncio.wait_for(get_telemetry_owner().flush_session(session_id, timeout=10.0), timeout=15.0)
    finally:
        pass

    a1 = wire.main_attempts[0]
    a2 = wire.main_attempts[1]
    tool_ops = _tool_operation_ids(session_dir)

    first = _join(origin, a1)
    # The engine's model traffic went to the scripted wire, not the mock's
    # chat route, so modelRecord stays None here — its capture closure is
    # covered by the mock contract test (test_combo_routes_telemetry_...).
    assert first["modelRecord"] is None
    assert first["llmReport"] is not None and first["llmReport"]["requestId"] == a1
    assert first["llmReport"]["spanId"]  # span present (logical turn id)
    assert [row["funcId"] for row in first["toolDetails"]] and {
        row["funcId"] for row in first["toolDetails"]
    } <= tool_ops
    assert first["toolDetails"][0]["funcName"] == "lookup"
    assert first["aiCodes"] == []  # lookup produced no mutation: degraded, not fabricated

    second = _join(origin, a2)
    assert second["llmReport"] is not None and second["llmReport"]["requestId"] == a2
    assert second["toolDetails"] == []

    server.shutdown()
    server.server_close()


@pytest.mark.asyncio
async def test_pipeline_skips_batch_when_model_not_server_dispatched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from aixcoding.mock.combined import start_combined

    from chrys.service.aixcoding.telemetry.owner import get_telemetry_owner

    origin, server, _thread = start_combined(port=0, with_telemetry=True)
    monkeypatch.setenv("AIXCODING_TELEMETRY_BASE_URL", origin)
    catalog_dir = tmp_path / "models"
    catalog_dir.mkdir()
    (catalog_dir / "telemetry-model.yaml").write_text("name: telemetry-model\n", encoding="utf-8")  # no marker

    monkeypatch.setattr("chrys.service.aixcoding.telemetry.filtering.catalog_directory", lambda: catalog_dir)

    session_id, _session_dir, wire, _store = await _run_turn(tmp_path, monkeypatch)
    await asyncio.wait_for(get_telemetry_owner().flush_session(session_id, timeout=10.0), timeout=15.0)

    joined = _join(origin, wire.main_attempts[0])
    assert joined["llmReport"] is None
    assert joined["toolDetails"] == []

    server.shutdown()
    server.server_close()


@pytest.mark.asyncio
async def test_real_traffic_join_closes_through_mock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Full-mock slice: the engine's model traffic really hits the combo's
    chat route, so the per-request capture (BR-1: each request records its
    own attempt) and the independent LLM report meet at the same raw id in
    the join view — the report's join-declared success closure, end to end."""
    from aixcoding.mock.combined import start_combined

    from chrys.service.aixcoding.telemetry.owner import get_telemetry_owner

    origin, server, _thread = start_combined(port=0, with_telemetry=True)
    monkeypatch.setenv("AIXCODING_TELEMETRY_BASE_URL", origin)
    catalog_dir = tmp_path / "models"
    catalog_dir.mkdir()
    (catalog_dir / "telemetry-model.yaml").write_text("synced_from_server: true\n", encoding="utf-8")
    monkeypatch.setattr("chrys.service.aixcoding.telemetry.filtering.catalog_directory", lambda: catalog_dir)

    session_id, session_dir, wire, _store = await _run_turn(tmp_path, monkeypatch, model_base_url=f"{origin}/v1")
    assert wire is None  # no scripted transport: traffic went to the mock for real
    await asyncio.wait_for(get_telemetry_owner().flush_session(session_id, timeout=10.0), timeout=15.0)

    result = read_trajectory(trajectory_events_path(session_dir))
    finals = [
        event.payload["request_attempt_id"]
        for event in result.events
        if event.event_type == EventType.MODEL_EXCHANGE_FINISHED and event.payload.get("outcome") == "success"
    ]
    assert len(finals) == 1  # one text-only turn through the mock's fixed reply

    joined = _join(origin, finals[0])
    assert joined["modelRecord"] is not None, "capture hook must have recorded the real request's attempt"
    assert joined["modelRecord"]["requestId"] == finals[0]
    assert joined["llmReport"] is not None and joined["llmReport"]["requestId"] == finals[0]
    assert joined["toolDetails"] == []

    server.shutdown()
    server.server_close()


# ---------------------------------------------------------------------------
# Boundary matrix (design §8 step 6): no hooks / suppressed save / no store
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_boundary_no_hooks_and_distinct_attempts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No hook manager is configured (the harness never installs one), yet the
    notice pipeline runs — telemetry must not depend on hooks (N3 §12.3); and
    the tool turn's two requests carry distinct attempts (A1 != A2)."""
    from aixcoding.mock.combined import start_combined

    from chrys.service.aixcoding.telemetry.owner import get_telemetry_owner

    origin, server, _thread = start_combined(port=0, with_telemetry=True)
    monkeypatch.setenv("AIXCODING_TELEMETRY_BASE_URL", origin)
    catalog_dir = tmp_path / "models"
    catalog_dir.mkdir()
    (catalog_dir / "telemetry-model.yaml").write_text("synced_from_server: true\n", encoding="utf-8")
    monkeypatch.setattr("chrys.service.aixcoding.telemetry.filtering.catalog_directory", lambda: catalog_dir)

    session_id, _session_dir, wire, _engine = await _run_turn(tmp_path, monkeypatch)
    await asyncio.wait_for(get_telemetry_owner().flush_session(session_id, timeout=10.0), timeout=15.0)

    a1, a2 = wire.main_attempts[0], wire.main_attempts[1]
    assert a1 != a2 and len(wire.main_attempts) == 2
    first = _join(origin, a1)
    assert first["llmReport"] is not None  # no hooks, pipeline still delivered
    assert _join(origin, a2)["llmReport"] is not None

    server.shutdown()
    server.server_close()


@pytest.mark.asyncio
async def test_boundary_suppressed_save_skips_notice(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """save=False ⇒ the notice carries saved=False and dispatch skips: nothing
    is reported and, crucially, no stale file is read to fabricate a turn."""
    from aixcoding.mock.combined import start_combined

    from chrys.service.aixcoding.telemetry.owner import get_telemetry_owner

    origin, server, _thread = start_combined(port=0, with_telemetry=True)
    monkeypatch.setenv("AIXCODING_TELEMETRY_BASE_URL", origin)
    catalog_dir = tmp_path / "models"
    catalog_dir.mkdir()
    (catalog_dir / "telemetry-model.yaml").write_text("synced_from_server: true\n", encoding="utf-8")
    monkeypatch.setattr("chrys.service.aixcoding.telemetry.filtering.catalog_directory", lambda: catalog_dir)

    session_id, _session_dir, wire, _engine = await _run_turn(tmp_path, monkeypatch, suppress_save=True)
    await asyncio.wait_for(get_telemetry_owner().flush_session(session_id, timeout=10.0), timeout=15.0)

    joined = _join(origin, wire.main_attempts[0])
    assert joined["llmReport"] is None
    assert joined["toolDetails"] == []

    server.shutdown()
    server.server_close()


@pytest.mark.asyncio
async def test_boundary_no_state_store_skips_notice(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No state store ⇒ no session_dir (the NO_SESSION_DIR trajectory-disabled
    shape from the batch design): the turn still runs, telemetry skips cleanly."""
    from aixcoding.mock.combined import start_combined

    from chrys.service.aixcoding.telemetry.owner import get_telemetry_owner

    origin, server, _thread = start_combined(port=0, with_telemetry=True)
    monkeypatch.setenv("AIXCODING_TELEMETRY_BASE_URL", origin)

    session_id, _session_dir, wire, _engine = await _run_turn(tmp_path, monkeypatch, with_state_store=False)
    owner = get_telemetry_owner()
    assert session_id not in owner._workers  # saved=False notices never enqueue

    joined = _join(origin, wire.main_attempts[0])
    assert joined["llmReport"] is None

    server.shutdown()
    server.server_close()
