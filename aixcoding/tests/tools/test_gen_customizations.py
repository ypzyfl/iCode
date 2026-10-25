# ruff: noqa: S101, RUF001
# (tests — asserts are pytest idiom, Chinese prose is the data)
"""Unit tests for aixcoding/tools/gen_customizations.py (generate + archaeology)."""

from __future__ import annotations

from pathlib import Path

from aixcoding.tools import gen_customizations as gc

SIGNED_DEMO = (
    "# 设计：demo\n\n- 责任人：t\n- 状态：已确认\n- 确认日期：2026-10-25\n\n"
    "## 定制点登记预告\n\n"
    "| 落点 | anchor（依赖的上游符号） | 风险等级 |\n|---|---|---|\n"
    "| src/chrys/aixcoding/demo | MODULE_ORDER | 低 |\n"
)
UNSIGNED_DEMO = SIGNED_DEMO.replace("- 状态：已确认", "- 状态：草案")

UPSTREAM_WITH_MARKER = "VALUE = 1  # AIxCoding demo: whitelist one entry (src/chrys/aixcoding/demo)\n"


def manifest_of(repo: Path) -> str:
    return (repo / "aixcoding" / "docs" / "CUSTOMIZATIONS.md").read_text(encoding="utf-8")


def test_clean_baseline_empty(file_tree):
    repo = file_tree({"src/chrys/app/up.py": "X = 1\n"})
    assert gc.run_generate(repo) == 0
    text = manifest_of(repo)
    assert "无定制点" in text
    assert "0.31.0" in text  # manual zone template carries the upstream base


def test_manual_zone_preserved_across_runs(file_tree):
    repo = file_tree({"src/chrys/app/up.py": "X = 1\n"})
    assert gc.run_generate(repo) == 0
    m = repo / "aixcoding" / "docs" / "CUSTOMIZATIONS.md"
    old = m.read_text(encoding="utf-8")
    m.write_text(
        old.replace("- 当前所基于的上游版本：0.31.0", "- 当前所基于的上游版本：9.9.9"),
        encoding="utf-8",
    )
    assert gc.run_generate(repo) == 0
    assert "9.9.9" in manifest_of(repo)


def test_marker_without_registration_errors(file_tree):
    repo = file_tree({"src/chrys/app/up.py": UPSTREAM_WITH_MARKER})
    assert gc.run_generate(repo) == 1
    assert not (repo / "aixcoding" / "docs" / "CUSTOMIZATIONS.md").exists()


def test_signed_design_registration_merges(file_tree):
    repo = file_tree(
        {
            "src/chrys/app/up.py": UPSTREAM_WITH_MARKER,
            "aixcoding/docs/demo/design.md": SIGNED_DEMO,
        }
    )
    assert gc.run_generate(repo) == 0
    text = manifest_of(repo)
    assert "src/chrys/app/up.py:1" in text
    assert "MODULE_ORDER" in text  # anchor merged
    assert "aixcoding/docs/demo/design.md" in text  # source linked


def test_unsigned_design_does_not_authorize(file_tree):
    repo = file_tree(
        {
            "src/chrys/app/up.py": UPSTREAM_WITH_MARKER,
            "aixcoding/docs/demo/design.md": UNSIGNED_DEMO,
        }
    )
    assert gc.run_generate(repo) == 1


def test_registered_but_unimplemented_warns_not_fails(file_tree):
    repo = file_tree(
        {
            "src/chrys/app/up.py": "X = 1\n",  # no marker yet
            "aixcoding/docs/demo/design.md": SIGNED_DEMO,
        }
    )
    assert gc.run_generate(repo) == 0
    assert "no matching marker" in manifest_of(repo)


def test_archaeology_mode(file_tree, tmp_path):
    repo = file_tree(
        {
            "src/chrys/app/up.py": UPSTREAM_WITH_MARKER,
            "src/chrys/foundation/branding.py": 'APP = "AIxCoding"\n',
            "src/chrys/aixcoding/demo.py": "X = 1\n",
        }
    )
    out = tmp_path / "report.md"
    assert gc.run_archaeology(repo, out) == 0
    report = out.read_text(encoding="utf-8")
    assert "注释标记" in report and "非注释命中" in report
    assert "src/chrys/app/up.py:1" in report
    assert "src/chrys/foundation/branding.py" in report
    assert "src/chrys/aixcoding/demo.py" in report  # custom asset listing


def test_archaeology_bad_repo_path(tmp_path):
    assert gc.run_archaeology(tmp_path / "nope", None) == 2
