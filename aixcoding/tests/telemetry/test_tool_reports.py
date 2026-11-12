# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Recorded 0.28.0 contracts for independent tool telemetry reports."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import pytest
from aixcoding.tests.telemetry._engine import mock_provider_profile, run_tool_reports
from aixcoding.tests.telemetry._responses import Script, call_item, mcp_item, resp_message


def test_consecutive_edits_match_recorded_reports() -> None:
    from chrys.service.aixcoding.telemetry.reporters import ToolStart, code_save, tool_finished, tool_started

    fixture = Path(__file__).with_name("fixtures") / "sdk-retry-and-repeated-edit.json"
    recorded = json.loads(fixture.read_text(encoding="utf-8"))["old_reports"]
    common = {"pluginVersion": "0.28.0", "channelType": "cli", "channelName": "icode", "projectName": "old-work"}
    actual = []
    for index, (before, after) in enumerate((("alpha", "beta"), ("beta", "alpha"))):
        start = ToolStart(
            session_id="probe-session",
            call_id=f"provider-{index}",
            tool_name="edit_file",
            tool_kind="filesystem.write",
            args={"path": "/probe/old-work/example.py", "old_string": before, "new_string": "pre-approval"},
            workspace_cwd="/probe/old-work",
            agent_name="Code",
            request_id="<requestId-1>",
            parent_span_id="<parentSpanId-2>",
            started_at="<timestamp>",
        )
        metadata = {"file_snapshot": (before + "\n", after + "\n"), "file_mutation_op": "modify"}
        actual.extend(tool_started(start, common=common))
        actual.append(tool_finished(start, metadata, duration_ms=0, finished_at="<timestamp>"))
        actual.append(code_save(start, metadata, common=common, report_id=f"<reportId-{3 + index}>"))
    assert [
        {"path": f"/csas/telemetry/api/v1/{report.endpoint}", "body": report.payload}
        for report in actual
        if report is not None
    ] == recorded


def test_failure_uses_structured_metadata_and_preserves_missing_fields() -> None:
    from chrys.service.aixcoding.telemetry.reporters import ToolStart, code_save, tool_finished, tool_started

    start = ToolStart("s", "local", "write_file", "filesystem.write", {"path": "new.py"}, started_at="start")
    save, pending = tool_started(start, common={}, full_mode=False)
    assert save.payload == {
        "funcId": "local",
        "funcName": "write_file",
        "funcType": 3,
        "sessionId": "s",
        "fileName": "new.py",
    }
    assert pending.payload["codeStatus"] == 3
    metadata = {"shell_timed_out": True}
    failed = tool_finished(start, metadata, duration_ms=9, result="Error: timed out")
    assert failed.payload == {
        "funcId": "local",
        "funcName": "write_file",
        "codeStatus": 2,
        "status": 0,
        "executionDurationMs": 9,
        "executionStartedAt": "start",
        "failureType": "timeout",
        "funcErrorMessage": "Error: timed out",
    }
    assert code_save(start, metadata, common={}) is None


def test_replace_all_tracks_each_range_and_manual_approval() -> None:
    from chrys.service.aixcoding.telemetry.reporters import ToolStart, code_save

    start = ToolStart(
        "s",
        "op",
        "edit_file",
        "filesystem.write",
        {"path": r"C:\repo\file.py", "old_string": "old", "new_string": "new", "replace_all": True},
        workspace_cwd=r"C:\repo",
    )
    metadata = {"file_snapshot": ("old\r\nkeep\r\nold\r\n", "new\r\nkeep\r\nnew\r\n")}
    report = code_save(start, metadata, common={}, manually_approved=True, report_id="id")

    assert report is not None
    assert report.payload["filepath"] == "file.py"
    assert report.payload["codeStatus"] == 5
    assert report.payload["blocks"] == [
        {"snippet": "new", "rangeStart": 1, "rangeEnd": 1},
        {"snippet": "new", "rangeStart": 3, "rangeEnd": 3},
    ]


def _call_reply(tool_name: str, args: dict[str, str], *, item_suffix: str = ""):
    item_id = f"fc_{tool_name}{item_suffix}"
    provider_id = f"call_{tool_name}"
    encoded = json.dumps(args)
    item = {**call_item(item_id, provider_id, encoded), "name": tool_name}
    script = Script().started()
    script.emit("response.output_item.added", output_index=0, item={**item, "status": "in_progress"})
    script.call_deltas(0, item_id, encoded).call_arguments_done(0, item_id, encoded)
    script.emit("response.output_item.done", output_index=0, item=item)
    return script.finished(item).reply()


