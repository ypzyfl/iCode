# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""The engine's own lifecycle drives the telemetry flush + close (design R2-4).

The pipeline tests reach this code too, but only as a side effect of their
harness shutting the engine down; none of them asserts what it did. These two
go through the real engine entries and pin both branches:

- a live session: ``shutdown()`` flushes its worker, then closes it;
- the live session deleted (``SessionDelete``): the delete flushes and closes
  the worker, then detaches the engine — it has no session id from then on —
  and the shutdown that follows (app exit after a delete) skips telemetry.

The harness mirrors test_pipeline_delivery.py (scripted wire over the real
engine).
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import json
import os
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from chrys.foundation.config.settings import Settings
from chrys.foundation.events.bus import EventBus
from chrys.foundation.events.types import Error, SessionDelete, SessionDeleted, UserMessage
from chrys.foundation.models.workspace import Workspace
from chrys.kernel import tool
from chrys.service.aixcoding.telemetry.owner import TelemetryOwner, get_telemetry_owner, reset_telemetry_owner_for_tests
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

_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _lookup(city: str) -> str:
    return f"Sunny in {city}, 21 degrees."


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


@dataclass
class _Harness:
    engine: Any
    bus: EventBus
    wire: _Wire
    errors: list[Error]


async def _start_engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> _Harness:
    """A started engine on a scripted wire; the test drives the turn and the shutdown."""
    for key in list(os.environ):
        if key.startswith(("OPENAI_", "CHRYS_")) or key.upper() in {"HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"}:
            monkeypatch.delenv(key)
    monkeypatch.setenv("NO_PROXY", "*")
    monkeypatch.setattr(
        "chrys.orchestration.session_hooks.get_platform",
        lambda: SimpleNamespace(config_dir=tmp_path / "empty-config"),
    )
    wire = _Wire([_text_completion("chatcmpl-final")])
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
    from chrys.orchestration.engine.assembly import assemble_agent_engine

    engine = assemble_agent_engine(
        bus,
        settings=Settings(model_profile=model.id, workspace_change_notice=False, default_approval_mode="bypass"),
        agent_registry=agents,
        model_registry=models,
        state_store=JsonFileStateStore(tmp_path / "sessions"),
        initial_workspace=Workspace.from_cwd(str(tmp_path)),
    )
    await engine.start(agents.get("telemetry-after-turn-slice"))
    return _Harness(engine, bus, wire, errors)


async def _send(harness: _Harness, text: str) -> None:
    await harness.bus.publish(UserMessage(text=text))
    await asyncio.wait_for(harness.engine.turns.turn_state.drain_for_boundary(), timeout=30)
    assert harness.errors == []


def _join(origin: str, request_id: str) -> dict[str, Any]:
    with _OPENER.open(f"{origin}/csas/telemetry/_test/join?requestId={request_id}", timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))  # type: ignore[no-any-return]


@pytest.fixture(autouse=True)
def _fresh_owner() -> None:
    reset_telemetry_owner_for_tests()


@pytest.fixture
def mock_origin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """The single-port mock on a free port; its catalog lets the turn's model pass the filter."""
    from aixcoding.mock.combined import start_combined

    origin, server, _thread = start_combined(port=0, with_telemetry=True)
    monkeypatch.setenv("AIXCODING_TELEMETRY_BASE_URL", origin)
    catalog_dir = tmp_path / "models"
    catalog_dir.mkdir()
    (catalog_dir / "telemetry-model.yaml").write_text("synced_from_server: true\n", encoding="utf-8")
    monkeypatch.setattr("chrys.service.aixcoding.telemetry.filtering.catalog_directory", lambda: catalog_dir)
    yield origin
    server.shutdown()
    server.server_close()


@pytest.fixture
def owner_calls(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str | None]]:
    """Every owner flush/close the engine issues — from a teardown or from
    deleting the live session — in order, each followed by the real call."""
    calls: list[tuple[str, str | None]] = []
    real_flush = TelemetryOwner.flush_session
    real_close = TelemetryOwner.close_session

    async def flush_session(self: TelemetryOwner, session_id: str | None, timeout: float) -> None:
        calls.append(("flush", session_id))
        await real_flush(self, session_id, timeout)

    def close_session(self: TelemetryOwner, session_id: str | None) -> None:
        calls.append(("close", session_id))
        real_close(self, session_id)

    monkeypatch.setattr(TelemetryOwner, "flush_session", flush_session)
    monkeypatch.setattr(TelemetryOwner, "close_session", close_session)
    return calls


@pytest.mark.asyncio
async def test_shutdown_flushes_then_closes_the_session_worker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mock_origin: str, owner_calls: list[tuple[str, str | None]]
) -> None:
    """A live saved session: the engine's teardown flushes its worker first,
    then closes it, and the turn's report has reached the mock by then."""
    harness = await _start_engine(tmp_path, monkeypatch)
    await _send(harness, "Check Paris")
    session_id = harness.engine.session.session_id
    assert session_id is not None
    assert session_id in get_telemetry_owner()._workers  # the turn's notice created the worker

    await harness.engine.shutdown()

    assert owner_calls == [("flush", session_id), ("close", session_id)]
    assert get_telemetry_owner()._workers == {}
    assert _join(mock_origin, harness.wire.main_attempts[0])["llmReport"] is not None
    assert harness.errors == []


@pytest.mark.asyncio
async def test_shutdown_after_deleting_the_current_session_skips_telemetry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mock_origin: str, owner_calls: list[tuple[str, str | None]]
) -> None:
    """Deleting the live session flushes and closes its worker, then detaches
    the engine — it has no session id from then on. The shutdown that follows
    (app exit after a delete) must skip telemetry instead of handing the owner
    a keyless session."""
    harness = await _start_engine(tmp_path, monkeypatch)
    await _send(harness, "Check Paris")
    session_id = harness.engine.session.session_id
    assert session_id is not None
    assert session_id in get_telemetry_owner()._workers
    deleted = asyncio.Event()

    async def on_deleted(_event: SessionDeleted) -> None:
        deleted.set()

    await harness.bus.subscribe(SessionDeleted, on_deleted)

    await harness.bus.publish(SessionDelete(session_id=session_id))
    await asyncio.wait_for(deleted.wait(), timeout=30)

    assert harness.engine.session.session_id is None  # detached: the state this branch exists for
    assert owner_calls == [("flush", session_id), ("close", session_id)]  # the delete drained and closed it
    assert get_telemetry_owner()._workers == {}

    await harness.engine.shutdown()

    assert owner_calls == [("flush", session_id), ("close", session_id)]  # the shutdown added nothing
    assert get_telemetry_owner()._workers == {}
    assert harness.errors == []
