# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Verify final system-call fields without borrowing another invocation's facts."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from chrys.foundation.trajectory.envelope import ActorRole


async def _system_call(role, profile, session_id, trajectory):
    from chrys.app.features.session_title.updater import SessionTitleUpdater
    from chrys.foundation.events.bus import EventBus
    from chrys.foundation.trajectory.context import side_call_scope
    from chrys.service.approval.judge import ApprovalJudge
    from chrys.service.context.compaction.last_words import LastWordsGenerator
    from chrys.service.llm.side_question import answer_side_question

    with side_call_scope(role, context=trajectory):
        if role == ActorRole.TITLE_GEN:
            updater = SessionTitleUpdater(EventBus(), None)
            try:
                await updater._generate_title(
                    SimpleNamespace(session_dir=None),
                    session_id,
                    "User: hello",
                    profile,
                    existing_title="",
                    trajectory=trajectory,
                )
            finally:
                await updater.shutdown()
        elif role == ActorRole.APPROVAL_JUDGE:
            judge = ApprovalJudge(profile, session_id=f"{session_id}-judge", parent_session_id=session_id)
            try:
                assert (await judge.evaluate("read", "read_file", "read_file", {"path": "file.txt"}, [])).approved
            finally:
                await judge.aclose()
        elif role == ActorRole.COMPACTION:
            generator = LastWordsGenerator(profile, session_id=f"{session_id}-summary", parent_session_id=session_id)
            try:
                from chrys.kernel import Message

                await generator._generate_once([Message("user", ["Summarize."])], max_tokens=1024)
            finally:
                await generator.aclose()
        else:
            await answer_side_question(
                profile, session_id=session_id, session_dir=None, question="Why?", context="History"
            )


@pytest.fixture
def system_probe(tmp_path, monkeypatch, isolated_config):
    from chrys.foundation.events.types import SessionReady
    from chrys.service.aixcoding.telemetry import model
    from chrys.service.aixcoding.telemetry.context import GitInfo, TelemetrySettings, forget_session_sources
    from chrys.service.aixcoding.telemetry.events import TelemetryEvents
    from chrys.service.llm import clients
    from chrys.service.profiles.models.schema import ModelProfile

    profile = ModelProfile(
        id="system-fields",
        name="System fields",
        provider="openai",
        model_id="fixture",
        base_url="https://model.invalid/v1",
        api_key="fixture",
        stream=False,
        http_max_retries=0,
    )
    settings = TelemetrySettings("https://telemetry.invalid", True, True, None, None)
    monkeypatch.setattr(model, "load_settings", lambda: settings)
    monkeypatch.setattr(model, "collect_git_info", lambda cwd: GitInfo(branch=f"branch-{Path(cwd).name}"))
    requests = []
    barrier = asyncio.Event()

    async def receive(request):
        payload = json.loads(request.content)["telemetry"]
        requests.append(payload)
        if payload["eventSubType"] == "system":
            if sum(item["eventSubType"] == "system" for item in requests) == 2:
                barrier.set()
            await asyncio.wait_for(barrier.wait(), 5)
        return httpx.Response(
            200,
            json={
                "id": "fixture",
                "object": "chat.completion",
                "created": 1,
                "model": "fixture",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": '{"approved":true,"reason":"fixture"}'},
                        "finish_reason": "stop",
                    }
                ],
            },
        )

    monkeypatch.setattr(
        clients,
        "_build_profile_http_client",
        lambda *args, **kwargs: httpx.AsyncClient(transport=httpx.MockTransport(receive)),
    )
    events = []

    async def register(index, enabled=True):
        session_id = f"system-fields-{index}"
        workspace = tmp_path / f"project-{index}"
        workspace.mkdir()
        handler = TelemetryEvents(SimpleNamespace(), settings)
        events.append(handler)
        if enabled:
            await handler.session_ready(
                SessionReady(session_id=session_id, primary_cwd=str(workspace), agent_profile=f"Main-{index}")
            )
        return session_id, workspace

    yield SimpleNamespace(profile=profile, requests=requests, register=register)
    for handler in events:
        if handler.session_id:
            forget_session_sources(handler.session_id)
        handler.unregister()


