# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""CLI argument parsing for ``collector run …`` (TS baseline ``cli.ts``).

Semantics are ported verbatim: exactly one of ``--session`` /
``--session-from-env``; ``--scope`` (required enum) and ``--attribution``
(required) are written into the hook argv by the installer;
``--report-retries`` defaults to 2 (0 disables, negatives rejected);
``--max-runtime-ms`` is the forced self-exit guard. Usage errors exit with
code 2 (argparse's default, matching ``EXIT_USAGE``).
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, Never

Scope = Literal["acp", "tui"]

DEFAULT_MAX_RUNTIME_MS = 30_000
DEFAULT_REPORT_RETRIES = 2


@dataclass(frozen=True, slots=True)
class CollectorArguments:
    """Parsed collector arguments (mirrors TS ``CollectorArguments``)."""

    session_id: str
    sessions_root: str
    state_dir: str
    report_config: str
    scope: Scope
    attribution: str
    final: bool = False
    analysis_version: int | None = None
    max_runtime_ms: int = DEFAULT_MAX_RUNTIME_MS
    report_retries: int = DEFAULT_REPORT_RETRIES
    log_file: str | None = None


class _ArgumentError(Exception):
    """Usage error carrying the exit code (2) of the TS baseline."""


class _Parser(argparse.ArgumentParser):
    """argparse that raises instead of calling sys.exit (testable)."""

    def error(self, message: str) -> Never:
        raise _ArgumentError(message)


def _positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        msg = f"must be a positive integer, got {value!r}"
        raise argparse.ArgumentTypeError(msg)
    return number


def _non_negative_int(value: str) -> int:
    number = int(value)
    if number < 0:
        msg = f"must be an integer >= 0, got {value!r}"
        raise argparse.ArgumentTypeError(msg)
    return number


def _build_parser() -> _Parser:
    parser = _Parser(prog="collector", add_help=False)
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run", add_help=False)

    run.add_argument("--session")
    run.add_argument("--session-from-env", dest="session_from_env")
    run.add_argument("--sessions-root", required=True)
    run.add_argument("--state-dir", required=True)
    run.add_argument("--report-config", required=True)
    run.add_argument("--scope", required=True, choices=("acp", "tui"))
    run.add_argument("--attribution", required=True)
    run.add_argument("--final", action="store_true")
    run.add_argument("--analysis-version", type=_positive_int)
    run.add_argument("--max-runtime-ms", type=_positive_int, default=DEFAULT_MAX_RUNTIME_MS)
    run.add_argument("--report-retries", type=_non_negative_int, default=DEFAULT_REPORT_RETRIES)
    run.add_argument("--log-file")
    return parser


def parse_collector_arguments(
    argv: list[str] | tuple[str, ...],
    env: Mapping[str, str] | None = None,
) -> CollectorArguments:
    """Parse ``argv``; raise ``_ArgumentError`` (usage, exit 2) on bad input.

    ``env`` defaults to ``os.environ``; used only for ``--session-from-env``.
    """
    environ = os.environ if env is None else env
    namespace = _build_parser().parse_args(list(argv))
    if namespace.command != "run":
        msg = 'The first argument must be "run".'
        raise _ArgumentError(msg)
    if (namespace.session is None) == (namespace.session_from_env is None):
        msg = "Exactly one of --session or --session-from-env is required."
        raise _ArgumentError(msg)

    session_id = namespace.session
    if session_id is None:
        from_env = environ.get(namespace.session_from_env, "")
        if not from_env:
            msg = f"Environment variable {namespace.session_from_env} is not set."
            raise _ArgumentError(msg)
        session_id = from_env
    if not 1 <= len(session_id) <= 512:
        msg = "The session id must be 1..512 characters."
        raise _ArgumentError(msg)
    if namespace.max_runtime_ms < 100:
        msg = "--max-runtime-ms must be an integer >= 100."
        raise _ArgumentError(msg)

    return CollectorArguments(
        session_id=session_id,
        sessions_root=namespace.sessions_root,
        state_dir=namespace.state_dir,
        report_config=namespace.report_config,
        scope=namespace.scope,
        attribution=namespace.attribution,
        final=namespace.final,
        analysis_version=namespace.analysis_version,
        max_runtime_ms=namespace.max_runtime_ms,
        report_retries=namespace.report_retries,
        log_file=namespace.log_file,
    )
