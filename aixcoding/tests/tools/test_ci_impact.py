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
