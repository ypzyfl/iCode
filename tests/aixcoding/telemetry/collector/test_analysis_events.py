# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Line diff / spanId / tool pairing / common field assembly tests
(scenarios ported from the TS ``events.test.ts``; guide §8.1 pairing
rules)."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from chrys.aixcoding.telemetry.collector.analysis.context import (
    EventCommonContext,
    ReportAttribution,
    build_event_common,
    derive_project_name,
    derive_span_id,
    first_working_dir,
)
from chrys.aixcoding.telemetry.collector.analysis.exchanges import build_tool_triples
from chrys.aixcoding.telemetry.collector.analysis.git_context import GitRepositoryInfo
from chrys.aixcoding.telemetry.collector.analysis.history import expand_history
from chrys.aixcoding.telemetry.collector.analysis.line_diff import compute_line_diff
from chrys.aixcoding.telemetry.collector.analysis.turns import TurnSegment, slice_turn_segments

SESSION_ID = "4201eebc-ca45-4328-8882-272f3d7c41cb"
UUID_FORM = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def message(role: str, properties: dict[str, Any] | None = None, contents: list[Any] | None = None) -> dict[str, Any]:
    return {
        "type": "message",
        "role": role,
        "contents": contents if contents is not None else [],
        "additional_properties": properties if properties is not None else {},
    }


def turn_marker(index: int) -> dict[str, Any]:
    return message("assistant", {"_chrys_kind": "turn", "_turn_id": f"turn_{index}", "_turn": index})


def function_call(
    call_id: str,
    name: str = "edit_file",
    content_properties: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "type": "function_call",
        "call_id": call_id,
        "name": name,
        "arguments": "{}",
        "additional_properties": content_properties if content_properties is not None else {},
    }


