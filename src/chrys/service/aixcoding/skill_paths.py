# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""AIxCoding local skill roots consumed by the upstream skill loader.

The desktop client (agent_studio, ``apps/desktop/src/main/local-skill-layout.ts``
is its authoritative layout) shares hand-placed skills with this CLI through a
file-system contract: ``SKILL.md`` directories under two HOME trees and one
per-workspace root.  This module is the CLI side of that contract — it only
reads those roots and never writes to them.

Trees and roots, in the scan order agreed with the desktop client
(``runtime-composition.ts`` puts the workspace root first, then the user trees):

* ``<workspace>/.aixcoding/skills`` — project skills, tied to ``runtime.cwd``.
* ``~/.aixcoding/skills`` — hand-placed user skills.
* ``~/.aixcoding/market-skills`` — reserved desktop-client layout root.
* ``~/.aixcoding/team-skills/<team>`` — one root per immediate subdirectory
  (hidden entries, symbolic links, and Windows junctions skipped, sorted by
  name); enumeration failures yield no roots so a broken container cannot
  block a session.
* ``~/.aixcoding_intellij/...`` — the same three-root layout for IDE-managed
  skills.

The account installation storage (``~/.aixcoding/<env>/users/<key>/private/skills``)
is deliberately *not* part of this contract: the desktop client owns those
packages' enable/disable state and injects the enabled ones into desktop
sessions via profile materialization.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chrys.foundation.models.session_env import SessionEnvironment
    from chrys.service.profiles.agents.schema import SkillsConfig

# Directory names of the desktop-client local skill layout.
_TREE_NAME = ".aixcoding"
_INTELLIJ_TREE_NAME = ".aixcoding_intellij"
_SKILLS_SUBDIRECTORY = "skills"
_MARKET_SKILLS_SUBDIRECTORY = "market-skills"
_TEAM_SKILLS_SUBDIRECTORY = "team-skills"


def user_aixcoding_dir() -> Path:
    """Return the AIxCoding user directory (``~/.aixcoding``).

    Module-level helper for the same monkeypatch/testing reasons as the
    upstream :func:`chrys.service.skills.adapter.user_agents_dir`; the value
    comes from the platform singleton so the tests' config-dir redirect covers
    it automatically.
    """
    from chrys.foundation.platform import get_platform

    return get_platform().aixcoding_dir


def _team_skill_dirs(container: Path) -> list[str]:
    """Return each immediate team directory of *container* as a skill root.

    Mirrors the desktop client's ``userTeamSkillRoots``: hidden entries,
    symbolic links, and Windows junctions are skipped, roots are sorted by
    name, an unreadable or missing container yields no roots, and one broken
    entry never removes the other roots.
    """
    try:
        with os.scandir(container) as entries:
            found = sorted(entries, key=lambda entry: entry.name)
    except OSError:
        return []
    roots: list[str] = []
    for entry in found:
        try:
            if entry.name.startswith(".") or entry.is_symlink() or entry.is_junction():
                continue
            if not entry.is_dir(follow_symlinks=False):
                continue
            roots.append(str(Path(entry.path).resolve()))
        except OSError:
            continue
    return roots


def user_aixcoding_skill_paths(config: SkillsConfig) -> list[str]:
    """Return the HOME-level AIxCoding skill roots when the toggle is on.

    Covers both the ``.aixcoding`` tree and the ``.aixcoding_intellij`` mirror
    (IDE-managed skills), each with the three desktop-client root kinds in the
    desktop scan order.
    """
    if not config.auto_load_aixcoding_user_skills:
        return []
    paths: list[str] = []
    base = user_aixcoding_dir().resolve()
    for tree in (base, base.parent / _INTELLIJ_TREE_NAME):
        paths.append(str((tree / _SKILLS_SUBDIRECTORY).resolve()))
        paths.append(str((tree / _MARKET_SKILLS_SUBDIRECTORY).resolve()))
        paths.extend(_team_skill_dirs(tree / _TEAM_SKILLS_SUBDIRECTORY))
    return paths


def cwd_aixcoding_skill_paths(config: SkillsConfig, runtime: SessionEnvironment | None) -> list[str]:
    """Return the workspace AIxCoding skill root when the toggle is on.

    Tied to the agent's ``SessionEnvironment`` (not ``os.getcwd()``) so it
    follows the workspace through soft restarts.  Deliberately independent of
    the project trust gate: the AIxCoding directory is a product-owned root,
    not repository-authored content (skills-aixcoding-dirs design decision 2).
    """
    if not config.auto_load_aixcoding_cwd_skills:
        return []
    if runtime is None or not runtime.cwd:
        return []
    return [str((Path(runtime.cwd) / _TREE_NAME / _SKILLS_SUBDIRECTORY).resolve())]
