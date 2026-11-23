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

    python3 aixcoding/tools/ci_impact.py /tmp/changed.txt            # upstream domain
    python3 aixcoding/tools/ci_impact.py --domains /tmp/changed.txt  # custom domains

Upstream mode exit codes: 0 = touched=false, 10 = touched=true, 2 = error (empty
list, unreadable input, …). The verdict line on stdout is exact-match validated
by the calling workflow; any other exit code / output combination fails the
filter job (fail-closed, no if-grep exit-code ambiguity).

Custom-domains mode (batch ci-gate-domains, design rules R1-R12) prints two
exact lines ``test_touched=true|false`` / ``guard_touched=true|false`` (exit 0;
2 on error). The domain set is the UNION of every matching rule's domains — an
empty-set rule (pure docs / exempt upstream areas) only contributes nothing and
never removes a domain another rule already gave (e.g. ``aixcoding/mock/*/README.md``
stays aixcoding-tests via the mock rule). Unknown paths default to BOTH domains
(fail-closed); exemptions must be explicit and evidence-backed (design R10/R11).
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


# --- custom-domain scope rules (batch ci-gate-domains, design R1-R12) ---------
#
# Deliberately separate verdict semantics from the upstream rules above; only
# _common's path constants are shared. The rule table below is the SINGLE
# registration point for the custom domains (docs describe it, never copy it).

DOMAIN_AIXCODING_TESTS = "aixcoding-tests"
DOMAIN_GUARD_DEPLOY = "guard-deploy"
BOTH_DOMAINS = frozenset({DOMAIN_AIXCODING_TESTS, DOMAIN_GUARD_DEPLOY})

# R1 — judge infrastructure changes always run both custom domains.
DOMAIN_FORCE_PATHS = frozenset(
    {
        "aixcoding/tools/ci_impact.py",
        "aixcoding/tools/_common.py",
        ".github/workflows/aixcoding-tests.yml",
        ".github/workflows/aixcoding-upstream-ci.yml",
    }
)

# R6 — executable code suffixes under aixcoding/tools/; other types fall through.
TOOL_CODE_SUFFIXES = frozenset({".py", ".sh", ".ps1"})
GUARD_INSTALL_MERGE = "aixcoding/tools/guard_install_merge.py"

# R7 — guard replay corpus; double-consumed (guard job + test_packaging is_file).
MANUAL_TESTS_PATH = "aixcoding/docs/batches/guard-hooks/rule-pack/MANUAL_TESTS.md"

# R8 — shared runtime environment of both custom-domain jobs.
ENV_FILES = frozenset({"pyproject.toml", "uv.lock", ".python-version"})

# R10 — known upstream non-source areas exempt from the custom domains (each
# with code-level evidence; new exemptions need a design revision).
CUSTOM_DOMAIN_EXEMPT_PREFIXES = ("tests/", "docs/", "locales/")

# R11 — "docs-as-test-input" exceptions: consumed by static contract tests
# (two consumption shapes verified across review rounds F1/N1/M1).
DOC_AS_TEST_INPUT = frozenset(
    {
        "AGENTS.md",
        "aixcoding/docs/standards/UPGRADE-RUNBOOK.md",
        "aixcoding/release/INSTALL.md",
        "aixcoding/docs/install-uninstall-support.md",
        "aixcoding/docs/batches/internal-installer/publishing.md",
        "aixcoding/docs/batches/guard-hooks/rule-pack/README.md",
        "aixcoding/docs/batches/guard-hooks/rule-pack/OPERATIONS.md",
        "aixcoding/docs/batches/guard-hooks/rule-pack/PORTING.md",
    }
)

# R11 body — pure docs contribute nothing to the domain set.
PURE_DOC_PREFIXES = ("aixcoding/docs/", "aixcoding/manual/")


def custom_domains(relpath: str) -> set[str]:
    """Domain set for one posix relpath: the UNION of all matching rules.

    Empty-set rules (R10/R11 body) only mark the path as covered — they never
    remove a domain another rule already contributed (design F2 semantics).
    Paths matched by no rule at all default to BOTH domains (R12, fail-closed).
    """
    rel = common.to_posix(relpath.strip())
    if rel in DOMAIN_FORCE_PATHS:  # R1
        return set(BOTH_DOMAINS)
    domains: set[str] = set()
    if rel.startswith(("aixcoding/tests/guard/", "src/chrys/kernel/aixcoding/guard/")):  # R2b/R3
        domains.add(DOMAIN_GUARD_DEPLOY)
    if rel.startswith("aixcoding/tests/"):  # R2
        domains.add(DOMAIN_AIXCODING_TESTS)
    if common.CUSTOM_SRC_TIER_RE.match(rel) is not None:  # R4
        domains.add(DOMAIN_AIXCODING_TESTS)
    if rel.startswith("aixcoding/mock/"):  # R5
        domains.add(DOMAIN_AIXCODING_TESTS)
    if rel.startswith("aixcoding/tools/") and "." in rel.rsplit("/", 1)[-1]:  # R6
        suffix = "." + rel.rsplit(".", 1)[1].lower()
        if suffix in TOOL_CODE_SUFFIXES:
            domains.add(DOMAIN_AIXCODING_TESTS)
            if rel == GUARD_INSTALL_MERGE:
                domains.add(DOMAIN_GUARD_DEPLOY)
    if rel == MANUAL_TESTS_PATH:  # R7 — double consumption (M1)
        domains |= BOTH_DOMAINS
    if rel in ENV_FILES:  # R8
        domains |= BOTH_DOMAINS
    if rel.startswith("src/chrys/") and common.CUSTOM_SRC_TIER_RE.match(rel) is None:  # R9
        domains |= BOTH_DOMAINS
    if rel in DOC_AS_TEST_INPUT:  # R11 exceptions contribute tests
        domains.add(DOMAIN_AIXCODING_TESTS)
    covered = (
        domains
        or rel.startswith(CUSTOM_DOMAIN_EXEMPT_PREFIXES)
        or rel.endswith(".md")
        or rel.startswith(PURE_DOC_PREFIXES)
    )
    if covered:  # R10/R11 body: covered, contribute nothing more
        return domains
    return set(BOTH_DOMAINS)  # R12 — unknown path, fail-closed


def needs_custom_domains(changed_files: list[str]) -> set[str]:
    """Union of custom domains over the whole change list (fail-closed on empty)."""
    files = [f for f in (common.to_posix(ln).strip() for ln in changed_files) if f]
    if not files:
        raise ValueError("empty change list — refusing to classify (fail-closed)")
    union: set[str] = set()
    for f in files:
        union |= custom_domains(f)
    return union


def main(argv: list[str]) -> int:
    if len(argv) == 3 and argv[1] == "--domains":
        try:
            lines = Path(argv[2]).read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            print(f"ci_impact: cannot read {argv[2]}: {exc}", file=sys.stderr)
            return EXIT_ERROR
        try:
            domains = needs_custom_domains(lines)
        except ValueError as exc:
            print(f"ci_impact: {exc}", file=sys.stderr)
            return EXIT_ERROR
        print(f"test_touched={'true' if DOMAIN_AIXCODING_TESTS in domains else 'false'}")
        print(f"guard_touched={'true' if DOMAIN_GUARD_DEPLOY in domains else 'false'}")
        return 0
    if len(argv) != 2:
        print("usage: ci_impact.py <changed-files-list> | ci_impact.py --domains <list>", file=sys.stderr)
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
