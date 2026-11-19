# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Directional experiments for final ACP response model-request identity."""

from __future__ import annotations

from pathlib import Path

from chrys.app.acp.bridge import with_chrys_metadata
from chrys.foundation.models.history_markers import HistoryMarkerKind
from chrys.foundation.models.turns import turn_slices
from chrys.foundation.trajectory.metadata import ANALYTICS_ITEM_ID_KEY
from chrys.kernel import Message
from chrys.service.trajectory.state import TurnRecord

_ATTEMPT_KEY = "_chrys_request_attempt_id"
_A_OLD = "00000000-0000-4000-8000-000000000001"
_A_NEW = "00000000-0000-4000-8000-000000000002"
_A_THIRD = "00000000-0000-4000-8000-000000000003"


def _message(
    role: str,
    text: str,
    *,
    item_id: str | None = None,
    attempt_id: str | None = None,
    marker: str | None = None,
    injected: bool = False,
) -> Message:
    message = Message(role, [text])
    if item_id is not None:
        message.additional_properties[ANALYTICS_ITEM_ID_KEY] = item_id
    if attempt_id is not None:
        message.additional_properties[_ATTEMPT_KEY] = attempt_id
    if marker is not None:
        message.additional_properties[HistoryMarkerKind.KEY] = marker
    if injected:
        message.additional_properties[HistoryMarkerKind.INJECTED_KEY] = True
    return message


def _record(number: int, turn_id: str, opening_item_id: str) -> TurnRecord:
    return TurnRecord(turn_number=number, turn_id=turn_id, opening_item_id=opening_item_id)


def _select_response_attempt(messages: list[Message], records: list[TurnRecord], turn_id: str) -> str | None:
    """Experiment only: select the last main response within an exact logical turn."""
    turn_by_opener = {
        record.opening_item_id: record.turn_id for record in records if record.opening_item_id is not None
    }
    last_response: Message | None = None
    for start, end in turn_slices(messages):
        opener = messages[start].additional_properties.get(ANALYTICS_ITEM_ID_KEY)
        if turn_by_opener.get(opener) != turn_id:
            continue
        for message in messages[start:end]:
            if message.role == "assistant" and HistoryMarkerKind.KEY not in message.additional_properties:
                last_response = message
    if last_response is None:
        return None
    attempt_id = last_response.additional_properties.get(_ATTEMPT_KEY)
    return attempt_id if isinstance(attempt_id, str) and attempt_id else None


def test_selects_exact_turn_and_last_main_response() -> None:
    messages = [
        _message("user", "first", item_id="open-a"),
        _message("assistant", "first answer", attempt_id=_A_OLD),
        _message("user", "second", item_id="open-b"),
        _message("assistant", "tool call", attempt_id=_A_NEW),
        _message("tool", "tool result"),
        _message("assistant", "final answer", attempt_id=_A_THIRD),
    ]
    records = [_record(1, "turn-a", "open-a"), _record(2, "turn-b", "open-b")]

    assert _select_response_attempt(messages, records, "turn-a") == _A_OLD
    assert _select_response_attempt(messages, records, "turn-b") == _A_THIRD
    assert _select_response_attempt(messages, records, "turn-missing") is None


def test_last_response_without_attempt_does_not_reuse_earlier_attempt() -> None:
    messages = [
        _message("user", "prompt", item_id="open-a"),
        _message("assistant", "tracked response", attempt_id=_A_OLD),
        _message("assistant", "untracked last response"),
    ]

    assert _select_response_attempt(messages, [_record(1, "turn-a", "open-a")], "turn-a") is None


def test_history_marker_is_not_a_model_response() -> None:
    messages = [
        _message("user", "prompt", item_id="open-a"),
        _message("assistant", "last model response", attempt_id=_A_OLD),
        _message(
            "assistant",
            "interrupted",
            attempt_id=_A_NEW,
            marker=HistoryMarkerKind.INTERRUPTED,
        ),
    ]

    assert _select_response_attempt(messages, [_record(1, "turn-a", "open-a")], "turn-a") == _A_OLD


def test_injected_retry_stays_in_logical_turn_and_new_response_wins() -> None:
    messages = [
        _message("user", "prompt", item_id="open-a"),
        _message("assistant", "before retry", attempt_id=_A_OLD),
        _message("user", "retry guidance", injected=True),
        _message("assistant", "after retry", attempt_id=_A_NEW),
    ]

    assert _select_response_attempt(messages, [_record(1, "turn-a", "open-a")], "turn-a") == _A_NEW


def test_missing_or_compacted_opener_fails_closed(tmp_path: Path) -> None:
    messages = [_message("assistant", "orphan", attempt_id=_A_OLD)]
    records = [_record(1, "turn-a", "open-a")]

    assert _select_response_attempt(messages, records, "turn-a") is None
    assert list(tmp_path.iterdir()) == []


def test_live_selection_needs_no_session_files(tmp_path: Path) -> None:
    messages = [
        _message("user", "prompt", item_id="open-a"),
        _message("assistant", "answer", attempt_id=_A_OLD),
    ]

    assert _select_response_attempt(messages, [_record(1, "turn-a", "open-a")], "turn-a") == _A_OLD
    assert list(tmp_path.iterdir()) == []


def test_custom_identity_preserves_upstream_chrys_metadata() -> None:
    meta = with_chrys_metadata(
        {
            "agent-studio.dev/telemetry": {
                "schemaVersion": 1,
                "sessionId": "3f2504e0-4f89-11d3-9a0c-0305e82c3301",
                "requestId": _A_OLD,
                "spanId": "turn-a",
            }
        },
        {"turnId": "turn-a", "turnNumber": 1},
    )

    assert meta["chrys"] == {"turnId": "turn-a", "turnNumber": 1}
    assert meta["agent-studio.dev/telemetry"]["requestId"] == _A_OLD
