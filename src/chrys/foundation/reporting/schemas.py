# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Shared contract for the Chrys session reporting 4+1 endpoints.

Single source of truth: the sending side
(:mod:`chrys.foundation.reporting.collector`) and the local receiving side
(``scripts/telemetry_mock.py``) both validate through this module, so the two
sides cannot drift apart. The contract is ported from the AIxCoding desktop
client's ``packages/contracts/src/chrys-telemetry-report.ts``; field semantics
and idempotency keys are documented in this package's ``docs/design.md``.

Validation follows receiving-side semantics: the required set is minimal (only
what breaks positioning or statistics is rejected), type errors always fail,
and unknown fields are ignored (the original zod contract used
``.passthrough()``).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

API_PREFIX = "/csas/telemetry/api/v1/"
TOOL_DETAIL_SAVE_ENDPOINT = f"{API_PREFIX}tool-detail/save"
TOOL_DETAIL_BATCH_SAVE_ENDPOINT = f"{API_PREFIX}tool-detail/batch-save"
TOOL_DETAIL_UPDATE_ENDPOINT = f"{API_PREFIX}tool-detail/update"
AI_CODE_SAVE_ENDPOINT = f"{API_PREFIX}ai-code/save"
EVENT_REACTION_ENDPOINT = f"{API_PREFIX}event-reaction/save"

REPORT_ENDPOINTS = (
    TOOL_DETAIL_SAVE_ENDPOINT,
    TOOL_DETAIL_BATCH_SAVE_ENDPOINT,
    TOOL_DETAIL_UPDATE_ENDPOINT,
    AI_CODE_SAVE_ENDPOINT,
    EVENT_REACTION_ENDPOINT,
)

# Idempotency helper headers (contract section 2.1): only tool-detail/save and
# ai-code/save carry them.
TURN_CONTENT_HASH_HEADER = "x-turn-content-hash"
ANALYSIS_VERSION_HEADER = "x-analysis-version"

MAX_OPTIONAL_STRING_LENGTH = 64 * 1024
_MAX_NAME_LENGTH = 256
_MAX_FUNC_ID_LENGTH = 512
_MAX_SOURCE_TYPE_LENGTH = 64
_MAX_BLOCKS = 64

# Channel and session common optional fields (shared by save items and
# batch-save elements).
_REPORT_COMMON_FIELDS = (
    "sessionId",
    "userId",
    "requestId",
    "spanId",
    "projectName",
    "channelType",
    "channelName",
    "channelVersion",
    "pluginVersion",
)

# Optional git attribution fields (tool-detail naming; ai-code names differ and
# is defined separately).
_TOOL_DETAIL_GIT_FIELDS = (
    "gitRemote",
    "gitBranch",
    "gitRevision",
    "gitOwner",
    "gitRepo",
)

_AI_CODE_OPTIONAL_STRING_FIELDS = (
    "sessionId",
    "spanId",
    "requestId",
    "channelType",
    "inputMethod",
    "language",
    "remoteUrl",
    "branch",
    "gitUserName",
    "gitUserEmail",
    "filepath",
)


@dataclass(frozen=True, slots=True)
class ReportVersion:
    """A report's version identity: part of the tool-detail/save idempotency key (contract section 4.3)."""

    turn_content_hash: str
    analysis_version: int


def parse_report_version(headers: Mapping[str, str]) -> ReportVersion | None:
    """Parse the idempotency helper headers; any missing or malformed header means "no version" (no folding)."""
    lowered = {name.lower(): value for name, value in headers.items()}
    content_hash = lowered.get(TURN_CONTENT_HASH_HEADER)
    version_text = lowered.get(ANALYSIS_VERSION_HEADER)
    if not isinstance(content_hash, str) or not isinstance(version_text, str):
        return None
    if len(content_hash) != 64 or any(character not in "0123456789abcdef" for character in content_hash):
        return None
    if not version_text.isdigit():
        return None
    version = int(version_text, 10)
    if version <= 0:
        return None
    return ReportVersion(turn_content_hash=content_hash, analysis_version=version)


