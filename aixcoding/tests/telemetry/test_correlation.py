# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Verify source attribution across model responses and tool dispatch."""

from __future__ import annotations

from chrys.foundation.models.invocations import InvocationOrigin
from chrys.foundation.trajectory.metadata import OPERATION_ID_KEY
from chrys.kernel import ChatResponse, Content, Message


def test_tool_operations_keep_sources_when_provider_call_ids_repeat() -> None:
    from chrys.kernel.aixcoding.telemetry.provenance import operation_source, remember_local_source
    from chrys.kernel.loop import _stamp_function_call_operations

    for source in ("request-a", "request-b"):
        call = Content.from_function_call("reused", "read_file", arguments={"path": "fixture"})
        response = ChatResponse(messages=[Message("assistant", [call])])
        remember_local_source(response, source)
        _stamp_function_call_operations(response, [call])
        assert operation_source(call.additional_properties[OPERATION_ID_KEY]) == source


def test_pass_scope_restores_its_parent() -> None:
    from chrys.kernel.aixcoding.telemetry.context import bind_pass, current_pass

    root = InvocationOrigin("turn", "session", "root", None)
    child = InvocationOrigin("sub_agent", "session", "child", root)
    reset_root = bind_pass(root, "root:1")
    try:
        reset_child = bind_pass(child, "child:1")
        try:
            assert current_pass() is not None
            assert current_pass().origin == child
        finally:
            reset_child()
        assert current_pass() is not None
        assert current_pass().origin == root
    finally:
        reset_root()
    assert current_pass() is None


async def test_same_session_hosted_events_keep_their_actual_sources_when_interleaved() -> None:
    import json

    import httpx

    from chrys.foundation.events.types import InvocationToolCallResult, InvocationToolCallStart, SessionReady
    from chrys.foundation.tool_kinds import KIND_MCP
    from chrys.kernel.aixcoding.telemetry.provenance import remember_hosted_source
    from chrys.service.agent_middleware.events.hosted_tools import adapt_hosted_tool
    from chrys.service.aixcoding.telemetry.context import (
        Channel,
        ModelSource,
        TelemetrySettings,
        forget_session_sources,
        remember_source,
    )
    from chrys.service.aixcoding.telemetry.delivery import TelemetryDelivery
    from chrys.service.aixcoding.telemetry.events import TelemetryEvents

    received = []

    def receive(request: httpx.Request) -> httpx.Response:
        received.append((request.url.path.rsplit("/telemetry/api/v1/", 1)[-1], json.loads(request.content)))
        return httpx.Response(200)

    delivery = TelemetryDelivery(
        "https://telemetry.invalid",
        token_provider=lambda: None,
        client=httpx.AsyncClient(transport=httpx.MockTransport(receive)),
    )
    settings = TelemetrySettings("https://telemetry.invalid", True, True, None, None)
    events = TelemetryEvents(delivery, settings)
    await events.session_ready(SessionReady(session_id="shared-session", primary_cwd="/work", agent_profile="Code"))
    origins = [InvocationOrigin("sub_agent", "shared-session", label, None) for label in ("a", "b")]
    sources = [
        ModelSource(
            f"request-{label}",
            "shared-session",
            "turn-span",
            f"parent-{label}",
            Channel("cli", "icode-tui"),
            f"Agent-{label}",
            "/work",
            None,
            origin,
        )
        for label, origin in zip(("a", "b"), origins, strict=True)
    ]
    try:
        for source in sources:
            remember_source(source)
        # Both calls reuse the provider ID. B is published after A's source was
        # registered, which made the old session-latest fallback misattribute B.
        for source, origin in zip(sources, origins, strict=True):
            call = Content.from_mcp_server_tool_call("shared-provider-id", "create_issue", arguments={})
            remember_hosted_source([call], source.request_id)
            view = adapt_hosted_tool(call)
            await events.tool_start(
                InvocationToolCallStart(
                    origin=origin,
                    session_id="shared-session",
                    call_id=f"presentation-{source.pass_id or source.request_id}",
                    provider_hosted=True,
                    provider_call_id="shared-provider-id",
                    tool_name=view.tool_name,
                    tool_kind=KIND_MCP,
                    args=view.arguments,
                    model_source_id=view.model_source_id,
                )
            )
        await events.session_ready(SessionReady(session_id="shared-session", primary_cwd="/work", agent_profile="Code"))
        for source, origin in zip(sources, origins, strict=True):
            result = InvocationToolCallResult(
                origin=origin,
                session_id="shared-session",
                call_id=f"presentation-{source.request_id}",
                provider_hosted=True,
                provider_call_id="shared-provider-id",
                tool_name="create_issue",
            )
            await events.tool_result(result)
            await events.tool_result(result)
        await events.tool_result(
            InvocationToolCallResult(
                origin=origins[0],
                call_id="unseen-presentation",
                provider_hosted=True,
                provider_call_id="unseen-provider",
                tool_name="create_issue",
                duration_ms=7,
            )
        )
    finally:
        await delivery.aclose()
        events.unregister()
        forget_session_sources("shared-session")

    saves = [body for path, body in received if path == "tool-detail/save"]
    assert [body["requestId"] for body in saves] == ["request-a", "request-b"]
    assert [body["parentSpanId"] for body in saves] == ["parent-a", "parent-b"]
    assert [body["agentName"] for body in saves] == ["Agent-a", "Agent-b"]
    assert {body["funcId"] for body in saves} == {"shared-provider-id"}
    updates = [body for path, body in received if path == "tool-detail/update"]
    assert [body["codeStatus"] for body in updates] == [3, 3, 1, 1, 1]
    assert all("executionStartedAt" in body for body in updates[2:4])
    assert updates[-1]["funcId"] == "unseen-provider"
    assert updates[-1]["executionDurationMs"] == 7
    assert "executionStartedAt" not in updates[-1]


