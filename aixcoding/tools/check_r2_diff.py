# ruff: noqa: T201, RUF002
# (CLI tool — print is the output channel; Chinese prose is the data)
"""R2 approval gate (ADR-0007 machine check): every changed upstream file
must be covered by a signed-off design.md R2 table.

The approved pool is the union of "上游改动清单（R2）" tables across
``aixcoding/docs/**/design.md`` **with sign-off status 已确认** — sign-off is
the R2 approval record (R10); tables in unsigned designs authorize nothing.

The changed set is ``git diff --name-only <base>`` (tracked modifications,
staged/unstaged, deletions) **plus untracked files**, so a never-added new
upstream file cannot slip past the gate. Custom paths (root ``aixcoding/``,
``src/chrys/aixcoding/``, the aixcoding CI workflow) are out of R2 scope.

Usage (repo root)::

    uv run python aixcoding/tools/check_r2_diff.py --base <ref>

``--base`` is explicit on purpose (design decision): local pre-commit use
passes the PR base or merge-base; the upgrade runbook passes the upstream
tag; CI passes the event base. No implicit guessing.

Exit code 0 = all upstream changes approved, 1 = unauthorized changes,
2 = environment error (bad ref, not a git repo).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from aixcoding.tools import _common as common


def main(argv: list[str] | None = None, repo: Path | None = None) -> int:
    parser = argparse.ArgumentParser(description="R2 approval diff gate")
    parser.add_argument("--base", required=True, help="git ref to diff against (PR base / upstream tag)")
    args = parser.parse_args(argv)

    root = (repo or common.REPO_ROOT).resolve()
    try:
        changed = common.changed_files(root, args.base)
    except common.GitError as exc:
        print(f"check_r2_diff: git error — {exc}", file=sys.stderr)
        return 2

    upstream_changed = sorted(f for f in changed if common.is_upstream(f))
    approved, notes = common.r2_approved_upstream_files(root / "aixcoding" / "docs")

    unauthorized = [f for f in upstream_changed if f not in approved]

    print(
        f"check_r2_diff: base={args.base} changed={len(changed)} "
        f"upstream_changed={len(upstream_changed)} approved_pool={len(approved)}"
    )
    for note in notes:
        print(f"  warn  {note}")
    for f in sorted(approved):
        state = "changed" if f in upstream_changed else "approved, untouched"
        print(f"  approved: {f} ({state})")

    if unauthorized:
        print("check_r2_diff: unauthorized upstream change(s):")
        for f in unauthorized:
            print(f"  ERROR {f}")
        print("  -> stop and obtain R2 approval (design.md R2 table + sign-off), or revert.")
        return 1
    print("check_r2_diff: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
