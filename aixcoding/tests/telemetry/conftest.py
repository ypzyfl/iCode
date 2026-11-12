# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Local configuration for telemetry tests that start an engine."""

from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from types import SimpleNamespace

import httpx
import pytest


@pytest.fixture
def agent_engine():
    from chrys.orchestration.engine.assembly import assemble_agent_engine

    return assemble_agent_engine


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    import chrys.foundation.platform as platform

    get_platform = platform.get_platform
    isolated = replace(get_platform(), config_dir=tmp_path / "platform-config", data_dir=tmp_path / "platform-config")
    with monkeypatch.context() as patch:
        patch.setattr(platform, "detect_platform", lambda: isolated)
        get_platform.cache_clear()
        yield
    get_platform.cache_clear()


@pytest.fixture
def telemetry_capture(tmp_path, monkeypatch, isolated_config):
    from chrys.kernel.aixcoding import auth
    from chrys.kernel.aixcoding.auth.crypto import MemoryBackend
    from chrys.orchestration.aixcoding.telemetry import lifecycle
    from chrys.service.aixcoding.telemetry.delivery import TelemetryDelivery

    login = auth.LoginSession(environment=auth.Environment.LOCAL, config_dir=tmp_path, backend=MemoryBackend())
    monkeypatch.setattr(auth, "get_login_session", lambda: login)
    monkeypatch.delenv("AIXCODING_TOKEN", raising=False)
    monkeypatch.delenv("AIXCODING_TELEMETRY_DISABLED", raising=False)
    monkeypatch.setenv("AIXCODING_EXTENSION_BASE_URL", "https://telemetry.invalid/csas")
    requests = []
    clients = []
    received = asyncio.Queue()

    def receive(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        received.put_nowait(request)
        return httpx.Response(204)

    def delivery(base_url, **kwargs):
        client = httpx.AsyncClient(transport=httpx.MockTransport(receive))
        clients.append(client)
        return TelemetryDelivery(base_url, client=client, **kwargs)

    monkeypatch.setattr(lifecycle, "TelemetryDelivery", delivery)
    return SimpleNamespace(requests=requests, clients=clients, login=login, received=received)


@pytest.fixture
def telemetry_provider(monkeypatch):
    from chrys.service.llm import clients
    from chrys.service.profiles.models.registry import ModelProfileRegistry
    from chrys.service.profiles.models.schema import ModelProfile

    requests = []
    calls = []
    model = ModelProfile(
        id="telemetry-boundaries",
        name="Telemetry boundaries",
        model_id="fixture",
        provider="openai",
        base_url="https://model.invalid/v1",
        api_key="fixture",
        stream=False,
        http_max_retries=0,
    )
    registry = ModelProfileRegistry()
    registry.register(model)

    def call(call_id, name, arguments):
        calls.append(
            {"id": call_id, "type": "function", "function": {"name": name, "arguments": json.dumps(arguments)}}
        )

    def receive(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        message = {"role": "assistant", "content": "Finished."}
        finish_reason = "stop"
        if calls:
            message = {"role": "assistant", "tool_calls": [calls.pop(0)]}
            finish_reason = "tool_calls"
        return httpx.Response(
            200,
            json={
                "id": f"chatcmpl-{len(requests)}",
                "object": "chat.completion",
                "created": 1,
                "model": "fixture",
                "choices": [{"index": 0, "message": message, "finish_reason": finish_reason}],
            },
        )

    monkeypatch.setattr(
        clients,
        "_build_profile_http_client",
        lambda *args, **kwargs: httpx.AsyncClient(transport=httpx.MockTransport(receive)),
    )
    return SimpleNamespace(model=model, registry=registry, requests=requests, call=call)


@pytest.fixture
def telemetry_engine(tmp_path, telemetry_provider, agent_engine):
    from chrys.foundation.config.settings import Settings
    from chrys.foundation.events.bus import EventBus
    from chrys.foundation.models.workspace import Workspace
    from chrys.service.approval.policy import ApprovalMode
    from chrys.service.profiles.agents.registry import AgentProfileRegistry
    from chrys.service.profiles.agents.schema import (
        AgentProfile,
        ApprovalConfig,
        CompactionConfig,
        SkillsConfig,
        ToolsConfig,
    )
    from chrys.service.state.store import JsonFileStateStore

    profile = AgentProfile(
        name="TelemetryBoundaries",
        instructions="Use the scripted tool.",
        tools=ToolsConfig(builtins=["filesystem.write"]),
        approval=ApprovalConfig(default="auto"),
        compaction=CompactionConfig(enabled=False),
        skills=SkillsConfig(auto_load_user_agents_skills=False, auto_load_cwd_agents_skills=False),
    )
    agents = AgentProfileRegistry()
    agents.register(profile)
    store = JsonFileStateStore(tmp_path / "sessions")
    workspace = Workspace.from_cwd(str(tmp_path))

    def build():
        return agent_engine(
            EventBus(),
            settings=Settings(
                model_profile=telemetry_provider.model.id,
                workspace_change_notice=False,
                max_transient_retries=0,
            ),
            agent_registry=agents,
            model_registry=telemetry_provider.registry,
            state_store=store,
            initial_workspace=workspace,
            initial_approval_mode=ApprovalMode.BYPASS,
        )

    return SimpleNamespace(build=build, profile=profile, agents=agents, workspace=workspace, store=store)
