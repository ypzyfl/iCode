# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Real engine turns with isolated model and telemetry HTTP transports."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx

from chrys.foundation.events.types import InvocationRetryAttempt
from chrys.service.profiles.models.schema import API_STYLE_CHAT_COMPLETIONS, ApiStyle, ModelProfile


def mock_provider_profile(
    provider: str,
    *,
    stream: bool,
    http_max_retries: int = 0,
    api_style: ApiStyle = API_STYLE_CHAT_COMPLETIONS,
    chat_options: str = "",
) -> ModelProfile:
    """Return a model profile for *provider* pointing at a fake host."""
    return ModelProfile(
        id=f"mock-{provider}",
        name=f"mock-{provider}",
        provider=provider,
        api_style=api_style,
        model_id="test-model",
        base_url="https://provider.example/v1" if provider != "anthropic" else "https://provider.example",
        api_key="test-key",
        http_max_retries=http_max_retries,
        stream=stream,
        chat_options=chat_options,
    )


async def run_tool_reports(
    tmp_path: Path,
    monkeypatch,
    agent_engine,
    replies,
    *,
    builtins: list[str],
    user_text: str,
    skills=None,
    model=None,
    child_profile=None,
    injection: tuple[int, str] | None = None,
    max_transient_retries: int | None = None,
    retries: list[InvocationRetryAttempt] | None = None,
):
    from chrys.foundation.config.settings import Settings
    from chrys.foundation.events.bus import EventBus
    from chrys.foundation.events.types import Error, InvocationMessage, UserInject, UserMessage
    from chrys.foundation.models.workspace import Workspace
    from chrys.orchestration.aixcoding.telemetry import lifecycle
    from chrys.service.aixcoding.telemetry.delivery import TelemetryDelivery
    from chrys.service.llm import clients as clients_module
    from chrys.service.profiles.agents.registry import AgentProfileRegistry
    from chrys.service.profiles.agents.schema import (
        AgentProfile,
        ApprovalConfig,
        CompactionConfig,
        SkillsConfig,
        SubAgentRef,
        SubAgentsConfig,
        ToolsConfig,
    )
    from chrys.service.profiles.models.registry import ModelProfileRegistry
    from chrys.service.profiles.models.schema import API_STYLE_RESPONSES
    from chrys.service.state.store import JsonFileStateStore

    reports = []
    requests = []
    original_delivery = TelemetryDelivery

    def receive_report(request: httpx.Request) -> httpx.Response:
        reports.append((request.url.path.rsplit("/telemetry/api/v1/", 1)[-1], json.loads(request.content)))
        return httpx.Response(200)

    def isolated_delivery(url, **kwargs):
        client = httpx.AsyncClient(transport=httpx.MockTransport(receive_report))
        return original_delivery(url, client=client, **kwargs)

    async def receive_model(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if injection is not None and len(requests) == injection[0]:
            await bus.publish(UserInject(text=injection[1], injection_id="skill-injection"), raise_handler_errors=True)
        reply = await replies(request) if callable(replies) else replies.pop(0)
        if isinstance(reply, httpx.Response):
            return reply
        if isinstance(reply, dict):
            return httpx.Response(200, json=reply, request=request)
        return httpx.Response(reply.status, headers=list(reply.headers), content=reply.body, request=request)

    monkeypatch.setenv("AIXCODING_EXTENSION_BASE_URL", "https://telemetry.invalid")
    monkeypatch.delenv("AIXCODING_TELEMETRY_DISABLED", raising=False)
    monkeypatch.setattr(lifecycle, "TelemetryDelivery", isolated_delivery)
    provider_http = httpx.AsyncClient(transport=httpx.MockTransport(receive_model))
    monkeypatch.setattr(clients_module, "_build_profile_http_client", lambda *args, **kwargs: provider_http)
    if model is None:
        model = mock_provider_profile(
            "openai", stream=True, api_style=API_STYLE_RESPONSES, chat_options='{"store": true}'
        )
    models = ModelProfileRegistry()
    models.register(model)
    agents = AgentProfileRegistry()
    children = SubAgentsConfig()
    if child_profile is not None:
        agents.register(child_profile)
        children.agents.append(SubAgentRef(child_profile.name))
    bus = EventBus()
    terminal = asyncio.get_running_loop().create_future()

    async def on_error(event: Error) -> None:
        if not terminal.done():
            terminal.set_result(event)

    async def on_message(event: InvocationMessage) -> None:
        if event.is_final and not terminal.done():
            terminal.set_result(event)

    async def on_retry(event: InvocationRetryAttempt) -> None:
        if retries is not None:
            retries.append(event)

    await bus.subscribe(Error, on_error)
    if retries is not None:
        await bus.subscribe(InvocationRetryAttempt, on_retry)
    await bus.subscribe(InvocationMessage, on_message)
    engine = agent_engine(
        bus,
        settings=Settings(
            model_profile=model.id, workspace_change_notice=False, max_transient_retries=max_transient_retries
        ),
        agent_registry=agents,
        model_registry=models,
        initial_workspace=Workspace.from_cwd(str(tmp_path)),
        state_store=JsonFileStateStore(tmp_path / "sessions"),
    )
    profile = AgentProfile(
        name="TelemetryWriter",
        instructions="Use the requested tool.",
        tools=ToolsConfig(builtins=builtins),
        skills=skills or SkillsConfig(auto_load_user_agents_skills=False, auto_load_cwd_agents_skills=False),
        approval=ApprovalConfig(default="auto", overrides={}),
        compaction=CompactionConfig(enabled=False),
        sub_agents=children,
    )
    try:
        await engine.start(profile, workspace=Workspace.from_cwd(str(tmp_path)))
        await bus.publish(UserMessage(text=user_text), raise_handler_errors=True)
        try:
            await asyncio.wait_for(asyncio.shield(terminal), timeout=15)
        except TimeoutError as error:
            raise AssertionError(
                f"Timed out waiting for terminal engine event; model_requests={len(requests)}, report_paths={[path for path, _ in reports]}"
            ) from error
    finally:
        await engine.shutdown()
        await provider_http.aclose()
    return requests, reports, terminal.result()
