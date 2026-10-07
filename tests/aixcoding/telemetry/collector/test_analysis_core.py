# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Analysis core equivalence tests (scenarios ported from the TS
``analysis.test.ts`` / ``collector.test.ts``: expansion dedup, turn slicing,
pending regions, rollback overwrite, incremental computation)."""

from __future__ import annotations

from typing import Any

import pytest

from chrys.aixcoding.telemetry.collector.analysis.canonical import canonical_json_encode
from chrys.aixcoding.telemetry.collector.analysis.history import expand_history
from chrys.aixcoding.telemetry.collector.analysis.index import (
    ANALYSIS_VERSION,
    MalformedSessionError,
    SessionRevisionInput,
    analyze_session_revision,
)
from chrys.aixcoding.telemetry.collector.analysis.turns import (
    PriorTurnRef,
    compute_incremental,
    slice_turn_segments,
)

SESSION_ID = "4201eebc-ca45-4328-8882-272f3d7c41cb"


def user_message(text: str = "hi", **properties: Any) -> dict[str, Any]:
    return {
        "role": "user",
        "contents": [{"type": "text", "text": text, "additional_properties": {}}],
        "additional_properties": dict(properties),
    }


def assistant_message(**properties: Any) -> dict[str, Any]:
    return {"role": "assistant", "contents": [], "additional_properties": dict(properties)}


def turn_marker(turn_id: str, turn: int) -> dict[str, Any]:
    return {
        "role": "assistant",
        "contents": [],
        "additional_properties": {"_chrys_kind": "turn", "_turn_id": turn_id, "_turn": turn},
    }


class TestCanonical:
    def test_keys_sorted_and_values_distinct(self) -> None:
        assert canonical_json_encode({"b": 1, "a": None}) == '{"a":null,"b":1}'
        assert canonical_json_encode([1.0, 2]) == "[1,2]"  # 1.0 prints as 1 (TS parity)
        assert canonical_json_encode({"k": ""}) == '{"k":""}'
        assert canonical_json_encode({"k": 0}) == '{"k":0}'

    def test_nested_containers(self) -> None:
        value: dict[str, Any] = {"z": [{"b": 2, "a": 1}], "y": [3, [4, 5]]}
        assert canonical_json_encode(value) == '{"y":[3,[4,5]],"z":[{"a":1,"b":2}]}'


class TestExpandHistory:
    def test_summary_text_excluded_and_analytics_dedup(self) -> None:
        state: dict[str, Any] = {
            "compressed_msgs": [
                {
                    "turn_range": [1, 2],
                    "messages": [
                        user_message("archived", _chrys_analytics_item_id="occ-1"),
                        assistant_message(_chrys_kind="summary"),
                    ],
                }
            ],
            "messages": [
                user_message("live-twin", _chrys_analytics_item_id="occ-1"),  # dedup (archive wins)
                user_message("fresh"),
            ],
        }
        entries = expand_history(state)
        texts = [entry.message["contents"][0]["text"] for entry in entries if entry.message["role"] == "user"]
        assert texts == ["archived", "fresh"]
        assert [entry.origin for entry in entries] == ["archive", "live"]

    def test_blocks_sorted_by_lower_bound_stably(self) -> None:
        state: dict[str, Any] = {
            "compressed_msgs": [
                {"turn_range": [5, 6], "messages": [user_message("late")]},
                {"turn_range": [1, 2], "messages": [user_message("early")]},
                {"turn_range": [1, 3], "messages": [user_message("same-bound")]},
            ],
            "messages": [],
        }
        texts = [entry.message["contents"][0]["text"] for entry in expand_history(state)]
        assert texts == ["early", "same-bound", "late"]


class TestSliceTurns:
    def test_closed_turn_and_pending_tail(self) -> None:
        entries = expand_history(
            {
                "messages": [
                    user_message("q1"),
                    assistant_message(),
                    turn_marker("turn_1", 1),
                    user_message("q2"),
                    assistant_message(),  # no marker yet → pending
                ]
            }
        )
        segments = slice_turn_segments(entries)
        assert [segment.turn_id for segment in segments] == ["turn_1", "pending-1"]
        assert segments[0].status == "ok"
        assert segments[0].turn_index == 1
        assert segments[1].status == "pending"

    def test_marker_only_numbering_without_turn_id(self) -> None:
        entries = expand_history(
            {
                "messages": [
                    user_message("q"),
                    {
                        "role": "assistant",
                        "contents": [],
                        "additional_properties": {"_chrys_kind": "turn", "_turn": 7},
                    },
                ]
            }
        )
        segments = slice_turn_segments(entries)
        assert segments[0].turn_id == "turn_7"

    def test_rollback_overwrites_in_place(self) -> None:
        entries = expand_history(
            {
                "messages": [
                    user_message("v1"),
                    turn_marker("turn_1", 1),
                    user_message("v2"),
                    turn_marker("turn_1", 1),  # rollback: same id again
                    user_message("next"),
                    turn_marker("turn_2", 2),
                ]
            }
        )
        segments = slice_turn_segments(entries)
        assert [segment.turn_id for segment in segments] == ["turn_1", "turn_2"]
        # turn_1 reflects the LAST view (v2).
        texts = [
            entry.message["contents"][0]["text"] for entry in segments[0].entries if entry.message["role"] == "user"
        ]
        assert "v2" in texts

    def test_displaced_opener_becomes_pending(self) -> None:
        entries = expand_history(
            {
                "messages": [
                    user_message("q1"),
                    user_message("q2"),  # displaces unclosed q1 → pending
                    turn_marker("turn_1", 1),
                ]
            }
        )
        segments = slice_turn_segments(entries)
        assert [segment.turn_id for segment in segments] == ["pending-1", "turn_1"]

    def test_visible_message_count(self) -> None:
        entries = expand_history(
            {
                "messages": [
                    user_message("q"),
                    {
                        "role": "assistant",
                        "contents": [{"type": "text", "text": "answer"}],
                        "additional_properties": {},
                    },
                    turn_marker("turn_1", 1),
                ]
            }
        )
        segments = slice_turn_segments(entries)
        assert segments[0].visible_message_count == 2


class TestIncremental:
    def test_new_and_changed_turns_are_incremental(self) -> None:
        entries = expand_history(
            {
                "messages": [
                    user_message("q1"),
                    turn_marker("turn_1", 1),
                    user_message("q2"),
                    turn_marker("turn_2", 2),
                ]
            }
        )
        segments = slice_turn_segments(entries)
        first_hash = segments[0].content_hash

        # Nothing prior → everything incremental.
        assert [s.turn_id for s in compute_incremental(segments, [])] == ["turn_1", "turn_2"]
        # turn_1 already reported with same hash → only turn_2 incremental.
        prior = [PriorTurnRef(turn_id="turn_1", content_hash=first_hash)]
        assert [s.turn_id for s in compute_incremental(segments, prior)] == ["turn_2"]
        # Content changed (different hash) → turn_1 re-enters the increment.
        prior_changed = [PriorTurnRef(turn_id="turn_1", content_hash="0" * 64)]
        assert [s.turn_id for s in compute_incremental(segments, prior_changed)] == ["turn_1", "turn_2"]

    def test_pending_turns_never_incremental(self) -> None:
        entries = expand_history({"messages": [user_message("q")]})
        segments = slice_turn_segments(entries)
        assert segments[0].status == "pending"
        assert compute_incremental(segments, []) == []


def _envelope(state: dict[str, Any], kind: str = "chat") -> dict[str, Any]:
    return {
        "meta": {
            "schema_version": 1,
            "app_version": "0.28.0",
            "session_id": SESSION_ID,
            "created_at": "2026-10-02T09:14:03Z",
            "updated_at": "2026-10-02T09:20:11Z",
            "kind": kind,
            "title": "test session",
            "last_surface": "acp",
        },
        "state": state,
        "session_checkpoint_id": "checkpoint-1",
    }


_CHAT_STATE: dict[str, Any] = {
    "messages": [user_message("hi"), turn_marker("turn_1", 1)],
    "turn_counter": 1,
}


class TestAnalyzeSessionRevision:
    def test_produces_turn_facts_and_full_incrementals_for_chat(self) -> None:
        analysis = analyze_session_revision(
            SessionRevisionInput(
                session_id=SESSION_ID,
                revision_hash="a" * 64,
                envelope=_envelope(_CHAT_STATE),
                source_path="C:\\sessions\\session.json",
            )
        )
        assert analysis["sessionFacts"]["turnCount"] == 1
        assert [fact["turnId"] for fact in analysis["turnFacts"]] == ["turn_1"]
        assert [fact["turnId"] for fact in analysis["incremental"]] == ["turn_1"]
        assert analysis["reportEvents"] == []

    def test_removes_ledger_matched_turns_from_incrementals(self) -> None:
        first = analyze_session_revision(
            SessionRevisionInput(
                session_id=SESSION_ID,
                revision_hash="a" * 64,
                envelope=_envelope(_CHAT_STATE),
                source_path="C:\\sessions\\session.json",
            )
        )
        prior_turns = [
            PriorTurnRef(turn_id=fact["turnId"], content_hash=fact["contentHash"]) for fact in first["turnFacts"]
        ]
        second = analyze_session_revision(
            SessionRevisionInput(
                session_id=SESSION_ID,
                revision_hash="b" * 64,
                envelope=_envelope(_CHAT_STATE),
                source_path="C:\\sessions\\session.json",
                prior_turns=prior_turns,
            )
        )
        assert second["turnFacts"] == first["turnFacts"]
        assert second["incremental"] == []

    def test_keeps_workflow_sessions_to_session_facts_only(self) -> None:
        analysis = analyze_session_revision(
            SessionRevisionInput(
                session_id=SESSION_ID,
                revision_hash="a" * 64,
                envelope=_envelope({"runs": []}, "workflow"),
                source_path="C:\\sessions\\session.json",
            )
        )
        assert analysis["sessionFacts"]["kind"] == "workflow"
        assert analysis["sessionFacts"]["turnCount"] is None
        assert analysis["turnFacts"] == []
        assert analysis["incremental"] == []

    def test_idempotent_for_identical_inputs(self) -> None:
        def run() -> dict[str, Any]:
            return analyze_session_revision(
                SessionRevisionInput(
                    session_id=SESSION_ID,
                    revision_hash="a" * 64,
                    envelope=_envelope(_CHAT_STATE),
                    source_path="C:\\sessions\\session.json",
                )
            )

        assert run() == run()
        assert ANALYSIS_VERSION == 2

    def test_session_level_fields_never_enter_turn_content_hash(self) -> None:
        first = analyze_session_revision(
            SessionRevisionInput(
                session_id=SESSION_ID,
                revision_hash="a" * 64,
                envelope=_envelope(_CHAT_STATE),
                source_path="C:\\sessions\\session.json",
            )
        )
        prior_turns = [
            PriorTurnRef(turn_id=fact["turnId"], content_hash=fact["contentHash"]) for fact in first["turnFacts"]
        ]
        second = analyze_session_revision(
            SessionRevisionInput(
                session_id=SESSION_ID,
                revision_hash="b" * 64,
                envelope=_envelope({**_CHAT_STATE, "total_session_tokens": 99_999, "turn_counter": 1}),
                source_path="C:\\sessions\\session.json",
                prior_turns=prior_turns,
            )
        )
        assert second["incremental"] == []

    def test_malformed_envelopes_raise(self) -> None:
        with pytest.raises(MalformedSessionError):
            analyze_session_revision(
                SessionRevisionInput(
                    session_id=SESSION_ID,
                    revision_hash="a" * 64,
                    envelope=[1, 2],
                    source_path="C:\\sessions\\session.json",
                )
            )
        with pytest.raises(MalformedSessionError):
            analyze_session_revision(
                SessionRevisionInput(
                    session_id=SESSION_ID,
                    revision_hash="a" * 64,
                    envelope={"meta": 42, "state": {}},
                    source_path="C:\\sessions\\session.json",
                )
            )
        with pytest.raises(MalformedSessionError):
            analyze_session_revision(
                SessionRevisionInput(
                    session_id=SESSION_ID,
                    revision_hash="a" * 64,
                    envelope=_envelope(_CHAT_STATE, "unknown-kind"),
                    source_path="C:\\sessions\\session.json",
                )
            )

    def test_session_id_mismatch_raises(self) -> None:
        with pytest.raises(MalformedSessionError):
            analyze_session_revision(
                SessionRevisionInput(
                    session_id="other-session",
                    revision_hash="a" * 64,
                    envelope=_envelope(_CHAT_STATE),
                    source_path="C:\\sessions\\session.json",
                )
            )
