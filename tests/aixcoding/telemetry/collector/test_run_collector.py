# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Collector end-to-end tests (scenarios ported from the TS
``collector.test.ts`` runCollector sections; ADR 0041 failure paths)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from chrys.aixcoding.telemetry.collector.cli import CollectorArguments
from chrys.aixcoding.telemetry.collector.exit_codes import (
    EXIT_CONFIG_INVALID,
    EXIT_DEFERRED,
    EXIT_MALFORMED,
    EXIT_OK,
    EXIT_REPORT_FAILED,
    EXIT_SESSION_NOT_FOUND,
)
from chrys.aixcoding.telemetry.collector.locator import session_short_id
from chrys.aixcoding.telemetry.collector.report.port import PortResult, SessionTelemetryReport
from chrys.aixcoding.telemetry.collector.run import CollectorRunOptions, run_collector

SESSION_ID = "4201eebc-ca45-4328-8882-272f3d7c41cb"


def session_json(**overrides: Any) -> str:
    meta: dict[str, Any] = {
        "schema_version": 1,
        "app_version": "0.28.0",
        "session_id": SESSION_ID,
        "created_at": "2026-10-02T09:14:03Z",
        "updated_at": "2026-10-02T09:20:11Z",
        "kind": "chat",
        "title": "test",
        "last_surface": "acp",
    }
    meta.update(overrides.pop("meta", {}))
    state: dict[str, Any] = {
        "messages": [
            {"role": "user", "contents": []},
            {
                "role": "assistant",
                "contents": [],
                "additional_properties": {"_chrys_kind": "turn", "_turn_id": "turn_1", "_turn": 1},
            },
        ],
        "turn_counter": 1,
    }
    state.update(overrides.pop("state", {}))
    # Remaining flat overrides land in state (turn_counter and friends).
    state.update(overrides)
    return json.dumps({"meta": meta, "state": state})


def make_workspace(tmp_path: Path, session_content: str | None = None) -> SimpleNamespace:
    sessions_root = tmp_path / "sessions"
    state_dir = tmp_path / "collector-state"
    session_directory = sessions_root / session_short_id(SESSION_ID)
    session_directory.mkdir(parents=True)
    if session_content is not None:
        (session_directory / "session.json").write_text(session_content, encoding="utf-8")
    (state_dir / "config").mkdir(parents=True)
    report_config = state_dir / "config" / "report-config.json"
    report_config.write_text(json.dumps({"version": 2, "sink": "file"}) + "\n", encoding="utf-8")
    attribution_file = tmp_path / "telemetry" / "attribution.json"
    attribution_file.parent.mkdir(parents=True)
    attribution_file.write_text(json.dumps({"version": 1, "account_id": "user-77"}) + "\n", encoding="utf-8")
    return SimpleNamespace(
        base=tmp_path,
        sessions_root=str(sessions_root),
        state_dir=str(state_dir),
        report_config=str(report_config),
        attribution_file=str(attribution_file),
        log_file=str(state_dir / "logs" / "collector-test.jsonl"),
    )


def arguments_for(workspace: SimpleNamespace, **overrides: Any) -> CollectorArguments:
    values: dict[str, Any] = {
        "session_id": SESSION_ID,
        "sessions_root": workspace.sessions_root,
        "state_dir": workspace.state_dir,
        "report_config": workspace.report_config,
        "scope": "acp",
        "attribution": workspace.attribution_file,
        "final": False,
        "analysis_version": None,
        "max_runtime_ms": 30_000,
        "report_retries": 2,
        "log_file": workspace.log_file,
    }
    values.update(overrides)
    return CollectorArguments(**values)


class CaptureSink:
    def __init__(self, results: list[PortResult] | None = None) -> None:
        self.reports: list[SessionTelemetryReport] = []
        self._results = list(results) if results is not None else None

    def report(self, event: SessionTelemetryReport) -> PortResult:
        self.reports.append(event)
        if self._results is not None and self._results:
            return self._results.pop(0)
        return PortResult(success=True)


def read_reports(workspace: SimpleNamespace) -> list[dict[str, Any]]:
    reports_directory = Path(workspace.state_dir) / "reports"
    if not reports_directory.is_dir():
        return []
    reports: list[dict[str, Any]] = []
    for name in sorted(entry.name for entry in reports_directory.iterdir() if entry.name.endswith(".json")):
        reports.append(json.loads((reports_directory / name).read_text(encoding="utf-8")))
    return reports


