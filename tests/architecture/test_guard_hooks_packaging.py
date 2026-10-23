# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""The wheel must build the guard rule pack from the repo-root source of truth.

``guard_hooks/`` at the repo root is the single source of the security rule
pack. The wheel force-includes it into ``chrys/app/guard_hooks/``, which
``chrys.app.guard_install`` reads on every startup and reinstalls from. A
second checked-in copy of these files once drifted and shipped stale rules
(the 127.0.0.1 loopback mis-block), so this guard pins the packaging mapping:
any file added to the pack without a matching ``force-include`` entry fails
here instead of silently missing from released builds.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GUARD_SOURCE_DIR = REPO_ROOT / "guard_hooks"
PACK_FILES = ("_guard_core.py", "_prompt_guard.py", "_tool_guard.py", "rules.json", "hooks.yaml", "_launcher.ps1")
WHEEL_TARGET_DIR = "chrys/app/guard_hooks"
# Source path (relative to guard_hooks/) -> wheel path (relative to the target dir).
PACK_MAPPINGS = {name: name for name in PACK_FILES}


def test_every_rule_pack_file_is_force_included_into_the_wheel() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    force_include = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]

    for source_name, target_name in PACK_MAPPINGS.items():
        source = GUARD_SOURCE_DIR / source_name
        assert source.is_file(), f"rule pack file missing at source of truth: {source}"
        mapping = f"guard_hooks/{source_name}"
        assert mapping in force_include, (
            f"{mapping} is not force-included into the wheel; released builds would "
            f"miss it (target: {WHEEL_TARGET_DIR}/{target_name})"
        )
        assert force_include[mapping] == f"{WHEEL_TARGET_DIR}/{target_name}"


def test_no_checked_in_copy_of_the_rule_pack_exists() -> None:
    """The old drift source: a second copy under src/ that shadows the root pack.

    Only rule-pack files count as a copy: a leftover directory holding nothing
    but ``__pycache__`` (untracked build residue) cannot drift or shadow the
    force-include, so it does not fail this guard.
    """

    stale_dir = REPO_ROOT / "src" / "chrys" / "app" / "guard_hooks"
    leftovers = [target for target in PACK_MAPPINGS.values() if (stale_dir / target).is_file()]
    assert not leftovers, (
        f"{stale_dir} holds a checked-in rule-pack copy ({', '.join(leftovers)}); "
        "it WILL drift from guard_hooks/ (the single source of truth) and ship "
        "stale rules. Build-time force-include in pyproject.toml already bundles "
        "the pack — delete the copy."
    )
