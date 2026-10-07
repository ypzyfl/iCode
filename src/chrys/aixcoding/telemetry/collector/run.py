# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Collector orchestration: lock → locate → read → ledger decision →
analyze → report → ledger write (TS ``run.ts``).

Failure paths: a failed report first does in-process backoff retries
(``--report-retries``, U5); exhaustion still failing never advances the
ledger, exit 40 finalizes in the engine's outbox failed/ and the next
trigger re-reports (ADR 0041 decision 5); when the report succeeded but
the ledger write failed, log outcome=ledger_write_failed and exit 0
(the next trigger naturally redoes it by the ledger difference; the
backend deduplicates by business keys). Tests can override the default
behavior by injecting sink/now/sleep.
"""

from __future__ import annotations

import json
import sys
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from chrys.aixcoding.telemetry.collector.analysis.attachments import SessionMutationBlobReader
from chrys.aixcoding.telemetry.collector.analysis.context import ReportAttribution
from chrys.aixcoding.telemetry.collector.analysis.git_context import create_git_context_resolver
from chrys.aixcoding.telemetry.collector.analysis.index import (
    ANALYSIS_VERSION,
    MalformedSessionError,
    SessionRevisionInput,
    analyze_session_revision,
)
from chrys.aixcoding.telemetry.collector.analysis.turns import PriorTurnRef
from chrys.aixcoding.telemetry.collector.attribution import (
    UNKNOWN_ACCOUNT_ID,
    MissingAttribution,
    read_attribution,
)
from chrys.aixcoding.telemetry.collector.cli import CollectorArguments
from chrys.aixcoding.telemetry.collector.exit_codes import (
    EXIT_CONFIG_INVALID,
    EXIT_DEFERRED,
    EXIT_MALFORMED,
    EXIT_OK,
    EXIT_REPORT_FAILED,
    EXIT_ROOT_UNREADABLE,
    EXIT_SESSION_NOT_FOUND,
)
from chrys.aixcoding.telemetry.collector.ledger import CollectorLedger, LedgerTurn, load_ledger, save_ledger
from chrys.aixcoding.telemetry.collector.locator import LocateFailureResult, locate_session_file
from chrys.aixcoding.telemetry.collector.lock import acquire_session_lock
from chrys.aixcoding.telemetry.collector.reader import ReadFailureResult, read_revision
from chrys.aixcoding.telemetry.collector.report.config import read_report_config
from chrys.aixcoding.telemetry.collector.report.http_sink import HttpReportSink, HttpReportSinkOptions
from chrys.aixcoding.telemetry.collector.report.port import SessionTelemetryPort, SessionTelemetryReport
from chrys.aixcoding.telemetry.collector.report.sink import FileReportSink

# Fixed backoff interval of in-process report retries (plan §7.2:
# default 2 attempts x 2s).
REPORT_RETRY_DELAY_MS = 2_000


@dataclass(frozen=True, slots=True)
class CollectorRunOptions:
    sink: SessionTelemetryPort | None = None
    now: Callable[[], datetime] | None = None
    # Retry backoff wait injection point (default time.sleep).
    sleep: Callable[[float], None] | None = None


@dataclass
class _RunSummary:
    revision_hash: str | None = None
    source_path: str | None = None
    json_path: str | None = None


def _append_log_line(log_file: str | None, entry: dict[str, Any]) -> None:
    line = json.dumps(entry)
    if log_file is None:
        sys.stderr.write(f"{line}\n")
        return
    try:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"{line}\n")
    except OSError:
        sys.stderr.write(f"{line}\n")


def run_collector(args: CollectorArguments, options: CollectorRunOptions | None = None) -> int:
    effective = options if options is not None else CollectorRunOptions()
    now = effective.now if effective.now is not None else datetime.now
    sleep = effective.sleep if effective.sleep is not None else time.sleep
    started = time.monotonic()
    analysis_version = args.analysis_version if args.analysis_version is not None else ANALYSIS_VERSION
    analyzed_turns = 0
    reported_turns = 0
    summary = _RunSummary()

    def log(outcome: str, exit_code: int, extra: dict[str, Any] | None = None) -> None:
        nonlocal analyzed_turns, reported_turns
        entry: dict[str, Any] = {
            "ts": now().isoformat(),
            "session_id": args.session_id,
        }
        if summary.revision_hash is not None:
            entry["revision_hash"] = summary.revision_hash
        if summary.source_path is not None:
            entry["source_path"] = summary.source_path
        if summary.json_path is not None:
            entry["json_path"] = summary.json_path
        entry.update(
            {
                "outcome": outcome,
                "analyzed_turns": analyzed_turns,
                "reported_turns": reported_turns,
                "duration_ms": int((time.monotonic() - started) * 1000),
                "exit_code": exit_code,
            }
        )
        if extra is not None:
            entry.update(extra)
        _append_log_line(args.log_file, entry)

    # Config fast-fails before the lock: missing/corrupt takes no lock
    # and does not retry (recovery comes with the next trigger).
    config_result = read_report_config(args.report_config)
    if config_result.config is None:
        log("config_invalid", EXIT_CONFIG_INVALID)
        return EXIT_CONFIG_INVALID
    config = config_result.config
    # Attribution reads independently (before the lock): missing/corrupt
    # degrades to unknown, never fails (P1).
    attribution_result = read_attribution(args.attribution)
    if isinstance(attribution_result, MissingAttribution):
        log("attribution_missing", EXIT_OK, {"attribution_path": args.attribution})
        account_id = UNKNOWN_ACCOUNT_ID
    else:
        account_id = attribution_result.account_id
    # Channel common fields: userId comes from attribution.json
    # (account-level attribution, U4); channelType derives from scope
    # (acp = desktop, tui = cli); channelName follows the K2
    # proceed-by-default values (registration table §3.8). channelVersion
    # is left to the analysis layer's engine-version fallback: the K2
    # default asks for the desktop build number on ACP, which the engine
    # side cannot obtain — the engine version is the recorded interim
    # value, corrected via ANALYSIS_VERSION re-report once the D1
    # review settles the channel.
    attribution = ReportAttribution(
        user_id=account_id,
        channel_type="desktop" if args.scope == "acp" else "cli",
        channel_name="aixcoding-desktop" if args.scope == "acp" else "icode",
    )
    client: httpx.Client | None = None
    default_sink = effective.sink
    if default_sink is None:
        if config.sink == "http":
            client = httpx.Client()
            default_sink = HttpReportSink(
                HttpReportSinkOptions(
                    endpoint=config.endpoint or "",
                    token=config.token,
                    client=client,
                )
            )
        else:
            default_sink = FileReportSink(args.state_dir)

    lock = acquire_session_lock(args.state_dir, args.session_id, max_age_ms=args.max_runtime_ms * 2)
    if lock is None:
        log("deferred", EXIT_DEFERRED)
        if client is not None:
            client.close()
        return EXIT_DEFERRED
    try:
        located = locate_session_file(args.sessions_root, args.session_id)
        if isinstance(located, LocateFailureResult):
            if located.reason == "root_unreadable":
                log("root_unreadable", EXIT_ROOT_UNREADABLE)
                return EXIT_ROOT_UNREADABLE
            log("session_not_found", EXIT_SESSION_NOT_FOUND)
            return EXIT_SESSION_NOT_FOUND
        revision = read_revision(located.ordered_paths)
        if isinstance(revision, ReadFailureResult):
            if revision.reason == "malformed":
                log("malformed", EXIT_MALFORMED)
                return EXIT_MALFORMED
            log("session_not_found", EXIT_SESSION_NOT_FOUND)
            return EXIT_SESSION_NOT_FOUND
        summary.revision_hash = revision.hash
        summary.source_path = revision.path

        ledger: CollectorLedger | None = load_ledger(args.state_dir, args.session_id)
        if (
            ledger is not None
            and ledger.last_revision_hash == revision.hash
            and ledger.analysis_version == analysis_version
            and ledger.report_state == "reported"
        ):
            log("idle", EXIT_OK)
            return EXIT_OK

        try:
            analysis = analyze_session_revision(
                SessionRevisionInput(
                    session_id=args.session_id,
                    revision_hash=revision.hash,
                    envelope=revision.envelope,
                    source_path=revision.path,
                    attribution=attribution,
                    blob_reader=SessionMutationBlobReader(str(Path(revision.path).parent)),
                    git_context=create_git_context_resolver(),
                    analysis_version=analysis_version,
                    # When the ledger's analysis_version differs from
                    # this run's, old turn results are not reused
                    # (guide §19.5): every turn re-reports under the
                    # new analysis rules; the backend's idempotency
                    # keys absorb it.
                    prior_turns=(
                        [PriorTurnRef(turn_id=turn.turn_id, content_hash=turn.content_hash) for turn in ledger.turns]
                        if ledger is not None and ledger.analysis_version == analysis_version
                        else []
                    ),
                )
            )
        except MalformedSessionError as cause:
            summary.json_path = cause.json_path
            log("malformed", EXIT_MALFORMED)
            return EXIT_MALFORMED
        analyzed_turns = len(analysis["turnFacts"])
        reported_turns = len(analysis["incremental"])

        report = SessionTelemetryReport(
            report_id=str(uuid.uuid4()),
            scope=args.scope,
            final=args.final,
            analysis_version=analysis_version,
            session=analysis["sessionFacts"],
            incremental_turns=analysis["incremental"],
            report_events=analysis["reportEvents"],
        )
        reported = default_sink.report(report)
        retry_used = 0
        if not reported.success and args.report_retries > 0:
            for attempt in range(1, args.report_retries + 1):
                sleep(REPORT_RETRY_DELAY_MS / 1000)
                reported = default_sink.report(report)
                retry_used = attempt
                if reported.success:
                    break
            if reported.success:
                log("report_retry_succeeded", EXIT_OK, {"report_retries_used": retry_used})
        if not reported.success:
            log("report_failed", EXIT_REPORT_FAILED)
            return EXIT_REPORT_FAILED

        try:
            save_ledger(
                args.state_dir,
                CollectorLedger(
                    version=1,
                    session_id=args.session_id,
                    last_revision_hash=revision.hash,
                    last_analyzed_at=now().isoformat(),
                    analysis_version=analysis_version,
                    report_state="reported",
                    # Reported-turn snapshot of the current view (pending
                    # stays unconfirmed, out of the ledger; turns removed
                    # by a rollback vanish with the overwrite — guide
                    # §19.7 current turn-set update).
                    turns=[
                        LedgerTurn(
                            turn_id=fact["turnId"],
                            content_hash=fact["contentHash"],
                            reported_at=now().isoformat(),
                        )
                        for fact in analysis["turnFacts"]
                        if fact["status"] != "pending"
                    ],
                    source_path=revision.path,
                ),
            )
        except OSError, ValueError:
            # The report already succeeded; the price of the un-advanced
            # ledger is the next trigger re-analyzing and re-reporting —
            # safe.
            log("ledger_write_failed", EXIT_OK)
            return EXIT_OK
        if analysis["aiCodeTruncatedPaths"]:
            # Lossy but successful (plan §6.3): the declared omission of
            # deterministically truncated over-cap files (metadata only,
            # no content) — observable and manually checkable for the
            # session; the ledger still writes.
            log(
                "ai_code_files_truncated",
                EXIT_OK,
                {"truncated_files": analysis["aiCodeTruncatedPaths"]},
            )
        log("reported", EXIT_OK)
        return EXIT_OK
    finally:
        lock.release()
        if client is not None:
            client.close()
