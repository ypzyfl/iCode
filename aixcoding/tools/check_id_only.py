# ruff: noqa: T201
"""Read-only proof for deterministic M1 id/path-only repairs (ADR-0024)."""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from aixcoding.tools import _common as common
from aixcoding.tools import check_docs as cd
from aixcoding.tools import gen_customizations as gc


@dataclass
class Row:
    design: str
    cid: str
    ids: list[str]
    landing: str
    anchor: str
    count: int
    fields: dict[str, str]
    ordinal: int


@dataclass
class Mapping:
    ids: dict[str, list[str]] = field(default_factory=dict)
    paths: dict[str, str] = field(default_factory=dict)
    adr_pairs: list[tuple[str, str, str, str]] = field(default_factory=list)
    designs: set[str] = field(default_factory=set)


def _base_text(repo: Path, base: str, rel: str) -> str | None:
    try:
        return common.git(repo, "show", f"{base}:{rel}")
    except common.GitError:
        return None


def _base_files(repo: Path, base: str, prefix: str) -> list[str]:
    out = common.git(repo, "ls-tree", "-r", "--name-only", "-z", base, "--", prefix)
    return sorted(part for part in out.split("\0") if part)


def _batch(design: str) -> str:
    parts = design.split("/")
    return parts[3] if len(parts) == 5 and parts[2] == "batches" else ""


def _parse_design(rel: str, text: str) -> tuple[list[Row], list[Row]]:
    if common.signoff_status(text) != common.SIGNED_OFF:
        return [], []
    section = gc._registration_section(text)
    rows = common.parse_table_section(gc._active_part(section), gc.REG_SECTION)
    active: list[Row] = []
    for ordinal, row in enumerate(rows, 1):
        cid = row.get("id", "").strip()
        landing = gc._pick(row, "落点").strip().strip("`")
        try:
            count = int(gc._pick(row, "计数") or "1")
        except ValueError:
            continue
        active.append(
            Row(rel, cid, gc.expand_ids(cid), common.to_posix(landing), gc._pick(row, "锚"), count, row, ordinal)
        )
    retired: list[Row] = []
    for ordinal, row in enumerate(gc._parse_retired_rows(section), 1):
        cid = (row.get("id") or "").strip()
        landing = (row.get("原落点") or row.get("落点") or "").strip().strip("`")
        retired.append(Row(rel, cid, gc.expand_ids(cid), common.to_posix(landing), "", 1, row, ordinal))
    return active, retired


def _current_or_base_designs(repo: Path, base: str) -> tuple[dict[str, str], dict[str, str]]:
    before_paths = [p for p in _base_files(repo, base, "aixcoding/docs/batches") if p.endswith("/design.md")]
    before = {rel: _base_text(repo, base, rel) or "" for rel in before_paths}
    docs = repo / "aixcoding/docs/batches"
    after = {
        common.to_posix(path.relative_to(repo)): path.read_text(encoding="utf-8")
        for path in sorted(docs.glob("*/design.md"))
    }
    return before, after


def _all_rows(designs: dict[str, str]) -> tuple[list[Row], list[Row]]:
    active: list[Row] = []
    retired: list[Row] = []
    for rel, text in designs.items():
        a, r = _parse_design(rel, text)
        active.extend(a)
        retired.extend(r)
    return active, retired


def _by_semantics(rows: list[Row], errors: list[str]) -> dict[tuple[str, str], Row]:
    result: dict[tuple[str, str], Row] = {}
    for row in rows:
        key = (row.landing, row.anchor)
        if key in result:
            errors.append(f"{row.design}: duplicate (落点, 锚) is M2, not M1: {key}")
        else:
            result[key] = row
    return result


def _allocate(preferred: str, index: int, occupied: set[str], render) -> str:
    candidate = render(preferred)
    suffix = index
    while candidate in occupied:
        candidate = render(f"{preferred}-m1-{suffix}")
        suffix += 1
    occupied.add(candidate)
    return candidate


