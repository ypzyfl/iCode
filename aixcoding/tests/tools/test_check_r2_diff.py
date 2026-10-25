# ruff: noqa: S101, RUF001
# (tests — asserts are pytest idiom, Chinese prose is the data)
"""Unit tests for aixcoding/tools/check_r2_diff.py (mini git repos)."""

from __future__ import annotations

from aixcoding.tools import check_r2_diff as r2

SIGNED_R2 = (
    "# 设计：demo\n\n- 责任人：t\n- 状态：已确认\n- 确认日期：2026-10-25\n\n"
    "## 上游改动清单（R2）\n\n"
    "| 文件 | 改什么 | 预估行数 | 标记注释位置 |\n|---|---|---|---|\n"
    "| src/chrys/app/up.py | tweak | 1 | 行尾 |\n"
)
UNSIGNED_R2 = SIGNED_R2.replace("- 状态：已确认", "- 状态：草案")

BASE_FILES = {
    "src/chrys/app/up.py": "X = 1\n",
    "aixcoding/tools/dummy.py": "Y = 2\n",
}


def test_no_upstream_change_passes(git_repo):
    repo = git_repo(BASE_FILES)
    (repo / "aixcoding" / "tools" / "new.py").write_text("Z = 3\n", encoding="utf-8")
    assert r2.main(["--base", "HEAD"], repo=repo) == 0


def test_unapproved_upstream_change_fails(git_repo, capsys):
    repo = git_repo(BASE_FILES)
    (repo / "src" / "chrys" / "app" / "up.py").write_text("X = 2\n", encoding="utf-8")
    (repo / "src" / "chrys" / "app" / "brand_new.py").write_text("N = 1\n", encoding="utf-8")  # untracked
    assert r2.main(["--base", "HEAD"], repo=repo) == 1
    out = capsys.readouterr().out
    assert "src/chrys/app/up.py" in out and "src/chrys/app/brand_new.py" in out


def test_unsigned_design_does_not_authorize(git_repo, capsys):
    repo = git_repo({**BASE_FILES, "aixcoding/docs/demo/design.md": UNSIGNED_R2})
    (repo / "src" / "chrys" / "app" / "up.py").write_text("X = 2\n", encoding="utf-8")
    assert r2.main(["--base", "HEAD"], repo=repo) == 1
    out = capsys.readouterr().out
    assert "sign-off" in out  # note about the ignored table


def test_signed_design_approves_only_listed_files(git_repo, capsys):
    repo = git_repo({**BASE_FILES, "aixcoding/docs/demo/design.md": SIGNED_R2})
    (repo / "src" / "chrys" / "app" / "up.py").write_text("X = 2\n", encoding="utf-8")
    assert r2.main(["--base", "HEAD"], repo=repo) == 0
    (repo / "src" / "chrys" / "app" / "other.py").write_text("O = 1\n", encoding="utf-8")
    assert r2.main(["--base", "HEAD"], repo=repo) == 1
    assert "src/chrys/app/other.py" in capsys.readouterr().out


def test_bad_base_ref_is_env_error(git_repo):
    repo = git_repo(BASE_FILES)
    assert r2.main(["--base", "no-such-ref-anywhere"], repo=repo) == 2


def test_chinese_filenames_not_misrouted_by_quotepath(git_repo, capsys):
    # git core.quotepath defaults to quoting non-ASCII paths as octal escapes;
    # the tool must see real UTF-8 so custom Chinese-named files route as custom.
    repo = git_repo(
        {
            **BASE_FILES,
            "aixcoding/docs/standards/adr/0001-定制测试独立收集.md": "# ADR\n",
        }
    )
    (repo / "aixcoding" / "docs" / "standards" / "adr" / "0001-定制测试独立收集.md").write_text(
        "# ADR updated\n", encoding="utf-8"
    )
    assert r2.main(["--base", "HEAD"], repo=repo) == 0  # custom path change: no upstream change
    out = capsys.readouterr().out
    assert "upstream_changed=0" in out
