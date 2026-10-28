# ruff: noqa: T201, RUF001
# (CLI tool — print is the output channel; Chinese prose is the data)
"""Customization manifest generator (DEVELOPMENT.md §5 / §8).

Two modes:

**Generate** (default, current repo) — scans upstream-side files for R3
``AIxCoding`` comment markers (code facts), merges semantic fields from the
registration tables ("定制点登记预告") of **signed-off** design.md files,
and writes ``aixcoding/docs/CUSTOMIZATIONS.md``:

- code facts (paths / marker text / attributed module) derive from the scan
  only — hand-maintained code facts are forbidden (§5);
- semantic fields (anchor / risk / …) merge from design.md registration
  tables — single source of truth, forcing the design-first loop: a marker
  with no registration row is an error (code before design); a registration
  row with no marker is a warning (designed but not yet implemented);
- unsigned design.md tables never contribute (sign-off = R2 approval record);
- the manual zone between markers is preserved verbatim across runs (§8:
  upstream base version lives there, maintained by hand).

**Archaeology** (``--repo <path>``) — scans a foreign checkout (e.g. the
legacy branch copy) and prints/writes a candidate report instead: upstream
marker hits classified comment-vs-brand-string, plus a listing of custom
dev assets. No design.md parsing, no manifest writing (ROADMAP §4 input).

Usage (repo root)::

    uv run python aixcoding/tools/gen_customizations.py
    uv run python aixcoding/tools/gen_customizations.py --repo <path> [--out <file>]

Exit code 0 = ok, 1 = errors (generate mode: manifest NOT rewritten), 2 = env.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from aixcoding.tools import _common as common

MANUAL_START = "<!-- manual-zone-start（人工维护区，生成脚本不触碰；DEVELOPMENT.md §8） -->"
MANUAL_END = "<!-- manual-zone-end -->"
GEN_START = "<!-- generated-zone-start -->"
GEN_END = "<!-- generated-zone-end -->"
MANUAL_TEMPLATE = (
    f"{MANUAL_START}\n- 当前所基于的上游版本：0.31.0\n- 最近一次升级完成日期：（随每次升级完成人工更新）\n{MANUAL_END}"
)

# R3 marker exemptions (formats that cannot carry a comment, ADR-0007): owned
# here so the generated zone stays script-rendered (no hand edits, §5).
MARKER_EXEMPTIONS = (
    (
        "tests/architecture/trajectory_wait_manifest.json",
        "生成产物：wait 节点清单随模块路径刷新（`uv run python -m tests.support.trajectory_wait_inventory`）",
        "aixcoding/docs/tier-migration/design.md",
    ),
)

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    "target",
    ".idea",
    ".vscode",
}


@dataclass
class Registration:
    design: str  # docs-relative posix path of the design.md
    landing: str  # 落点
    fields: dict[str, str] = field(default_factory=dict)  # anchor / risk / extras


def iter_upstream_files(repo: Path):
    for path in sorted(repo.rglob("*")):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(repo).parts
        if any(part in EXCLUDED_DIRS for part in rel_parts):
            continue
        rel = common.to_posix(path.relative_to(repo))
        if common.is_custom(rel):
            continue
        yield rel, path


def scan_markers(repo: Path) -> list[common.MarkerHit]:
    hits: list[common.MarkerHit] = []
    for rel, path in iter_upstream_files(repo):
        hits.extend(common.scan_file(rel, path))
    hits.sort(key=lambda h: (h.file, h.line))
    return hits


def load_registrations(docs_root: Path) -> tuple[list[Registration], list[str]]:
    """Registration rows from signed-off designs only; unsigned ones noted."""
    regs: list[Registration] = []
    notes: list[str] = []
    for doc in common.find_design_docs(docs_root):
        text = doc.read_text(encoding="utf-8", errors="replace")
        rel = common.to_posix(doc.relative_to(docs_root.parents[1]))
        status = common.signoff_status(text) or ""
        rows = common.parse_table_section(text, "定制点登记预告")
        if not rows:
            continue
        if status != common.SIGNED_OFF:
            notes.append(f"{rel}: registration table present but sign-off is '{status or 'missing'}' — ignored")
            continue
        landings = [(row.get("落点") or "").strip().strip("`") for row in rows]
        if rows and not any(landings):
            # Header drift must be loud, not a silent empty registration set.
            notes.append(
                f"{rel}: registration table has {len(rows)} row(s) but no recognizable "
                f"'落点' column — header drift? ignored"
            )
            continue
        for row, landing in zip(rows, landings, strict=True):
            if landing:
                regs.append(Registration(design=rel, landing=common.to_posix(landing), fields=row))
    return regs, notes


def module_matches(module: str, landing: str) -> bool:
    """Marker attribution ↔ registration landing: prefix containment either
    way (dir/file), or short-word form matching a path segment."""
    if not module:
        return False
    m, lnd = common.to_posix(module), common.to_posix(landing)
    if m == lnd or lnd.startswith(m + "/") or m.startswith(lnd + "/"):
        return True
    return "/" not in m and m in lnd.split("/")


def pick_field(row: dict[str, str], *keywords: str) -> str:
    for key, val in row.items():
        if any(kw.lower() in key.lower() for kw in keywords):
            v = val.strip()
            if v:
                return v
    return ""


def match_markers_to_regs(
    markers: list[common.MarkerHit], regs: list[Registration]
) -> tuple[list[tuple[common.MarkerHit, list[Registration]]], list[str], list[str]]:
    """Returns (pairs, errors, warnings)."""
    pairs: list[tuple[common.MarkerHit, list[Registration]]] = []
    errors: list[str] = []
    warnings: list[str] = []
    used: set[int] = set()
    for hit in markers:
        if not hit.is_comment:
            continue  # brand-string hits are not custom points
        matched = [i for i, r in enumerate(regs) if module_matches(hit.module, r.landing)]
        if not matched:
            errors.append(
                f"{hit.file}:{hit.line}: marker `{hit.text}` (module `{hit.module}`) has no "
                f"registration row in any signed-off design.md — code before design (R2/R10)"
            )
            pairs.append((hit, []))
            continue
        used.update(matched)
        pairs.append((hit, [regs[i] for i in matched]))
    for i, r in enumerate(regs):
        if i not in used:
            warnings.append(
                f"{r.design}: registration row `{r.landing}` has no matching marker "
                f"(designed but not implemented yet, or attribution typo)"
            )
    return pairs, errors, warnings


def render_manifest(
    pairs: list[tuple[common.MarkerHit, list[Registration]]],
    warnings: list[str],
    manual_zone: str,
) -> str:
    lines: list[str] = [
        "# 定制清单（CUSTOMIZATIONS）",
        "",
        manual_zone.rstrip(),
        "",
        "> 生成区由 `aixcoding/tools/gen_customizations.py` 自动生成（DEVELOPMENT.md §5：禁止手工维护",
        "> 代码事实）；语义字段合并自已签认 design.md 的定制点登记预告表；`upstream_base` 取人工区",
        "> 全局值（§8）。标记豁免（无法加注释的格式）在下方豁免表登记。",
        "",
        GEN_START,
        "## 定制点",
        "",
    ]
    if not pairs:
        lines.append("（当前为上游干净基线，无定制点。）")
    else:
        lines.append("| id | paths | 标记 | 归属模块 | anchor | risk | reason | tests | removal_condition | 来源 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for idx, (hit, regs) in enumerate(pairs, start=1):
            anchor = "；".join(
                dict.fromkeys(pick_field(r.fields, "anchor") for r in regs if pick_field(r.fields, "anchor"))
            )
            risk = "；".join(
                dict.fromkeys(
                    pick_field(r.fields, "风险", "risk") for r in regs if pick_field(r.fields, "风险", "risk")
                )
            )
            sources = "；".join(dict.fromkeys(r.design for r in regs)) or "待补（缺登记，见错误）"
            marker_cell = hit.text.replace("|", "\\|")
            lines.append(
                f"| C{idx:03d} | {hit.file}:{hit.line} | {marker_cell} | {hit.module} "
                f"| {anchor or '待补'} | {risk or '待补'} | 待补 | 待补 | 待补 | {sources} |"
            )
    lines += [
        "",
        "## 标记豁免（无法加注释的格式）",
        "",
        "| 文件 | 改动概述 | 依据 |",
        "| --- | --- | --- |",
    ]
    if MARKER_EXEMPTIONS:
        lines.extend(f"| `{f}` | {d} | {src} |" for f, d, src in MARKER_EXEMPTIONS)
    else:
        lines.append("（暂无。）")
    lines += [
        "",
        "## 校验备注",
        "",
    ]
    if warnings:
        lines.extend(f"- {w}" for w in warnings)
    else:
        lines.append("- （无警告。）")
    lines += ["", GEN_END, ""]
    return "\n".join(lines)


def extract_manual_zone(text: str) -> str | None:
    start, end = text.find(MANUAL_START), text.find(MANUAL_END)
    if start < 0 or end < 0 or end < start:
        return None
    return text[start : end + len(MANUAL_END)]


def run_generate(repo: Path | None = None) -> int:
    repo = (repo or common.REPO_ROOT).resolve()
    docs_root = repo / "aixcoding" / "docs"
    manifest = docs_root / "CUSTOMIZATIONS.md"
    markers = scan_markers(repo)
    regs, notes = load_registrations(docs_root)
    pairs, errors, warnings = match_markers_to_regs(markers, regs)
    warnings = [*notes, *warnings]

    if errors:
        print("gen_customizations: errors — manifest NOT rewritten:")
        for e in errors:
            print(f"  ERROR {e}")
        for w in warnings:
            print(f"  warn  {w}")
        return 1

    if manifest.exists():
        old = manifest.read_text(encoding="utf-8", errors="replace")
        manual = extract_manual_zone(old)
        if manual is None:
            if GEN_START in old:
                print(
                    "gen_customizations: manual zone markers missing in existing manifest — "
                    "refusing to overwrite; inspect the CUSTOMIZATIONS.md under aixcoding/docs",
                    file=sys.stderr,
                )
                return 2
            print(
                "gen_customizations: existing manifest has no zone markers — treating as first build", file=sys.stderr
            )
        manual_zone = manual or MANUAL_TEMPLATE
    else:
        manual_zone = MANUAL_TEMPLATE

    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(render_manifest(pairs, warnings, manual_zone), encoding="utf-8")
    print(
        f"gen_customizations: wrote {manifest.relative_to(repo)} "
        f"({len(pairs)} custom point(s), {len(warnings)} warning(s))"
    )
    for w in warnings:
        print(f"  warn  {w}")
    return 0


def run_archaeology(repo: Path, out: Path | None) -> int:
    repo = repo.resolve()
    if not repo.is_dir():
        print(f"gen_customizations: --repo not a directory: {repo}", file=sys.stderr)
        return 2
    hits = scan_markers(repo)

    custom_assets: list[str] = []
    # Legacy single-point layout kept for archaeology scans of pre-ADR-0011 checkouts;
    # current repos carry src/chrys/{tier}/aixcoding/ (ADR-0011).
    bases = ["aixcoding", "src/chrys/aixcoding"]
    bases += [common.to_posix(p.relative_to(repo)) for p in sorted((repo / "src" / "chrys").glob("*/aixcoding"))]
    for base in bases:
        base_dir = repo / base
        if base_dir.is_dir():
            custom_assets.extend(
                common.to_posix(p.relative_to(repo))
                for p in sorted(base_dir.rglob("*"))
                if p.is_file() and not any(part in EXCLUDED_DIRS for part in p.relative_to(repo).parts)
            )

    lines = [
        "# 考古扫描报告（candidate custom points）",
        "",
        f"- 扫描目标：`{repo}`",
        (
            f"- 上游侧标记命中：{len(hits)}（注释标记 {sum(h.is_comment for h in hits)} /"
            f" 非注释命中 {sum(not h.is_comment for h in hits)}）"
        ),
        f"- 定制资产文件数：{len(custom_assets)}（aixcoding/ + src/chrys/*/aixcoding/，兼容考古目标旧单点形态）",
        "",
        "## 上游侧命中（甄别分类；非注释命中多为品牌字符串，需人工判定归属）",
        "",
        "| 类型 | 文件:行 | 内容 | 归属模块 |",
        "| --- | --- | --- | --- |",
    ]
    lines.extend(
        f"| {'注释标记' if h.is_comment else '非注释命中'} | {h.file}:{h.line} "
        f"| {h.text.replace('|', chr(92) + '|')} | {h.module or '—'} |"
        for h in hits
    )
    lines += ["", "## 定制资产清单（ROADMAP §4 盘点输入）", ""]
    lines.extend(f"- `{p}`" for p in custom_assets)

    report = "\n".join(lines) + "\n"
    if out is None:
        sys.stdout.write(report)
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"gen_customizations: archaeology report written to {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Customization manifest generator / archaeology scanner")
    parser.add_argument("--repo", type=Path, default=None, help="archaeology mode: foreign checkout to scan")
    parser.add_argument("--out", type=Path, default=None, help="archaeology mode: report file (default stdout)")
    args = parser.parse_args(argv)
    if args.repo is not None:
        return run_archaeology(args.repo, args.out)
    return run_generate()


if __name__ == "__main__":
    raise SystemExit(main())