def validate_report_body(endpoint: str, body: object) -> str | None:
    """Dispatch validation by endpoint; returns the first problem, or ``None`` when valid."""
    if endpoint == TOOL_DETAIL_SAVE_ENDPOINT:
        return validate_tool_detail_save(body)
    if endpoint == TOOL_DETAIL_BATCH_SAVE_ENDPOINT:
        return validate_tool_detail_batch(body)
    if endpoint == TOOL_DETAIL_UPDATE_ENDPOINT:
        return validate_tool_detail_update(body)
    if endpoint == AI_CODE_SAVE_ENDPOINT:
        return validate_ai_code_save(body)
    if endpoint == EVENT_REACTION_ENDPOINT:
        return validate_event_reaction(body)
    return f"unknown_endpoint: {endpoint}"


def validate_tool_detail_save(body: object) -> str | None:
    if not isinstance(body, dict):
        return _problem("", "invalid_type", "expected object")
    product_name = body.get("productName")
    if not isinstance(product_name, str) or len(product_name) > _MAX_NAME_LENGTH:
        return _problem("productName", "invalid_type", f"expected string of length <= {_MAX_NAME_LENGTH}")
    problem = _required_non_negative_int(body, "funcType")
    if problem is not None:
        return problem
    func_name = body.get("funcName")
    if not isinstance(func_name, str) or not func_name or len(func_name) > _MAX_NAME_LENGTH:
        return _problem("funcName", "invalid_type", f"expected string of length 1..{_MAX_NAME_LENGTH}")
    for field_name in ("funcId", "value", "fileName"):
        problem = _optional_string(body, field_name)
        if problem is not None:
            return problem
    problem = _optional_non_negative_int(body, "codeStatus")
    if problem is not None:
        return problem
    if "extra" in body and not isinstance(body["extra"], dict):
        return _problem("extra", "invalid_type", "expected object")
    return _validate_optional_field_sets(body)


def validate_tool_detail_batch(body: object) -> str | None:
    if not isinstance(body, list):
        return _problem("", "invalid_type", "expected array")
    if not body:
        return _problem("", "too_small", "expected array of length >= 1")
    for index, item in enumerate(body):
        problem = _validate_batch_item(item, f"[{index}]")
        if problem is not None:
            return problem
    return None


def validate_tool_detail_update(body: object) -> str | None:
    if not isinstance(body, dict):
        return _problem("", "invalid_type", "expected object")
    func_id = body.get("funcId")
    if not isinstance(func_id, str) or not func_id or len(func_id) > _MAX_FUNC_ID_LENGTH:
        return _problem("funcId", "invalid_type", f"expected string of length 1..{_MAX_FUNC_ID_LENGTH}")
    problem = _required_non_negative_int(body, "codeStatus")
    if problem is not None:
        return problem
    for field_name in ("funcName", "funcErrorMessage"):
        problem = _optional_string(body, field_name)
        if problem is not None:
            return problem
    for field_name in ("originalLines", "addedLines", "deletedLines"):
        problem = _optional_non_negative_int(body, field_name)
        if problem is not None:
            return problem
    return None


def validate_ai_code_save(body: object) -> str | None:
    if not isinstance(body, dict):
        return _problem("", "invalid_type", "expected object")
    report_id = body.get("reportId")
    if not isinstance(report_id, str) or not report_id or len(report_id) > _MAX_NAME_LENGTH:
        return _problem("reportId", "invalid_type", f"expected string of length 1..{_MAX_NAME_LENGTH}")
    source_type = body.get("sourceType")
    if not isinstance(source_type, str) or not source_type or len(source_type) > _MAX_SOURCE_TYPE_LENGTH:
        return _problem("sourceType", "invalid_type", f"expected string of length 1..{_MAX_SOURCE_TYPE_LENGTH}")
    blocks = body.get("blocks")
    if not isinstance(blocks, list):
        return _problem("blocks", "invalid_type", "expected array")
    if len(blocks) > _MAX_BLOCKS:
        return _problem("blocks", "too_big", f"expected array of length <= {_MAX_BLOCKS}")
    # An empty array is valid: a missing/skipped/oversized blob still reports
    # the event with zero blocks (contract: the event is never dropped).
    for index, block in enumerate(blocks):
        problem = _validate_ai_code_block(block, f"blocks[{index}]")
        if problem is not None:
            return problem
    for field_name in _AI_CODE_OPTIONAL_STRING_FIELDS:
        problem = _optional_string(body, field_name)
        if problem is not None:
            return problem
    return None


