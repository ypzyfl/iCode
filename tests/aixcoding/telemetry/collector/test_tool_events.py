# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Tool save/update event tests (scenarios ported from the TS
``events.test.ts`` buildToolEvents sections; contract §3.2/§3.3)."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

import pytest

from chrys.aixcoding.telemetry.collector.analysis.attachments import MutationBlobReader
from chrys.aixcoding.telemetry.collector.analysis.context import (
    EventCommonContext,
    ReportAttribution,
    derive_span_id,
)
from chrys.aixcoding.telemetry.collector.analysis.history import expand_history
from chrys.aixcoding.telemetry.collector.analysis.tool_events import build_tool_events
from chrys.aixcoding.telemetry.collector.analysis.turns import TurnSegment, slice_turn_segments

SESSION_ID = "4201eebc-ca45-4328-8882-272f3d7c41cb"


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


class MemoryBlobReader:
    def __init__(self, blobs: dict[str, str]) -> None:
        self._blobs = blobs

    def read_blob_text(self, blob_hash: str) -> str | None:
        return self._blobs.get(blob_hash)


class NullBlobReader:
    def read_blob_text(self, blob_hash: str) -> str | None:
        return None


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


CONTEXT = EventCommonContext(
    session_id=SESSION_ID,
    attribution=ReportAttribution(
        channel_type="desktop",
        user_id="user-1",
        channel_name="aixcoding-desktop",
        channel_version="1.2.3",
    ),
    product_name="my-project",
    project_name="my-project",
    plugin_version="0.28.0",
    primary_cwd=None,
    git=None,
)


def events_for(
    messages: list[Any],
    mutations: Any = None,
    blobs: dict[str, str] | None = None,
    attribution: ReportAttribution | None = ...,
) -> list[dict[str, Any]]:
    segment = single_turn(messages)
    effective_attribution = CONTEXT.attribution if attribution is ... else attribution
    context = EventCommonContext(
        session_id=CONTEXT.session_id,
        attribution=effective_attribution,
        product_name=CONTEXT.product_name,
        project_name=CONTEXT.project_name,
        plugin_version=CONTEXT.plugin_version,
        primary_cwd=CONTEXT.primary_cwd,
        git=CONTEXT.git,
    )
    blob_reader: MutationBlobReader = MemoryBlobReader(blobs) if blobs is not None else NullBlobReader()
    return build_tool_events(segment, context, mutations, blob_reader)


