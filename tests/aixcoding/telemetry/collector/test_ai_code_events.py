# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Net-change ai-code event tests (scenarios ported from the TS
``ai-code.test.ts`` buildAiCodeEvents sections; contract §3.5, M5 plan
§6.3)."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from chrys.aixcoding.telemetry.collector.analysis.ai_code_events import (
    AiCodeEventInputs,
    build_ai_code_events,
)
from chrys.aixcoding.telemetry.collector.analysis.attachments import NULL_BLOB_READER, SessionMutationBlobReader
from chrys.aixcoding.telemetry.collector.analysis.context import EventCommonContext
from chrys.aixcoding.telemetry.collector.analysis.git_context import GitFileContext, GitRepositoryInfo
from chrys.aixcoding.telemetry.collector.analysis.history import expand_history
from chrys.aixcoding.telemetry.collector.analysis.index import SessionRevisionInput, analyze_session_revision
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


def single_turn(messages: list[Any], index: int = 1) -> TurnSegment:
    segments = slice_turn_segments(expand_history({"messages": messages, "compressed_msgs": []}))
    for segment in segments:
        if segment.turn_id == f"turn_{index}":
            return segment
    return segments[0]


class MemoryBlobReader:
    def __init__(self, blobs: dict[str, str]) -> None:
        self._blobs = blobs

    def read_blob_text(self, blob_hash: str) -> str | None:
        return self._blobs.get(blob_hash)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def mutation(path: str, operation: str, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    base: dict[str, Any] = {
        "path": path,
        "operation": operation,
        "source": "edit_file",
        "tool_call_id": "call-1",
        "timestamp": 1,
        "provenance": "proven",
    }
    if overrides is not None:
        base.update(overrides)
    return base


def ledger(
    turn_index: int,
    mutations: list[dict[str, Any]],
    snapshots: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "turns": [{"turn_id": turn_index, "mutations": mutations, "detection_truncated": False}],
        "snapshots": snapshots if snapshots is not None else {},
    }


GIT_INFO = GitRepositoryInfo(
    remote_url="https://cnb.boecy.cn/team/proj",
    revision="rev-1",
    branch="main",
    user_name="dev",
    user_email="dev@example.com",
    owner="team",
    repo="proj",
)


class FakeGitContext:
    def __init__(self, git_root: str | None = "D:\\repo") -> None:
        self._git_root = git_root

    def for_directory(self, directory: str) -> GitRepositoryInfo:
        return GIT_INFO

    def for_file(self, file_path: str) -> GitFileContext:
        return GitFileContext(
            remote_url=GIT_INFO.remote_url,
            revision=GIT_INFO.revision,
            branch=GIT_INFO.branch,
            user_name=GIT_INFO.user_name,
            user_email=GIT_INFO.user_email,
            owner=GIT_INFO.owner,
            repo=GIT_INFO.repo,
            root=self._git_root,
        )


EVENT_CONTEXT = EventCommonContext(
    session_id=SESSION_ID,
    attribution=None,
    product_name="repo",
    project_name="repo",
    plugin_version="0.28.0",
    primary_cwd="D:\\repo",
    git=None,
)


def turn_with_call(call_id: str = "call-1") -> TurnSegment:
    return single_turn(
        [
            message("user"),
            message(
                "assistant",
                {"_chrys_operation_id": "wire-1"},
                [
                    {
                        "type": "function_call",
                        "call_id": call_id,
                        "name": "edit_file",
                        "arguments": "{}",
                        "additional_properties": {
                            "_chrys_operation_id": "op-1",
                            "_chrys_tool_kind": "filesystem.write",
                        },
                    }
                ],
            ),
            turn_marker(1),
        ]
    )


def build(
    segment: TurnSegment,
    mutations_ledger: Any,
    blobs: dict[str, str] | None = None,
    analysis_version: int = 1,
    git_context: Any = None,
    context: EventCommonContext | None = None,
) -> Any:
    return build_ai_code_events(
        AiCodeEventInputs(
            segment=segment,
            session_id=SESSION_ID,
            analysis_version=analysis_version,
            context=context if context is not None else EVENT_CONTEXT,
            mutations_ledger=mutations_ledger,
            blob_reader=MemoryBlobReader(blobs) if blobs else NULL_BLOB_READER,
            git_context=git_context if git_context is not None else FakeGitContext(),
        )
    )


class TestBuildAiCodeEvents:
    def test_emits_modify_net_change_with_diff_blocks(self) -> None:
        before_hash = sha256("a\nb\nc\n")
        after_hash = sha256("a\nx\nc\n")
        result = build(
            turn_with_call(),
            ledger(
                1, [mutation("D:\\repo\\src\\a.ts", "modify", {"before_hash": before_hash, "after_hash": after_hash})]
            ),
            {before_hash: "a\nb\nc\n", after_hash: "a\nx\nc\n"},
        )
        assert len(result.events) == 1
        event = result.events[0]
        assert event["kind"] == "ai-code-saved"
        assert event["sourceType"] == "edit"
        assert event["inputMethod"] == "agent"
        assert event["language"] == "typescript"
        assert event["remoteUrl"] == "https://cnb.boecy.cn/team/proj"
        assert event["branch"] == "main"
        assert event["gitUserName"] == "dev"
        assert event["gitUserEmail"] == "dev@example.com"
        assert event["requestId"] == "wire-1"
        assert event["sessionId"] == SESSION_ID
        assert UUID_FORM.fullmatch(event["reportId"])
        assert event["blocks"] == [{"rangeStart": 2, "rangeEnd": 3}]
        assert result.truncated_paths == []

    def test_missing_before_hash_treated_as_create_whole_range(self) -> None:
        after_hash = sha256("x\ny\n")
        result = build(
            turn_with_call(),
            ledger(1, [mutation("D:\\repo\\new.py", "create", {"after_hash": after_hash})]),
            {after_hash: "x\ny\n"},
        )
        assert result.events[0]["language"] == "python"
        assert result.events[0]["blocks"] == [{"rangeStart": 1, "rangeEnd": 2}]

    def test_skips_delete_and_net_zero_changes(self) -> None:
        before_hash = sha256("a\n")
        result = build(
            turn_with_call(),
            ledger(
                1,
                [
                    mutation("D:\\repo\\gone.txt", "delete", {"before_hash": before_hash}),
                    mutation("D:\\repo\\same.txt", "modify", {"before_hash": before_hash, "after_hash": before_hash}),
                ],
            ),
            {before_hash: "a\n"},
        )
        # delete has no generated-code-into-repository meaning; net-zero
        # (initial == final) not counted.
        assert result.events == []

    def test_excludes_foreign_provenance(self) -> None:
        after_hash = sha256("x\n")
        result = build(
            turn_with_call(),
            ledger(
                1,
                [
                    mutation(
                        "D:\\repo\\foreign.txt",
                        "modify",
                        {"provenance": "foreign", "before_hash": sha256("f\n"), "after_hash": after_hash},
                    ),
                    mutation(
                        "D:\\repo\\truncated-detection.txt",
                        "modify",
                        {"before_hash": sha256("q\n"), "after_hash": after_hash},
                    ),
                ],
            ),
            {after_hash: "x\n", sha256("q\n"): "q\n"},
        )
        assert len(result.events) == 1

    def test_merges_same_path_via_earliest_snapshot_of_turn(self) -> None:
        snapshot_hash = sha256("v1\n")
        middle_hash = sha256("v2\n")
        final_hash = sha256("v3\n")
        path = "D:\\repo\\multi.txt"
        result = build(
            turn_with_call(),
            ledger(
                1,
                [
                    mutation(path, "modify", {"before_hash": snapshot_hash, "after_hash": middle_hash}),
                    mutation(path, "modify", {"before_hash": middle_hash, "after_hash": final_hash}),
                ],
                {
                    f"{path}::1": {
                        "path": path,
                        "period_index": 1,
                        "existed": True,
                        "content_hash": snapshot_hash,
                        "size": 3,
                    }
                },
            ),
            {snapshot_hash: "v1\n", middle_hash: "v2\n", final_hash: "v3\n"},
        )
        assert len(result.events) == 1
        # Merge: earliest snapshot v1 vs final v3 — the v2 middle state
        # does not participate.
        assert result.events[0]["blocks"] == [{"rangeStart": 1, "rangeEnd": 2}]

    def test_falls_back_to_first_mutation_before_hash_without_snapshot(self) -> None:
        first_before = sha256("a\n")
        after = sha256("a\nb\n")
        path = "D:\\repo\\fallback.txt"
        result = build(
            turn_with_call(),
            ledger(
                1,
                [
                    mutation(path, "modify", {"before_hash": first_before, "after_hash": sha256("tmp\n")}),
                    mutation(path, "modify", {"before_hash": sha256("tmp\n"), "after_hash": after}),
                ],
            ),
            {first_before: "a\n", after: "a\nb\n"},
        )
        assert len(result.events) == 1
        assert result.events[0]["blocks"] == [{"rangeStart": 2, "rangeEnd": 2}]

    def test_move_compares_against_old_path_content(self) -> None:
        before_hash = sha256("old-a\nold-b\n")
        after_hash = sha256("new-a\nnew-b\nnew-c\n")
        result = build(
            turn_with_call(),
            ledger(
                1,
                [
                    mutation(
                        "D:\\repo\\new.ts",
                        "move",
                        {"old_path": "D:\\repo\\old.ts", "before_hash": before_hash, "after_hash": after_hash},
                    )
                ],
            ),
            {before_hash: "old-a\nold-b\n", after_hash: "new-a\nnew-b\nnew-c\n"},
        )
        assert result.events[0]["blocks"] == [{"rangeStart": 1, "rangeEnd": 5}]

    def test_keeps_event_but_drops_blocks_when_blobs_missing(self) -> None:
        before_hash = sha256("a\n")
        after_hash = sha256("b\n")
        result = build(
            turn_with_call(),
            ledger(
                1, [mutation("D:\\repo\\skipped.md", "modify", {"before_hash": before_hash, "after_hash": after_hash})]
            ),
            # No blobs: blocks=[], the event survives.
            {},
        )
        assert len(result.events) == 1
        assert result.events[0]["blocks"] == []

    def test_derives_deterministic_report_id_varying_with_version(self) -> None:
        before_hash = sha256("a\n")
        after_hash = sha256("b\n")
        mutations_ledger = ledger(
            1, [mutation("D:\\repo\\a.ts", "modify", {"before_hash": before_hash, "after_hash": after_hash})]
        )
        blobs = {before_hash: "a\n", after_hash: "b\n"}
        first = build(turn_with_call(), mutations_ledger, blobs)
        second = build(turn_with_call(), mutations_ledger, blobs)
        assert first.events[0]["reportId"] == second.events[0]["reportId"]

        upgraded = build(turn_with_call(), mutations_ledger, blobs, analysis_version=2)
        assert upgraded.events[0]["reportId"] != first.events[0]["reportId"]

    def test_same_span_id_new_report_id_for_rolled_back_versions(self) -> None:
        before_hash = sha256("a\n")
        after_hash = sha256("b\n")
        mutations_ledger = ledger(
            1, [mutation("D:\\repo\\a.ts", "modify", {"before_hash": before_hash, "after_hash": after_hash})]
        )
        blobs = {before_hash: "a\n", after_hash: "b\n"}
        version_a = build(turn_with_call(), mutations_ledger, blobs)
        version_b = build(turn_with_call("call-9"), mutations_ledger, blobs)
        assert version_a.events[0]["spanId"] == version_b.events[0]["spanId"]
        assert version_a.events[0]["reportId"] != version_b.events[0]["reportId"]

    def test_truncates_files_beyond_per_turn_cap_deterministically(self) -> None:
        before_hash = sha256("a\n")
        after_hash = sha256("b\n")
        paths = [f"D:\\repo\\file-{index:03d}.ts" for index in range(260)]
        mutations_ledger = ledger(
            1,
            [mutation(path, "modify", {"before_hash": before_hash, "after_hash": after_hash}) for path in paths],
        )
        blobs = {before_hash: "a\n", after_hash: "b\n"}
        result = build(turn_with_call(), mutations_ledger, blobs)
        assert len(result.events) == 256
        # Lexicographic truncation: keep the first 256, surface the
        # remaining 4 paths.
        assert result.truncated_paths == paths[256:]
        assert len({event["reportId"] for event in result.events}) == 256
        # Two truncations of the same input yield identical results.
        assert build(turn_with_call(), mutations_ledger, blobs) == result

    def test_caps_blocks_per_file_at_64(self) -> None:
        before_lines = [f"same-{'x' if index % 2 == 0 else 'y'}" for index in range(200)]
        after_lines = [f"{line}!" if index % 2 == 0 else line for index, line in enumerate(before_lines)]
        before_hash = sha256("\n".join(before_lines))
        after_hash = sha256("\n".join(after_lines))
        result = build(
            turn_with_call(),
            ledger(
                1,
                [
                    mutation(
                        "D:\\repo\\many-edits.ts",
                        "modify",
                        {"before_hash": before_hash, "after_hash": after_hash},
                    )
                ],
            ),
            {before_hash: "\n".join(before_lines), after_hash: "\n".join(after_lines)},
        )
        # 100 alternating edit runs → truncated to 64 ranges.
        assert len(result.events[0]["blocks"]) == 64

    def test_omits_language_for_unknown_extensions_and_request_id_without_call(self) -> None:
        after_hash = sha256("content\n")
        result = build(
            single_turn([message("user"), turn_marker(1)]),
            ledger(
                1,
                [
                    mutation(
                        "D:\\repo\\README.unknownext",
                        "create",
                        {"after_hash": after_hash, "tool_call_id": "missing-call"},
                    )
                ],
            ),
            {after_hash: "content\n"},
        )
        assert "language" not in result.events[0]
        assert "requestId" not in result.events[0]

    def test_falls_back_to_heuristic_ownership_for_request_id(self) -> None:
        # Real engine shape: the message call_id is a provider id
        # (call_00_...), the ledger tool_call_id is a Chrys short id
        # (uuid hex[:12]) — no mapping; unique-write-call fallback
        # associates ownership, requestId takes the owning call's
        # message-level _chrys_operation_id.
        after_hash = sha256("123456789\n")
        result = build(
            single_turn(
                [
                    message("user"),
                    message(
                        "assistant",
                        {"_chrys_operation_id": "wire-1"},
                        [
                            {
                                "type": "function_call",
                                "call_id": "call_00_pKRVw4yi2OYSn1pUyLF46824",
                                "name": "write_file",
                                "arguments": "{}",
                                "additional_properties": {"_chrys_operation_id": "op-1"},
                            }
                        ],
                    ),
                    message(
                        "tool",
                        None,
                        [{"type": "function_result", "call_id": "call_00_pKRVw4yi2OYSn1pUyLF46824", "result": "ok"}],
                    ),
                    turn_marker(1),
                ]
            ),
            ledger(
                1,
                [mutation("D:\\repo\\test1.txt", "create", {"after_hash": after_hash, "tool_call_id": "2872b118b0b2"})],
            ),
            {after_hash: "123456789\n"},
        )
        assert result.events[0]["requestId"] == "wire-1"

    def test_resolves_request_id_by_timing_window_and_refuses_ambiguity(self) -> None:
        a_start = "2026-10-03T13:47:55.819516+00:00"
        b_start = "2026-10-03T13:50:00.000000+00:00"

        def write_turn() -> TurnSegment:
            return single_turn(
                [
                    message("user"),
                    message(
                        "assistant",
                        {"_chrys_operation_id": "wire-a"},
                        [
                            {
                                "type": "function_call",
                                "call_id": "call_00_A",
                                "name": "write_file",
                                "arguments": "{}",
                                "additional_properties": {
                                    "_chrys_timing": {
                                        "started_at": a_start,
                                        "finished_at": "2026-10-03T13:47:58.630065+00:00",
                                    }
                                },
                            }
                        ],
                    ),
                    message("tool", None, [{"type": "function_result", "call_id": "call_00_A", "result": "ok"}]),
                    message(
                        "assistant",
                        {"_chrys_operation_id": "wire-b"},
                        [
                            {
                                "type": "function_call",
                                "call_id": "call_00_B",
                                "name": "write_file",
                                "arguments": "{}",
                                "additional_properties": {
                                    "_chrys_timing": {
                                        "started_at": b_start,
                                        "finished_at": "2026-10-03T13:50:02.000000+00:00",
                                    }
                                },
                            }
                        ],
                    ),
                    message("tool", None, [{"type": "function_result", "call_id": "call_00_B", "result": "ok"}]),
                    turn_marker(1),
                ]
            )

        after_hash = sha256("b-after\n")

        # Mutation time inside call B's window → requestId owned by
        # wire-b.
        owned = build(
            write_turn(),
            ledger(
                1,
                [
                    mutation(
                        "D:\\repo\\b.txt",
                        "create",
                        {
                            "after_hash": after_hash,
                            "tool_call_id": "bbbbbbbbbbbb",
                            "t_start": datetime.fromisoformat(b_start).timestamp(),
                        },
                    )
                ],
            ),
            {after_hash: "b-after\n"},
        )
        assert owned.events[0]["requestId"] == "wire-b"

        # Ambiguity refused: two mutations inside the single call's
        # window (ownership cannot pick one) → no guessing, requestId
        # omitted (same basis as the tool-events line-count columns).
        ambiguous = build(
            single_turn(
                [
                    message("user"),
                    message(
                        "assistant",
                        {"_chrys_operation_id": "wire-a"},
                        [
                            {
                                "type": "function_call",
                                "call_id": "call_00_A",
                                "name": "write_file",
                                "arguments": "{}",
                                "additional_properties": {
                                    "_chrys_timing": {
                                        "started_at": a_start,
                                        "finished_at": "2026-10-03T13:47:58.630065+00:00",
                                    }
                                },
                            }
                        ],
                    ),
                    message("tool", None, [{"type": "function_result", "call_id": "call_00_A", "result": "ok"}]),
                    turn_marker(1),
                ]
            ),
            ledger(
                1,
                [
                    mutation(
                        "D:\\repo\\x.txt",
                        "create",
                        {
                            "after_hash": after_hash,
                            "tool_call_id": "xxxxxxxxxxxx",
                            "t_start": datetime.fromisoformat(a_start).timestamp(),
                        },
                    ),
                    mutation(
                        "D:\\repo\\y.txt",
                        "create",
                        {
                            "after_hash": after_hash,
                            "tool_call_id": "yyyyyyyyyyyy",
                            "t_start": datetime.fromisoformat(a_start).timestamp(),
                        },
                    ),
                ],
            ),
            {after_hash: "x\n"},
        )
        assert len(ambiguous.events) == 2
        for event in ambiguous.events:
            assert "requestId" not in event

    def test_derives_filepath_relative_to_primary_cwd_outside_git(self) -> None:
        outside_git = FakeGitContext(git_root=None)
        after_hash = sha256("x\n")
        context = EventCommonContext(
            session_id=SESSION_ID,
            attribution=None,
            product_name="repo",
            project_name="repo",
            plugin_version="0.28.0",
            primary_cwd="D:\\work",
            git=None,
        )
        result = build(
            turn_with_call(),
            ledger(1, [mutation("D:\\work\\notes\\a.md", "create", {"after_hash": after_hash})]),
            {after_hash: "x\n"},
            git_context=outside_git,
            context=context,
        )
        # No git root → relative to primary_cwd (affects reportId
        # derivation; filepath itself is a focus field, not emitted).
        assert len(result.events) == 1
        rebuild = build(
            turn_with_call(),
            ledger(1, [mutation("D:\\work\\notes\\a.md", "create", {"after_hash": after_hash})]),
            {after_hash: "x\n"},
            git_context=outside_git,
            context=context,
        )
        assert rebuild.events[0]["reportId"] == result.events[0]["reportId"]

    def test_counts_crlf_blobs_by_lf_without_changing_line_counts(self) -> None:
        before_hash = sha256("a\r\nb\r\n")
        after_hash = sha256("a\r\nx\r\n")
        result = build(
            turn_with_call(),
            ledger(
                1,
                [mutation("D:\\repo\\src\\a.ts", "modify", {"before_hash": before_hash, "after_hash": after_hash})],
            ),
            {before_hash: "a\r\nb\r\n", after_hash: "a\r\nx\r\n"},
        )
        # \r stays inside line content without changing line counts:
        # same range basis as LF-equivalent content (plan §6.3 item 8).
        assert result.events[0]["blocks"] == [{"rangeStart": 2, "rangeEnd": 3}]

    def test_normalizes_fallback_filepath_separators_for_report_id(self) -> None:
        outside_git = FakeGitContext(git_root=None)
        after_hash = sha256("x\n")
        context = EventCommonContext(
            session_id=SESSION_ID,
            attribution=None,
            product_name="repo",
            project_name="repo",
            plugin_version="0.28.0",
            primary_cwd="D:\\work",
            git=None,
        )
        with_backslashes = build(
            turn_with_call(),
            ledger(1, [mutation("E:\\outside\\a.ts", "create", {"after_hash": after_hash})]),
            {after_hash: "x\n"},
            git_context=outside_git,
            context=context,
        )
        with_slashes = build(
            turn_with_call(),
            ledger(1, [mutation("E:/outside/a.ts", "create", {"after_hash": after_hash})]),
            {after_hash: "x\n"},
            git_context=outside_git,
            context=context,
        )
        # Fallback (outside the git root and primary_cwd) unifies '/'
        # separators: the same path in both spellings derives the same
        # reportId (plan §6.3 item 8).
        assert UUID_FORM.fullmatch(with_backslashes.events[0]["reportId"])
        assert with_backslashes.events[0]["reportId"] == with_slashes.events[0]["reportId"]

    def test_lowercases_extension_when_inferring_language(self) -> None:
        after_hash = sha256("x\n")
        result = build(
            turn_with_call(),
            ledger(1, [mutation("D:\\repo\\src\\Widget.TS", "create", {"after_hash": after_hash})]),
            {after_hash: "x\n"},
        )
        assert result.events[0]["language"] == "typescript"


class TestAnalyzeSessionRevisionIntegration:
    def test_produces_tool_events_followed_by_ai_code_events(self) -> None:
        before_hash = sha256("a\nb\n")
        after_hash = sha256("a\nx\nb\n")
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
                    message("user"),
                    message(
                        "assistant",
                        {"_chrys_operation_id": "wire-1"},
                        [
                            {
                                "type": "function_call",
                                "call_id": "call-1",
                                "name": "edit_file",
                                "arguments": "{}",
                                "additional_properties": {
                                    "_chrys_operation_id": "op-1",
                                    "_chrys_tool_kind": "filesystem.write",
                                },
                            }
                        ],
                    ),
                    message(
                        "tool",
                        None,
                        [{"type": "function_result", "call_id": "call-1", "result": "ok", "additional_properties": {}}],
                    ),
                    turn_marker(1),
                ],
                "turn_counter": 1,
                "chrys_mutations": ledger(
                    1,
                    [mutation("D:\\repo\\src\\a.ts", "modify", {"before_hash": before_hash, "after_hash": after_hash})],
                ),
            },
        }

        def run() -> Any:
            return analyze_session_revision(
                SessionRevisionInput(
                    session_id=SESSION_ID,
                    revision_hash="0" * 64,
                    envelope=envelope,
                    source_path="D:\\sessions\\session.json",
                    analysis_version=7,
                    blob_reader=MemoryBlobReader({before_hash: "a\nb\n", after_hash: "a\nx\nb\n"}),
                    git_context=FakeGitContext(),
                )
            )

        result = run()
        assert result["aiCodeTruncatedPaths"] == []
        assert [event["kind"] for event in result["reportEvents"]] == [
            "tool-use-saved",
            "tool-status-updated",
            "ai-code-saved",
        ]
        ai_code = result["reportEvents"][2]
        assert ai_code["kind"] == "ai-code-saved"
        assert ai_code["requestId"] == "wire-1"
        # Revision-level idempotence: rerunning the same input (a pure
        # function) yields identical events.
        assert run() == result


class TestSessionMutationBlobReader:
    def test_skips_blobs_beyond_2mb_and_enforces_boundary(self, tmp_path: Path) -> None:
        session_directory = tmp_path / "session"
        (session_directory / "mutations").mkdir(parents=True)
        small_hash = sha256("small\n")
        (session_directory / "mutations" / small_hash).write_text("small\n", encoding="utf-8")
        large_hash = sha256("large")
        (session_directory / "mutations" / large_hash).write_text("x" * (2 * 1024 * 1024 + 1), encoding="utf-8")

        reader = SessionMutationBlobReader(str(session_directory))
        assert reader.read_blob_text(small_hash) == "small\n"
        # Over the cap is a skip: None (blocks source missing, the
        # event survives).
        assert reader.read_blob_text(large_hash) is None
        # Illegal hash (path traversal) refused.
        assert reader.read_blob_text("../escape") is None
