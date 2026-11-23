# (test fixture — asserts are pytest idiom, Chinese-free for lint parity,
#  tmp_path trees are the data)
"""Behavior anchors for the relaxed Agent Skills name gate (skills-aixcoding-dirs v5).

R12 record 5 of the batch design: the CLI accepts the desktop client's
CamelCase skill names (the real installed skills look like
``React-Code-Standard``), while every other upstream constraint stays
untouched.  The underscored-name anchor pins the relaxation boundary — the
upstream suite keeps ``Bad_Name`` as its invalid-name counterexample, so if
the camel-case anchor goes red an upstream change re-tightened the gate, and
if the underscore anchor goes red someone widened the charset past uppercase
letters and must re-check the upstream tests too.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from chrys.service.skills.loader import load_file_skill
from chrys.service.skills.model import Skill, SkillLoadFailure

if TYPE_CHECKING:
    from pathlib import Path


def _write_skill(root: Path, name: str) -> Path:
    skill_dir = root / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: A desktop shared skill.\n---\n\nBody.\n",
        encoding="utf-8",
    )
    return skill_dir


def _load(skill_dir: Path) -> Skill | SkillLoadFailure:
    return load_file_skill(str(skill_dir), script_extensions=(".py",))


def test_desktop_camel_case_skill_name_is_accepted(tmp_path: Path) -> None:
    skill = _load(_write_skill(tmp_path, "React-Code-Standard"))

    assert isinstance(skill, Skill)
    assert skill.name == "React-Code-Standard"


def test_underscored_skill_name_still_rejected(tmp_path: Path) -> None:
    failure = _load(_write_skill(tmp_path, "Bad_Name"))

    assert isinstance(failure, SkillLoadFailure)
    assert "invalid skill name" in failure.reason
