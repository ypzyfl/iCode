# ruff: noqa: T201
# (CLI tool — print is the output channel; Chinese prose is the data)
"""Upstream-CI impact classifier (batch upstream-ci-tiering, ADR-upstream-ci-tiering--pr-gate-tiering).

Answers "does this PR touch the upstream surface?" — a deliberately separate
question from ``_common.is_custom()`` (ownership governance for R2/R3). Only
the low-level path constants are shared; the verdict semantics are not.

Rule priority (first match wins per file; ANY force/upstream file => touched):

1. FORCE   — always run the full upstream suite:
   ``README.pypi.md`` (wheel metadata source), the bridge workflow itself
   (``.github/workflows/aixcoding-upstream-ci.yml``), and this classifier plus
   its data source ``_common.py`` (the judge must never acquit itself).
2. DOC     — skippable: ``docs/`` (trusted doc area incl. ``index.yaml``,
   measured 2026-11-12: 66 md + index.yaml, no scripts) and any other ``*.md``.
3. CUSTOM  — skippable: ``aixcoding/`` (incl. ``manual/``, D2), the ADR-0011
   tier dirs ``src/chrys/{tier}/aixcoding/``, and the exactly-registered
   custom workflow (``.github/workflows/aixcoding-tests.yml``; newly added
   ``aixcoding-*.yml`` files are NOT covered — they default to touched).
4. default — everything else is touched (fail-closed for unknown paths).

Usage (repo root, after actions/checkout)::

    python3 aixcoding/tools/ci_impact.py /tmp/changed.txt

Exit codes: 0 = touched=false, 10 = touched=true, 2 = error (empty list,
unreadable input, …). The verdict line on stdout is exact-match validated by
the calling workflow; any other exit code / output combination fails the
filter job (fail-closed, no if-grep exit-code ambiguity).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from aixcoding.tools import _common as common

EXIT_TOUCHED = 10
EXIT_ERROR = 2

# FORCE: fork-owned or not, these always require the real full-suite run.
FORCE_PATHS = frozenset(
    {
        "README.pypi.md",
        ".github/workflows/aixcoding-upstream-ci.yml",
        "aixcoding/tools/ci_impact.py",
        "aixcoding/tools/_common.py",
    }
)

# CUSTOM skippable workflows: exact registration only — derived from
# CUSTOM_EXACT_PATHS minus the bridge itself (FORCE above), so a newly added
# aixcoding-*.yml stays untouched-by-default until explicitly registered.
CUSTOM_WORKFLOW_PATHS = frozenset(common.CUSTOM_EXACT_PATHS) - {".github/workflows/aixcoding-upstream-ci.yml"}


def classify(relpath: str) -> str:
    """One of 'force' / 'doc' / 'custom' / 'upstream' for a posix relpath."""
    rel = common.to_posix(relpath.strip())
    if rel in FORCE_PATHS:
        return "force"
    if rel.startswith("docs/") or rel.endswith(".md"):
        return "doc"
    if (
        rel.startswith(common.CUSTOM_PATH_PREFIXES)
        or common.CUSTOM_SRC_TIER_RE.match(rel) is not None
        or rel in CUSTOM_WORKFLOW_PATHS
    ):
        return "custom"
    return "upstream"


def needs_upstream_ci(changed_files: list[str]) -> bool:
    """True if any changed file requires the full upstream suite.

    An empty change list is an error (fail-closed): the caller produces it via
    ``git diff --name-only --no-renames`` and an empty diff must abort, never
    count as skippable (upstream-ci batch C2 precedent).
    """
    files = [f for f in (common.to_posix(ln).strip() for ln in changed_files) if f]
    if not files:
        raise ValueError("empty change list — refusing to classify (fail-closed)")
    return any(classify(f) in ("force", "upstream") for f in files)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: ci_impact.py <changed-files-list>", file=sys.stderr)
        return EXIT_ERROR
    try:
        lines = Path(argv[1]).read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        print(f"ci_impact: cannot read {argv[1]}: {exc}", file=sys.stderr)
        return EXIT_ERROR
    try:
        touched = needs_upstream_ci(lines)
    except ValueError as exc:
        print(f"ci_impact: {exc}", file=sys.stderr)
        return EXIT_ERROR
    if touched:
        print("upstream_touched=true")
        return EXIT_TOUCHED
    print("upstream_touched=false")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
