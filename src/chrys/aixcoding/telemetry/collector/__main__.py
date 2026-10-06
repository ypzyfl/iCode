# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Collector entry point (``python -m chrys.aixcoding.telemetry.collector
run …``, TS ``main.ts``).

``--max-runtime-ms`` is a hard soft-timeout: in the detach scenario the
caller has no hard-timeout fallback, so reaching the threshold kills the
process outright (in-flight network requests included) — the only guard
against hangs.
"""

from __future__ import annotations

import os
import sys
import threading

from chrys.aixcoding.telemetry.collector.cli import _ArgumentError, parse_collector_arguments
from chrys.aixcoding.telemetry.collector.exit_codes import EXIT_TIMEOUT, EXIT_USAGE
from chrys.aixcoding.telemetry.collector.run import run_collector


def main(argv: list[str] | None = None) -> int:
    effective_argv = sys.argv[1:] if argv is None else argv
    try:
        arguments = parse_collector_arguments(effective_argv)
    except _ArgumentError as error:
        sys.stderr.write(f"{error}\n")
        return EXIT_USAGE

    def force_exit() -> None:
        os._exit(EXIT_TIMEOUT)

    timer = threading.Timer(arguments.max_runtime_ms / 1000, force_exit)
    timer.daemon = True
    timer.start()
    try:
        return run_collector(arguments)
    finally:
        timer.cancel()


if __name__ == "__main__":
    sys.exit(main())
