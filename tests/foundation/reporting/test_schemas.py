# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Unit tests for the Chrys session reporting contract validation (single source of truth)."""

from __future__ import annotations

from chrys.foundation.reporting.schemas import (
    AI_CODE_SAVE_ENDPOINT,
    EVENT_REACTION_ENDPOINT,
    TOOL_DETAIL_SAVE_ENDPOINT,
    parse_report_version,
    report_is_accepted,
    validate_report_body,
)


def _save_body() -> dict[str, object]:
    return {
        "productName": "icode",
        "funcType": 3,
        "funcName": "read_file",
        "funcId": "a" * 32,
        "value": "src/a.js",
        "fileName": "src/a.js",
        "codeStatus": 0,
        "sessionId": "session-1",
        "requestId": "b" * 32,
        "spanId": "11111111-2222-4333-8444-555555555555",
        "channelType": "tui",
        "unknownExtraField": {"kept": True},
    }


def test_tool_detail_save_accepts_valid_body_with_unknown_fields() -> None:
    assert validate_report_body(TOOL_DETAIL_SAVE_ENDPOINT, _save_body()) is None


def test_tool_detail_save_rejects_missing_required_field() -> None:
    body = _save_body()
    del body["productName"]
    problem = validate_report_body(TOOL_DETAIL_SAVE_ENDPOINT, body)
    assert problem is not None
    assert "productName" in problem


def test_tool_detail_save_rejects_wrong_types() -> None:
    body = _save_body() | {"funcType": True}
    assert "funcType" in (validate_report_body(TOOL_DETAIL_SAVE_ENDPOINT, body) or "")
    body = _save_body() | {"funcType": -1}
    assert "funcType" in (validate_report_body(TOOL_DETAIL_SAVE_ENDPOINT, body) or "")
    body = _save_body() | {"value": 42}
    assert "value" in (validate_report_body(TOOL_DETAIL_SAVE_ENDPOINT, body) or "")
    body = _save_body() | {"extra": "not-an-object"}
    assert "extra" in (validate_report_body(TOOL_DETAIL_SAVE_ENDPOINT, body) or "")


def test_batch_requires_non_empty_array_of_valid_items() -> None:
    from chrys.foundation.reporting.schemas import TOOL_DETAIL_BATCH_SAVE_ENDPOINT

    item = {
        "funcType": 0,
        "funcName": "java_code_review",
        "sessionId": "session-1",
        "spanId": "11111111-2222-4333-8444-555555555555",
    }
    assert validate_report_body(TOOL_DETAIL_BATCH_SAVE_ENDPOINT, [item]) is None
    assert validate_report_body(TOOL_DETAIL_BATCH_SAVE_ENDPOINT, []) is not None
    assert validate_report_body(TOOL_DETAIL_BATCH_SAVE_ENDPOINT, {"not": "array"}) is not None
    problem = validate_report_body(TOOL_DETAIL_BATCH_SAVE_ENDPOINT, [{**item, "funcName": ""}])
    assert problem is not None
    assert "[0].funcName" in problem


def test_update_requires_func_id_and_code_status() -> None:
    from chrys.foundation.reporting.schemas import TOOL_DETAIL_UPDATE_ENDPOINT

    valid = {"funcId": "a" * 32, "codeStatus": 1, "addedLines": 3, "deletedLines": 1}
    assert validate_report_body(TOOL_DETAIL_UPDATE_ENDPOINT, valid) is None
    assert validate_report_body(TOOL_DETAIL_UPDATE_ENDPOINT, {"codeStatus": 1}) is not None
    assert validate_report_body(TOOL_DETAIL_UPDATE_ENDPOINT, {"funcId": "a" * 32}) is not None
    problem = validate_report_body(TOOL_DETAIL_UPDATE_ENDPOINT, {**valid, "codeStatus": -1})
    assert "codeStatus" in (problem or "")


def test_ai_code_save_validates_blocks_and_optional_fields() -> None:
    valid = {
        "reportId": "report-1",
        "sourceType": "file_edit",
        "blocks": [{"rangeStart": 0, "rangeEnd": 5, "snippet": "print(1)"}],
        "filepath": "src/a.py",
    }
    assert validate_report_body(AI_CODE_SAVE_ENDPOINT, valid) is None
    # An empty array is valid: a missing/skipped/oversized blob keeps the event with zero blocks.
    assert validate_report_body(AI_CODE_SAVE_ENDPOINT, {**valid, "blocks": []}) is None
    problem = validate_report_body(AI_CODE_SAVE_ENDPOINT, {**valid, "blocks": [{"rangeStart": 0}]})
    assert "blocks[0].rangeEnd" in (problem or "")
    problem = validate_report_body(AI_CODE_SAVE_ENDPOINT, {**valid, "sourceType": ""})
    assert "sourceType" in (problem or "")
    problem = validate_report_body(AI_CODE_SAVE_ENDPOINT, {**valid, "blocks": [{"rangeStart": 0, "rangeEnd": 1}] * 65})
    assert "blocks" in (problem or "")


def test_event_reaction_accepts_any_object() -> None:
    assert validate_report_body(EVENT_REACTION_ENDPOINT, {"anything": True}) is None
    assert validate_report_body(EVENT_REACTION_ENDPOINT, ["not", "object"]) is not None


def test_validate_report_body_rejects_unknown_endpoint() -> None:
    problem = validate_report_body("/csas/telemetry/api/v1/unknown/save", {})
    assert problem is not None
    assert "unknown_endpoint" in problem


def test_report_is_accepted_handles_both_envelopes() -> None:
    success = {"success": True, "message": "保存成功", "code": 200, "result": None, "e": None}
    rejected = {"success": False, "message": "simulated business failure", "code": 500}
    assert report_is_accepted(TOOL_DETAIL_SAVE_ENDPOINT, status_code=200, payload=success)
    assert not report_is_accepted(TOOL_DETAIL_SAVE_ENDPOINT, status_code=200, payload=rejected)
    assert not report_is_accepted(TOOL_DETAIL_SAVE_ENDPOINT, status_code=500, payload=success)

    assert report_is_accepted(AI_CODE_SAVE_ENDPOINT, status_code=200, payload={"code": 200, "data": None})
    assert not report_is_accepted(AI_CODE_SAVE_ENDPOINT, status_code=200, payload={"code": 500, "data": None})


def test_parse_report_version_requires_wellformed_headers() -> None:
    content_hash = "ab" * 32
    assert parse_report_version({"X-Turn-Content-Hash": content_hash, "X-Analysis-Version": "3"}) is not None
    # Header names are case-insensitive.
    assert parse_report_version({"x-turn-content-hash": content_hash, "x-analysis-version": "3"}) is not None
    # Missing headers, a malformed hash or a non-positive version all mean "no version".
    assert parse_report_version({"X-Analysis-Version": "3"}) is None
    assert parse_report_version({"X-Turn-Content-Hash": "zz" * 32, "X-Analysis-Version": "3"}) is None
    assert parse_report_version({"X-Turn-Content-Hash": content_hash, "X-Analysis-Version": "0"}) is None
    assert parse_report_version({"X-Turn-Content-Hash": content_hash, "X-Analysis-Version": "1.5"}) is None
