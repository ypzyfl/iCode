# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Desktop envelopes are returned by the real ACP prompt entry point."""

from __future__ import annotations

import asyncio
import json
from uuid import uuid4

import httpx
import pytest
from acp import schema as acp_schema
from acp.helpers import text_block
from acp.utils import serialize_params


@pytest.mark.parametrize("cancelled", [False, True])
async def test_acp_prompt_merges_telemetry_with_chrys_metadata(
    cancelled: bool, tmp_path, monkeypatch, isolated_config, telemetry_engine, telemetry_provider
) -> None:
    from chrys.app.acp.server import ChrysAcpServer
    from chrys.app.acp.session_manager import AcpSessionManager
    from chrys.app.aixcoding.telemetry.acp import prompt_scope
    from chrys.foundation.config.settings_store import load_settings
    from chrys.foundation.events.types import TurnStarted
    from chrys.foundation.models.invocations import InvocationOrigin
    from chrys.kernel import ChatResponse, ChatResponseUpdate, ResponseStream
    from chrys.kernel.aixcoding.telemetry.context import bind_pass
    from chrys.kernel.middleware import ChatContext
    from chrys.orchestration.session_host import Cancelled, EndTurn
    from chrys.service.acp_client.protocol import parse_protocol_json
    from chrys.service.aixcoding.telemetry.context import desktop_prompt, forget_session_sources
    from chrys.service.aixcoding.telemetry.model import TelemetryModelMiddleware
    from chrys.service.approval.policy import ApprovalMode

    observed = {}
    turn_notifications = []

    class Client:
        async def session_update(self, session_id, update, **kwargs) -> None:
            notification = acp_schema.SessionNotification(sessionId=session_id, update=update, **kwargs)
            parse_protocol_json(json.dumps(serialize_params(notification), allow_nan=False).encode("ascii"))

        async def ext_notification(self, method, params) -> None:
            payload = parse_protocol_json(json.dumps(params, allow_nan=False).encode("ascii"))
            if method == "chrys/turn_started":
                turn_notifications.append(payload)

    manager = AcpSessionManager(
        loaded_settings=load_settings(env={}, model_profile=telemetry_provider.model.id),
        profile_name=telemetry_engine.profile.name,
        approval_mode=ApprovalMode.BYPASS,
        process_cwd=str(tmp_path),
        state_store=telemetry_engine.store,
        agent_registry=telemetry_engine.agents,
        model_registry=telemetry_provider.registry,
    )
    server = ChrysAcpServer(manager, initial_vision=True)
    server.on_connect(Client())
    attribution = str(uuid4())
    try:
        session_id = (await server.new_session(cwd=str(tmp_path), mcp_servers=[])).session_id
        host = manager.get(session_id).host

        async def iter_turn_events(_message):
            prompt = desktop_prompt.get()
            assert prompt is not None
            assert prompt.selected_agent == "Selected"

            async def updates():
                yield ChatResponseUpdate()

            stream = ResponseStream(updates(), finalizer=lambda _: ChatResponse(messages=[]))
            context = ChatContext(client=None, messages=[], options=None, stream=True)

            async def send():
                context.result = stream

            reset = bind_pass(InvocationOrigin("turn", session_id, "turn", None), "pass-1")
            try:
                await TelemetryModelMiddleware(session_id, None).process(context, send)
                observed.update(context.options["extra_body"]["telemetry"])
                # A deferred finalizer can run under another prompt's context.
                with prompt_scope(session_id, {}) as other:
                    await stream.get_final_response()
                    assert other.latest is None
            finally:
                reset()
                forget_session_sources(session_id)
            yield TurnStarted(turn_id="1" * 32, turn_number=1, session_id=session_id)
            host._last_turn_outcome = Cancelled() if cancelled else EndTurn()

        monkeypatch.setattr(host, "iter_turn_events", iter_turn_events)
        response = await server.prompt(
            [text_block("hello")],
            session_id=session_id,
            **{
                "agent-studio.dev/ide-name": {"schemaVersion": 1, "ideName": "studio"},
                "agent-studio.dev/selected-agent": {
                    "schemaVersion": 1,
                    "agentName": "Selected",
                    "agentMarketSkillId": "id",
                },
                "agent-studio.dev/response-attribution": {"schemaVersion": 1, "spanId": attribution},
            },
        )
    finally:
        await manager.shutdown()
    assert response.stop_reason == ("cancelled" if cancelled else "end_turn")
    assert response.field_meta is not None
    assert response.field_meta["chrys"]["turnId"] == "1" * 32
    (started,) = turn_notifications
    assert started["sessionId"] == session_id
    assert started["turnId"] == response.field_meta["chrys"]["turnId"]
    assert observed["channelType"] == "desktop"
    assert observed["sessionId"] == session_id
    request_id = observed["requestId"]
    assert response.field_meta["agent-studio.dev/telemetry"] == {
        "schemaVersion": 1,
        "requestId": request_id,
    }
    assert response.field_meta["agent-studio.dev/final-model-identity"] == {
        "schemaVersion": 1,
        "spanId": attribution,
        "requestId": request_id,
        "source": "model_request_id",
    }
    assert desktop_prompt.get() is None