def function_result(
    call_id: str,
    content_properties: dict[str, Any] | None = None,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base: dict[str, Any] = {
        "type": "function_result",
        "call_id": call_id,
        "result": "ok",
        "additional_properties": content_properties if content_properties is not None else {},
    }
    if overrides is not None:
        base.update(overrides)
    return base


def single_turn(messages: list[Any]) -> TurnSegment:
    segments = slice_turn_segments(expand_history({"messages": messages, "compressed_msgs": []}))
    assert len(segments) == 1
    return segments[0]


class TestComputeLineDiff:
    def test_returns_equal_ops_for_identical_sequences(self) -> None:
        assert compute_line_diff(["a", "b"], ["a", "b"]) == ["=", "="]

    def test_counts_insertions_and_deletions_across_a_middle_edit(self) -> None:
        ops = compute_line_diff(["a", "b", "c"], ["a", "x", "c"])
        assert ops is not None
        assert ops.count("+") == 1
        assert ops.count("-") == 1
        assert ops.count("=") == 2

    def test_handles_empty_sides(self) -> None:
        assert compute_line_diff([], ["x", "y"]) == ["+", "+"]
        assert compute_line_diff(["x", "y"], []) == ["-", "-"]
        assert compute_line_diff([], []) == []

    def test_returns_none_beyond_the_safety_limits(self) -> None:
        many = [f"line-{index}" for index in range(10_001)]
        assert compute_line_diff(many, []) is None
        far_apart = [f"before-{index}" for index in range(1_200)]
        other = [f"after-{index}" for index in range(1_200)]
        assert compute_line_diff(far_apart, other) is None


class TestDeriveSpanId:
    def test_derives_a_deterministic_turn_scoped_uuid(self) -> None:
        span_id = derive_span_id(SESSION_ID, "turn_3")
        assert UUID_FORM.fullmatch(span_id)
        assert span_id == derive_span_id(SESSION_ID, "turn_3")
        assert span_id != derive_span_id(SESSION_ID, "turn_4")
        assert span_id != derive_span_id("other-session", "turn_3")
        expected = hashlib.sha256(f"{SESSION_ID}:turn_3".encode()).hexdigest()
        assert span_id.replace("-", "") == expected[:32]


class TestBuildToolTriples:
    def test_pairs_calls_with_results_inside_one_exchange(self) -> None:
        triples = build_tool_triples(
            single_turn(
                [
                    message("user"),
                    message("assistant", None, [function_call("c1", "read_file")]),
                    message("tool", None, [function_result("c1")]),
                    turn_marker(1),
                ]
            )
        )
        assert len(triples) == 1
        assert triples[0].result is not None

    def test_treats_structural_chrys_kind_messages_as_hard_boundaries(self) -> None:
        triples = build_tool_triples(
            single_turn(
                [
                    message("user"),
                    message("assistant", None, [function_call("c1")]),
                    message("assistant", {"_chrys_kind": "interrupted"}),
                    message("tool", None, [function_result("c1")]),
                    turn_marker(1),
                ]
            )
        )
        assert len(triples) == 1
        # Result after the hard boundary: no cross-boundary pairing; the
        # call keeps no result (truncation/interruption is legal).
        assert triples[0].result is None

    def test_starts_a_new_exchange_after_tool_output(self) -> None:
        triples = build_tool_triples(
            single_turn(
                [
                    message("user"),
                    message("assistant", None, [function_call("X")]),
                    message("tool", None, [function_result("X")]),
                    message("assistant", None, [function_call("X")]),
                    message("tool", None, [function_result("X")]),
                    turn_marker(1),
                ]
            )
        )
        assert len(triples) == 2
        assert triples[0].result is not None
        assert triples[1].result is not None
        assert triples[0].assistant_message is not triples[1].assistant_message

    def test_pairs_embedded_results_preceding_their_calls(self) -> None:
        triples = build_tool_triples(
            single_turn(
                [
                    message("user"),
                    message("assistant", None, [function_result("c1"), function_call("c1")]),
                    turn_marker(1),
                ]
            )
        )
        assert len(triples) == 1
        assert triples[0].result is not None

    def test_does_not_answer_later_sibling_calls_with_earlier_embedded_results(self) -> None:
        triples = build_tool_triples(
            single_turn(
                [
                    message("user"),
                    message("assistant", None, [function_result("c1")]),
                    message("assistant", None, [function_call("c1")]),
                    turn_marker(1),
                ]
            )
        )
        assert len(triples) == 1
        # The result's message opens the output segment; later calls open
        # a new exchange, never pairing backwards.
        assert triples[0].result is None

    def test_one_result_covers_same_id_calls_and_orphans_stay_unresolved(self) -> None:
        triples = build_tool_triples(
            single_turn(
                [
                    message("user"),
                    message("assistant", None, [function_call("c1"), function_call("c1")]),
                    message("tool", None, [function_result("c1"), function_result("unknown-id")]),
                    turn_marker(1),
                ]
            )
        )
        assert len(triples) == 2
        assert triples[0].result is not None
        assert triples[1].result is not None

    def test_excludes_informational_only_and_provider_hosted_types(self) -> None:
        informational = {**function_call("c1"), "informational_only": True}
        hosted_call = {
            "type": "mcp_server_tool_call",
            "call_id": "c2",
            "tool_name": "t",
            "server_name": "s",
            "arguments": "{}",
        }
        image_call = {"type": "image_generation_tool_call", "image_id": "i1"}
        triples = build_tool_triples(
            single_turn(
                [
                    message("user"),
                    message("assistant", None, [informational, hosted_call, image_call]),
                    message("tool", None, [function_result("c1")]),
                    turn_marker(1),
                ]
            )
        )
        assert triples == []

    def test_sorts_by_invocation_order_with_missing_last(self) -> None:
        triples = build_tool_triples(
            single_turn(
                [
                    message("user"),
                    message(
                        "assistant",
                        None,
                        [
                            function_call("late", "read_file", {"_chrys_tool_invocation_order": 5}),
                            function_call("early", "read_file", {"_chrys_tool_invocation_order": 2}),
                            function_call("no-order", "read_file"),
                        ],
                    ),
                    turn_marker(1),
                ]
            )
        )
        assert [triple.call["call_id"] for triple in triples] == ["early", "late", "no-order"]


class TestProjectName:
    def test_first_working_dir_and_basename(self) -> None:
        meta: dict[str, Any] = {"working_dirs": ["D:\\repo\\sub", "D:\\other"]}
        assert first_working_dir(meta) == "D:\\repo\\sub"
        assert derive_project_name(meta) == "sub"
        assert derive_project_name({"working_dirs": ["/repo/sub"]}) == "sub"

    def test_missing_or_malformed_dirs_yield_none(self) -> None:
        assert first_working_dir({}) is None
        assert first_working_dir({"working_dirs": []}) is None
        assert first_working_dir({"working_dirs": [""]}) is None
        assert first_working_dir({"working_dirs": [42]}) is None
        assert derive_project_name({}) is None


class TestBuildEventCommon:
    def test_full_assembly_omits_none_and_carries_git_remote(self) -> None:
        git = GitRepositoryInfo(
            remote_url="https://host/o/r",
            revision="64704138a5deed7f83c88a45695308f6f5675d04",
            branch="master",
            user_name="dev",
            user_email="dev@example.com",
            owner="o",
            repo="r",
        )
        context = EventCommonContext(
            session_id=SESSION_ID,
            attribution=ReportAttribution(
                channel_type="cli",
                user_id="ehr-1",
                channel_name="cn",
                channel_version="1.2.3",
            ),
            product_name="prod",
            project_name="proj",
            plugin_version="9.9.9",
            primary_cwd="D:\\repo",
            git=git,
        )
        common = build_event_common(context, "turn_1")
        assert common == {
            "sessionId": SESSION_ID,
            "spanId": derive_span_id(SESSION_ID, "turn_1"),
            "productName": "prod",
            "projectName": "proj",
            "channelType": "cli",
            "channelName": "cn",
            "channelVersion": "1.2.3",
            "userId": "ehr-1",
            "pluginVersion": "9.9.9",
            # Registration-focus common field (M4): constructed here,
            # gated by the HTTP sink's focus_fields_enabled switch.
            "gitRemote": "https://host/o/r",
            "gitBranch": "master",
            "gitRevision": "64704138a5deed7f83c88a45695308f6f5675d04",
            "gitOwner": "o",
            "gitRepo": "r",
        }

    def test_defaults_channel_type_to_desktop_without_attribution(self) -> None:
        context = EventCommonContext(
            session_id="s",
            attribution=None,
            product_name="p",
            project_name=None,
            plugin_version=None,
            primary_cwd=None,
            git=None,
        )
        common = build_event_common(context, "turn_1")
        assert common == {
            "sessionId": "s",
            "spanId": derive_span_id("s", "turn_1"),
            "productName": "p",
            "channelType": "desktop",
        }