def _map_custom_ids(
    repo: Path, base: str, batch: str, before: dict[str, str], after: dict[str, str], mapping: Mapping
) -> list[str]:
    errors: list[str] = []
    before_active, before_retired = _all_rows(before)
    after_active, after_retired = _all_rows(after)
    before_target = [row for row in before_active if _batch(row.design) == batch]
    after_target = [row for row in after_active if _batch(row.design) == batch]
    before_keys = _by_semantics(before_target, errors)
    after_keys = _by_semantics(after_target, errors)
    if set(before_keys) != set(after_keys):
        errors.append(f"{batch}: registration landing/anchor rows were added or removed")
        return errors

    outside = Counter(
        cid for row in [*before_active, *before_retired] if _batch(row.design) != batch for cid in row.ids
    )
    inside = Counter(row.cid for row in before_target)
    repair_ids = {cid for cid, count in inside.items() if count > 1 or outside[cid] > 0}
    repair = [row for row in before_target if row.cid in repair_ids]
    repair_set = set(map(id, repair))
    occupied = {cid for row in [*before_active, *before_retired] if id(row) not in repair_set for cid in row.ids}
    occupied.update(cid for row in [*after_active, *after_retired] if _batch(row.design) != batch for cid in row.ids)

    expected: dict[int, str] = {}
    ordered = sorted(repair, key=lambda row: (row.design, row.ordinal))
    for index, row in enumerate(ordered, 1):
        if gc.ID_RANGE_RE.fullmatch(row.cid):
            errors.append(f"{row.design}: legacy range/twin group cannot be mechanically converted: {row.cid}")
            continue
        if gc.LEGACY_ID_RE.fullmatch(row.cid):
            preferred = f"legacy-{row.cid.lower()}"
        elif gc.SEMANTIC_ID_RE.fullmatch(row.cid):
            preferred = row.cid.split(":", 1)[1]
        else:
            errors.append(f"{row.design}: unsupported legacy id for M1: {row.cid}")
            continue
        expected[id(row)] = _allocate(preferred, index, occupied, lambda slug: f"{batch}:{slug}")

    for key, old in before_keys.items():
        new = after_keys[key]
        old_fields = {k: v for k, v in old.fields.items() if k != "id"}
        new_fields = {k: v for k, v in new.fields.items() if k != "id"}
        if old_fields != new_fields or old.count != new.count:
            errors.append(f"{old.design}: registration semantics changed at {key}")
            continue
        if old.cid in repair_ids:
            wanted = expected.get(id(old))
            if wanted is None or new.cid != wanted:
                errors.append(f"{old.design}: expected deterministic id {wanted!r}, found {new.cid!r}")
                continue
            mapping.ids.setdefault(old.cid, []).append(new.cid)
            mapping.designs.add(old.design)
        elif old.cid != new.cid:
            errors.append(f"{old.design}: id change is outside a proven collision group: {old.cid} -> {new.cid}")
    return errors


def _adr_paths(repo: Path, base: str) -> tuple[dict[str, str], dict[str, str]]:
    before_paths = [p for p in _base_files(repo, base, "aixcoding/docs") if "/adr/" in p and p.endswith(".md")]
    before = {rel: _base_text(repo, base, rel) or "" for rel in before_paths}
    docs = repo / "aixcoding/docs"
    after = {
        common.to_posix(path.relative_to(repo)): path.read_text(encoding="utf-8")
        for path in sorted(docs.glob("**/adr/*.md"))
    }
    return before, after


def _map_adrs(repo: Path, base: str, batch: str, mapping: Mapping) -> list[str]:
    errors: list[str] = []
    before, after = _adr_paths(repo, base)
    prefix = f"aixcoding/docs/batches/{batch}/adr/"
    targets = sorted(rel for rel in before if rel.startswith(prefix))
    all_ids = {rel: cd._adr_id(Path(rel)) for rel in before}
    counts = Counter(adr_id for adr_id in all_ids.values() if adr_id)
    repair = [rel for rel in targets if all_ids[rel] and counts[all_ids[rel]] > 1]
    repair_set = set(repair)
    occupied = {adr_id for rel, adr_id in all_ids.items() if adr_id and rel not in repair_set}
    for index, old_path in enumerate(repair, 1):
        old_id = all_ids[old_path]
        number = old_id.removeprefix("ADR-")
        if not number.isdigit():
            errors.append(f"{old_path}: only numeric legacy ADR ids can be mechanically converted")
            continue
        slug = f"legacy-adr-{number}"
        new_id = _allocate(slug, index, occupied, lambda value: f"ADR-{batch}--{value}")
        new_path = f"aixcoding/docs/standards/adr/{new_id.removeprefix('ADR-')}.md"
        text = after.get(new_path)
        if text is None:
            errors.append(f"{old_path}: expected migrated ADR file is missing: {new_path}")
            continue
        if cd._h1_adr_id(text) != new_id:
            errors.append(f"{new_path}: H1 must be {new_id}")
            continue
        mapping.ids.setdefault(old_id, []).append(new_id)
        mapping.paths[old_path] = new_path
        mapping.adr_pairs.append((old_path, new_path, old_id, new_id))
    return errors


def _changed_files(repo: Path, base: str) -> set[str]:
    tracked = common.git(repo, "diff", "--name-only", "-z", base, "--").split("\0")
    untracked = common.git(repo, "ls-files", "--others", "--exclude-standard", "-z").split("\0")
    return {path for path in [*tracked, *untracked] if path}


def _id_pattern(value: str) -> str:
    return rf"(?<![A-Za-z0-9_.:\-]){re.escape(value)}(?![A-Za-z0-9_.:\-])"


