# ruff: noqa: S101
# (tests — asserts are pytest idiom, Chinese prose is the data)
"""The governance tools themselves must stay stdlib-only (devtools design)."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[2] / "aixcoding" / "tools"
ALLOWED_TOPS = frozenset(sys.stdlib_module_names) | {"aixcoding"}


def test_tools_import_stdlib_only():
    offenders: list[str] = []
    for path in sorted(TOOLS_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules = [node.module]
            for module in modules:
                top = module.split(".")[0]
                if top not in ALLOWED_TOPS:
                    offenders.append(f"{path.name}:{node.lineno} imports {module}")
    assert offenders == []