async def test_workflow_retry_does_not_re_report_the_tool_from_the_recovered_attempt(
    tmp_path, monkeypatch, isolated_config
) -> None:
    import asyncio
    import json
    from types import ModuleType

    import httpx
    from aixcoding.tests.telemetry._engine import mock_provider_profile
    from aixcoding.tests.telemetry._responses import Script, call_item, resp_message

    from chrys.foundation.config.settings import Settings
    from chrys.foundation.events.types import WorkflowRunAccepted
    from chrys.foundation.platform.files import atomic_write_owner_only_bytes
    from chrys.orchestration.aixcoding.telemetry import lifecycle
    from chrys.orchestration.session_host import ChrysSessionHost
    from chrys.orchestration.workflows import agent_node
    from chrys.service.aixcoding.telemetry.delivery import TelemetryDelivery
    from chrys.service.approval.policy import ApprovalMode
    from chrys.service.llm import clients as clients_module
    from chrys.service.profiles.agents.registry import AgentProfileRegistry
    from chrys.service.profiles.agents.schema import AgentProfile, ApprovalConfig, CompactionConfig, ToolsConfig
    from chrys.service.profiles.models.registry import ModelProfileRegistry
    from chrys.service.profiles.models.schema import API_STYLE_RESPONSES
    from chrys.service.state.store import JsonFileStateStore
    from chrys.service.workflows.discovery import project_workflows_dir

    reports = []
    requests = []
    second_request = asyncio.Event()
    expire = asyncio.Event()
    node_deadline = 3600.0
    original_delivery = TelemetryDelivery

    async def wait_for_node(tasks, *, timeout=None, return_when=asyncio.ALL_COMPLETED):
        if timeout != node_deadline:
            return await asyncio.wait(tasks, timeout=timeout, return_when=return_when)
        tasks = set(tasks)
        deadline = asyncio.create_task(expire.wait())
        try:
            await asyncio.wait({*tasks, deadline}, return_when=asyncio.FIRST_COMPLETED)
        finally:
            deadline.cancel()
            await asyncio.gather(deadline, return_exceptions=True)
            expire.clear()
        done = {task for task in tasks if task.done()}
        return done, tasks - done

    node_asyncio = ModuleType("asyncio")
    node_asyncio.__dict__.update(vars(asyncio), wait=wait_for_node)
    monkeypatch.setattr(agent_node, "asyncio", node_asyncio)

    def receive_report(request: httpx.Request) -> httpx.Response:
        reports.append((request.url.path.rsplit("/telemetry/api/v1/", 1)[-1], json.loads(request.content)))
        return httpx.Response(200)

    def isolated_delivery(url, **kwargs):
        client = httpx.AsyncClient(transport=httpx.MockTransport(receive_report))
        return original_delivery(url, client=client, **kwargs)

    project = tmp_path / "project"
    workflow_file = project_workflows_dir(project) / "review.py"
    atomic_write_owner_only_bytes(
        workflow_file,
        (
            "from chrys.workflows import Retry, WorkflowBuilder\n"
            "wf = WorkflowBuilder('retry')\n"
            f"review = wf.agent('review', profile='Headless', timeout={node_deadline!r}, retry=Retry(max_attempts=2))\n"
            "wf.start(review)\nwf.output(review)\nworkflow = wf.build()\n"
        ).encode(),
    )
    reference = project / "reference.txt"
    reference.write_text("reference", encoding="utf-8")
    encoded = json.dumps({"path": str(reference)})
    call = {**call_item("fc_read", "call_read", encoded), "name": "read_file"}
    first = Script().started()
    first.emit("response.output_item.added", output_index=0, item={**call, "status": "in_progress"})
    first.call_deltas(0, "fc_read", encoded).call_arguments_done(0, "fc_read", encoded)
    first.emit("response.output_item.done", output_index=0, item=call)
    first_reply = first.finished(call).reply()
    final_reply = (
        Script().started().text(0, "msg_done", "reviewed").finished(resp_message("msg_done", "reviewed")).reply()
    )

    async def receive_model(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 2:
            second_request.set()
            await asyncio.Event().wait()
        reply = first_reply if len(requests) == 1 else final_reply
        return httpx.Response(reply.status, headers=list(reply.headers), content=reply.body, request=request)

    monkeypatch.setenv("AIXCODING_EXTENSION_BASE_URL", "https://telemetry.invalid")
    monkeypatch.delenv("AIXCODING_TELEMETRY_DISABLED", raising=False)
    monkeypatch.setattr(lifecycle, "TelemetryDelivery", isolated_delivery)
    provider_http = httpx.AsyncClient(transport=httpx.MockTransport(receive_model))
    monkeypatch.setattr(clients_module, "_build_profile_http_client", lambda *args, **kwargs: provider_http)
    model = mock_provider_profile("openai", stream=True, api_style=API_STYLE_RESPONSES)
    models = ModelProfileRegistry()
    models.register(model)
    agents = AgentProfileRegistry()
    agents.register(
        AgentProfile(
            name="Headless",
            instructions="You are a test assistant.",
            tools=ToolsConfig(builtins=["filesystem.read"]),
            approval=ApprovalConfig(default="require", overrides={}),
            compaction=CompactionConfig(enabled=False),
        )
    )
    host = ChrysSessionHost(
        profile_name="Headless",
        settings=Settings(model_profile=model.id),
        approval_mode=ApprovalMode.BYPASS,
        agent_registry=agents,
        model_registry=models,
        state_store=JsonFileStateStore(tmp_path / "sessions"),
        cwd=str(project),
        allow_user_interaction=False,
    )
    target = host.workflow_target("review")

    async def run_review():
        run_id = ""
        async for event in host.iter_workflow_events(target, input_text="Review the reference."):
            if isinstance(event, WorkflowRunAccepted):
                run_id = event.run_id
        result = host.engine.workflows.result(run_id)
        assert result is not None
        return result

    try:
        preview = await host.preview_workflow(target, trust=True)
        host.confirm_workflow(preview)
        async with asyncio.TaskGroup() as tasks:
            task = tasks.create_task(run_review())
            request_started = tasks.create_task(second_request.wait())
            async with asyncio.timeout(15):
                await asyncio.wait({task, request_started}, return_when=asyncio.FIRST_COMPLETED)
                assert second_request.is_set() and not task.done()
            expire.set()
        result = task.result()
        assert result.outcome.value == "completed"
        assert result.outputs[0].value.text == "reviewed"
    finally:
        await host.shutdown()
        await provider_http.aclose()

    assert len(requests) == 3
    assert [path for path, _ in reports] == ["tool-detail/save", "tool-detail/update", "tool-detail/update"]
    save, pending, finished = (body for _, body in reports)
    assert save["funcId"] == "call_read"
    assert save["requestId"] == json.loads(requests[0].content)["telemetry"]["requestId"]
    assert save["requestId"] != json.loads(requests[2].content)["telemetry"]["requestId"]
    assert [pending["codeStatus"], finished["codeStatus"]] == [3, 1]
