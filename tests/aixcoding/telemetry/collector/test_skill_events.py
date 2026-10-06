# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Skill trigger event tests (scenarios ported from the TS
``skill-events.test.ts``; contract §3.4, M5 plan §6.2)."""

from __future__ import annotations

import json
from typing import Any

from chrys.aixcoding.telemetry.collector.analysis.context import EventCommonContext, ReportAttribution
from chrys.aixcoding.telemetry.collector.analysis.git_context import GitRepositoryInfo
from chrys.aixcoding.telemetry.collector.analysis.history import expand_history
from chrys.aixcoding.telemetry.collector.analysis.index import SessionRevisionInput, analyze_session_revision
from chrys.aixcoding.telemetry.collector.analysis.skill_events import build_skill_events
from chrys.aixcoding.telemetry.collector.analysis.turns import TurnSegment, slice_turn_segments

SESSION_ID = "4201eebc-ca45-4328-8882-272f3d7c41cb"

CONTEXT = EventCommonContext(
    session_id=SESSION_ID,
    attribution=ReportAttribution(channel_type="desktop", channel_name="aixcoding-desktop"),
    product_name="proj",
    project_name="my-project",
    plugin_version="0.28.0",
    primary_cwd="D:\\repo",
    git=GitRepositoryInfo(
        remote_url="https://cnb.boecy.cn/team/proj",
        revision="rev-1",
        branch="main",
        user_name="dev",
        user_email="dev@example.com",
        owner="team",
        repo="proj",
    ),
)


def user_message(text: str, properties: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "type": "message",
        "role": "user",
        "contents": [{"type": "text", "text": text, "additional_properties": {}}],
        "additional_properties": properties if properties is not None else {},
    }


def assistant_message(contents: list[Any], properties: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "type": "message",
        "role": "assistant",
        "contents": contents,
        "additional_properties": properties if properties is not None else {},
    }


def tool_message(contents: list[Any]) -> dict[str, Any]:
    return {"type": "message", "role": "tool", "contents": contents, "additional_properties": {}}


def function_call(
    call_id: str,
    name: str,
    call_arguments: Any,
    content_properties: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "type": "function_call",
        "call_id": call_id,
        "name": name,
        "arguments": call_arguments,
        "additional_properties": content_properties if content_properties is not None else {},
    }


def function_result(call_id: str) -> dict[str, Any]:
    return {"type": "function_result", "call_id": call_id, "result": "ok", "additional_properties": {}}


def turn_marker(index: int) -> dict[str, Any]:
    return assistant_message([], {"_chrys_kind": "turn", "_turn_id": f"turn_{index}", "_turn": index})


def single_turn(messages: list[Any]) -> TurnSegment:
    segments = slice_turn_segments(expand_history({"messages": messages, "compressed_msgs": []}))
    assert len(segments) == 1
    return segments[0]


def skill_turn(
    opener_text: str,
    skill_name: str | None = "my-skill",
    call_arguments: Any = None,
    call_name: str = "load_skill",
) -> TurnSegment:
    if call_arguments is None:
        call_arguments = json.dumps({"skill_name": skill_name or ""})
    contents: list[Any] = []
    if skill_name is not None:
        contents.append(function_call("call-1", call_name, call_arguments, {"_chrys_tool_kind": "skill"}))
    messages: list[Any] = [user_message(opener_text)]
    if contents:
        messages.append(assistant_message(contents, {"_chrys_operation_id": "wire-1"}))
        messages.append(tool_message([function_result("call-1")]))
    messages.append(turn_marker(1))
    return single_turn(messages)


class TestBuildSkillEvents:
    def test_emits_event_when_opener_matches_and_load_skill_corroborates(self) -> None:
        events = build_skill_events(skill_turn("/my-skill do something"), CONTEXT)
        assert len(events) == 1
        event = events[0]
        assert event["kind"] == "input-triggered-use"
        assert event["funcType"] == 0
        assert event["funcName"] == "my-skill"
        assert event["sessionId"] == SESSION_ID
        assert event["channelType"] == "desktop"
        assert event["projectName"] == "my-project"
        assert event["pluginVersion"] == "0.28.0"
        # tool-detail git common fields (primary_cwd located).
        assert event["gitBranch"] == "main"
        assert event["gitRevision"] == "rev-1"
        assert event["gitOwner"] == "team"
        assert event["gitRepo"] == "proj"
        # Never carried (contract §2.3).
        for key in ("funcId", "value", "extra", "fileName", "requestId", "gitRemote"):
            assert key not in event

    def test_accepts_full_width_slash_and_bare_token(self) -> None:
        assert len(build_skill_events(skill_turn("\uff0fmy-skill"), CONTEXT)) == 1
        assert len(build_skill_events(skill_turn("/my-skill"), CONTEXT)) == 1

    def test_does_not_report_unmatched_slash_text_without_corroboration(self) -> None:
        # Local commands never enter messages; a hand-typed non-skill
        # /xxx without corroboration is not reported.
        assert build_skill_events(skill_turn("/model gpt-4", None), CONTEXT) == []
        assert build_skill_events(skill_turn("/anything else"), CONTEXT) == build_skill_events(
            skill_turn("/anything else", "other-skill"), CONTEXT
        )

    def test_requires_corroborating_skill_name_to_equal_the_token(self) -> None:
        assert build_skill_events(skill_turn("/my-skill", "different-skill"), CONTEXT) == []
        # Non-skill-kind tools (same argument name) give no
        # corroboration: judged by _chrys_tool_kind.
        non_skill_kind = single_turn(
            [
                user_message("/my-skill"),
                assistant_message(
                    [
                        function_call(
                            "call-1",
                            "read_file",
                            json.dumps({"skill_name": "my-skill"}),
                            {"_chrys_tool_kind": "filesystem.read"},
                        )
                    ],
                    {"_chrys_operation_id": "wire-1"},
                ),
                tool_message([function_result("call-1")]),
                turn_marker(1),
            ]
        )
        assert build_skill_events(non_skill_kind, CONTEXT) == []

    def test_treats_truncated_non_json_arguments_as_no_evidence(self) -> None:
        events = build_skill_events(skill_turn("/my-skill", "my-skill", '{"skill_name": "my-skill", "res'), CONTEXT)
        assert events == []

    def test_accepts_object_form_arguments(self) -> None:
        events = build_skill_events(skill_turn("/my-skill", "my-skill", {"skill_name": "my-skill"}), CONTEXT)
        assert len(events) == 1

    def test_reports_at_most_first_match_per_turn_and_ignores_injected_openers(self) -> None:
        events = build_skill_events(
            single_turn(
                [
                    user_message("/my-skill and /other-skill"),
                    assistant_message(
                        [
                            function_call(
                                "call-1",
                                "load_skill",
                                json.dumps({"skill_name": "my-skill"}),
                                {"_chrys_tool_kind": "skill"},
                            )
                        ],
                        {"_chrys_operation_id": "wire-1"},
                    ),
                    tool_message([function_result("call-1")]),
                    turn_marker(1),
                ]
            ),
            CONTEXT,
        )
        assert [event["funcName"] for event in events] == ["my-skill"]

        # An injected user message's slash text is not an opener.
        injected = build_skill_events(
            single_turn(
                [
                    user_message("plain question"),
                    user_message("/my-skill", {"_injected": True}),
                    assistant_message(
                        [
                            function_call(
                                "call-1",
                                "load_skill",
                                json.dumps({"skill_name": "my-skill"}),
                                {"_chrys_tool_kind": "skill"},
                            )
                        ],
                        {"_chrys_operation_id": "wire-1"},
                    ),
                    tool_message([function_result("call-1")]),
                    turn_marker(1),
                ]
            ),
            CONTEXT,
        )
        assert injected == []

    def test_keeps_func_type_zero_for_batch_elements(self) -> None:
        events = build_skill_events(skill_turn("/my-skill run"), CONTEXT)
        for event in events:
            assert event["funcType"] == 0


class TestAnalyzeSessionRevisionIntegration:
    def test_orders_batch_element_before_tool_and_ai_code_events(self) -> None:
        envelope = {
            "meta": {
                "schema_version": 1,
                "app_version": "0.28.0",
                "session_id": SESSION_ID,
                "created_at": "2026-10-02T09:14:03Z",
                "updated_at": "2026-10-02T09:20:11Z",
                "kind": "chat",
                "title": "test",
                "last_surface": "acp",
                "primary_cwd": "D:\\repo",
                "working_dirs": ["D:\\repo"],
            },
            "state": {
                "messages": [
                    user_message("/my-skill fix it"),
                    assistant_message(
                        [
                            function_call(
                                "call-1",
                                "load_skill",
                                json.dumps({"skill_name": "my-skill"}),
                                {"_chrys_tool_kind": "skill", "_chrys_operation_id": "op-1"},
                            ),
                            function_call(
                                "call-2", "bash", "{}", {"_chrys_tool_kind": "shell", "_chrys_operation_id": "op-2"}
                            ),
                        ],
                        {"_chrys_operation_id": "wire-1"},
                    ),
                    tool_message([function_result("call-1"), function_result("call-2")]),
                    turn_marker(1),
                ],
                "turn_counter": 1,
            },
        }
        analysis = analyze_session_revision(
            SessionRevisionInput(
                session_id=SESSION_ID,
                revision_hash="0" * 64,
                envelope=envelope,
                source_path="D:\\sessions\\session.json",
            )
        )
        assert [event["kind"] for event in analysis["reportEvents"]] == [
            "input-triggered-use",
            "tool-use-saved",
            "tool-status-updated",
            "tool-use-saved",
            "tool-status-updated",
        ]
        assert analysis["reportEvents"][0]["funcType"] == 0
        assert analysis["reportEvents"][0]["funcName"] == "my-skill"