@pytest.mark.parametrize(
    "role", [ActorRole.TITLE_GEN, ActorRole.APPROVAL_JUDGE, ActorRole.COMPACTION, ActorRole.SIDE_QUESTION]
)
@pytest.mark.parametrize(("registered", "matching"), [(True, True), (False, True), (True, False)])
async def test_system_calls_get_only_their_matching_session_fields(system_probe, role, registered, matching):
    from chrys.foundation.models.invocations import InvocationOrigin
    from chrys.kernel.aixcoding.telemetry.context import bind_pass
    from chrys.service.trajectory.session import SessionTrajectory

    async def invoke(index):
        session_id, workspace = await system_probe.register(index, registered)
        trace = SessionTrajectory(session_id=session_id if matching else "unrelated", session_dir=None)
        context = trace.context(turn_id=None if role == ActorRole.TITLE_GEN else f"turn-{index}")
        reset = bind_pass(InvocationOrigin("turn", session_id, f"run-{index}", None), f"pass-{index}")
        try:
            await _system_call(role, system_probe.profile, session_id, context)
        finally:
            reset()
        return session_id, workspace

    sessions = await asyncio.gather(invoke(0), invoke(1))
    payloads = {item["sessionId"]: item for item in system_probe.requests}
    assert len({item["requestId"] for item in payloads.values()}) == 2
    for index, (session_id, workspace) in enumerate(sessions):
        payload = payloads[session_id]
        assert payload["eventSubType"] == "system"
        if registered and matching:
            assert payload["projectName"] == workspace.name
            assert payload["gitBranch"] == f"branch-{workspace.name}"
            assert payload["agentName"] == f"Main-{index}"
        else:
            assert "projectName" not in payload and "gitBranch" not in payload and "agentName" not in payload
        assert ("spanId" in payload) == (role != ActorRole.TITLE_GEN)


@pytest.mark.parametrize("role", [ActorRole.APPROVAL_JUDGE, ActorRole.COMPACTION])
@pytest.mark.parametrize("kind", ["sub_agent", "workflow_node"])
@pytest.mark.parametrize("live_pass", [True, False])
@pytest.mark.parametrize("explicit_facts", [True, False])
async def test_system_calls_use_their_own_pass_instead_of_the_latest_session_source(
    system_probe, role, kind, live_pass, explicit_facts
):
    from chrys.foundation.models.invocations import InvocationOrigin
    from chrys.foundation.trajectory.context import trajectory_scope
    from chrys.kernel import Message
    from chrys.kernel.aixcoding.telemetry.context import bind_pass
    from chrys.service.aixcoding.telemetry.model import for_agent_build
    from chrys.service.llm.clients import create_client
    from chrys.service.llm.one_shot import get_final_response
    from chrys.service.trajectory.session import SessionTrajectory

    async def invoke(index):
        session_id, workspace = await system_probe.register(index)
        trace = SessionTrajectory(session_id=session_id, session_dir=None).context(turn_id=f"turn-{index}")
        parent = InvocationOrigin("turn", session_id, f"root-{index}", None)
        origin = InvocationOrigin(kind, session_id, f"child-{index}", parent)

        async def seed(invocation, name, cwd):
            reset = bind_pass(invocation, invocation.invocation_id)
            client = await for_agent_build(create_client, name, cwd)(system_probe.profile, session_id=session_id)
            try:
                with trajectory_scope(trace):
                    await get_final_response(client, [Message("user", ["Seed context."])], stream=False)
            finally:
                await client.aclose()
                reset()

        await seed(origin, f"Child-{index}", str(workspace))
        await seed(InvocationOrigin(kind, session_id, f"other-{index}", parent), "Other-child", "/other-project")
        reset = bind_pass(origin, origin.invocation_id if live_pass else "different-pass")
        try:
            call = (
                for_agent_build(_system_call, f"Explicit-{index}", "/explicit-project")
                if explicit_facts
                else _system_call
            )
            await call(role, system_probe.profile, session_id, trace)
        finally:
            reset()

    await asyncio.gather(invoke(0), invoke(1))
    payloads = {item["sessionId"]: item for item in system_probe.requests if item["eventSubType"] == "system"}
    for index in range(2):
        payload = payloads[f"system-fields-{index}"]
        if explicit_facts:
            assert payload["agentName"] == f"Explicit-{index}"
            assert payload["projectName"] == "explicit-project"
            assert payload["gitBranch"] == "branch-explicit-project"
        elif live_pass:
            assert payload["agentName"] == f"Child-{index}"
            assert payload["projectName"] == f"project-{index}"
            assert payload["gitBranch"] == f"branch-project-{index}"
        else:
            assert "agentName" not in payload and "projectName" not in payload and "gitBranch" not in payload


