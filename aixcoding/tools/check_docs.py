# ruff: noqa: RUF001, T201
# (validates Chinese sign-off fields — fullwidth punctuation is the data;
#  CLI tool — print is the output channel)
"""Governance document validation and merge-time closure checks (R10 / ADR-0024).

Default mode validates sign-off fields and ADR identity/location while allowing
local drafts. ``--closure`` additionally enforces signed decisions, six required
batch files, exact ADR references, structured plan completion records, and the
machine-readable closure exemption list.
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = REPO_ROOT / "aixcoding" / "docs"

FIELD_OWNER = re.compile(r"^-\s*责任人[：:]\s*(.*)$")
FIELD_STATUS = re.compile(r"^-\s*状态[：:]\s*(.*)$")
FIELD_DATE = re.compile(r"^-\s*确认日期[：:]\s*(.*)$")
FIELD_APPROVER = re.compile(r"^-\s*审批人[：:]\s*(.*)$")
FIELD_APPROVE_DATE = re.compile(r"^-\s*审批日期[：:]\s*(.*)$")
DATE_FORMAT = re.compile(r"\d{4}-\d{2}-\d{2}")
DEP_SECTION = re.compile(r"^##\s*第三方依赖申请")

SLUG = r"[a-z0-9]+(?:-[a-z0-9]+)*"
NUMERIC_ADR_ID = r"\d{4}"
SEMANTIC_ADR_ID = rf"{SLUG}--{SLUG}"
ADR_REF_RE = re.compile(rf"(?<![A-Za-z0-9_-])ADR-(?:{NUMERIC_ADR_ID}|{SEMANTIC_ADR_ID})(?![A-Za-z0-9_-])")
SUPERSEDED_REF = re.compile(rf"被\s*(ADR-(?:{NUMERIC_ADR_ID}|{SEMANTIC_ADR_ID}))")
SEMANTIC_FILE_RE = re.compile(rf"(?P<batch>{SLUG})--(?P<decision>{SLUG})\.md")
NUMERIC_FILE_RE = re.compile(r"(?P<number>\d{4})-")

VALID_STATUS = ("草案", "已确认", "被取代")
VALID_STATUS_DOC = ("草案", "已确认")
REQUIRED_BATCH_FILES = (
    "requirements.md",
    "design.md",
    "test-plan.md",
    "plan.md",
    "verification.md",
    "self-review.md",
)
PLAN_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9_.-])(self-review|verification)(?:\.md)?(?![A-Za-z0-9_.-])")


def _display(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _header(text: str) -> list[str]:
    lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            break
        lines.append(line)
    return lines


def _first_match(lines: list[str], pattern: re.Pattern[str]) -> str | None:
    for line in lines:
        match = pattern.match(line.strip())
        if match:
            return match.group(1).strip()
    return None


def _status(text: str) -> str:
    raw = _first_match(_header(text), FIELD_STATUS) or ""
    return raw.split("（")[0].split("(")[0].strip()


def _successor_path(path: Path, adr_id: str) -> Path | None:
    adr_id = adr_id.removeprefix("ADR-")
    if adr_id.isdigit():
        return next(path.parent.glob(f"{int(adr_id):04d}-*.md"), None)
    candidate = path.parent / f"{adr_id}.md"
    return candidate if candidate.is_file() else None


def check_signoff(path: Path, text: str, *, superseded_ok: bool) -> list[str]:
    errors: list[str] = []
    rel = _display(path)
    lines = _header(text)
    owner = _first_match(lines, FIELD_OWNER)
    status_raw = _first_match(lines, FIELD_STATUS)
    date = _first_match(lines, FIELD_DATE)
    if owner is None:
        errors.append(f"{rel}: missing '- 责任人：' field")
    if status_raw is None:
        errors.append(f"{rel}: missing '- 状态：' field")
        return errors
    if date is None:
        errors.append(f"{rel}: missing '- 确认日期：' field")

    status = status_raw.split("（")[0].split("(")[0].strip()
    valid = VALID_STATUS if superseded_ok else VALID_STATUS_DOC
    if status not in valid:
        errors.append(f"{rel}: invalid status {status_raw!r} (expected one of {valid})")
        return errors
    if status == "已确认":
        if not owner:
            errors.append(f"{rel}: status 已确认 but 责任人 is empty")
        if not date:
            errors.append(f"{rel}: status 已确认 but 确认日期 is empty")
        elif not DATE_FORMAT.fullmatch(date):
            errors.append(f"{rel}: 确认日期 {date!r} does not match YYYY-MM-DD")
    if status == "被取代" and superseded_ok:
        match = SUPERSEDED_REF.search(status_raw)
        if not match:
            errors.append(f"{rel}: status 被取代 must reference a numeric or semantic ADR successor")
        elif _successor_path(path, match.group(1)) is None:
            errors.append(f"{rel}: superseding {match.group(1)} not found in {path.parent.name}/")
    return errors


def check_design(path: Path, text: str) -> list[str]:
    errors = check_signoff(path, text, superseded_ok=False)
    rel = _display(path)
    if not any(DEP_SECTION.match(line.strip()) for line in text.splitlines()):
        return errors
    if _status(text) != "已确认":
        return errors
    lines = _header(text)
    approver = _first_match(lines, FIELD_APPROVER)
    approve_date = _first_match(lines, FIELD_APPROVE_DATE)
    if approver is None or approve_date is None:
        errors.append(f"{rel}: has 第三方依赖申请 section but header lacks 审批人/审批日期 fields")
        return errors
    if not approver:
        errors.append(f"{rel}: dependency section present but 审批人 is empty")
    if not approve_date:
        errors.append(f"{rel}: dependency section present but 审批日期 is empty")
    return errors


def _adr_id(path: Path) -> str | None:
    match = NUMERIC_FILE_RE.match(path.name)
    if match:
        return f"ADR-{match.group('number')}"
    match = SEMANTIC_FILE_RE.fullmatch(path.name)
    if match:
        return f"ADR-{match.group('batch')}--{match.group('decision')}"
    return None


def _h1_adr_id(text: str) -> str | None:
    first = text.splitlines()[0].strip() if text.splitlines() else ""
    if not first.startswith("# "):
        return None
    title = first[2:].strip()
    match = re.match(rf"(ADR-(?:{NUMERIC_ADR_ID}|{SEMANTIC_ADR_ID}))(?=[：:\s]|$)", title)
    return match.group(1) if match else None


def _check_adr_identity(path: Path, text: str, docs_root: Path) -> list[str]:
    errors: list[str] = []
    rel = _display(path)
    global_pool = docs_root / "standards" / "adr"
    if path.parent != global_pool:
        errors.append(f"{rel}: ADR must be in {global_pool.name}/ global pool; feature pools are forbidden")
    adr_id = _adr_id(path)
    if adr_id is None:
        errors.append(f"{rel}: invalid ADR filename (expected NNNN-*.md or <batch>--<decision>.md)")
        return errors
    h1_id = _h1_adr_id(text)
    if h1_id != adr_id:
        errors.append(f"{rel}: H1 ADR id {h1_id!r} does not match filename id {adr_id!r}")
    semantic = SEMANTIC_FILE_RE.fullmatch(path.name)
    if semantic and not (docs_root / "batches" / semantic.group("batch")).is_dir():
        errors.append(f"{rel}: ADR batch directory does not exist: {semantic.group('batch')}")
    return errors


def _without_fences(text: str) -> str:
    lines: list[str] = []
    in_code = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_code = not in_code
            continue
        if not in_code:
            lines.append(line)
    return "\n".join(lines)


def _check_adr_references(docs_root: Path, adr_status: dict[str, str]) -> list[str]:
    errors: list[str] = []
    for path in sorted(docs_root.rglob("*.md")):
        if "templates" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"{_display(path)}: unreadable while checking ADR references: {exc}")
            continue
        for match in ADR_REF_RE.finditer(_without_fences(text)):
            adr_id = match.group(0)
            status = adr_status.get(adr_id)
            if status is None:
                errors.append(f"{_display(path)}: ADR reference {adr_id} has no global-pool target")
            elif status not in {"已确认", "被取代"}:
                errors.append(f"{_display(path)}: ADR reference {adr_id} targets a draft")
    return errors


def _load_exemptions(docs_root: Path) -> tuple[dict[str, set[str]], list[str]]:
    path = docs_root / "standards" / "closure-exemptions.toml"
    if not path.is_file():
        return {}, [f"{_display(path)}: closure exemption file is required"]
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        raw = data.get("exemptions", {})
        if not isinstance(raw, dict):
            raise TypeError("exemptions must be a table")
        exemptions: dict[str, set[str]] = {}
        for batch, files in raw.items():
            if not isinstance(files, list) or any(name not in REQUIRED_BATCH_FILES for name in files):
                raise ValueError(f"invalid missing-file list for {batch}")
            exemptions[batch] = set(files)
        return exemptions, []
    except (OSError, UnicodeError, tomllib.TOMLDecodeError, TypeError, ValueError) as exc:
        return {}, [f"{_display(path)}: invalid closure exemptions: {exc}"]


def _check_batch_files(docs_root: Path, exemptions: dict[str, set[str]]) -> list[str]:
    errors: list[str] = []
    batches_root = docs_root / "batches"
    if not batches_root.is_dir():
        return [f"{_display(batches_root)}: batches directory is required for closure"]
    known = set(exemptions)
    for batch in sorted(path for path in batches_root.iterdir() if path.is_dir()):
        missing = {name for name in REQUIRED_BATCH_FILES if not (batch / name).is_file()}
        allowed = exemptions.get(batch.name, set())
        errors.extend(f"{_display(batch)}: required batch file missing: {name}" for name in sorted(missing - allowed))
        errors.extend(f"{_display(batch)}: stale closure exemption: {name}" for name in sorted(allowed - missing))
        known.discard(batch.name)
    errors.extend(f"closure-exemptions.toml: stale exemption for unknown batch: {batch}" for batch in sorted(known))
    return errors


def _table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _minimal_markdown(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [f"{_display(path)}: completion target unreadable: {exc}"]
    lines = text.splitlines()
    h1 = next((index for index, line in enumerate(lines) if line.startswith("# ")), None)
    if h1 is None:
        return [f"{_display(path)}: completion target has no H1"]
    if not any(line.strip() for line in lines[h1 + 1 :]):
        return [f"{_display(path)}: completion target has no non-blank body after H1"]
    return []


def _check_plan_completion(batch: Path, allowed_missing: set[str]) -> list[str]:
    path = batch / "plan.md"
    if not path.is_file():
        return []
    try:
        lines = _without_fences(path.read_text(encoding="utf-8")).splitlines()
    except (OSError, UnicodeError) as exc:
        return [f"{_display(path)}: unreadable plan: {exc}"]
    errors: list[str] = []
    targets: set[str] = set()
    index = 0
    while index < len(lines):
        header = _table_cells(lines[index]) if lines[index].strip().startswith("|") else []
        if "任务" not in header or "状态" not in header or index + 1 >= len(lines):
            index += 1
            continue
        task_col = header.index("任务")
        status_col = header.index("状态")
        index += 2
        while index < len(lines) and lines[index].strip().startswith("|"):
            cells = _table_cells(lines[index])
            if max(task_col, status_col) < len(cells):
                status = re.sub(r"[\s`*_]", "", cells[status_col])
                complete = re.fullmatch(r"完成(?:|[（(].*[）)])", status) is not None
                haystack = f"{cells[task_col]} {cells[status_col]}"
                if complete:
                    targets.update(match.group(1) for match in PLAN_TOKEN_RE.finditer(haystack))
            index += 1
    for token in sorted(targets):
        filename = f"{token}.md"
        if filename in allowed_missing:
            continue
        target = batch / filename
        if not target.is_file():
            errors.append(f"{_display(path)}: completed plan row requires {filename}")
        else:
            errors.extend(_minimal_markdown(target))
    return errors


def run_check(docs_root: Path = DOCS_ROOT, *, closure: bool = False) -> int:
    docs_root = docs_root.resolve()
    adr_files = sorted(path for path in docs_root.glob("**/adr/*.md") if "templates" not in path.parts)
    design_files = sorted(path for path in docs_root.glob("**/design.md") if "templates" not in path.parts)
    review_files = sorted(path for path in docs_root.glob("**/self-review.md") if "templates" not in path.parts)
    errors: list[str] = []
    texts: dict[Path, str] = {}
    for path in [*adr_files, *design_files, *review_files]:
        try:
            texts[path] = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"{_display(path)}: unreadable: {exc}")
    for path in adr_files:
        if path in texts:
            errors.extend(check_signoff(path, texts[path], superseded_ok=True))
            errors.extend(_check_adr_identity(path, texts[path], docs_root))
    for path in design_files:
        if path in texts:
            errors.extend(check_design(path, texts[path]))
    for path in review_files:
        if path in texts:
            errors.extend(check_signoff(path, texts[path], superseded_ok=False))

    adr_status: dict[str, str] = {}
    for path in adr_files:
        if path not in texts:
            continue
        adr_id = _adr_id(path)
        if adr_id is None:
            continue
        if adr_id in adr_status:
            errors.append(f"{_display(path)}: duplicate ADR id {adr_id}")
        else:
            adr_status[adr_id] = _status(texts[path])

    exemptions: dict[str, set[str]] = {}
    if closure:
        for path, text in texts.items():
            if _status(text) == "草案":
                errors.append(f"{_display(path)}: draft decision/review document is forbidden by closure")
        errors.extend(_check_adr_references(docs_root, adr_status))
        exemptions, exemption_errors = _load_exemptions(docs_root)
        errors.extend(exemption_errors)
        errors.extend(_check_batch_files(docs_root, exemptions))
        batches_root = docs_root / "batches"
        if batches_root.is_dir():
            for batch in sorted(path for path in batches_root.iterdir() if path.is_dir()):
                errors.extend(_check_plan_completion(batch, exemptions.get(batch.name, set())))

    print(
        f"check_docs: scanned {len(adr_files)} ADR(s), {len(design_files)} design(s), "
        f"{len(review_files)} self-review(s) under aixcoding/docs"
    )
    for err in errors:
        print(f"  ERROR {err}", file=sys.stderr)
    if errors:
        print(f"check_docs: FAILED with {len(errors)} error(s)", file=sys.stderr)
        return 1
    print("check_docs: OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--closure", action="store_true", help="enforce merge-time document closure")
    args = parser.parse_args(argv)
    return run_check(closure=args.closure)


if __name__ == "__main__":
    raise SystemExit(main())