def _done_reply():
    return Script().started().text(0, "msg_done", "Done.").finished(resp_message("msg_done", "Done.")).reply()


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
async def test_other_model_protocols_send_the_legacy_telemetry_body(
    tmp_path, monkeypatch, agent_engine, provider
) -> None:
    from uuid import UUID

    from chrys.foundation.events.types import InvocationMessage

    replies = {
        "openai": {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 1767225600,
            "model": "test-model",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "Done."}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12},
        },
        "anthropic": {
            "id": "msg-test",
            "type": "message",
            "role": "assistant",
            "model": "test-model",
            "content": [{"type": "text", "text": "Done."}],
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {"input_tokens": 10, "output_tokens": 2},
        },
    }
    requests, reports, terminal = await run_tool_reports(
        tmp_path,
        monkeypatch,
        agent_engine,
        [replies[provider]],
        builtins=[],
        user_text="Say done",
        model=mock_provider_profile(provider, stream=False),
    )
    assert isinstance(terminal, InvocationMessage) and terminal.text == "Done."
    assert reports == []
    (request,) = requests
    assert request.method == "POST"
    assert request.url.path == {"openai": "/v1/chat/completions", "anthropic": "/v1/messages"}[provider]
    telemetry = json.loads(request.content)["telemetry"]
    assert UUID(telemetry.pop("requestId")).version == 4
    assert UUID(telemetry.pop("spanId")).version == 5
    from chrys import __version__

    assert telemetry == {
        "sessionId": terminal.origin.session_id,
        "eventType": "llm",
        "eventSubType": "agent",
        "channelType": "cli",
        "channelName": "icode",
        "pluginVersion": __version__,
        "agentName": "TelemetryWriter",
        "projectName": tmp_path.name,
    }


async def test_engine_edit_reports_match_the_old_snapshot_and_correlation_contract(
    tmp_path: Path, monkeypatch, agent_engine
) -> None:
    from chrys.foundation.events.types import InvocationMessage

    target = tmp_path / "sample.py"
    target.write_text("alpha\n", encoding="utf-8")
    args = {"path": str(target), "old_string": "alpha", "new_string": "beta"}
    reverse = {"path": str(target), "old_string": "beta", "new_string": "alpha"}
    requests, reports, terminal = await run_tool_reports(
        tmp_path,
        monkeypatch,
        agent_engine,
        [_call_reply("edit_file", args), _call_reply("edit_file", reverse, item_suffix="_next"), _done_reply()],
        builtins=["filesystem.write"],
        user_text="Edit the file",
    )

    assert isinstance(terminal, InvocationMessage) and terminal.text == "Done."
    assert target.read_text(encoding="utf-8") == "alpha\n"
    assert [path for path, _ in reports] == [
        "tool-detail/save",
        "tool-detail/update",
        "tool-detail/update",
        "tool-detail/save",
        "tool-detail/update",
        "tool-detail/update",
        "ai-code/save",
        "ai-code/save",
    ]
    request_ids = [json.loads(request.content)["telemetry"]["requestId"] for request in requests]
    assert len(set(request_ids)) == len(request_ids) == 3
    for index, edit in enumerate((args, reverse)):
        save, pending, finished = (body for _, body in reports[3 * index : 3 * index + 3])
        code = reports[6 + index][1]
        assert save["funcId"] == pending["funcId"] == finished["funcId"] == "call_edit_file"
        assert save["requestId"] == code["requestId"] == request_ids[index]
        assert save["value"] == json.dumps({**edit, "replace_all": False})
        assert save["fileName"] == code["filepath"] == "sample.py"
        assert save["agentName"] == "TelemetryWriter"
        assert pending["codeStatus"] == 3
        assert finished["codeStatus"] == finished["status"] == code["codeStatus"] == 1
        assert {key: finished[key] for key in ("originalLines", "addedLines", "deletedLines")} == {
            "originalLines": 1,
            "addedLines": 1,
            "deletedLines": 1,
        }
        assert code["blocks"] == [{"snippet": edit["new_string"], "rangeStart": 1, "rangeEnd": 1}]


