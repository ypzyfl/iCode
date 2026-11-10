# ruff: noqa: T201
"""Print a deterministic, read-only panorama of batch directories (ADR-0024)."""

from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = REPO_ROOT / "aixcoding" / "docs"
TITLE_SOURCES = ("requirements.md", "design.md", "plan.md")
KEY_DOCUMENTS = (
    "requirements.md",
    "design.md",
    "test-plan.md",
    "plan.md",
    "verification.md",
    "self-review.md",
)


def _display(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _first_h1(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("# ") and line[2:].strip():
            return line[2:].strip()
    return None


def _title(batch: Path, warnings: list[str]) -> str:
    for name in TITLE_SOURCES:
        path = batch / name
        if not path.is_file():
            continue
        try:
            title = _first_h1(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError) as exc:
            warnings.append(f"{_display(path)}: unreadable: {exc}")
            continue
        if title is not None:
            return title
        warnings.append(f"{_display(path)}: no non-empty H1")
    warnings.append(f"{_display(batch)}: no usable title in requirements.md, design.md or plan.md")
    return "(无可用导航标题)"


def _links(batch: Path) -> str:
    links = []
    for name in KEY_DOCUMENTS:
        path = batch / name
        if path.is_file():
            label = name.removesuffix(".md")
            links.append(f"[{label}]({_display(path)})")
    return " · ".join(links) or "—"


def run_report(docs_root: Path = DOCS_ROOT) -> int:
    docs_root = docs_root.resolve()
    batches_root = docs_root / "batches"
    warnings: list[str] = []
    rows: list[str] = []
    if batches_root.is_dir():
        batches = sorted((path for path in batches_root.iterdir() if path.is_dir()), key=lambda path: path.name)
    else:
        batches = []
        warnings.append(f"{_display(batches_root)}: batches directory is missing")
    for batch in batches:
        title = _title(batch, warnings).replace("|", r"\|")
        rows.append(f"| [{batch.name}]({_display(batch)}/) | {title} | {_links(batch)} |")

    print("# 批次目录全景\n")
    print("| 批次目录 | 标题 | 可用关键文档 |")
    print("|---|---|---|")
    for row in rows:
        print(row)
    for warning in warnings:
        print(f"WARNING {warning}", file=sys.stderr)
    print(f"docs_report: {len(batches)} batch director{'y' if len(batches) == 1 else 'ies'}")
    if warnings:
        print(f"docs_report: FAILED with {len(warnings)} warning(s)", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    return run_report(DOCS_ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
