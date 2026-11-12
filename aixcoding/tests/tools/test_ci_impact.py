"""Unit matrix for aixcoding/tools/ci_impact.py (batch upstream-ci-tiering).

Covers every rule tier of design 决策 1 plus the fail-closed paths. The
classifier is the single implementation consumed by the bridge workflow, so
these tests guard the real CI verdict, not a mirror.
"""

from __future__ import annotations

import pytest
from aixcoding.tools import ci_impact
from aixcoding.tools.ci_impact import classify, needs_upstream_ci

# --- skippable: custom assets -------------------------------------------------

SKIPPABLE_CASES = [
    "aixcoding/tests/catalog/test_auto_sync_gate.py",
    "aixcoding/docs/batches/upstream-ci-tiering/design.md",
    "aixcoding/mock/model_catalog/README.md",
    "aixcoding/manual/zh-Hans/start/getting-started.md",
    "aixcoding/manual/index.yaml",  # D2: handbook data-only tree stays skippable
    "src/chrys/kernel/aixcoding/auth/session.py",
    "src/chrys/service/aixcoding/config/loader.py",
    "src/chrys/orchestration/aixcoding/x/y.py",
    "src/chrys/app/aixcoding/tui/login.py",
    ".github/workflows/aixcoding-tests.yml",  # exactly-registered custom workflow
    # --- skippable: docs ------------------------------------------------------
    "README.md",
    "AGENTS.md",
    "docs/en/start/what-is-icode.md",
    "docs/index.yaml",  # trusted doc area incl. the index data file (决策 5)
    # Deliberate consequence of the trusted-doc-area rule (test-plan oracle 注):
    # a hypothetical script under docs/ is currently skipped BY DESIGN; if such
    # a file ever appears for real, the rule must be revisited (ADR obligation).
    "docs/build.py",
]

# --- touched: force -----------------------------------------------------------

FORCE_CASES = [
    "README.pypi.md",  # wheel metadata source (D1)
    ".github/workflows/aixcoding-upstream-ci.yml",  # the bridge itself
    "aixcoding/tools/ci_impact.py",  # the judge never acquits itself
    "aixcoding/tools/_common.py",  # the classifier's data source
]

# --- touched: upstream / unknown ----------------------------------------------

UPSTREAM_CASES = [
    "src/chrys/app/app.py",
    "src/chrys/service/models/catalog.py",
    "tests/app/test_app.py",
    "scripts/chrys_test.py",
    "locales/chrys.pot",
    "pyproject.toml",
    "uv.lock",
    ".python-version",
    "hatch_build.py",
    ".github/workflows/ci.yml",
    ".github/workflows/cd.yml",
    ".github/workflows/aixcoding-new.yml",  # not registered: fail-closed, never skippable
    "brand-new-unknown-dir/file.txt",
]


@pytest.mark.parametrize("rel", SKIPPABLE_CASES)
def test_skippable(rel: str) -> None:
    assert classify(rel) in ("doc", "custom")
    assert needs_upstream_ci([rel]) is False


@pytest.mark.parametrize("rel", FORCE_CASES)
def test_force(rel: str) -> None:
    assert classify(rel) == "force"
    assert needs_upstream_ci([rel]) is True


@pytest.mark.parametrize("rel", UPSTREAM_CASES)
def test_upstream(rel: str) -> None:
    assert classify(rel) == "upstream"
    assert needs_upstream_ci([rel]) is True


def test_mixed_pr_114_shape_skippable() -> None:
    """PR #114 form: custom product code + custom tests + batch docs only."""
    files = [
        "src/chrys/service/aixcoding/config/loader.py",
        "src/chrys/service/aixcoding/models/catalog.py",
        "aixcoding/tests/catalog/test_auto_sync_gate.py",
        "aixcoding/docs/batches/catalog-auto-sync/design.md",
        "aixcoding/mock/README.md",
    ]
    assert needs_upstream_ci(files) is False


def test_mixed_with_force_wins() -> None:
    files = ["aixcoding/tests/x/test_y.py", "README.pypi.md"]
    assert needs_upstream_ci(files) is True


def test_rename_shape_source_participates() -> None:
    """--no-renames diff of upstream -> custom move: source deletion is listed."""
    files = ["src/chrys/service/old.py", "src/chrys/service/aixcoding/old.py"]
    assert needs_upstream_ci(files) is True


def test_empty_list_fails_closed() -> None:
    with pytest.raises(ValueError):
        needs_upstream_ci([])
    with pytest.raises(ValueError):
        needs_upstream_ci(["", "   "])


def test_windows_separators_normalized() -> None:
    assert needs_upstream_ci(["aixcoding\\tests\\x\\test_y.py"]) is False
    assert needs_upstream_ci(["src\\chrys\\app\\app.py"]) is True