async def test_engine_reports_slash_and_model_skill_usage_with_the_old_dimensions(
    tmp_path: Path, monkeypatch, agent_engine
) -> None:
    from chrys.foundation.events.types import InvocationMessage
    from chrys.service.profiles.agents.schema import SkillConfig, SkillsConfig

    skills = SkillsConfig(
        inline=[SkillConfig(name="review", description="Review files", instructions="Review carefully.")],
        auto_load_user_agents_skills=False,
        auto_load_cwd_agents_skills=False,
    )
    requests, reports, terminal = await run_tool_reports(
        tmp_path,
        monkeypatch,
        agent_engine,
        [_call_reply("load_skill", {"skill_name": "review"}), _done_reply()],
        builtins=[],
        user_text="/review focus on auth",
        skills=skills,
    )

    assert isinstance(terminal, InvocationMessage) and terminal.text == "Done."
    assert [path for path, _ in reports] == [
        "tool-detail/save",
        "tool-detail/save",
        "tool-detail/update",
        "tool-detail/save",
        "tool-detail/update",
    ]
    slash, tool_save, pending, skill_usage, finished = (body for _, body in reports)
    assert slash["funcName"] == "review"
    assert slash["funcType"] == 0
    assert "funcId" not in slash
    assert "requestId" not in slash
    assert tool_save["funcName"] == "load_skill"
    assert tool_save["funcType"] == 3
    assert tool_save["value"] == "review"
    assert pending["codeStatus"] == 3
    assert skill_usage["funcName"] == "review"
    assert skill_usage["funcType"] == 0
    assert "funcId" not in skill_usage
    assert skill_usage["requestId"] == json.loads(requests[0].content)["telemetry"]["requestId"]
    assert finished["codeStatus"] == 1


@pytest.mark.parametrize("inject_on_request", [1, 2])
async def test_appended_slash_skill_reports_once_and_reaches_next_model_request(
    tmp_path: Path, monkeypatch, agent_engine, isolated_config, inject_on_request: int
) -> None:
    from chrys.foundation.events.types import InvocationMessage
    from chrys.service.profiles.agents.schema import SkillConfig, SkillsConfig

    target = tmp_path / "notes.txt"
    target.write_text("notes", encoding="utf-8")
    skills = SkillsConfig(
        inline=[SkillConfig(name="review", description="Review files", instructions="Inspect the appended notes.")],
        auto_load_user_agents_skills=False,
        auto_load_cwd_agents_skills=False,
    )
    requests, reports, terminal = await run_tool_reports(
        tmp_path,
        monkeypatch,
        agent_engine,
        [
            _call_reply("read_file", {"path": str(target)}),
            _call_reply("read_file", {"path": str(target)}, item_suffix="_next"),
            _done_reply(),
        ],
        builtins=["filesystem.read"],
        user_text="Read the file",
        skills=skills,
        injection=(inject_on_request, "/review review after reading"),
    )

    assert isinstance(terminal, InvocationMessage) and terminal.text == "Done."
    next_request = requests[inject_on_request]
    assert b"review after reading" in next_request.content
    assert b"[Skill Reference] User explicitly invoked a skill: review" in next_request.content
    [(path, usage)] = [(path, body) for path, body in reports if body.get("funcType") == 0]
    assert path == "tool-detail/save"
    assert usage["funcName"] == "review"
    assert usage["sessionId"] == terminal.origin.session_id
    assert usage["projectName"] == tmp_path.name
    assert usage["agentName"] == "TelemetryWriter"
    assert "funcId" not in usage and "requestId" not in usage
    if inject_on_request == 1:
        assert "spanId" not in usage
    else:
        assert usage["spanId"] == json.loads(requests[0].content)["telemetry"]["spanId"]


async def test_long_lived_model_client_refreshes_git_fields_after_cache_expiry(
    tmp_path: Path, monkeypatch, agent_engine, isolated_config
) -> None:
    from types import SimpleNamespace

    from chrys.foundation.events.types import InvocationMessage
    from chrys.service.aixcoding.telemetry import context

    clock = 100.0
    revision = "before"
    monkeypatch.setattr(context, "time", SimpleNamespace(monotonic=lambda: clock))
    monkeypatch.setattr(context, "_collect_git", lambda _cwd: context.GitInfo(revision=revision))
    target = tmp_path / "notes.txt"
    target.write_text("notes", encoding="utf-8")
    replies = [
        _call_reply("read_file", {"path": str(target)}),
        _call_reply("read_file", {"path": str(target)}, item_suffix="_next"),
        _call_reply("read_file", {"path": str(target)}, item_suffix="_later"),
        _done_reply(),
    ]

    async def respond(_request):
        nonlocal clock, revision
        revision = "after"
        clock += 151
        return replies.pop(0)

    requests, reports, terminal = await run_tool_reports(
        tmp_path, monkeypatch, agent_engine, respond, builtins=["filesystem.read"], user_text="Read three times"
    )
    assert isinstance(terminal, InvocationMessage) and terminal.text == "Done."
    assert [json.loads(request.content)["telemetry"]["gitRevision"] for request in requests] == [
        "before",
        "before",
        "after",
        "after",
    ]
    assert [body["gitRevision"] for path, body in reports if path == "tool-detail/save"] == [
        "before",
        "before",
        "after",
    ]


