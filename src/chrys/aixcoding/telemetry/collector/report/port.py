# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Shared report port types (TS ``@agent-studio/core`` SessionTelemetry
Port / PortResult / SessionTelemetryReport, projected for the Python
collector).

SessionTelemetryReport is the single report payload: the run layer
assembles it from the analysis output; file/http sinks only read it.
``session`` carries the sessionFacts JSON (camelCase keys, the
``sessionId`` key is the sink locator input); ``incremental_turns``
carries SessionTurnFact JSON (turnId/contentHash are the idempotency
header inputs); ``report_events`` carries the analysis event JSON.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class SessionTelemetryPort(Protocol):
    def report(self, event: SessionTelemetryReport) -> PortResult: ...


@dataclass(frozen=True, slots=True)
class PortResult:
    """Outcome of one report call. ``success`` False carries the
    failure semantics (ADR 0041 decision 5: a failed report never
    advances the ledger; a retry re-analyzes and re-reports, the
    backend deduplicates by business keys)."""

    success: bool
    retryable: bool = False
    message: str | None = None


@dataclass(frozen=True, slots=True)
class SessionTelemetryReport:
    report_id: str
    scope: str  # "acp" | "tui"
    final: bool
    analysis_version: int
    session: dict[str, Any]
    incremental_turns: list[dict[str, Any]] = field(default_factory=list)
    report_events: list[dict[str, Any]] = field(default_factory=list)
