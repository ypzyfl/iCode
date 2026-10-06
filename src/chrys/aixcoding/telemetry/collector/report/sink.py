# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""File sink: write the report payload to
``<state-dir>/reports/<safe-file-id>-<seq>.json`` (TS ``report/sink.ts``).

The skeleton-stage observability exit (implementation plan §1.3): a
file appearing is physical evidence the report call happened; the
payload is the draft of the future HTTP body. Payload serialization
omits null fields (the engine's write convention) and keeps numeric
zeros.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from chrys.aixcoding.telemetry.collector.locator import safe_file_id
from chrys.aixcoding.telemetry.collector.report.port import PortResult, SessionTelemetryReport


def _omit_nulls(value: Any) -> Any:
    if isinstance(value, list):
        return [_omit_nulls(entry) for entry in value]
    if isinstance(value, dict):
        return {key: _omit_nulls(entry) for key, entry in value.items() if entry is not None}
    return value


class FileReportSink:
    def __init__(self, state_dir: str) -> None:
        self._state_dir = state_dir

    def report(self, event: SessionTelemetryReport) -> PortResult:
        try:
            reports_directory = Path(self._state_dir) / "reports"
            reports_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            identifier = safe_file_id(str(event.session.get("sessionId") or ""))
            sequence = self._next_sequence(reports_directory, identifier)
            target = reports_directory / f"{identifier}-{sequence}.json"
            temporary = reports_directory / f".{identifier}-{sequence}-{os.getpid()}.tmp"
            temporary.write_text(
                json.dumps(_omit_nulls(_report_payload(event)), indent=2) + "\n",
                encoding="utf-8",
            )
            os.replace(temporary, target)
            return PortResult(success=True)
        except OSError:
            return PortResult(
                success=False,
                retryable=True,
                message="The session telemetry payload could not be written.",
            )

    def _next_sequence(self, reports_directory: Path, identifier: str) -> int:
        """The filename sequence serves readability and no-overwrite
        only, never idempotence (idempotence belongs to the ledger and
        the backend business keys)."""
        pattern = re.compile(rf"^{re.escape(identifier)}-(\d+)\.json$")
        maximum = 0
        try:
            names = os.listdir(reports_directory)
        except OSError:
            names = []
        for name in names:
            match = pattern.fullmatch(name)
            if match is None:
                continue
            try:
                sequence = int(match.group(1))
            except ValueError:
                continue
            if sequence > maximum:
                maximum = sequence
        return maximum + 1


def _report_payload(event: SessionTelemetryReport) -> dict[str, Any]:
    """Serialize the report as the TS SessionTelemetryReport JSON
    (camelCase, reportId/scope/final/analysisVersion/session/
    incrementalTurns/reportEvents)."""
    return {
        "reportId": event.report_id,
        "scope": event.scope,
        "final": event.final,
        "analysisVersion": event.analysis_version,
        "session": event.session,
        "incrementalTurns": event.incremental_turns,
        "reportEvents": event.report_events,
    }