def _id_count(text: str, value: str) -> int:
    return len(re.findall(_id_pattern(value), text))


def _replace_id(text: str, value: str, token: str, count: int = 0) -> str:
    return re.sub(_id_pattern(value), lambda _: token, text, count=count)


def _canonical_pair(rel: str, before: str, after: str, mapping: Mapping) -> tuple[str, str, list[str]]:
    errors: list[str] = []
    for old_path, new_path in mapping.paths.items():
        token = f"__M1_PATH_{len(mapping.paths)}__"
        before = before.replace(old_path, token)
        after = after.replace(new_path, token)
    for old_id, new_ids in mapping.ids.items():
        tokens = [f"__M1_ID_{old_id}_{index}__" for index in range(len(new_ids))]
        if len(new_ids) == 1:
            before = _replace_id(before, old_id, tokens[0])
            after = _replace_id(after, new_ids[0], tokens[0])
            continue
        if rel not in mapping.designs:
            if old_id in before or any(new_id in after for new_id in new_ids):
                errors.append(f"{rel}: ambiguous reference for multi-mapped id {old_id}")
            continue
        if _id_count(before, old_id) != len(new_ids) or any(_id_count(after, new_id) != 1 for new_id in new_ids):
            errors.append(f"{rel}: multi-mapped id {old_id} has references outside unique registration rows")
            continue
        for token in tokens:
            before = _replace_id(before, old_id, token, 1)
        for new_id, token in zip(new_ids, tokens, strict=True):
            after = _replace_id(after, new_id, token, 1)
    return before, after, errors


def _allowlist(before: dict[str, str], batch: str) -> set[str]:
    allowed: set[str] = set()
    for rel, text in before.items():
        if _batch(rel) != batch:
            continue
        match = re.search(r"^## 文件与改动清单.*?(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
        if match:
            allowed.update(re.findall(r"`((?:src|tests|aixcoding)/[^`]+)`", match.group(0)))
    return allowed


def run_check(repo: Path, base: str, batch: str) -> int:
    repo = repo.resolve()
    errors: list[str] = []
    try:
        before, after = _current_or_base_designs(repo, base)
        mapping = Mapping()
        errors.extend(_map_custom_ids(repo, base, batch, before, after, mapping))
        errors.extend(_map_adrs(repo, base, batch, mapping))
        changed = _changed_files(repo, base)
        allowed = _allowlist(before, batch)
        prefix = f"aixcoding/docs/batches/{batch}/"
        handled = {path for pair in mapping.adr_pairs for path in pair[:2]}
        for old_path, new_path, old_id, new_id in mapping.adr_pairs:
            old_text = _base_text(repo, base, old_path)
            new_text = (repo / new_path).read_text(encoding="utf-8") if (repo / new_path).is_file() else None
            if old_text is None or new_text is None:
                errors.append(f"{old_path}: ADR rename source/target missing")
                continue
            local = Mapping(ids={old_id: [new_id]}, paths={old_path: new_path})
            left, right, pair_errors = _canonical_pair(old_path, old_text, new_text, local)
            errors.extend(pair_errors)
            if left != right:
                errors.append(f"{old_path}: ADR content differs beyond declared id/path mapping")
        for rel in sorted(changed - handled):
            if rel in {"aixcoding/docs/INDEX.md", "aixcoding/docs/ROADMAP.md"}:
                errors.append(f"{rel}: shared governance files are outside M1 authorization")
                continue
            if not rel.startswith(prefix) and rel not in allowed:
                errors.append(f"{rel}: changed file is outside the signed M1 scope")
                continue
            old_text = _base_text(repo, base, rel)
            path = repo / rel
            new_text = path.read_text(encoding="utf-8") if path.is_file() else None
            if old_text is None or new_text is None:
                errors.append(f"{rel}: only in-place edits or declared ADR renames are allowed")
                continue
            left, right, pair_errors = _canonical_pair(rel, old_text, new_text, mapping)
            errors.extend(pair_errors)
            if left != right:
                errors.append(f"{rel}: content differs beyond declared id/path mapping")
    except (OSError, UnicodeError, ValueError, common.GitError) as exc:
        errors.append(str(exc))
    if errors:
        for error in errors:
            print(f"ERROR {error}", file=sys.stderr)
        print(f"check_id_only: FAILED with {len(errors)} error(s)", file=sys.stderr)
        return 1
    print(
        f"check_id_only: OK — {len(mapping.ids)} id mapping(s), {len(mapping.adr_pairs)} ADR migration(s), zero writes"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="pre-repair Git revision")
    parser.add_argument("--batch", required=True, help="unmerged batch slug being repaired")
    args = parser.parse_args(argv)
    return run_check(Path.cwd(), args.base, args.batch)


if __name__ == "__main__":
    raise SystemExit(main())