def read_log_lines(workspace: SimpleNamespace) -> list[dict[str, Any]]:
    raw = Path(workspace.log_file).read_text(encoding="utf-8")
    return [json.loads(line) for line in raw.splitlines() if line]


def read_ledger(workspace: SimpleNamespace) -> dict[str, Any] | None:
    path = Path(workspace.state_dir) / "ledger" / f"{SESSION_ID.replace('-', '')}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


class TestRunCollector:
    def test_reports_and_advances_ledger(self, tmp_path: Path) -> None:
        workspace = make_workspace(tmp_path, session_json())
        exit_code = run_collector(arguments_for(workspace))
        assert exit_code == EXIT_OK
        reports = read_reports(workspace)
        assert len(reports) == 1
        assert reports[0]["session"]["sessionId"] == SESSION_ID
        assert reports[0]["session"]["turnCount"] == 1
        ledger = read_ledger(workspace)
        assert ledger is not None
        assert ledger["report_state"] == "reported"
        lines = read_log_lines(workspace)
        assert lines[-1]["outcome"] == "reported"
        assert lines[-1]["analyzed_turns"] == 1
        assert lines[-1]["reported_turns"] == 1

    def test_idle_when_revision_and_version_match(self, tmp_path: Path) -> None:
        workspace = make_workspace(tmp_path, session_json())
        assert run_collector(arguments_for(workspace)) == EXIT_OK
        assert run_collector(arguments_for(workspace)) == EXIT_OK
        assert read_log_lines(workspace)[-1]["outcome"] == "idle"
        assert len(read_reports(workspace)) == 1

    def test_re_reports_when_revision_changes(self, tmp_path: Path) -> None:
        workspace = make_workspace(tmp_path, session_json())
        assert run_collector(arguments_for(workspace)) == EXIT_OK
        session_path = Path(workspace.sessions_root) / session_short_id(SESSION_ID) / "session.json"
        session_path.write_text(session_json(turn_counter=2), encoding="utf-8")
        assert run_collector(arguments_for(workspace)) == EXIT_OK
        reports = read_reports(workspace)
        assert len(reports) == 2
        assert reports[1]["session"]["turnCount"] == 2
        # Revision changed but turn_1's content (messages) did not: the
        # turn-level increment is empty (the revision-level re-reports
        # as usual).
        assert reports[1]["incrementalTurns"] == []

    def test_re_analyzes_when_ledger_version_older(self, tmp_path: Path) -> None:
        workspace = make_workspace(tmp_path, session_json())
        assert run_collector(arguments_for(workspace)) == EXIT_OK
        assert run_collector(arguments_for(workspace, analysis_version=99)) == EXIT_OK
        reports = read_reports(workspace)
        assert len(reports) == 2
        # Old turn results are not reused: everything re-reports.
        assert len(reports[1]["incrementalTurns"]) == 1

    def test_falls_back_to_bak(self, tmp_path: Path) -> None:
        workspace = make_workspace(tmp_path, session_json())
        session_directory = Path(workspace.sessions_root) / session_short_id(SESSION_ID)
        (session_directory / "session.json").write_text('{"meta": broken', encoding="utf-8")
        (session_directory / "session.json.bak").write_text(session_json(turn_counter=3), encoding="utf-8")
        assert run_collector(arguments_for(workspace)) == EXIT_OK
        ledger = read_ledger(workspace)
        assert ledger is not None
        assert ledger["source_path"] == str(session_directory / "session.json.bak")
        assert read_reports(workspace)[0]["session"]["turnCount"] == 3

    def test_rebuilds_corrupt_ledger_and_re_reports(self, tmp_path: Path) -> None:
        workspace = make_workspace(tmp_path, session_json())
        assert run_collector(arguments_for(workspace)) == EXIT_OK
        ledger_path = Path(workspace.state_dir) / "ledger" / f"{SESSION_ID.replace('-', '')}.json"
        ledger_path.write_text('{"version": 1, "brok', encoding="utf-8")
        assert run_collector(arguments_for(workspace)) == EXIT_OK
        assert len(read_reports(workspace)) == 2
        assert read_ledger(workspace) is not None

    def test_rejects_mismatched_session_ids(self, tmp_path: Path) -> None:
        workspace = make_workspace(tmp_path, session_json(meta={"session_id": "another-session-id"}))
        exit_code = run_collector(arguments_for(workspace))
        assert exit_code == EXIT_MALFORMED
        assert read_log_lines(workspace)[-1]["json_path"] == "$.meta.session_id"

    def test_config_invalid_before_lock(self, tmp_path: Path) -> None:
        workspace = make_workspace(tmp_path, session_json())
        exit_code = run_collector(arguments_for(workspace, report_config=str(Path(workspace.base) / "missing.json")))
        assert exit_code == EXIT_CONFIG_INVALID
        assert read_log_lines(workspace)[-1]["outcome"] == "config_invalid"
        assert read_ledger(workspace) is None

    def test_session_not_found(self, tmp_path: Path) -> None:
        workspace = make_workspace(tmp_path)
        exit_code = run_collector(arguments_for(workspace))
        assert exit_code == EXIT_SESSION_NOT_FOUND
        assert read_log_lines(workspace)[-1]["outcome"] == "session_not_found"

    def test_attribution_missing_degrades_unknown(self, tmp_path: Path) -> None:
        workspace = make_workspace(tmp_path, session_json())
        exit_code = run_collector(arguments_for(workspace, attribution=str(Path(workspace.base) / "absent.json")))
        # Attribution degradation never fails (P1: collect with
        # degraded attribution rather than not at all).
        assert exit_code == EXIT_OK
        assert read_reports(workspace)[0]["reportEvents"] == []
        lines = read_log_lines(workspace)
        assert any(line["outcome"] == "attribution_missing" for line in lines)
        assert lines[-1]["outcome"] == "reported"

    def test_attribution_corrupted_degrades_unknown(self, tmp_path: Path) -> None:
        workspace = make_workspace(tmp_path, session_json())
        Path(workspace.attribution_file).write_text('{"version": 1, "account_id": ', encoding="utf-8")
        assert run_collector(arguments_for(workspace)) == EXIT_OK
        assert any(line["outcome"] == "attribution_missing" for line in read_log_lines(workspace))

    def test_report_retry_succeeds(self, tmp_path: Path) -> None:
        workspace = make_workspace(tmp_path, session_json())
        sink = CaptureSink(results=[PortResult(success=False, retryable=True, message="first fails")])
        exit_code = run_collector(
            arguments_for(workspace),
            CollectorRunOptions(sink=sink, sleep=lambda seconds: None),
        )
        assert exit_code == EXIT_OK
        assert len(sink.reports) == 2
        lines = read_log_lines(workspace)
        retry = next(line for line in lines if line["outcome"] == "report_retry_succeeded")
        assert retry["report_retries_used"] == 1
        assert lines[-1]["outcome"] == "reported"
        assert read_ledger(workspace) is not None

    def test_report_failure_exhausts_retries_and_never_advances_ledger(self, tmp_path: Path) -> None:
        workspace = make_workspace(tmp_path, session_json())
        sink = CaptureSink(results=[PortResult(success=False, retryable=True, message="down") for _ in range(3)])
        exit_code = run_collector(
            arguments_for(workspace),
            CollectorRunOptions(sink=sink, sleep=lambda seconds: None),
        )
        assert exit_code == EXIT_REPORT_FAILED
        # 1 attempt + 2 retries.
        assert len(sink.reports) == 3
        assert read_log_lines(workspace)[-1]["outcome"] == "report_failed"
        assert read_ledger(workspace) is None

    def test_deferred_when_locked(self, tmp_path: Path) -> None:
        import os
        import time as time_module

        workspace = make_workspace(tmp_path, session_json())
        locks = Path(workspace.state_dir) / "locks"
        locks.mkdir(parents=True)
        (locks / f"{SESSION_ID.replace('-', '')}.lock").write_text(
            json.dumps({"pid": os.getpid(), "created_at": time_module.time() * 1000}),
            encoding="utf-8",
        )
        exit_code = run_collector(arguments_for(workspace))
        assert exit_code == EXIT_DEFERRED
        assert read_log_lines(workspace)[-1]["outcome"] == "deferred"
