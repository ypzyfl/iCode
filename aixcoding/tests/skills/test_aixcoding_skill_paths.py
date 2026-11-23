# (test fixture — asserts are pytest idiom, Chinese-free for lint parity,
#  tmp_path trees are the data)
"""aixcoding local skill roots — unit tests for the desktop-shared contract.

Covers ``chrys.service.aixcoding.skill_paths`` (the seven desktop roots, the
desktop-installed storage across environments and accounts, the
team-directory enumeration, both profile toggles) and the upstream hook in
``_collect_skill_paths`` that merges them.  Isolation is per-test monkeypatch
of ``skill_paths.user_aixcoding_dir`` / ``desktop_app_data_dir`` — this suite
does not depend on the upstream tests' config-dir redirect.
"""

from __future__ import annotations

import contextlib
import dataclasses
import json
import sys
from pathlib import Path

import pytest

import chrys.service.aixcoding.skill_paths as skill_paths_module
from chrys.foundation import platform as platform_module
from chrys.foundation.models.session_env import SessionEnvironment
from chrys.foundation.models.workspace import Workspace
from chrys.service.profiles.agents.loader import _parse_skills
from chrys.service.profiles.agents.schema import SkillsConfig
from chrys.service.skills.adapter import _collect_skill_paths

SKILL_MD = "---\nname: demo\ndescription: A demo skill.\n---\n\nDo things.\n"


def _make_runtime(cwd: Path) -> SessionEnvironment:
    return SessionEnvironment.capture(workspace=Workspace.from_cwd(str(cwd)))


def _fake_home(monkeypatch: pytest.MonkeyPatch, home: Path) -> None:
    import chrys.service.aixcoding.skill_paths as skill_paths

    monkeypatch.setattr(skill_paths, "user_aixcoding_dir", lambda: home / ".aixcoding")
    monkeypatch.setattr(skill_paths, "desktop_app_data_dir", lambda: home / "app-data")


def _place_skill(root: Path, skill_name: str = "demo") -> Path:
    skill_dir = root / skill_name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")
    return root


def _place_desktop_skill(
    app_data: Path,
    environment: str,
    account: str,
    skill_name: str = "demo",
) -> Path:
    """Create the desktop's installed-skill content dir and one skill; return the root."""
    container = app_data / "AIxCoding"
    if environment:
        container = container / environment
    content_root = container / "users" / account / "private" / "skills" / "system"
    return _place_skill(content_root, skill_name)


# --- HOME trees: roots appear / toggle off -----------------------------------


def test_user_aixcoding_skills_loaded_by_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    _place_skill(home / ".aixcoding" / "skills")
    _fake_home(monkeypatch, home)

    paths = _collect_skill_paths(SkillsConfig())

    assert str((home / ".aixcoding" / "skills").resolve()) in paths


def test_market_skills_root_loaded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    _fake_home(monkeypatch, home)

    paths = _collect_skill_paths(SkillsConfig())

    assert str((home / ".aixcoding" / "market-skills").resolve()) in paths


def test_intellij_mirror_tree_loaded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    _place_skill(home / ".aixcoding_intellij" / "skills")
    _place_skill(home / ".aixcoding_intellij" / "team-skills" / "ide-team")
    _fake_home(monkeypatch, home)

    paths = _collect_skill_paths(SkillsConfig())

    assert str((home / ".aixcoding_intellij" / "skills").resolve()) in paths
    assert str((home / ".aixcoding_intellij" / "market-skills").resolve()) in paths
    assert str((home / ".aixcoding_intellij" / "team-skills" / "ide-team").resolve()) in paths


def test_team_skill_dirs_enumerated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    teams = home / ".aixcoding" / "team-skills"
    _place_skill(teams / "alpha")
    _place_skill(teams / "beta")
    _fake_home(monkeypatch, home)

    paths = _collect_skill_paths(SkillsConfig())

    assert str((teams / "alpha").resolve()) in paths
    assert str((teams / "beta").resolve()) in paths
    alpha_index = paths.index(str((teams / "alpha").resolve()))
    market_index = paths.index(str((home / ".aixcoding" / "market-skills").resolve()))
    assert market_index < alpha_index, "team roots come after skills/market-skills"