def test_cli_exit_codes(tmp_path) -> None:
    skipped = tmp_path / "skip.txt"
    skipped.write_text("aixcoding/tests/x/test_y.py\n", encoding="utf-8")
    assert ci_impact.main(["ci_impact.py", str(skipped)]) == 0

    touched = tmp_path / "touched.txt"
    touched.write_text("pyproject.toml\n", encoding="utf-8")
    assert ci_impact.main(["ci_impact.py", str(touched)]) == ci_impact.EXIT_TOUCHED

    empty = tmp_path / "empty.txt"
    empty.write_text("", encoding="utf-8")
    assert ci_impact.main(["ci_impact.py", str(empty)]) == ci_impact.EXIT_ERROR

    assert ci_impact.main(["ci_impact.py", str(tmp_path / "missing.txt")]) == ci_impact.EXIT_ERROR
    assert ci_impact.main(["ci_impact.py"]) == ci_impact.EXIT_ERROR


# --- custom-domain rules (batch ci-gate-domains, design R1-R12) ----------------

import ast  # noqa: E402
from pathlib import Path  # noqa: E402

from aixcoding.tools.ci_impact import (  # noqa: E402
    BOTH_DOMAINS,
    DOMAIN_AIXCODING_TESTS,
    DOMAIN_GUARD_DEPLOY,
    custom_domains,
    needs_custom_domains,
)

TESTS = frozenset({DOMAIN_AIXCODING_TESTS})
GUARD = frozenset({DOMAIN_GUARD_DEPLOY})
BOTH = frozenset(BOTH_DOMAINS)
NONE: frozenset[str] = frozenset()

DOMAIN_CASES = [
    # R1 judge infrastructure
    ("aixcoding/tools/ci_impact.py", BOTH),
    ("aixcoding/tools/_common.py", BOTH),
    (".github/workflows/aixcoding-tests.yml", BOTH),
    (".github/workflows/aixcoding-upstream-ci.yml", BOTH),
    # R2 test assets (+guard overlap)
    ("aixcoding/tests/config/test_config.py", TESTS),
    ("aixcoding/tests/conftest.py", TESTS),
    ("aixcoding/tests/guard/verify_guard_deployed.py", BOTH),
    # R3 guard tree (+ R4 tier rule => both, union semantics)
    ("src/chrys/kernel/aixcoding/guard/guard_install.py", BOTH),
    ("src/chrys/kernel/aixcoding/guard/pack/_guard_core.py", BOTH),
    # R4 custom product code (each tier)
    ("src/chrys/kernel/aixcoding/auth/session.py", TESTS),
    ("src/chrys/service/aixcoding/config/loader.py", TESTS),
    ("src/chrys/app/aixcoding/tui/login.py", TESTS),
    # R5 mock (incl. README union case R5+R11)
    ("aixcoding/mock/model_catalog/server.py", TESTS),
    ("aixcoding/mock/auth/README.md", TESTS),
    # R6 tools executable code; docs fall through to R11
    ("aixcoding/tools/gen_customizations.py", TESTS),
    ("aixcoding/tools/guard_install_merge.py", BOTH),
    ("aixcoding/tools/README.md", NONE),
    # R7 corpus: double consumption (M1)
    ("aixcoding/docs/batches/guard-hooks/rule-pack/MANUAL_TESTS.md", BOTH),
    # R8 shared environment
    ("pyproject.toml", BOTH),
    ("uv.lock", BOTH),
    (".python-version", BOTH),
    # R9 upstream product source
    ("src/chrys/app/app.py", BOTH),
    ("src/chrys/foundation/branding.py", BOTH),
    # R10 evidence-backed exemptions
    ("tests/app/test_app.py", NONE),
    ("docs/en/start/what-is-icode.md", NONE),
    ("docs/index.yaml", NONE),
    ("locales/chrys.pot", NONE),
    # R11 docs-as-test-input exceptions (8) + pure-doc body
    ("AGENTS.md", TESTS),
    ("aixcoding/docs/standards/UPGRADE-RUNBOOK.md", TESTS),
    ("aixcoding/release/INSTALL.md", TESTS),
    ("aixcoding/docs/install-uninstall-support.md", TESTS),
    ("aixcoding/docs/batches/internal-installer/publishing.md", TESTS),
    ("aixcoding/docs/batches/guard-hooks/rule-pack/README.md", TESTS),
    ("aixcoding/docs/batches/guard-hooks/rule-pack/OPERATIONS.md", TESTS),
    ("aixcoding/docs/batches/guard-hooks/rule-pack/PORTING.md", TESTS),
    ("aixcoding/docs/batches/ci-gate-domains/design.md", NONE),
    ("aixcoding/manual/zh-Hans/start/getting-started.md", NONE),
    ("README.md", NONE),
    ("README.pypi.md", NONE),
    # R12 unknown paths fail closed (both custom domains)
    ("brand-new-dir/file.txt", BOTH),
    ("weird.ext", BOTH),
    ("noext", BOTH),
    ("hatch_build.py", BOTH),
    ("scripts/check_wheel.py", BOTH),
    (".github/workflows/cd.yml", BOTH),
    (".github/workflows/aixcoding-new.yml", BOTH),
]


@pytest.mark.parametrize(("rel", "expected"), DOMAIN_CASES)
def test_custom_domains_rule(rel: str, expected: frozenset) -> None:
    assert custom_domains(rel) == set(expected)


