# ruff: noqa: T201
# (stderr notes are the observable-degradation channel, DEVELOPMENT.md §9)
"""Process entry: install diagnostics hooks, then hand off to the upstream CLI.

Run as ``python -m chrys.kernel.aixcoding.diagnostics.launcher`` (equivalent to the
``chrys`` entrypoint, but with crash capture, snapshot and the aixcoding log
sink active). Zero upstream source changes: the upstream entrypoint is loaded
dynamically by name — an explicitly registered R9 entry-point exemption
(aixcoding/docs/diagnostics/design.md, registration table row ``launcher.py``),
not a layering import. The logging component does not depend on this module:
whoever imports ``logging_support`` gets the sink, launcher or not.
"""

from __future__ import annotations

import sys
from pathlib import Path

from .config import load_config, resolve_config_dir
from .crash import install_crash_hooks, session_stem
from .logging_support import setup_logging
from .snapshot import write_snapshot

SESSION_DIR_NAME = "aixcoding-diagnostics"
UPSTREAM_ENTRYPOINT = "chrys.app.cli.app:main"


def _session_dir(config_dir: Path) -> Path:
    return config_dir / SESSION_DIR_NAME / session_stem()


def main(argv: list[str] | None = None) -> int:
    """Install hooks, then call the upstream entrypoint with the real argv."""
    if argv is not None:  # pragma: no cover — test seam only
        sys.argv = [sys.argv[0], *argv]
    cfg = load_config()
    config_dir = resolve_config_dir(None)
    if config_dir is not None:
        session = _session_dir(config_dir)
        install_crash_hooks(session)
        write_snapshot(session, extras={"diagnostics_panel": cfg.logging.panel})
    setup_logging(cfg)

    from importlib import import_module

    try:
        # Constant call on purpose: the architecture DAG collector only sees
        # string-constant import_module calls — the R9 exemption registered in
        # tests/architecture/test_layering.py must match a real, visible edge.
        upstream_main = import_module("chrys.app.cli.app").main
    except Exception as exc:
        print(f"aixcoding.launcher: cannot load {UPSTREAM_ENTRYPOINT} ({exc})", file=sys.stderr)
        return 127
    return upstream_main()


if __name__ == "__main__":
    raise SystemExit(main())