def saves(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [event for event in events if event["kind"] == "tool-use-saved"]


def updates(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [event for event in events if event["kind"] == "tool-status-updated"]


def test_maps_func_type_via_chrys_tool_kind() -> None:
    events = events_for(
        [
            message("user"),
            message(
                "assistant",
                {"_chrys_operation_id": "req-1"},
                [
                    function_call("c1", "search_code", {"_chrys_tool_kind": "mcp", "_chrys_operation_id": "op-1"}),
                    function_call("c2", "bash", {"_chrys_tool_kind": "shell", "_chrys_operation_id": "op-2"}),
                    function_call(
                        "c3", "run_sub_agent", {"_chrys_tool_kind": "sub_agent", "_chrys_operation_id": "op-3"}
                    ),
                ],
            ),
            message("tool", None, [function_result("c1"), function_result("c2"), function_result("c3")]),
            turn_marker(1),
        ]
    )
    assert [event["funcType"] for event in saves(events)] == [1, 3, 3]


def test_derives_func_id_with_three_level_fallback() -> None:
    with_operation = events_for(
        [
            message("user"),
            message(
                "assistant",
                None,
                [function_call("c1", "bash", {"_chrys_operation_id": "op-77", "_chrys_tool_kind": "shell"})],
            ),
            turn_marker(1),
        ]
    )
    assert with_operation[0]["funcId"] == "op-77"

    with_occurrence = events_for(
        [
            message("user"),
            message(
                "assistant",
                None,
                [function_call("c1", "bash", {"_chrys_analytics_item_id": "occ-9", "_chrys_tool_kind": "shell"})],
            ),
            turn_marker(1),
        ]
    )
    assert with_occurrence[0]["funcId"] == "c1:occ-9"

    bare = events_for(
        [
            message("user"),
            message("assistant", None, [function_call("c9", "bash", {"_chrys_tool_kind": "shell"})]),
            turn_marker(1),
        ]
    )
    assert bare[0]["funcId"] == "c9:registration-0"


def test_keeps_double_semantics_request_id_and_func_id() -> None:
    events = events_for(
        [
            message("user"),
            message(
                "assistant",
                {"_chrys_operation_id": "wire-call-1"},
                [
                    function_call("c1", "bash", {"_chrys_operation_id": "tool-op-1", "_chrys_tool_kind": "shell"}),
                    function_call(
                        "c2", "read_file", {"_chrys_operation_id": "tool-op-2", "_chrys_tool_kind": "filesystem.read"}
                    ),
                ],
            ),
            message("tool", None, [function_result("c1"), function_result("c2")]),
            turn_marker(1),
        ]
    )
    save_events = saves(events)
    assert [event["requestId"] for event in save_events] == ["wire-call-1", "wire-call-1"]
    assert {event["funcId"] for event in save_events} == {"tool-op-1", "tool-op-2"}


def test_omits_request_id_when_message_level_operation_id_missing() -> None:
    events = events_for(
        [
            message("user"),
            message(
                "assistant",
                None,
                [function_call("c1", "bash", {"_chrys_operation_id": "op-1", "_chrys_tool_kind": "shell"})],
            ),
            turn_marker(1),
        ]
    )
    assert "requestId" not in events[0]


STATUS_CASES = [
    ("approval user_rejected -> 4", {"_chrys_tool_result_metadata": {"approval": "user_rejected"}}, None, 4),
    (
        "tool_error_kind approval_rejected -> 4",
        {"_chrys_tool_result_metadata": {"tool_error_kind": "approval_rejected"}},
        None,
        4,
    ),
    ("tool_error_kind hook_denied -> 4", {"_chrys_tool_result_metadata": {"tool_error_kind": "hook_denied"}}, None, 4),
    ("errored -> 2", {"_chrys_tool_result_metadata": {"errored": True}}, None, 2),
    ("failed -> 2", {"_chrys_tool_result_metadata": {"failed": True}}, None, 2),
    ("exception -> 2", {}, {"exception": "boom"}, 2),
    ("shell_timed_out -> 2", {"_chrys_tool_result_metadata": {"shell_timed_out": True}}, None, 2),
    ("process_exit_code 1 -> 2", {"_chrys_tool_result_metadata": {"process_exit_code": 1}}, None, 2),
    ("shell_exit_code 127 -> 2", {"_chrys_tool_result_metadata": {"shell_exit_code": 127}}, None, 2),
    ("interrupted -> 2", {"_chrys_tool_result_metadata": {"interrupted": True}}, None, 2),
    ("failed=false -> 1", {"_chrys_tool_result_metadata": {"failed": False}}, None, 1),
    ("shell_exit_code 0 -> 1", {"_chrys_tool_result_metadata": {"shell_exit_code": 0}}, None, 1),
    ("no evidence -> 1", {}, None, 1),
]


@pytest.mark.parametrize(("label", "result_properties", "overrides", "expected"), STATUS_CASES)
def test_maps_code_status(
    label: str, result_properties: dict[str, Any], overrides: dict[str, Any] | None, expected: int
) -> None:
    events = events_for(
        [
            message("user"),
            message(
                "assistant",
                None,
                [function_call("c1", "bash", {"_chrys_operation_id": "op-1", "_chrys_tool_kind": "shell"})],
            ),
            message("tool", None, [function_result("c1", result_properties, overrides)]),
            turn_marker(1),
        ]
    )
    update = updates(events)[0]
    expected_update: dict[str, Any] = {"kind": "tool-status-updated", "funcId": "op-1", "codeStatus": expected}
    # Failure evidence (M4): codeStatus 2 attaches funcErrorMessage when
    # a source exists — the exception override is the only case here.
    if expected == 2 and overrides is not None and "exception" in overrides:
        expected_update["funcErrorMessage"] = overrides["exception"]
    assert update == expected_update


def test_produces_only_a_save_for_calls_without_results() -> None:
    events = events_for(
        [
            message("user"),
            message(
                "assistant",
                None,
                [function_call("c1", "bash", {"_chrys_operation_id": "op-1", "_chrys_tool_kind": "shell"})],
            ),
            turn_marker(1),
        ]
    )
    assert len(events) == 1
    assert events[0]["kind"] == "tool-use-saved"
    assert events[0]["codeStatus"] == 0


def test_joins_write_mutations_by_call_id_for_line_counts() -> None:
    before_hash = sha256("a\nb\nc\n")
    after_hash = sha256("a\nx\nc\n")
    events = events_for(
        [
            message("user"),
            message(
                "assistant",
                None,
                [
                    function_call(
                        "call-1", "edit_file", {"_chrys_operation_id": "op-1", "_chrys_tool_kind": "filesystem.write"}
                    )
                ],
            ),
            message("tool", None, [function_result("call-1", {"_chrys_tool_result_metadata": {"failed": False}})]),
            turn_marker(1),
        ],
        mutations={
            "turns": [
                {
                    "turn_id": 1,
                    "mutations": [
                        {
                            "path": "D:\\repo\\a.txt",
                            "operation": "modify",
                            "source": "edit_file",
                            "tool_call_id": "call-1",
                            "timestamp": 1,
                            "provenance": "proven",
                            "before_hash": before_hash,
                            "after_hash": after_hash,
                        }
                    ],
                    "detection_truncated": False,
                }
            ],
            "snapshots": {},
        },
        blobs={before_hash: "a\nb\nc\n", after_hash: "a\nx\nc\n"},
    )
    update = updates(events)[0]
    assert update["funcId"] == "op-1"
    assert update["codeStatus"] == 1
    assert update["originalLines"] == 3
    assert update["addedLines"] == 1
    assert update["deletedLines"] == 1


def test_counts_crlf_blobs_with_the_same_line_counts_as_lf() -> None:
    before_hash = sha256("a\r\nb\r\nc\r\n")
    after_hash = sha256("a\r\nx\r\nc\r\n")
    events = events_for(
        [
            message("user"),
            message(
                "assistant",
                None,
                [
                    function_call(
                        "call-1", "edit_file", {"_chrys_operation_id": "op-1", "_chrys_tool_kind": "filesystem.write"}
                    )
                ],
            ),
            message("tool", None, [function_result("call-1", {"_chrys_tool_result_metadata": {"failed": False}})]),
            turn_marker(1),
        ],
        mutations={
            "turns": [
                {
                    "turn_id": 1,
                    "mutations": [
                        {
                            "path": "D:\\repo\\a.txt",
                            "operation": "modify",
                            "source": "edit_file",
                            "tool_call_id": "call-1",
                            "timestamp": 1,
                            "provenance": "proven",
                            "before_hash": before_hash,
                            "after_hash": after_hash,
                        }
                    ],
                    "detection_truncated": False,
                }
            ],
            "snapshots": {},
        },
        blobs={before_hash: "a\r\nb\r\nc\r\n", after_hash: "a\r\nx\r\nc\r\n"},
    )
    update = updates(events)[0]
    # CRLF keeps \r inside line content without changing line counts:
    # same three columns as the LF sample (plan §6.3 item 8).
    assert update["originalLines"] == 3
    assert update["addedLines"] == 1
    assert update["deletedLines"] == 1


def test_counts_create_and_delete_mutations_without_diffing_missing_side() -> None:
    create_after = sha256("x\ny\n")
    delete_before = sha256("g\n")
    events = events_for(
        [
            message("user"),
            message(
                "assistant",
                None,
                [
                    function_call(
                        "call-1", "write_file", {"_chrys_operation_id": "op-1", "_chrys_tool_kind": "filesystem.write"}
                    ),
                    function_call(
                        "call-2", "edit_file", {"_chrys_operation_id": "op-2", "_chrys_tool_kind": "filesystem.write"}
                    ),
                ],
            ),
            message("tool", None, [function_result("call-1"), function_result("call-2")]),
            turn_marker(1),
        ],
        mutations={
            "turns": [
                {
                    "turn_id": 1,
                    "mutations": [
                        {
                            "path": "D:\\repo\\new.txt",
                            "operation": "create",
                            "source": "write_file",
                            "tool_call_id": "call-1",
                            "timestamp": 1,
                            "after_hash": create_after,
                        },
                        {
                            "path": "D:\\repo\\old.txt",
                            "operation": "delete",
                            "source": "edit_file",
                            "tool_call_id": "call-2",
                            "timestamp": 2,
                            "before_hash": delete_before,
                        },
                    ],
                    "detection_truncated": False,
                }
            ],
            "snapshots": {},
        },
        blobs={create_after: "x\ny\n", delete_before: "g\n"},
    )
    update_events = updates(events)
    assert update_events[0] == {
        "kind": "tool-status-updated",
        "funcId": "op-1",
        "codeStatus": 1,
        "originalLines": 0,
        "addedLines": 2,
        "deletedLines": 0,
    }
    assert update_events[1] == {
        "kind": "tool-status-updated",
        "funcId": "op-2",
        "codeStatus": 1,
        "originalLines": 1,
        "addedLines": 0,
        "deletedLines": 1,
    }


def test_falls_back_to_unique_write_call_when_ledger_uses_engine_short_id() -> None:
    # Real engine shape: the message call_id is a provider id
    # (call_00_...), the ledger tool_call_id is a Chrys short id (uuid
    # hex[:12]) — no mapping between the two ID systems; the
    # unique-write-call-within-turn fallback applies.
    after_hash = sha256("x\ny\n")
    events = events_for(
        [
            message("user"),
            message(
                "assistant",
                None,
                [
                    function_call(
                        "call_00_pKRVw4yi2OYSn1pUyLF46824",
                        "write_file",
                        {"_chrys_operation_id": "op-1", "_chrys_tool_kind": "filesystem.write"},
                    )
                ],
            ),
            message("tool", None, [function_result("call_00_pKRVw4yi2OYSn1pUyLF46824")]),
            turn_marker(1),
        ],
        mutations={
            "turns": [
                {
                    "turn_id": 1,
                    "mutations": [
                        {
                            "path": "D:\\repo\\new.txt",
                            "operation": "create",
                            "source": "write_file",
                            "tool_call_id": "2872b118b0b2",
                            "timestamp": 1,
                            "after_hash": after_hash,
                        }
                    ],
                    "detection_truncated": False,
                }
            ],
            "snapshots": {},
        },
        blobs={after_hash: "x\ny\n"},
    )
    update_events = updates(events)
    assert len(update_events) == 1
    assert update_events[0]["originalLines"] == 0
    assert update_events[0]["addedLines"] == 2
    assert update_events[0]["deletedLines"] == 0


def test_resolves_mismatched_ids_by_timing_window_and_refuses_ambiguity() -> None:
    a_after = sha256("a-after\n")
    b_after = sha256("b-after\n")
    a_start = "2026-10-03T13:47:55.819516+00:00"
    b_start = "2026-10-03T13:50:00.000000+00:00"
    a_stamp = datetime.fromisoformat(a_start).timestamp()
    b_stamp = datetime.fromisoformat(b_start).timestamp()
    events = events_for(
        [
            message("user"),
            message(
                "assistant",
                None,
                [
                    function_call(
                        "call_00_A",
                        "write_file",
                        {"_chrys_timing": {"started_at": a_start, "finished_at": "2026-10-03T13:47:58.630065+00:00"}},
                    ),
                    function_call(
                        "call_00_B",
                        "write_file",
                        {"_chrys_timing": {"started_at": b_start, "finished_at": "2026-10-03T13:50:02.000000+00:00"}},
                    ),
                ],
            ),
            message("tool", None, [function_result("call_00_A"), function_result("call_00_B")]),
            turn_marker(1),
        ],
        mutations={
            "turns": [
                {
                    "turn_id": 1,
                    "mutations": [
                        {
                            "path": "D:\\repo\\a.txt",
                            "operation": "create",
                            "source": "write_file",
                            "tool_call_id": "aaaaaaaaaaaa",
                            "timestamp": a_stamp,
                            "after_hash": a_after,
                        },
                        {
                            "path": "D:\\repo\\b.txt",
                            "operation": "create",
                            "source": "write_file",
                            "tool_call_id": "bbbbbbbbbbbb",
                            "timestamp": b_stamp,
                            "after_hash": b_after,
                        },
                    ],
                    "detection_truncated": False,
                }
            ],
            "snapshots": {},
        },
        blobs={a_after: "a-after\n", b_after: "b-after\n"},
    )
    update_events = updates(events)
    assert len(update_events) == 2
    assert update_events[0]["addedLines"] == 1
    assert update_events[1]["addedLines"] == 1

    # Ambiguity refused: both mutations fall inside the single call's
    # window -> no guessing, line counts omitted.
    ambiguous = events_for(
        [
            message("user"),
            message(
                "assistant",
                None,
                [
                    function_call(
                        "call_00_C",
                        "write_file",
                        {"_chrys_timing": {"started_at": a_start, "finished_at": "2026-10-03T13:47:58.630065+00:00"}},
                    )
                ],
            ),
            message("tool", None, [function_result("call_00_C")]),
            turn_marker(1),
        ],
        mutations={
            "turns": [
                {
                    "turn_id": 1,
                    "mutations": [
                        {
                            "path": "D:\\repo\\x.txt",
                            "operation": "create",
                            "source": "write_file",
                            "tool_call_id": "cccccccccccc",
                            "timestamp": a_stamp,
                            "after_hash": a_after,
                        },
                        {
                            "path": "D:\\repo\\y.txt",
                            "operation": "create",
                            "source": "write_file",
                            "tool_call_id": "dddddddddddd",
                            "timestamp": a_stamp + 1,
                            "after_hash": b_after,
                        },
                    ],
                    "detection_truncated": False,
                }
            ],
            "snapshots": {},
        },
        blobs={a_after: "a-after\n", b_after: "b-after\n"},
    )
    ambiguous_updates = updates(ambiguous)
    assert len(ambiguous_updates) == 1
    assert "addedLines" not in ambiguous_updates[0]


def test_skips_foreign_provenance_non_write_sources_and_missing_blobs() -> None:
    before_hash = sha256("a\n")
    events = events_for(
        [
            message("user"),
            message(
                "assistant",
                None,
                [
                    function_call(
                        "call-1", "edit_file", {"_chrys_operation_id": "op-1", "_chrys_tool_kind": "filesystem.write"}
                    ),
                    function_call(
                        "call-2", "edit_file", {"_chrys_operation_id": "op-2", "_chrys_tool_kind": "filesystem.write"}
                    ),
                    function_call(
                        "call-3", "edit_file", {"_chrys_operation_id": "op-3", "_chrys_tool_kind": "filesystem.write"}
                    ),
                ],
            ),
            message("tool", None, [function_result("call-1"), function_result("call-2"), function_result("call-3")]),
            turn_marker(1),
        ],
        mutations={
            "turns": [
                {
                    "turn_id": 1,
                    "mutations": [
                        {
                            "path": "D:\\repo\\foreign.txt",
                            "operation": "modify",
                            "source": "edit_file",
                            "tool_call_id": "call-1",
                            "timestamp": 1,
                            "provenance": "foreign",
                            "before_hash": before_hash,
                            "after_hash": sha256("b\n"),
                        },
                        {
                            "path": "D:\\repo\\shell.txt",
                            "operation": "modify",
                            "source": "shell",
                            "tool_call_id": "call-2",
                            "timestamp": 2,
                            "before_hash": sha256("missing-before\n"),
                            "after_hash": sha256("missing-after\n"),
                        },
                        {
                            "path": "D:\\repo\\skipped.txt",
                            "operation": "modify",
                            "source": "edit_file",
                            "tool_call_id": "call-3",
                            "timestamp": 3,
                            "before_hash": sha256("no-blob\n"),
                            "after_hash": sha256("no-blob-2\n"),
                        },
                    ],
                    "detection_truncated": False,
                }
            ],
            "snapshots": {},
        },
        blobs={},
    )
    update_events = updates(events)
    assert len(update_events) == 3
    for update in update_events:
        assert "originalLines" not in update
        assert "addedLines" not in update
        assert "deletedLines" not in update


def test_carries_common_fields_on_saves_only_updates_stay_bare() -> None:
    events = events_for(
        [
            message("user"),
            message(
                "assistant",
                {"_chrys_operation_id": "wire-1"},
                [function_call("c1", "bash", {"_chrys_operation_id": "op-1", "_chrys_tool_kind": "shell"})],
            ),
            message("tool", None, [function_result("c1")]),
            turn_marker(1),
        ]
    )
    save = events[0]
    assert save["kind"] == "tool-use-saved"
    assert save["sessionId"] == SESSION_ID
    assert save["channelType"] == "desktop"
    assert save["channelName"] == "aixcoding-desktop"
    assert save["channelVersion"] == "1.2.3"
    assert save["userId"] == "user-1"
    assert save["pluginVersion"] == "0.28.0"
    assert save["projectName"] == "my-project"
    assert save["spanId"] == derive_span_id(SESSION_ID, "turn_1")
    update = events[1]
    assert sorted(update.keys()) == ["codeStatus", "funcId", "kind"]


def test_defaults_channel_type_to_desktop_without_attribution() -> None:
    events = events_for(
        [
            message("user"),
            message(
                "assistant",
                None,
                [function_call("c1", "bash", {"_chrys_operation_id": "op-1", "_chrys_tool_kind": "shell"})],
            ),
            turn_marker(1),
        ],
        attribution=None,
    )
    assert events[0]["channelType"] == "desktop"
    assert "channelName" not in events[0]


def test_never_emits_registered_focus_fields() -> None:
    events = events_for(
        [
            message("user"),
            message(
                "assistant",
                None,
                [
                    function_call(
                        "c1",
                        "read_file",
                        {
                            "_chrys_operation_id": "op-1",
                            "_chrys_tool_kind": "filesystem.read",
                            "_chrys_tool_context": {"mcpUri": "mcp://srv/tool"},
                        },
                    )
                ],
            ),
            message("tool", None, [function_result("c1")]),
            turn_marker(1),
        ]
    )
    for event in events:
        for field in ("value", "fileName", "extra", "funcErrorMessage"):
            assert field not in event
