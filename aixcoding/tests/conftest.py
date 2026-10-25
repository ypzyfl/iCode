# ruff: noqa: S101, S603, S607
# (test fixture — asserts are pytest idiom, git subprocess builds mini repos,
#  Chinese prose is the data)
"""aixcoding/tests conftest — self-built fixtures, no upstream tests/support reuse.

See aixcoding/docs/standards/DIRECTORY.md §5 (ADR-0001: the checker must not
share a failure domain with the checked).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _git(repo: Path, *args: str) -> None:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args], check=False, capture_output=True, text=True, encoding="utf-8"
    )
    assert proc.returncode == 0, f"git {args} failed: {proc.stderr}"


def write_tree(root: Path, files: dict[str, str]) -> None:
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


@pytest.fixture
def file_tree(tmp_path: Path):
    """Returns a builder: make(rel->content dict) -> repo root Path."""

    def make(files: dict[str, str]) -> Path:
        write_tree(tmp_path, files)
        return tmp_path

    return make


@pytest.fixture
def git_repo(tmp_path: Path):
    """Returns a builder: make(rel->content dict) -> committed repo Path."""

    def make(files: dict[str, str]) -> Path:
        repo = tmp_path / "repo"
        write_tree(repo, files)
        _git(repo, "init", "-q")
        _git(repo, "add", "-A")
        _git(
            repo,
            "-c",
            "user.email=t@example.com",
            "-c",
            "user.name=t",
            "commit",
            "-q",
            "-m",
            "base",
        )
        return repo

    return make