async def test_two_real_acp_sessions_report_their_own_model_and_selected_agent(
    tmp_path, monkeypatch, isolated_config
) -> None:
    from chrys.app.acp.server import ChrysAcpServer
    from chrys.app.acp.session_manager import AcpSessionManager
    from chrys.foundation.config.settings_store import load_settings
    from chrys.orchestration.aixcoding.telemetry import lifecycle
    from chrys.service.aixcoding.telemetry.delivery import TelemetryDelivery
    from chrys.service.approval.policy import ApprovalMode
    from chrys.service.llm import clients
    from chrys.service.profiles.agents.registry import AgentProfileRegistry
    from chrys.service.profiles.agents.schema import AgentProfile, CompactionConfig, SkillsConfig, ToolsConfig
    from chrys.service.profiles.models.registry import ModelProfileRegistry
    from chrys.service.profiles.models.schema import ModelProfile
    from chrys.service.state.store import JsonFileStateStore

    class Client:
        async def session_update(self, *args, **kwargs) -> None:
            pass

        async def ext_notification(self, *args, **kwargs) -> None:
            pass

    model_requests = {}
    system_requests = []
    reports = {}
    both_requests_started = asyncio.Event()
    both_system_requests_seen = asyncio.Event()

    def receive_report(request):
        assert request.url.path.endswith("/tool-detail/save")
        report = json.loads(request.content)
        reports.setdefault(report["sessionId"], []).append(report)
        return httpx.Response(200)

    async def receive_model(request):
        telemetry = json.loads(request.content)["telemetry"]
        if telemetry["eventSubType"] == "system":
            system_requests.append(telemetry)
            if len({row["sessionId"] for row in system_requests}) == 2:
                both_system_requests_seen.set()
        else:
            assert telemetry["sessionId"] not in model_requests
            model_requests[telemetry["sessionId"]] = telemetry
            if len(model_requests) == 2:
                both_requests_started.set()
            await asyncio.wait_for(both_requests_started.wait(), timeout=10)
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "created": 1767225600,
                "model": "test",
                "choices": [
                    {"index": 0, "message": {"role": "assistant", "content": "Done."}, "finish_reason": "stop"}
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12},
            },
        )

    monkeypatch.setenv("AIXCODING_EXTENSION_BASE_URL", "https://telemetry.invalid")
    monkeypatch.delenv("AIXCODING_TELEMETRY_DISABLED", raising=False)
    monkeypatch.setattr(
        lifecycle,
        "TelemetryDelivery",
        lambda url, **kwargs: TelemetryDelivery(
            url, client=httpx.AsyncClient(transport=httpx.MockTransport(receive_report)), **kwargs
        ),
    )
    monkeypatch.setattr(
        clients,
        "_build_profile_http_client",
        lambda *args, **kwargs: httpx.AsyncClient(transport=httpx.MockTransport(receive_model)),
    )
    models = ModelProfileRegistry()
    model = ModelProfile(
        id="acp-model",
        name="Test",
        provider="openai",
        model_id="test",
        base_url="https://model.invalid/v1",
        api_key="test-key",
        stream=False,
        http_max_retries=0,
    )
    models.register(model)
    agents = AgentProfileRegistry()
    agents.register(
        AgentProfile(
            name="ACPReporter",
            instructions="Reply briefly.",
            tools=ToolsConfig(builtins=[]),
            skills=SkillsConfig(auto_load_user_agents_skills=False, auto_load_cwd_agents_skills=False),
            compaction=CompactionConfig(enabled=False),
        )
    )
    manager = AcpSessionManager(
        loaded_settings=load_settings(env={}, model_profile=model.id, session_title_auto=True),
        profile_name="ACPReporter",
        approval_mode=ApprovalMode.BYPASS,
        process_cwd=str(tmp_path),
        state_store=JsonFileStateStore(tmp_path / "sessions"),
        agent_registry=agents,
        model_registry=models,
    )
    server = ChrysAcpServer(manager, initial_vision=False)
    server.on_connect(Client())

    async def prompt(session_id: str, label: str):
        return await server.prompt(
            [text_block("hello")],
            session_id=session_id,
            **{
                "agent-studio.dev/ide-name": {"schemaVersion": 1, "ideName": "studio"},
                "agent-studio.dev/ide-version": {"schemaVersion": 1, "ideVersion": label},
                "agent-studio.dev/function-name": {"schemaVersion": 1, "functionName": f"runner-{label}"},
                "agent-studio.dev/selected-agent": {
                    "schemaVersion": 1,
                    "agentName": f"selected-{label}",
                    "agentMarketSkillId": f"market-{label}",
                },
            },
        )

    try:
        labels = ("one", "two")
        ids = [(await server.new_session(cwd=str(tmp_path), mcp_servers=[])).session_id for _ in labels]
        responses = await asyncio.gather(
            *(prompt(session_id, label) for session_id, label in zip(ids, labels, strict=True))
        )
        await asyncio.wait_for(both_system_requests_seen.wait(), timeout=5)
    finally:
        await manager.shutdown()

    assert set(reports) == set(model_requests) == set(ids)
    assert len({payload["requestId"] for payload in model_requests.values()}) == 2
    assert {payload["sessionId"] for payload in system_requests} == set(ids)
    for session_id, label, response in zip(ids, labels, responses, strict=True):
        request = model_requests[session_id]
        assert response.stop_reason == "end_turn"
        assert response.field_meta is not None
        assert response.field_meta["chrys"]["turnId"]
        assert response.field_meta["agent-studio.dev/telemetry"]["requestId"] == request["requestId"]
        assert request["channelType"] == "desktop"
        assert request["channelVersion"] == label
        assert "agentName" not in request
        (report,) = reports[session_id]
        assert report["funcType"] == 1001
        assert report["funcName"] == f"selected-{label}"
        assert report["agentName"] == f"runner-{label}"
        assert report["channelName"] == "studio"
        assert report["channelVersion"] == label
        assert report["requestId"] == request["requestId"]
        assert report["spanId"] == request["spanId"]
        assert "agentMarketSkillId" not in report
