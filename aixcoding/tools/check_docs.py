# ruff: noqa: RUF001, RUF002, T201
# (validates Chinese sign-off fields — fullwidth punctuation is the data;
#  CLI tool — print is the output channel)
"""Sign-off field validation for governance documents (R10 / R11).

Scans under ``aixcoding/docs`` (``standards/templates/`` excluded):

- ``**/adr/*.md``        ADRs (global pool ``standards/adr/`` + feature pools)
- ``**/design.md``       feature designs (sign-off = R2 approval record)
- ``**/self-review.md``  dual-AI review records

Header sign-off block (shared shape across the three kinds):

- required fields present: ``- 责任人：`` / ``- 状态：`` / ``- 确认日期：``
- status is one of: 草案 / 已确认 (+ 被取代 for ADRs only)
- status 已确认  -> 责任人 and 确认日期 filled, date matches YYYY-MM-DD
- status 被取代 -> references ``被 ADR-<num>`` and that ADR exists in the
  same directory (ADR-only)

design.md extra (R11): when the document contains a ``第三方依赖申请``
section and its status is 已确认, the header ``审批人`` / ``审批日期``
fields must be present and non-empty. Field presence only — whether the
approver actually consented is an honesty boundary handled by spot checks
and git blame, not by this script.

Usage (repo root)::

    uv run python aixcoding/tools/check_docs.py

Exit code 0 = all pass, 1 = errors found.

v1 scope note: git blame cross-check (sign-off line author vs. the named
owner) is a planned enhancement; CI wiring lands with the aixcoding-tests
workflow. See aixcoding/docs/standards/adr/0004.
"""

from __future__ import annotations

import re
import sys
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
SUPERSEDED_REF = re.compile(r"被\s*ADR-(\d+)")
DEP_SECTION = re.compile(r"^##\s*第三方依赖申请")

VALID_STATUS = ("草案", "已确认", "被取代")
VALID_STATUS_DOC = ("草案", "已确认")


def _header(text: str) -> list[str]:
    """Lines before the first body heading (``## ``); falls back to all lines.

    Robust against long leading comment blocks (e.g. templates/adr.md keeps
    its sign-off fields at lines 27-30) — no fixed window.
    """
    lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            break
        lines.append(line)
    return lines


def _first_match(lines: list[str], pattern: re.Pattern[str]) -> str | None:
    for line in lines:
        m = pattern.match(line.strip())
        if m:
            return m.group(1).strip()
    return None


def check_signoff(path: Path, text: str, *, superseded_ok: bool) -> list[str]:
    """Shared header validation; superseded handling only when allowed."""
    errors: list[str] = []
    rel = path.relative_to(REPO_ROOT).as_posix()
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
        m = SUPERSEDED_REF.search(status_raw)
        if not m:
            errors.append(f"{rel}: status 被取代 must reference '被 ADR-<num>'")
        else:
            successor = next(path.parent.glob(f"{int(m.group(1)):04d}-*.md"), None)
            if successor is None:
                errors.append(f"{rel}: superseding ADR-{m.group(1)} not found in {path.parent.name}/")

    return errors


def check_design(path: Path, text: str) -> list[str]:
    """Design sign-off + R11 linkage: dependency section requires filled
    approver fields once the design is confirmed."""
    errors = check_signoff(path, text, superseded_ok=False)
    rel = path.relative_to(REPO_ROOT).as_posix()
    if not any(DEP_SECTION.match(line.strip()) for line in text.splitlines()):
        return errors

    lines = _header(text)
    status_raw = _first_match(lines, FIELD_STATUS)
    if status_raw is None or status_raw.split("（")[0].split("(")[0].strip() != "已确认":
        return errors  # draft designs are not required to have approval yet

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


def main() -> int:
    adr_files = sorted(p for p in DOCS_ROOT.glob("**/adr/*.md") if "templates" not in p.parts)
    design_files = sorted(p for p in DOCS_ROOT.glob("**/design.md") if "templates" not in p.parts)
    review_files = sorted(p for p in DOCS_ROOT.glob("**/self-review.md") if "templates" not in p.parts)

    errors: list[str] = []
    for path in adr_files:
        errors.extend(check_signoff(path, path.read_text(encoding="utf-8"), superseded_ok=True))
    for path in design_files:
        errors.extend(check_design(path, path.read_text(encoding="utf-8")))
    for path in review_files:
        errors.extend(check_signoff(path, path.read_text(encoding="utf-8"), superseded_ok=False))

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


if __name__ == "__main__":
    raise SystemExit(main())
