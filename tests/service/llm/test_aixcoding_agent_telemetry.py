# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Agent attribution at the telemetry payload boundary."""

from __future__ import annotations

import pytest

from chrys.aixcoding.context import ChannelContext
from chrys.aixcoding.telemetry.reporters.ai_code import AiCodeReporter
from chrys.aixcoding.telemetry.reporters.tool_detail import ToolDetailReporter
from chrys.foundation.events.types import InvocationToolCallResult, InvocationToolCallStart
from chrys.foundation.models.invocations import InvocationOrigin


@pytest.mark.parametrize("desktop", [False, True])
@pytest.mark.parametrize("name", ["", "Code", "QA"])
@pytest.mark.parametrize("kind", ["turn", "sub_agent", "workflow_node"])
def test_tool_and_code_agent_attribution(monkeypatch, tmp_path, desktop, name, kind):
    monkeypatch.setattr(
        "chrys.aixcoding.context._desktop_channel",
        ChannelContext("desktop", "AgentStudio", "1.0") if desktop else None,
    )
    monkeypatch.setattr("chrys.aixcoding.context._function_name", "desktop-runner")
    origin = InvocationOrigin(kind, "session", "invocation", None)
    start = InvocationToolCallStart(
        origin=origin,
        agent_name=name if kind == "sub_agent" else "",
        agent_profile_name=name if kind != "sub_agent" else "",
        tool_name="write_file",
        args={"path": "demo.py"},
        call_id="call",
        session_id="session",
        workspace_cwd=str(tmp_path),
    )
    result = InvocationToolCallResult(
        origin=origin,
        agent_name=name if kind == "sub_agent" else "",
        agent_profile_name=name if kind != "sub_agent" else "",
        tool_name="write_file",
        call_id="call",
        session_id="session",
        workspace_cwd=str(tmp_path),
        metadata={"file_snapshot": ("", "print(1)\n")},
    )
    saves = []
    codes = []
    tool = ToolDetailReporter(lambda endpoint, payload: saves.append(dict(payload)))
    code = AiCodeReporter(codes.append)

    tool.on_start(start)
    code.on_start(start)
    code.on_result(result, code_status=1, errored=False)

    expected = "desktop-runner" if desktop else name or None
    assert saves[0].get("agentName") == expected
    assert codes[0].get("agentName") == expected


@pytest.mark.parametrize("name", [None, "Code", "QA"])
def test_input_skill_agent_attribution(monkeypatch, name):
    monkeypatch.setattr("chrys.aixcoding.context._desktop_channel", None)
    saves = []
    reporter = ToolDetailReporter(lambda endpoint, payload: saves.append(dict(payload)))

    reporter.record_invocation("review", "session", name)

    assert saves[0].get("agentName") == name


@pytest.mark.parametrize("kind", ["turn", "sub_agent", "workflow_node"])
async def test_tool_event_preserves_profile_without_changing_display_name(kind):
    from chrys.foundation.events.bus import EventBus
    from chrys.service.agent_middleware import SubAgentEventMiddleware, ToolEventMiddleware
    from tests.service.agent_middleware._event_fakes import _ctx
    from tests.support.event_capture import capture_events

    bus = EventBus()
    starts = await capture_events(bus, InvocationToolCallStart)
    results = await capture_events(bus, InvocationToolCallResult)
    origin = InvocationOrigin(kind, "session", "invocation", None)
    if kind == "turn":
        middleware = ToolEventMiddleware(bus, profile_name="QA", session_id="session", origin=origin)
    else:
        middleware = SubAgentEventMiddleware(
            bus,
            agent_name="Friendly label",
            invocation_id="invocation",
            profile_name="QA",
            session_id="session",
            origin=origin,
        )
    context = _ctx("read_file", args={"path": "demo.py"})

    async def run_tool():
        context.result = "done"

    await middleware.process(context, run_tool)

    events = [*starts, *results]
    assert len(events) == 2
    assert all(event.agent_profile_name == "QA" for event in events)
    assert all(event.agent_name == ("" if kind == "turn" else "Friendly label") for event in events)