def validate_event_reaction(body: object) -> str | None:
    """Reserved endpoint (desktop GUI event-reaction instrumentation): accepts any object verbatim."""
    if not isinstance(body, dict):
        return _problem("", "invalid_type", "expected object")
    return None


def report_is_accepted(endpoint: str, *, status_code: int, payload: object) -> bool:
    """Whether a report response is a business success (ai-code/save uses a different envelope)."""
    if status_code != 200 or not isinstance(payload, dict):
        return False
    if endpoint == AI_CODE_SAVE_ENDPOINT:
        return payload.get("code") == 200
    return payload.get("success") is True


# --------------------------------------------------------------------- internals


def _validate_batch_item(item: object, path: str) -> str | None:
    """A batch element's required set is smaller than a single save's (no productName; legacy batches omit it)."""
    if not isinstance(item, dict):
        return _problem(path, "invalid_type", "expected object")
    problem = _required_non_negative_int(item, "funcType", path=path)
    if problem is not None:
        return problem
    func_name = item.get("funcName")
    if not isinstance(func_name, str) or not func_name or len(func_name) > _MAX_NAME_LENGTH:
        return _problem(f"{path}.funcName", "invalid_type", f"expected string of length 1..{_MAX_NAME_LENGTH}")
    return _validate_optional_field_sets(item, path=path)


def _validate_ai_code_block(block: object, path: str) -> str | None:
    if not isinstance(block, dict):
        return _problem(path, "invalid_type", "expected object")
    for field_name in ("rangeStart", "rangeEnd"):
        problem = _required_non_negative_int(block, field_name, path=f"{path}.{field_name}")
        if problem is not None:
            return problem
    return _optional_string(block, "snippet", path=f"{path}.snippet")


def _validate_optional_field_sets(record: dict[str, Any], *, path: str = "") -> str | None:
    prefix = f"{path}." if path else ""
    for field_name in (*_REPORT_COMMON_FIELDS, *_TOOL_DETAIL_GIT_FIELDS):
        problem = _optional_string(record, field_name, path=f"{prefix}{field_name}")
        if problem is not None:
            return problem
    return None


def _required_non_negative_int(record: dict[str, Any], field_name: str, *, path: str | None = None) -> str | None:
    if field_name not in record:
        return _problem(path or field_name, "invalid_type", "required")
    return _check_non_negative_int(record[field_name], path or field_name)


def _optional_non_negative_int(record: dict[str, Any], field_name: str, *, path: str | None = None) -> str | None:
    if field_name not in record:
        return None
    return _check_non_negative_int(record[field_name], path or field_name)


def _check_non_negative_int(value: object, path: str) -> str | None:
    # ``bool`` is a subclass of ``int``; the contract's integers never accept one.
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return _problem(path, "invalid_type", "expected non-negative integer")
    return None


def _optional_string(record: dict[str, Any], field_name: str, *, path: str | None = None) -> str | None:
    if field_name not in record:
        return None
    value = record[field_name]
    if not isinstance(value, str):
        return _problem(path or field_name, "invalid_type", "expected string")
    if len(value) > MAX_OPTIONAL_STRING_LENGTH:
        return _problem(path or field_name, "too_big", f"expected string of length <= {MAX_OPTIONAL_STRING_LENGTH}")
    return None


def _problem(field_name: str, code: str, message: str) -> str:
    if not field_name:
        return f"{code}: {message}"
    return f"{code} at {field_name}: {message}"
