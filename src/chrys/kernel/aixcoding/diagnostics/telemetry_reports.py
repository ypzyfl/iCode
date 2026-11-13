# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Full POST diagnostics shared by the detail file and the local log viewer."""

from __future__ import annotations

import json
import logging
import os
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock
from typing import TYPE_CHECKING

from .logging_support import DETAIL_LEVEL, DETAIL_LOGGER_NAME

if TYPE_CHECKING:
    from collections.abc import Mapping

_LOGGER = logging.getLogger(f"{DETAIL_LOGGER_NAME}.telemetry")
_MAX_RECORDS = 100
_MAX_BYTES = 4_000_000


def report_logging_enabled() -> bool:
    return os.environ.get("AIXCODING_TELEMETRY_LOG_PAYLOAD") == "1"


@dataclass(frozen=True, slots=True)
class ReportLog:
    sequence: int
    summary: str
    json_line: str

    def pretty_json(self) -> str:
        return json.dumps(json.loads(self.json_line), ensure_ascii=False, indent=2)

    def __str__(self) -> str:
        return self.json_line

    def __repr__(self) -> str:
        # Logging's handler error path prints the arguments with repr().
        return f"ReportLog(sequence={self.sequence})"


_recent: deque[ReportLog] = deque()
_recent_size = 0
_sequence = 0
_lock = Lock()


def recent_report_logs() -> tuple[ReportLog, ...]:
    with _lock:
        return tuple(reversed(_recent))


def record_report(
    *,
    url: str,
    endpoint: str,
    payload: Mapping[str, object],
    status_code: int | None,
    peer: tuple[str, int] | None,
    error_type: str | None,
    duration_ms: float,
) -> None:
    global _recent_size, _sequence
    with _lock:
        _sequence += 1
        logged_at = datetime.now(UTC).isoformat(timespec="milliseconds")
        json_line = json.dumps(
            {
                "sequence": _sequence,
                "timestamp": logged_at,
                "method": "POST",
                "url": url,
                "endpoint": endpoint,
                "peer_ip": peer[0] if peer else None,
                "peer_port": peer[1] if peer else None,
                "status_code": status_code,
                "error_type": error_type,
                "duration_ms": duration_ms,
                "payload": payload,
            },
            separators=(",", ":"),
        )
        outcome = f"HTTP {status_code}" if status_code is not None else error_type
        summary = f"{logged_at[11:23]} UTC  POST {endpoint}  {outcome}  {duration_ms:.1f} ms"
        record = ReportLog(_sequence, summary, json_line)
        _recent.append(record)
        _recent_size += len(json_line)  # json.dumps escapes non-ASCII for the file sink.
        while len(_recent) > 1 and (len(_recent) > _MAX_RECORDS or _recent_size > _MAX_BYTES):
            _recent_size -= len(_recent.popleft().json_line)
    # Keep full payloads inside the explicitly configured, isolated detail channel.
    if not logging.getLogger(DETAIL_LOGGER_NAME).propagate:
        _LOGGER.log(DETAIL_LEVEL, "telemetry.report: %s", record)
