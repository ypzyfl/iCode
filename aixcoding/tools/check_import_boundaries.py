# ruff: noqa: T201, RUF002, RUF003
# (CLI tool — print is the output channel; Chinese prose is the data)
"""Import boundary checker (DEVELOPMENT.md §9 / DIRECTORY.md §4–6).

Statically scans ``.py`` files with AST and enforces four rules:

- **B1** — everything under root ``aixcoding/`` (dev assets: tests, tools,
  mocks) must not import the upstream test infrastructure (``tests.*``);
  reading/copying is allowed, importing is not.
- **B2** — upstream code (``src/chrys/`` outside ``src/chrys/*/aixcoding/``)
  must not import the root ``aixcoding`` namespace: that namespace only
  exists in the dev repo, never in the wheel (DIRECTORY.md §4).
- **B3** — customized product code (``src/chrys/*/aixcoding/``, ADR-0011
  tier placement) must not
  import ``tests.*`` nor the root ``aixcoding`` namespace.
- **B4** — ``aixcoding/mock/`` is stdlib-only (DIRECTORY.md §6): standard
  library plus its own package (``aixcoding.mock.*``); no product packages,
  no third-party imports; relative imports must stay inside the package.

Tier/R9 layering is enforced separately by the upstream architecture tests
(``tests/architecture/test_layering.py``) and is intentionally not checked
here (see aixcoding/docs/batches/devtools/design.md, non-goals).

Usage (repo root)::

    uv run python aixcoding/tools/check_import_boundaries.py [repo_root]

Exit code 0 = clean, 1 = violations found, 2 = usage/environment error.
"""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from aixcoding.tools import _common as common

STDLIB_TOPS: frozenset[str] = frozenset(sys.stdlib_module_names)
MOCK_NS = "aixcoding.mock"


@dataclass
class Violation:
    file: str
    lineno: int
    rule: str
    detail: str


def python_module_path(relpath: str) -> list[str]:
    """Relpath -> package parts (``aixcoding/mock/foo.py`` -> ``aixcoding.mock.foo``)."""
    parts = list(Path(relpath).with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return parts


def resolve_relative(pkg_parts: list[str], level: int, target: str | None) -> list[str] | None:
    """Resolve a relative import to absolute module parts; None if it escapes the root."""
    if level <= 0 or level - 1 > len(pkg_parts):
        return None
    base = pkg_parts[: len(pkg_parts) - (level - 1)] if level > 1 else pkg_parts
    return [*base, *(target.split(".") if target else [])]


def _import_stmt_text(node: ast.stmt) -> str:
    try:
        return ast.unparse(node)
    except Exception:
        return "<unparsable import>"


def check_file(relpath: str, path: Path) -> list[Violation]:
    rel = common.to_posix(relpath)
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=str(path))
    except SyntaxError as exc:
        return [Violation(rel, getattr(exc, "lineno", 0) or 0, "parse", f"cannot parse: {exc}")]

    is_custom_root = rel.startswith("aixcoding/")
    is_mock = rel.startswith("aixcoding/mock/")
    is_chrys_aixcoding = common.is_custom_src(rel)
    is_chrys_upstream = rel.startswith("src/chrys/") and not is_chrys_aixcoding

    violations: list[Violation] = []
    module_parts = python_module_path(rel)
    is_pkg_init = Path(rel).name == "__init__.py"
    pkg_parts = module_parts if is_pkg_init else module_parts[:-1]

    def top_of(module: str) -> str:
        return module.split(".")[0]

    def report(rule: str, node: ast.stmt, detail: str) -> None:
        violations.append(Violation(rel, node.lineno, rule, f"{detail} (in `{_import_stmt_text(node)}`)"))

    for node in ast.walk(tree):
        modules: list[tuple[str, ast.stmt]] = []
        relative: list[tuple[int, str | None, ast.stmt]] = []
        if isinstance(node, ast.Import):
            modules = [(alias.name, node) for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                if node.module:
                    modules = [(node.module, node)]
            else:
                relative = [(node.level, node.module, node)]

        for module, stmt in modules:
            top = top_of(module)
            if is_custom_root and top == "tests":
                report("B1", stmt, f"root aixcoding/ dev asset imports upstream test infra `{module}`")
            if is_chrys_upstream and top == "aixcoding":
                report("B2", stmt, f"upstream code imports dev-only namespace `{module}`")
            if is_chrys_aixcoding and top in ("tests", "aixcoding"):
                report("B3", stmt, f"customized product code imports `{module}` (tests.* / root aixcoding.*)")
            if is_mock:
                if top == "aixcoding":
                    if not module.startswith(MOCK_NS):
                        report("B4", stmt, f"mock imports outside aixcoding.mock: `{module}`")
                elif top not in STDLIB_TOPS:
                    report("B4", stmt, f"mock is stdlib-only but imports `{module}`")

        for level, target, stmt in relative:
            if is_mock:
                resolved = resolve_relative(pkg_parts, level, target)
                if resolved is None or not ".".join(resolved).startswith(MOCK_NS):
                    report("B4", stmt, f"relative import escapes aixcoding.mock (level={level} target={target})")
            # B1–B3: a relative import inside chrys/aixcoding trees can never
            # reach the top-level `tests` or root `aixcoding` namespaces.
    return violations


def iter_rule_targets(root: Path):
    for base in ("aixcoding", "src/chrys"):
        for path in sorted((root / base).rglob("*.py")):
            yield common.to_posix(path.relative_to(root)), path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("repo_root", nargs="?", default=str(common.REPO_ROOT))
    args = parser.parse_args(argv)

    root = Path(args.repo_root).resolve()
    if not root.is_dir():
        print(f"check_import_boundaries: repo root not found: {root}", file=sys.stderr)
        return 2

    violations: list[Violation] = []
    scanned = 0
    for relpath, path in iter_rule_targets(root):
        scanned += 1
        violations.extend(check_file(relpath, path))

    print(f"check_import_boundaries: scanned {scanned} files under {root}")
    if violations:
        for v in violations:
            print(f"  [{v.rule}] {v.file}:{v.lineno}: {v.detail}")
        print(f"check_import_boundaries: {len(violations)} violation(s) found")
        return 1
    print("check_import_boundaries: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