async def test_hosted_report_delayed_behind_a_local_call_keeps_the_observing_request(
    tmp_path: Path, monkeypatch, agent_engine
) -> None:
    from chrys.foundation.events.types import InvocationMessage

    reference = tmp_path / "reference.txt"
    reference.write_text("reference", encoding="utf-8")
    encoded = json.dumps({"path": str(reference)})
    local = {**call_item("fc_read", "call_read", encoded), "name": "read_file"}
    hosted = mcp_item("mcp_delayed")
    script = Script().started()
    script.emit("response.output_item.added", output_index=0, item={**local, "status": "in_progress"})
    script.call_deltas(0, "fc_read", encoded).call_arguments_done(0, "fc_read", encoded)
    script.emit("response.output_item.done", output_index=0, item=local)
    script.hosted(1, hosted).finished(local, hosted)
    requests, reports, terminal = await run_tool_reports(
        tmp_path,
        monkeypatch,
        agent_engine,
        [script.reply(), _done_reply()],
        builtins=["filesystem.read"],
        user_text="Read and create",
    )

    assert isinstance(terminal, InvocationMessage) and terminal.text == "Done."
    saves = [body for path, body in reports if path == "tool-detail/save"]
    assert [body["funcId"] for body in saves] == ["call_read", "mcp_delayed"]
    request_id = json.loads(requests[0].content)["telemetry"]["requestId"]
    assert [body["requestId"] for body in saves] == [request_id, request_id]
    assert [body["codeStatus"] for path, body in reports if path == "tool-detail/update"] == [3, 3, 1, 1]


async def test_concurrent_child_reports_with_one_provider_id_follow_their_own_requests(
    tmp_path: Path, monkeypatch, agent_engine
) -> None:
    from chrys.foundation.events.types import InvocationMessage
    from chrys.service.profiles.agents.schema import AgentProfile, CompactionConfig, SkillsConfig, ToolsConfig

    files = [tmp_path / "left.txt", tmp_path / "right.txt"]
    for path in files:
        path.write_text(path.stem, encoding="utf-8")
    child_name = "TelemetryReader"
    children_started = asyncio.Event()
    child_requests = {}
    routes = set()
    main_calls = 0

    async def respond(request: httpx.Request):
        body = json.loads(request.content)
        telemetry = body["telemetry"]
        if telemetry["agentName"] == child_name:
            route = request.headers["x-session-id"]
            if route in routes:
                return _done_reply()
            routes.add(route)
            inputs = json.dumps(body["input"])
            (path,) = [path for path in files if path.name in inputs]
            child_requests[path.name] = telemetry
            if len(child_requests) == 2:
                children_started.set()
            await asyncio.wait_for(children_started.wait(), timeout=10)
            return _call_reply("read_file", {"path": str(path)})

        nonlocal main_calls
        main_calls += 1
        if main_calls != 1:
            return _done_reply()
        script = Script().started()
        calls = []
        for index, path in enumerate(files):
            item_id = f"fc_child_{index}"
            args = json.dumps({"prompt": f"Read {path.name}."})
            call = {**call_item(item_id, f"call_child_{index}", args), "name": child_name}
            script.emit("response.output_item.added", output_index=index, item={**call, "status": "in_progress"})
            script.call_deltas(index, item_id, args).call_arguments_done(index, item_id, args)
            script.emit("response.output_item.done", output_index=index, item=call)
            calls.append(call)
        return script.finished(*calls).reply()

    child = AgentProfile(
        name=child_name,
        instructions="Read the requested file.",
        tools=ToolsConfig(builtins=["filesystem.read"]),
        skills=SkillsConfig(auto_load_user_agents_skills=False, auto_load_cwd_agents_skills=False),
        compaction=CompactionConfig(enabled=False),
    )
    _, reports, terminal = await run_tool_reports(
        tmp_path, monkeypatch, agent_engine, respond, builtins=[], user_text="Delegate both reads", child_profile=child
    )
    assert isinstance(terminal, InvocationMessage) and terminal.text == "Done."
    assert len(routes) == len(child_requests) == 2
    assert {request["sessionId"] for request in child_requests.values()} == {terminal.origin.session_id}
    assert len({request["requestId"] for request in child_requests.values()}) == 2
    child_saves = [body for path, body in reports if path == "tool-detail/save" and body["funcName"] == "read_file"]
    assert len(child_saves) == 2
    assert {body["funcId"] for body in child_saves} == {"call_read_file"}
    assert {body["fileName"]: body["requestId"] for body in child_saves} == {
        name: request["requestId"] for name, request in child_requests.items()
    }
    assert sorted(
        body["codeStatus"]
        for path, body in reports
        if path == "tool-detail/update" and body["funcId"] == "call_read_file"
    ) == [1, 1, 3, 3]