def test_team_scan_skips_hidden_and_symlink_entries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    teams = home / ".aixcoding" / "team-skills"
    _place_skill(teams / "real")
    (teams / ".hidden").mkdir()
    link_target = tmp_path / "elsewhere"
    _place_skill(link_target)
    with contextlib.suppress(OSError):  # platform without symlink privilege
        (teams / "linked").symlink_to(link_target, target_is_directory=True)
    _fake_home(monkeypatch, home)

    paths = _collect_skill_paths(SkillsConfig())

    assert str((teams / "real").resolve()) in paths
    assert all(".hidden" not in path for path in paths)
    assert all(str(link_target) not in path or str((teams / "real").resolve()) == path for path in paths)


def test_team_container_missing_yields_no_roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    _fake_home(monkeypatch, home)

    paths = _collect_skill_paths(SkillsConfig())

    assert all("team-skills" not in path for path in paths)


def test_user_aixcoding_trees_skipped_when_toggle_off(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    _place_skill(home / ".aixcoding" / "skills")
    _fake_home(monkeypatch, home)

    paths = _collect_skill_paths(SkillsConfig(auto_load_aixcoding_user_skills=False))

    assert all(".aixcoding" not in path for path in paths)


# --- Workspace root ----------------------------------------------------------


def test_cwd_aixcoding_skills_loaded_with_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    cwd = tmp_path / "project"
    cwd.mkdir()
    _fake_home(monkeypatch, home)

    paths = _collect_skill_paths(SkillsConfig(), runtime=_make_runtime(cwd))

    assert str((cwd / ".aixcoding" / "skills").resolve()) in paths


def test_cwd_aixcoding_skills_load_despite_project_gate_off(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """skills-aixcoding-dirs design decision 2 anchor: the workspace aixcoding root ignores the trust gate."""
    home = tmp_path / "home"
    cwd = tmp_path / "project"
    _place_skill(cwd / ".aixcoding" / "skills")
    _fake_home(monkeypatch, home)

    paths = _collect_skill_paths(SkillsConfig(), runtime=_make_runtime(cwd), project_skills_enabled=False)

    assert str((cwd / ".aixcoding" / "skills").resolve()) in paths


def test_cwd_aixcoding_skills_skipped_when_toggle_off(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    cwd = tmp_path / "project"
    cwd.mkdir()
    _fake_home(monkeypatch, home)

    paths = _collect_skill_paths(SkillsConfig(auto_load_aixcoding_cwd_skills=False), runtime=_make_runtime(cwd))

    assert all(not path.startswith(str(cwd)) for path in paths)


def test_cwd_aixcoding_skills_skipped_without_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    cwd = tmp_path / "project"
    cwd.mkdir()
    _fake_home(monkeypatch, home)

    paths = _collect_skill_paths(SkillsConfig(), runtime=None)

    assert all(not path.startswith(str(cwd)) for path in paths)
    assert str((home / ".aixcoding" / "skills").resolve()) in paths, "HOME trees stay on without a runtime"


# --- Scan order (desktop parity) ----------------------------------------------


def test_scan_order_matches_desktop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Workspace root beats the HOME trees; aixcoding beats the matching .agents root."""
    home = tmp_path / "home"
    cwd = tmp_path / "project"
    cwd.mkdir()
    _fake_home(monkeypatch, home)
    monkeypatch.setattr("chrys.service.skills.adapter.user_agents_dir", lambda: home / ".agents")

    paths = _collect_skill_paths(SkillsConfig(), runtime=_make_runtime(cwd), project_skills_enabled=True)

    cwd_aix_index = paths.index(str((cwd / ".aixcoding" / "skills").resolve()))
    user_aix_index = paths.index(str((home / ".aixcoding" / "skills").resolve()))
    agents_user_index = paths.index(str((home / ".agents" / "skills").resolve()))
    agents_cwd_index = paths.index(str((cwd / ".agents" / "skills").resolve()))
    assert cwd_aix_index < user_aix_index, "workspace root precedes HOME trees (desktop parity)"
    assert user_aix_index < agents_user_index, "aixcoding precedes the matching .agents root (D3)"
    assert cwd_aix_index < agents_cwd_index


# --- Desktop installed storage (v4) --------------------------------------------


def test_desktop_installed_skill_paths_enumerated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Every environment times every account contributes one root, sorted by name."""
    home = tmp_path / "home"
    app_data = home / "app-data"
    development_first = _place_desktop_skill(app_data, "development", "u-1")
    development_second = _place_desktop_skill(app_data, "development", "u-2")
    production = _place_desktop_skill(app_data, "production", "u-1")
    _fake_home(monkeypatch, home)

    paths = _collect_skill_paths(SkillsConfig())

    for root in (development_first, development_second, production):
        assert str(root.resolve()) in paths
    assert paths.index(str(development_first.resolve())) < paths.index(str(development_second.resolve()))
    assert paths.index(str(development_second.resolve())) < paths.index(str(production.resolve()))


def test_desktop_installed_skill_paths_without_environment_layer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The data root itself is a user container too (legacy layout)."""
    home = tmp_path / "home"
    app_data = home / "app-data"
    root = _place_desktop_skill(app_data, "", "u-1")
    _fake_home(monkeypatch, home)

    paths = _collect_skill_paths(SkillsConfig())

    assert str(root.resolve()) in paths


def test_desktop_installed_skill_paths_skip_hidden_and_symlink(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    app_data = home / "app-data"
    real_root = _place_desktop_skill(app_data, "development", "u-1")
    _place_desktop_skill(app_data, ".hidden-environment", "u-1")
    elsewhere = tmp_path / "elsewhere"
    elsewhere_root = _place_skill(elsewhere / "users" / "u-1" / "private" / "skills" / "system")
    with contextlib.suppress(OSError):  # platform without symlink privilege
        (app_data / "AIxCoding" / "linked-environment").symlink_to(elsewhere, target_is_directory=True)
    with contextlib.suppress(OSError):
        (app_data / "AIxCoding" / "development" / "users" / "linked-account").symlink_to(
            elsewhere, target_is_directory=True
        )
    _fake_home(monkeypatch, home)

    paths = _collect_skill_paths(SkillsConfig())

    assert str(real_root.resolve()) in paths
    assert all(".hidden-environment" not in path for path in paths)
    assert str(elsewhere_root.resolve()) not in paths


def test_desktop_installed_skill_paths_missing_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A machine without the desktop client adds no roots and never raises."""
    home = tmp_path / "home"
    _fake_home(monkeypatch, home)

    paths = _collect_skill_paths(SkillsConfig())

    assert all("AIxCoding" not in path for path in paths)


def test_desktop_installed_skill_paths_skipped_when_toggle_off(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    app_data = home / "app-data"
    _place_desktop_skill(app_data, "development", "u-1")
    _fake_home(monkeypatch, home)

    paths = _collect_skill_paths(SkillsConfig(auto_load_aixcoding_user_skills=False))

    assert all(str(app_data.resolve()) not in path for path in paths)


def test_desktop_installed_roots_between_intellij_and_agents(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Scan order: hand-placed trees, then the installed storage, then .agents."""
    home = tmp_path / "home"
    app_data = home / "app-data"
    _place_skill(home / ".aixcoding_intellij" / "skills")
    desktop_root = _place_desktop_skill(app_data, "development", "u-1")
    _fake_home(monkeypatch, home)
    monkeypatch.setattr("chrys.service.skills.adapter.user_agents_dir", lambda: home / ".agents")

    paths = _collect_skill_paths(SkillsConfig())

    intellij_index = paths.index(str((home / ".aixcoding_intellij" / "skills").resolve()))
    desktop_index = paths.index(str(desktop_root.resolve()))
    agents_index = paths.index(str((home / ".agents" / "skills").resolve()))
    assert intellij_index < desktop_index < agents_index


def test_desktop_disabled_skill_is_still_discovered(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Installation is not enablement: the desktop's enabled flag is never read."""
    home = tmp_path / "home"
    app_data = home / "app-data"
    content_root = _place_desktop_skill(app_data, "development", "u-1", "disabled-skill")
    (content_root.parent / "active-candidates.json").write_text(
        json.dumps({"candidates": [{"candidate": {"skillNameEn": "disabled-skill", "enabled": False}}]}),
        encoding="utf-8",
    )
    _fake_home(monkeypatch, home)

    paths = _collect_skill_paths(SkillsConfig())

    assert str(content_root.resolve()) in paths


# --- Profile parsing -----------------------------------------------------------


def test_parse_skills_defaults_true() -> None:
    config = _parse_skills(None)

    assert config.auto_load_aixcoding_user_skills is True
    assert config.auto_load_aixcoding_cwd_skills is True


def test_parse_skills_explicit_false() -> None:
    config = _parse_skills({"auto_load_aixcoding_user_skills": False, "auto_load_aixcoding_cwd_skills": False})

    assert config.auto_load_aixcoding_user_skills is False
    assert config.auto_load_aixcoding_cwd_skills is False


# --- Hook degradation and dedup ------------------------------------------------


def test_hook_swallows_missing_customization(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A broken customization package degrades to the plain upstream roots."""
    monkeypatch.setitem(sys.modules, "chrys.service.aixcoding.skill_paths", None)

    paths = _collect_skill_paths(SkillsConfig())

    assert any(".chrys" in path or "chrys" in path for path in paths)
    assert all(".aixcoding" not in path for path in paths)


def test_paths_resolved_and_deduped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    cwd = tmp_path / "project"
    aix_skills = _place_skill(cwd / ".aixcoding" / "skills")
    _fake_home(monkeypatch, home)

    config = SkillsConfig(paths=[str(aix_skills), str(aix_skills)])
    paths = _collect_skill_paths(config, runtime=_make_runtime(cwd))

    assert paths.count(str(aix_skills.resolve())) == 1


# --- Mechanism regression: the platform field follows the redirect -------------


def test_platform_redirect_covers_aixcoding_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The helper reads ``PlatformInfo.aixcoding_dir``, so pinning the platform
    singleton (what the upstream tests' config-dir redirect does) isolates the
    desktop-shared roots without any per-test toggle edits."""
    pinned = tmp_path / "platform-config"
    fake = dataclasses.replace(platform_module.get_platform(), aixcoding_dir=pinned / ".aixcoding")
    monkeypatch.setattr(platform_module, "detect_platform", lambda: fake)
    platform_module.get_platform.cache_clear()
    try:
        assert skill_paths_module.user_aixcoding_dir() == pinned / ".aixcoding"
        assert skill_paths_module.user_aixcoding_dir() != Path.home() / ".aixcoding"
        # dataclasses.replace keeps unspecified fields intact.
        redirected = dataclasses.replace(fake, config_dir=pinned)
        assert redirected.aixcoding_dir == pinned / ".aixcoding"
        assert redirected.data_dir == fake.data_dir
    finally:
        platform_module.get_platform.cache_clear()


def test_platform_redirect_covers_app_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The installed-storage helper reads ``PlatformInfo.app_data_dir``, so the
    same redirect isolates the desktop client's storage from upstream tests."""
    pinned = tmp_path / "platform-config"
    fake = dataclasses.replace(platform_module.get_platform(), app_data_dir=pinned / "app-data")
    monkeypatch.setattr(platform_module, "detect_platform", lambda: fake)
    platform_module.get_platform.cache_clear()
    try:
        assert skill_paths_module.desktop_app_data_dir() == pinned / "app-data"
        assert skill_paths_module.desktop_app_data_dir() != platform_module._conventional_app_data_dir()
        # dataclasses.replace keeps unspecified fields intact.
        redirected = dataclasses.replace(fake, config_dir=pinned)
        assert redirected.app_data_dir == pinned / "app-data"
        assert redirected.data_dir == fake.data_dir
    finally:
        platform_module.get_platform.cache_clear()
