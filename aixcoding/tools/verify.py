# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Fork-local verification entry: upstream chrys_test delegation + the full custom suite.

Design: aixcoding/docs/batches/local-verify/design.md (signed off 2026-11-01).
The upstream Smart Test selector never sees ``aixcoding/`` (three hardcoded
path assumptions), and its ``--full`` covers only ``tests/`` — so a bare
``LoginSession``-style blind spot existed locally too: editing custom tests
yielded an all-green lie. This entry closes that: the custom suite always
runs in the default modes, both suites always run in dual-suite modes (no
short-circuit), and any failure fails the whole run.

Modes (mutually exclusive; ``--paths`` only with the smart pair):
  --smart           delegate ``chrys_test.py --smart [--paths ...]`` + run the
                    full custom suite unconditionally (default recommendation)
  --upstream-smart  delegate only (explicit skip of the custom suite)
  --full            fork-full: full custom suite + delegate ``chrys_test.py --full``
  --upstream-full   delegate ``chrys_test.py --full`` only
  --custom-full     full custom suite only

Only the public CLI of ``scripts/chrys_test.py`` is used (subprocess boundary,
no imports of its internals — design decision table).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
_EXCLUDED_MARKERS = "not integration and not gc_calibration"
_UPSTREAM_SELECTOR = REPO_ROOT / "scripts" / "chrys_test.py"

_DUAL_MODES = {"smart", "full"}
_UPSTREAM_MODES = {"upstream-smart", "upstream-full"}


def _custom_command() -> list[str]:
    """The custom suite, same shape as the aixcoding-tests.yml CI gate."""
    return [sys.executable, "-m", "pytest", "aixcoding/tests", "-m", _EXCLUDED_MARKERS]


def _delegate_command(mode_args: list[str]) -> list[str]:
    return [sys.executable, _UPSTREAM_SELECTOR.as_posix(), *mode_args]


def _run_process(args: list[str]) -> tuple[int, str]:
    """Stream the child's merged output live; return ``(exit_code, last_line)``.

    Overridden in tests (the single subprocess seam this tool has).
    """
    proc = subprocess.Popen(  # noqa: S603 - argv built locally, never via a shell (R13 approved: local-verify verification V2 F-01, 2026-11-01)
        args,
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    last_line = ""
    if proc.stdout is not None:  # PIPE + text mode always yields one; guard for type checkers
        for line in proc.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            if line.strip():
                last_line = line.strip()
    return proc.wait(), last_line


class _Suite:
    """One suite execution's outcome; ``returncode=None`` means it never ran."""

    def __init__(self, name: str, returncode: int | None, result_line: str = "", reason: str = "") -> None:
        self.name = name
        self.returncode = returncode
        self.result_line = result_line
        self.reason = reason

    @property
    def state(self) -> str:
        if self.returncode is None:
            return "not run"
        return "passed" if self.returncode == 0 else "failed"


def _run_suite(name: str, args: list[str]) -> _Suite:
    try:
        returncode, last_line = _run_process(args)
    except OSError as exc:
        return _Suite(name, None, reason=f"spawn failed: {exc}")
    return _Suite(name, returncode, result_line=last_line)


def _print_summary(suites: list[_Suite], returncode: int) -> None:
    sys.stdout.write("\n")
    sys.stdout.write(f"Fork verify Summary: {'PASSED' if returncode == 0 else 'FAILED'} (exit {returncode})\n")
    width = max((len(s.name) for s in suites), default=0)
    for suite in suites:
        detail = suite.reason if suite.returncode is None else f"exit {suite.returncode}"
        if suite.result_line:
            detail = f"{detail}; {suite.result_line}"
        sys.stdout.write(f"  {suite.name.ljust(width)}  {suite.state:<7} {detail}\n")
    sys.stdout.flush()


def _aggregate(suites: list[_Suite]) -> int:
    """First non-zero exit code; a never-started suite fails the run (exit 2)."""
    for suite in suites:
        if suite.returncode is None:
            return 2
        if suite.returncode != 0:
            return suite.returncode
    return 0


def _suite_plan(mode: str, paths: list[str]) -> list[tuple[str, list[str]]]:
    """(name, argv) pairs; custom first (fast, early signal), then upstream."""
    delegate_args = {
        "smart": ["--smart", *(["--paths", *paths] if paths else [])],
        "upstream-smart": ["--smart", *(["--paths", *paths] if paths else [])],
        "full": ["--full"],
        "upstream-full": ["--full"],
    }
    plan: list[tuple[str, list[str]]] = []
    if mode in _DUAL_MODES:
        plan.append(("custom", _custom_command()))
    if mode in _UPSTREAM_MODES or mode in _DUAL_MODES:
        plan.append(("upstream", _delegate_command(delegate_args[mode])))
    if mode == "custom-full":
        plan.append(("custom", _custom_command()))
    return plan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="verify",
        description="Fork-local verification: upstream chrys_test delegation + the full custom suite.",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--smart", action="store_true", help="delegate --smart + run the full custom suite (default)")
    mode.add_argument("--upstream-smart", action="store_true", help="delegate --smart only (skip the custom suite)")
    mode.add_argument("--full", action="store_true", help="fork-full: custom suite + delegated --full")
    mode.add_argument("--upstream-full", action="store_true", help="delegate --full only")
    mode.add_argument("--custom-full", action="store_true", help="custom suite only")
    parser.add_argument("--paths", nargs="+", metavar="PATH", help="with --smart/--upstream-smart: forwarded verbatim")
    return parser


def _resolve_mode(options: argparse.Namespace) -> str:
    for name in ("smart", "upstream_smart", "full", "upstream_full", "custom_full"):
        if getattr(options, name):
            return name.replace("_", "-")
    raise AssertionError("argparse required mode")  # pragma: no cover


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    options = parser.parse_args(argv)
    mode = _resolve_mode(options)
    if options.paths and mode not in {"smart", "upstream-smart"}:
        parser.error("--paths is only valid with --smart / --upstream-smart")
    suites = [_run_suite(name, args) for name, args in _suite_plan(mode, options.paths or [])]
    returncode = _aggregate(suites)
    _print_summary(suites, returncode)
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
