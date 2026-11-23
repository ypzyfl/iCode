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
* ``<appData>/AIxCoding/<environment>/users/<key>/private/skills/system`` —
  the desktop client's installed-skill storage, enumerated across every
  environment and every account (see :func:`desktop_installed_skill_paths`).

The installed storage is read as installed, not as enabled: the desktop's
per-skill ``enabled`` flag lives in its own index and only filters desktop
sessions, so a skill the user disabled there is still discovered here
(decision of 2026-11-18; both the IntelliJ plugin and this CLI scan the
directory rather than parsing the desktop's internal state files).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chrys.foundation.models.session_env import SessionEnvironment
    from chrys.service.profiles.agents.schema import SkillsConfig

# AIxCoding logging (batches/logging-coverage): skill-root loading is a
# background degrade (skills silently absent when it fails), so everything
# here is detail-only on the aixcoding tree (ADR-0017, DEVELOPMENT.md §9).
_detail_log = logging.getLogger("aixcoding.detail.skills")
_DETAIL_LEVEL = 5  # mirrors diagnostics.logging_support (session.py precedent)

# Directory names of the desktop-client local skill layout.
_TREE_NAME = ".aixcoding"
_INTELLIJ_TREE_NAME = ".aixcoding_intellij"
_SKILLS_SUBDIRECTORY = "skills"
_MARKET_SKILLS_SUBDIRECTORY = "market-skills"
_TEAM_SKILLS_SUBDIRECTORY = "team-skills"

# The desktop client's own application directory and its installed-skill storage.
_DESKTOP_APP_DIRECTORY = "AIxCoding"
_DESKTOP_SKILLS_PARTS = ("private", "skills", "system")


def user_aixcoding_dir() -> Path:
    """Return the AIxCoding user directory (``~/.aixcoding``).

    Module-level helper for the same monkeypatch/testing reasons as the
    upstream :func:`chrys.service.skills.adapter.user_agents_dir`; the value
    comes from the platform singleton so the tests' config-dir redirect covers
    it automatically.
    """
    from chrys.foundation.platform import get_platform

    return get_platform().aixcoding_dir


def desktop_app_data_dir() -> Path:
    """Return the OS application-data parent the desktop client writes under.

    Same platform-singleton indirection as :func:`user_aixcoding_dir`, so the
    tests' config-dir redirect covers it too.
    """
    from chrys.foundation.platform import get_platform

    return get_platform().app_data_dir


def _real_subdirectory_paths(container: Path, *, log_label: str) -> list[Path]:
    """Return each immediate real subdirectory of *container*, resolved.

    Mirrors the desktop client's container enumeration (``userTeamSkillRoots``
    and its external-root walk): hidden entries, symbolic links, and Windows
    junctions are skipped, results are sorted by name, an unreadable or
    missing container yields no roots, and one broken entry never removes the
    other roots.  *log_label* names the directory kind in the failure trace
    (team roots vs. desktop environment/account containers).
    """
    try:
        with os.scandir(container) as entries:
            found = sorted(entries, key=lambda entry: entry.name)
    except FileNotFoundError:
        # The common case: the user never created this tree — not an event.
        return []
    except OSError as exc:
        _detail_log.log(_DETAIL_LEVEL, "%s枚举失败：%s", log_label, exc)
        return []
    roots: list[Path] = []
    for entry in found:
        try:
            if entry.name.startswith(".") or entry.is_symlink() or entry.is_junction():
                continue
            if not entry.is_dir(follow_symlinks=False):
                continue
            roots.append(Path(entry.path).resolve())
        except OSError:
            continue
    return roots


def _team_skill_dirs(container: Path) -> list[str]:
    """Return each immediate team directory of *container* as a skill root.

    Stringified view of ``_real_subdirectory_paths`` — the desktop client's
    ``userTeamSkillRoots`` enumeration semantics live there.
    """
    return [str(root) for root in _real_subdirectory_paths(container, log_label="团队技能目录")]


def user_aixcoding_skill_paths(config: SkillsConfig) -> list[str]:
    """Return the HOME-level AIxCoding skill roots when the toggle is on.

    Covers both the ``.aixcoding`` tree and the ``.aixcoding_intellij`` mirror
    (IDE-managed skills), each with the three desktop-client root kinds in the
    desktop scan order, followed by the desktop client's installed-skill
    storage.  Hand-placed roots come first so they win a same-name conflict.
    """
    try:
        if not config.auto_load_aixcoding_user_skills:
            return []
        paths: list[str] = []
        base = user_aixcoding_dir().resolve()
        for tree in (base, base.parent / _INTELLIJ_TREE_NAME):
            paths.append(str((tree / _SKILLS_SUBDIRECTORY).resolve()))
            paths.append(str((tree / _MARKET_SKILLS_SUBDIRECTORY).resolve()))
            paths.extend(_team_skill_dirs(tree / _TEAM_SKILLS_SUBDIRECTORY))
        paths.extend(desktop_installed_skill_paths())
    except Exception:
        # Logged before the upstream adapter's own swallow (batches/logging-coverage
        # plan B): the record lands in the detail volume, then the original
        # exception propagates unchanged.
        _detail_log.log(_DETAIL_LEVEL, "读取 aixcoding 技能根目录（用户）失败。", exc_info=True)
        raise
    if paths:
        _detail_log.log(_DETAIL_LEVEL, "已登记 aixcoding 技能根目录（用户）：%s", ", ".join(paths))
    return paths


def desktop_installed_skill_paths() -> list[str]:
    """Return the desktop client's installed-skill roots, environment by environment.

    Mirrors the IntelliJ plugin's ``getDesktopInstalledSkillRoots``: the data
    root itself and each of its real subdirectories (normally one per release
    environment) are user containers; below each, every ``users/<key>`` account
    contributes ``private/skills/system`` when that is a real directory.
    Everything is read-only; the desktop's ``skill.json`` and
    ``active-candidates.json`` are never parsed, so an installed-but-disabled
    skill is still discovered.
    """
    data_root = desktop_app_data_dir() / _DESKTOP_APP_DIRECTORY
    try:
        if not data_root.is_dir():
            return []
    except OSError:
        # An unreadable data root (e.g. permission denied) yields no installed
        # roots — the hand-placed trees collected by the caller stay intact.
        return []
    roots: list[str] = []
    for user_container in [data_root, *_real_subdirectory_paths(data_root, log_label="桌面端环境目录")]:
        for account in _real_subdirectory_paths(user_container / "users", log_label="桌面端账号目录"):
            content_root = account.joinpath(*_DESKTOP_SKILLS_PARTS)
            try:
                if not content_root.is_dir() or content_root.is_symlink() or content_root.is_junction():
                    continue
            except OSError:
                continue
            roots.append(str(content_root))
    return roots


def cwd_aixcoding_skill_paths(config: SkillsConfig, runtime: SessionEnvironment | None) -> list[str]:
    """Return the workspace AIxCoding skill root when the toggle is on.

    Tied to the agent's ``SessionEnvironment`` (not ``os.getcwd()``) so it
    follows the workspace through soft restarts.  Deliberately independent of
    the project trust gate: the AIxCoding directory is a product-owned root,
    not repository-authored content (skills-aixcoding-dirs design decision 2).
    """
    try:
        if not config.auto_load_aixcoding_cwd_skills:
            return []
        if runtime is None or not runtime.cwd:
            return []
        paths = [str((Path(runtime.cwd) / _TREE_NAME / _SKILLS_SUBDIRECTORY).resolve())]
    except Exception:
        # Same contract as the user variant above: detail trace, then re-raise.
        _detail_log.log(_DETAIL_LEVEL, "读取 aixcoding 技能根目录（工作区）失败。", exc_info=True)
        raise
    _detail_log.log(_DETAIL_LEVEL, "已登记 aixcoding 技能根目录（工作区）：%s", ", ".join(paths))
    return paths
