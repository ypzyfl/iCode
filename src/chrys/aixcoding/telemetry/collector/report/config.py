# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""report-config.json reading and validation (TS ``report/config.ts``;
implementation plan §6.2; unified Hook plan §4.5).

``sink: "file"`` (local observability) or ``"http"`` (4-interface
reporting); ``token`` is the request-header credential (refreshed by the
engine-side install from the chrys-only env variables / login state).
Since v2 attribution moved out of this file (it lives in
attribution.json); reading v1 ignores the attribution field for old
files. The writer tightens file permissions when the config carries
authentication material.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

_ENDPOINT_MAX_LENGTH = 2_048
_TOKEN_MAX_LENGTH = 16_384
_SINKS = ("file", "http")


@dataclass(frozen=True, slots=True)
class ReportConfig:
    version: int  # 1 | 2
    sink: str  # "file" | "http"
    endpoint: str | None = None
    token: str | None = None


@dataclass(frozen=True, slots=True)
class ReadReportConfigResult:
    """``config is not None`` means ok; ``message is not None`` means
    invalid (mirrors the TS ok/invalid union)."""

    config: ReportConfig | None = None
    message: str | None = None


def _is_url(value: str) -> bool:
    parsed = urlparse(value)
    return bool(parsed.scheme) and bool(parsed.netloc)


def _validate_common(config: dict[str, object]) -> str | None:
    sink = config.get("sink")
    if sink not in _SINKS:
        return f"Invalid input: expected 'file' | 'http', received {sink!r}"
    endpoint = config.get("endpoint")
    if endpoint is not None:
        if not isinstance(endpoint, str):
            return f"Invalid input: expected string, received {type(endpoint).__name__}"
        if len(endpoint) > _ENDPOINT_MAX_LENGTH:
            return f"Too big: expected maximum length {_ENDPOINT_MAX_LENGTH}"
        if not _is_url(endpoint):
            return "Invalid url"
    token = config.get("token")
    if token is not None:
        if not isinstance(token, str):
            return f"Invalid input: expected string, received {type(token).__name__}"
        if not 1 <= len(token) <= _TOKEN_MAX_LENGTH:
            return "String must contain from 1 to 16384 character(s)"
    if sink == "http" and endpoint is None:
        return 'endpoint is required when sink is "http".'
    return None


def _validate_v2(config: dict[str, object]) -> str | None:
    # strict schema: any key outside {version, sink, endpoint, token}
    # (attribution included — it moved out in v2) is rejected.
    known = {"version", "sink", "endpoint", "token"}
    for key in config:
        if key not in known:
            return f"Unrecognized key: {key!r}"
    return _validate_common(config)


def _validate_v1(config: dict[str, object]) -> str | None:
    # v1 compat: attribution already moved out of report-config; the
    # field in old files is ignored.
    known = {"version", "sink", "endpoint", "token", "attribution"}
    for key in config:
        if key not in known:
            return f"Unrecognized key: {key!r}"
    return _validate_common(config)


def read_report_config(path: str) -> ReadReportConfigResult:
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError:
        return ReadReportConfigResult(message=f"The report config file is unreadable: {path}")
    try:
        parsed = json.loads(raw)
    except ValueError:
        return ReadReportConfigResult(message="The report config file is not valid JSON.")
    if not isinstance(parsed, dict):
        return ReadReportConfigResult(message="Invalid report config: expected an object")
    version = parsed.get("version")
    if version == 2:
        message = _validate_v2(parsed)
    elif version == 1:
        message = _validate_v1(parsed)
    else:
        return ReadReportConfigResult(message=f"Invalid report config: version must be 1 or 2, got {version!r}")
    if message is not None:
        return ReadReportConfigResult(message=f"Invalid report config: {message}")
    return ReadReportConfigResult(
        config=ReportConfig(
            version=version,
            sink=parsed["sink"],
            endpoint=parsed.get("endpoint"),
            token=parsed.get("token"),
        )
    )
