# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""CLI parsing equivalence tests (TS baseline ``collector.test.ts`` argument
parsing block, scenarios ported)."""

from __future__ import annotations

import pytest

from chrys.aixcoding.telemetry.collector.cli import (
    _ArgumentError,
    parse_collector_arguments,
)

SESSION_ID = "4201eebc-ca45-4328-8882-272f3d7c41cb"

BASE = [
    "run",
    "--session",
    SESSION_ID,
    "--sessions-root",
    "/tmp/sessions",
    "--state-dir",
    "/tmp/state",
    "--report-config",
    "/tmp/state/config/report-config.json",
    "--scope",
    "acp",
    "--attribution",
    "/tmp/state/telemetry/attribution.json",
]


def test_parses_the_documented_shape_with_defaults() -> None:
    parsed = parse_collector_arguments(BASE)
    assert parsed.session_id == SESSION_ID
    assert parsed.scope == "acp"
    assert parsed.attribution == "/tmp/state/telemetry/attribution.json"
    assert parsed.final is False
    assert parsed.max_runtime_ms == 30_000
    assert parsed.report_retries == 2
    assert parsed.analysis_version is None


def test_reads_the_session_id_from_an_environment_variable() -> None:
    parsed = parse_collector_arguments(
        ["run", "--session-from-env", "AIXCOLLECT_SESSION_ID", *BASE[3:]],
        {"AIXCOLLECT_SESSION_ID": SESSION_ID},
    )
    assert parsed.session_id == SESSION_ID


def test_rejects_missing_or_duplicated_session_sources() -> None:
    with pytest.raises(_ArgumentError):
        parse_collector_arguments(BASE[3:])
    with pytest.raises(_ArgumentError):
        parse_collector_arguments([*BASE, "--session-from-env", "OTHER"])


def test_rejects_unknown_options_and_missing_values() -> None:
    with pytest.raises(_ArgumentError):
        parse_collector_arguments([*BASE, "--unknown"])
    with pytest.raises(_ArgumentError):
        parse_collector_arguments([*BASE[:-1]])  # --attribution without value
    with pytest.raises(_ArgumentError):
        parse_collector_arguments(["collect", *BASE[1:]])


def test_requires_scope_with_an_enum_value_and_attribution() -> None:
    without_scope = [arg for arg in BASE if arg not in ("--scope", "acp")]
    with pytest.raises(_ArgumentError):
        parse_collector_arguments(without_scope)
    with pytest.raises(_ArgumentError):
        parse_collector_arguments([*BASE[:-3], "web", *BASE[-2:]])


def test_parses_report_retries_with_zero_allowed_and_rejects_negatives() -> None:
    assert parse_collector_arguments([*BASE, "--report-retries", "0"]).report_retries == 0
    assert parse_collector_arguments([*BASE, "--report-retries", "5"]).report_retries == 5
    with pytest.raises(_ArgumentError):
        parse_collector_arguments([*BASE, "--report-retries", "-1"])
    with pytest.raises(_ArgumentError):
        parse_collector_arguments([*BASE, "--report-retries", "abc"])


def test_final_flag_and_analysis_version() -> None:
    parsed = parse_collector_arguments([*BASE, "--final", "--analysis-version", "99"])
    assert parsed.final is True
    assert parsed.analysis_version == 99
    with pytest.raises(_ArgumentError):
        parse_collector_arguments([*BASE, "--analysis-version", "0"])


def test_session_id_bounds() -> None:
    with pytest.raises(_ArgumentError):
        parse_collector_arguments(["run", "--session", "", *BASE[3:]])
    with pytest.raises(_ArgumentError):
        parse_collector_arguments(["run", "--session", "x" * 513, *BASE[3:]])
