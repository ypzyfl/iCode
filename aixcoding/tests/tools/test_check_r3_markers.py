# ruff: noqa: S101, RUF001
# (tests — asserts are pytest idiom, Chinese prose is the data)
"""Unit tests for aixcoding/tools/check_r3_markers.py (mini git repos)."""

from __future__ import annotations

from pathlib import Path

from aixcoding.tools import check_r3_markers as r3

BASE_FILES = {
    "src/chrys/app/up.py": "X = 1\n",
    "src/chrys/app/data.json": '{"a": 1}\n',
}

EXEMPT_MANIFEST = (
    "# 定制清单\n\n"
    "## 标记豁免（无法加注释的格式）\n\n"
    "| 文件 | 改动概述 | 依据 |\n|---|---|---|\n"
    "| src/chrys/app/data.json | tweak | demo design |\n"
)


def test_marker_present_passes(git_repo):
    repo = git_repo(BASE_FILES)
    (repo / "src" / "chrys" / "app" / "up.py").write_text(
        "X = 2  # AIxCoding demo: whitelist entry (src/chrys/kernel/aixcoding/demo)\n", encoding="utf-8"
    )
    assert r3.main(["--base", "HEAD"], repo=repo) == 0


def test_marker_missing_fails(git_repo, capsys):
    repo = git_repo(BASE_FILES)
    (repo / "src" / "chrys" / "app" / "up.py").write_text("X = 2\n", encoding="utf-8")
    assert r3.main(["--base", "HEAD"], repo=repo) == 1
    out = capsys.readouterr().out
    assert "src/chrys/app/up.py" in out


def test_untracked_read_failure_fails_closed(git_repo, monkeypatch, capsys):
    repo = git_repo(BASE_FILES)
    (repo / "src" / "chrys" / "app" / "fresh.py").write_text("Y = 1\n", encoding="utf-8")

    def boom(self, *args, **kwargs):
        raise OSError("boom")

    monkeypatch.setattr(Path, "read_text", boom)
    assert r3.main(["--base", "HEAD"], repo=repo) == 1
    out = capsys.readouterr().out
    assert "cannot read untracked file" in out


def test_untracked_upstream_file_checked_as_whole(git_repo, capsys):
    repo = git_repo(BASE_FILES)
    (repo / "src" / "chrys" / "app" / "fresh.py").write_text(
        "# AIxCoding demo: whole new upstream file (src/chrys/kernel/aixcoding/demo)\nY = 1\n",
        encoding="utf-8",
    )
    assert r3.main(["--base", "HEAD"], repo=repo) == 0
    (repo / "src" / "chrys" / "app" / "fresh2.py").write_text("Z = 1\n", encoding="utf-8")
    assert r3.main(["--base", "HEAD"], repo=repo) == 1


def test_exempt_format_requires_registration(git_repo, capsys):
    repo = git_repo(BASE_FILES)
    (repo / "src" / "chrys" / "app" / "data.json").write_text('{"a": 2}\n', encoding="utf-8")
    assert r3.main(["--base", "HEAD"], repo=repo) == 1
    assert "exemption" in capsys.readouterr().out

    m = repo / "aixcoding" / "docs" / "CUSTOMIZATIONS.md"
    m.parent.mkdir(parents=True, exist_ok=True)
    m.write_text(EXEMPT_MANIFEST, encoding="utf-8")
    assert r3.main(["--base", "HEAD"], repo=repo) == 0


def test_custom_files_out_of_scope(git_repo):
    repo = git_repo(BASE_FILES)
    tools = repo / "aixcoding" / "tools"
    tools.mkdir(parents=True, exist_ok=True)
    (tools / "new.py").write_text("no marker at all\n", encoding="utf-8")
    assert r3.main(["--base", "HEAD"], repo=repo) == 0