@pytest.mark.parametrize(
    "role", [ActorRole.TITLE_GEN, ActorRole.APPROVAL_JUDGE, ActorRole.COMPACTION, ActorRole.SIDE_QUESTION]
)
async def test_unbound_system_calls_do_not_invent_a_child_profile(system_probe, role):
    from chrys.service.trajectory.session import SessionTrajectory

    async def invoke(index):
        session_id, _ = await system_probe.register(index)
        trace = SessionTrajectory(session_id=session_id, session_dir=None).context()
        await _system_call(role, system_probe.profile, session_id, trace)

    await asyncio.gather(invoke(0), invoke(1))
    for index, payload in enumerate(sorted(system_probe.requests, key=lambda item: item["sessionId"])):
        assert payload["projectName"] == f"project-{index}"
        assert payload["gitBranch"] == f"branch-project-{index}"
        if role in (ActorRole.TITLE_GEN, ActorRole.SIDE_QUESTION):
            assert payload["agentName"] == f"Main-{index}"
        else:
            assert "agentName" not in payload
        assert "spanId" not in payload


async def test_system_workspace_fill_still_excludes_installation_project_names(system_probe, monkeypatch):
    from chrys.foundation.models.invocations import InvocationOrigin
    from chrys.kernel.aixcoding.telemetry.context import bind_pass
    from chrys.service.aixcoding.telemetry import context
    from chrys.service.trajectory.session import SessionTrajectory

    sessions = [await system_probe.register(index) for index in range(2)]
    monkeypatch.setattr(
        context,
        "sys",
        SimpleNamespace(
            prefix=str(sessions[0][1]),
            exec_prefix=str(sessions[1][1]),
            executable=context.sys.executable,
            argv=context.sys.argv,
        ),
    )

    async def invoke(index):
        session_id, _ = sessions[index]
        trace = SessionTrajectory(session_id=session_id, session_dir=None).context(turn_id=f"turn-{index}")
        reset = bind_pass(InvocationOrigin("turn", session_id, f"run-{index}", None), f"pass-{index}")
        try:
            await _system_call(ActorRole.COMPACTION, system_probe.profile, session_id, trace)
        finally:
            reset()

    await asyncio.gather(invoke(0), invoke(1))
    for payload in system_probe.requests:
        assert payload["projectName"] == ""
        assert payload["agentName"]
        assert payload["gitBranch"]


def test_pass_source_expires_without_borrowing_a_different_pass(monkeypatch):
    from chrys.foundation.models.invocations import InvocationOrigin
    from chrys.service.aixcoding.telemetry import context

    now = [100.0]
    monkeypatch.setattr(context, "time", SimpleNamespace(monotonic=lambda: now[0]))
    origin = InvocationOrigin("turn", "expiry-session", "expiry-turn", None)
    source = context.ModelSource(
        request_id="expiry-request",
        session_id=origin.session_id,
        span_id="",
        parent_span_id="",
        channel=context.Channel("cli", "icode-tui"),
        agent_name="Code",
        workspace_cwd="/project",
        git=None,
        origin=origin,
        pass_id="live-pass",
    )
    try:
        context.remember_source(source)
        assert context.lookup_pass_source(origin, "live-pass") is source
        assert context.lookup_pass_source(origin, "different-pass") is None
        now[0] = 1900.0
        assert context.lookup_pass_source(origin, "live-pass") is None
    finally:
        context.forget_session_sources(origin.session_id)