def test_union_semantics_empty_rule_never_removes() -> None:
    """F2: the domain set is the union; empty-set rules never remove domains."""
    # R5+R11: mock README is a brand-test consumption object despite being .md
    assert custom_domains("aixcoding/mock/auth/README.md") == set(TESTS)
    # R7+R11: corpus md hits both custom domains
    assert custom_domains("aixcoding/docs/batches/guard-hooks/rule-pack/MANUAL_TESTS.md") == set(BOTH)


def test_needs_custom_domains_union_over_list() -> None:
    assert needs_custom_domains(["aixcoding/tests/x/test_y.py"]) == set(TESTS)
    assert needs_custom_domains(
        ["aixcoding/tests/x/test_y.py", "src/chrys/kernel/aixcoding/guard/pack/rule.py"]
    ) == set(BOTH)
    assert needs_custom_domains(["aixcoding/docs/batches/z/design.md"]) == set()
    with pytest.raises(ValueError):
        needs_custom_domains([])
    with pytest.raises(ValueError):
        needs_custom_domains(["", "   "])


def test_domains_cli_exact_output(tmp_path, capsys) -> None:
    both = tmp_path / "both.txt"
    both.write_text("pyproject.toml\n", encoding="utf-8")
    assert ci_impact.main(["ci_impact.py", "--domains", str(both)]) == 0
    assert capsys.readouterr().out == "test_touched=true\nguard_touched=true\n"

    none = tmp_path / "none.txt"
    none.write_text("aixcoding/docs/batches/z/design.md\n", encoding="utf-8")
    assert ci_impact.main(["ci_impact.py", "--domains", str(none)]) == 0
    assert capsys.readouterr().out == "test_touched=false\nguard_touched=false\n"

    tests_only = tmp_path / "tests_only.txt"
    tests_only.write_text("aixcoding/tests/config/test_config.py\n", encoding="utf-8")
    assert ci_impact.main(["ci_impact.py", "--domains", str(tests_only)]) == 0
    assert capsys.readouterr().out == "test_touched=true\nguard_touched=false\n"

    empty = tmp_path / "empty.txt"
    empty.write_text("", encoding="utf-8")
    assert ci_impact.main(["ci_impact.py", "--domains", str(empty)]) == ci_impact.EXIT_ERROR
    assert ci_impact.main(["ci_impact.py", "--domains"]) == ci_impact.EXIT_ERROR


# --- F6: AST dual-shape scan — every repo file consumed by aixcoding/tests
# must be classified as aixcoding-tests-touched (review F1/N1/M1 enforcement). ---

_TESTS_ROOT = Path(__file__).resolve().parents[2] / "tests"


def _looks_like_repo_path(text: str) -> bool:
    if not text or text.startswith(("http://", "https://")) or "://" in text:
        return False
    if any(ch.isspace() for ch in text):
        return False
    if "\n" in text or "{" in text or "<" in text:
        return False
    last = text.rsplit("/", 1)[-1]
    return "/" in text or ("." in last and not last.startswith("."))


def _div_chain(node: ast.AST) -> tuple[bool, list[str]] | None:
    """(rooted, parts) of a Div chain; rooted iff the leftmost operand is a *ROOT name."""
    if isinstance(node, ast.Name):
        return ("ROOT" in node.id.upper(), [])
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return (False, [node.value])
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        left = _div_chain(node.left)
        right = _div_chain(node.right)
        if left is None or right is None:
            return None
        return (left[0], left[1] + right[1])
    return None


def _repo_paths_consumed_by_tests() -> set[str]:
    """Extract repo-relative path literals from aixcoding/tests sources (AST).

    Only the two real consumption shapes (review N1) — ``REPO_ROOT / "a" / "b"``
    Div chains rooted at a *ROOT name, and ``_read("a/b")`` call arguments —
    and only paths that actually exist in the repo (kills fixture fakes and
    bare assertion strings like ``is_upstream("tests/support/ci.py")``).
    """
    repo_root = Path(__file__).resolve().parents[3]
    consumed: set[str] = set()
    for py in _TESTS_ROOT.rglob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
                chain = _div_chain(node)
                if chain and chain[0] and chain[1]:
                    consumed.update(s for s in ["/".join(chain[1])] if _looks_like_repo_path(s))
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_read":
                for arg in node.args:
                    if (
                        isinstance(arg, ast.Constant)
                        and isinstance(arg.value, str)
                        and _looks_like_repo_path(arg.value)
                    ):
                        consumed.add(arg.value)
    return {p for p in consumed if (repo_root / p).is_file()}


def test_f6_every_consumed_repo_path_hits_aixcoding_tests_domain() -> None:
    consumed = _repo_paths_consumed_by_tests()
    assert consumed, "scan found nothing — extractor broken, not the registry complete"
    missing = sorted(p for p in consumed if DOMAIN_AIXCODING_TESTS not in custom_domains(p))
    assert not missing, (
        "repo files consumed by aixcoding/tests but NOT aixcoding-tests-touched "
        f"(register them in ci_impact.custom_domains): {missing}"
    )
