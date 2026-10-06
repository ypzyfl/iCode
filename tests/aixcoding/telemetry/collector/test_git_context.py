# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Git context resolver tests (scenarios ported from the TS
``ai-code.test.ts`` git-context sections)."""

from __future__ import annotations

import subprocess

from chrys.aixcoding.telemetry.collector.analysis import git_context
from chrys.aixcoding.telemetry.collector.analysis.git_context import (
    EMPTY_GIT_INFO,
    GitCommandRunner,
    GitRepositoryInfo,
    create_git_context_resolver,
    parse_git_owner_and_repo,
)


def fake_runner(responses: dict[str, str], calls: list[str] | None = None) -> GitCommandRunner:
    recorded = calls if calls is not None else []

    def run(cwd: str, args: list[str]) -> str:
        key = " ".join(args)
        recorded.append(f"{cwd} {key}")
        return responses.get(key, "")

    return run


class TestParseGitOwnerAndRepo:
    def test_takes_the_last_two_segments_for_common_remotes(self) -> None:
        assert parse_git_owner_and_repo("https://cnb.boecy.cn/ShangHaiJT-CSAS_GRPC/csas_extension_backend") == (
            "ShangHaiJT-CSAS_GRPC",
            "csas_extension_backend",
        )
        assert parse_git_owner_and_repo("https://host/group/repo.git") == ("group", "repo")
        assert parse_git_owner_and_repo("git@host:owner/repo.git") == ("owner", "repo")
        # GitLab subgroups yield the last two segments: known
        # legacy-parity limitation (D-M5-5).
        assert parse_git_owner_and_repo("https://gitlab.com/group/subgroup/repo") == ("subgroup", "repo")

    def test_returns_none_when_fewer_than_two_segments(self) -> None:
        assert parse_git_owner_and_repo("https://host-only") is None
        assert parse_git_owner_and_repo("") is None


class TestGitContextResolver:
    def test_prefers_cnb_then_origin_then_the_first_remote(self) -> None:
        run = fake_runner(
            {
                "rev-parse --show-toplevel": "D:\\repo",
                "remote": "upstream\norigin\ncnb",
                "config --get remote.cnb.url": "https://cnb.example/team/cnb-proj",
            }
        )
        info = create_git_context_resolver(run).for_directory("D:\\repo\\sub")
        assert info.remote_url == "https://cnb.example/team/cnb-proj"
        assert info.owner == "team"
        assert info.repo == "cnb-proj"

    def test_falls_back_to_origin_then_the_first_remote(self) -> None:
        origin_run = fake_runner(
            {
                "rev-parse --show-toplevel": "D:\\repo",
                "remote": "origin\nupstream",
                "config --get remote.origin.url": "https://host/o/r",
            }
        )
        assert create_git_context_resolver(origin_run).for_directory("D:\\repo").remote_url == "https://host/o/r"

        first_run = fake_runner(
            {
                "rev-parse --show-toplevel": "D:\\repo",
                "remote": "fork\nmirror",
                "config --get remote.fork.url": "https://host/f/m",
            }
        )
        assert create_git_context_resolver(first_run).for_directory("D:\\repo").remote_url == "https://host/f/m"

    def test_resolves_revision_branch_and_identity_omitting_on_failure(self) -> None:
        run = fake_runner(
            {
                "rev-parse --show-toplevel": "D:\\repo",
                "rev-parse HEAD": "64704138a5deed7f83c88a45695308f6f5675d04",
                "branch --show-current": "master",
                "config user.name": "dev",
                "config user.email": "dev@example.com",
            }
        )
        info = create_git_context_resolver(run).for_directory("D:\\repo")
        assert info == GitRepositoryInfo(
            remote_url=None,
            revision="64704138a5deed7f83c88a45695308f6f5675d04",
            branch="master",
            user_name="dev",
            user_email="dev@example.com",
            owner=None,
            repo=None,
        )

    def test_returns_empty_info_outside_git_repositories(self) -> None:
        run = fake_runner({})
        info = create_git_context_resolver(run).for_file("D:\\plain\\file.txt")
        assert info.remote_url is None
        assert info.root is None
        assert info.branch is None

    def test_caches_root_resolution_and_repository_info_per_run(self) -> None:
        calls: list[str] = []
        run = fake_runner(
            {
                "rev-parse --show-toplevel": "D:\\repo",
                "branch --show-current": "main",
            },
            calls,
        )
        resolver = create_git_context_resolver(run)
        resolver.for_file("D:\\repo\\a\\b.txt")
        resolver.for_file("D:\\repo\\a\\c.txt")
        # Same directory (D:\repo\a): root resolution runs once;
        # different directories resolve separately.
        resolver.for_directory("D:\\repo")
        assert len([call for call in calls if "rev-parse --show-toplevel" in call]) == 2
        # Repository info for the same repository root (D:\repo) is
        # collected once.
        assert len([call for call in calls if "branch --show-current" in call]) == 1

    def test_normalizes_cache_keys_case_insensitively_with_dual_separators(self) -> None:
        calls: list[str] = []
        run = fake_runner(
            {
                "rev-parse --show-toplevel": "D:\\Repo",
                "branch --show-current": "main",
            },
            calls,
        )
        resolver = create_git_context_resolver(run, "win32")
        resolver.for_directory("D:\\repo")
        resolver.for_directory("d:/REPO")
        # Same directory in two case/separator spellings: root resolution
        # and repository info each run once (plan §7 platform matrix).
        assert len([call for call in calls if "rev-parse --show-toplevel" in call]) == 1
        assert len([call for call in calls if "branch --show-current" in call]) == 1

    def test_keeps_cache_keys_case_sensitive_on_linux(self) -> None:
        calls: list[str] = []
        run = fake_runner({"rev-parse --show-toplevel": "/repo"}, calls)
        resolver = create_git_context_resolver(run, "linux")
        resolver.for_directory("/Repo")
        resolver.for_directory("/repo")
        # On a case-sensitive filesystem differently-cased directories are
        # different: resolved separately, never merged (plan §7 platform
        # matrix).
        assert len([call for call in calls if "rev-parse --show-toplevel" in call]) == 2

    def test_normalizes_cache_keys_on_macos_and_omits_fields_on_failure(self) -> None:
        calls: list[str] = []
        run = fake_runner(
            {
                "rev-parse --show-toplevel": "/Repo",
                "branch --show-current": "main",
            },
            calls,
        )
        resolver = create_git_context_resolver(run, "darwin")
        resolver.for_directory("/repo")
        resolver.for_directory("/REPO")
        assert len([call for call in calls if "rev-parse --show-toplevel" in call]) == 1
        # Xcode CLT stub: git exists but the command exits non-zero →
        # related fields omitted (never relying on stub success, plan §7).
        stub_run = fake_runner({})
        assert create_git_context_resolver(stub_run, "darwin").for_directory("/repo") == EMPTY_GIT_INFO


class TestGitCommandRunnerWindowsConsole:
    """The collector runs console-less (pythonw): any console creation on a
    machine whose default terminal is Windows Terminal opens a visible
    window, so the git child must be spawned fully detached — stdio flows
    through the capture pipes (TUI manual acceptance finding, 2026-10-06)."""

    def test_git_runner_spawns_without_a_console_on_windows(self, monkeypatch) -> None:
        recorded: dict[str, object] = {}

        class _Completed:
            returncode = 0
            stdout = "main\n"

        def fake_run(*args: object, **kwargs: object) -> object:
            recorded["argv"] = args
            recorded["kwargs"] = kwargs
            return _Completed()

        monkeypatch.setattr(git_context.subprocess, "run", fake_run)
        monkeypatch.setattr(git_context.sys, "platform", "win32")
        runner = git_context.create_git_command_runner()
        assert runner("D:\\repo", ["branch", "--show-current"]) == "main"

        kwargs = recorded["kwargs"]
        assert kwargs["stdin"] is subprocess.DEVNULL
        assert kwargs["creationflags"] == subprocess.DETACHED_PROCESS
        assert "startupinfo" not in kwargs

    def test_git_runner_has_no_extra_flags_off_windows(self, monkeypatch) -> None:
        recorded: dict[str, object] = {}

        class _Completed:
            returncode = 0
            stdout = ""

        def fake_run(*args: object, **kwargs: object) -> object:
            recorded["kwargs"] = kwargs
            return _Completed()

        monkeypatch.setattr(git_context.subprocess, "run", fake_run)
        monkeypatch.setattr(git_context.sys, "platform", "linux")
        runner = git_context.create_git_command_runner()
        assert runner("/repo", ["remote"]) == ""

        kwargs = recorded["kwargs"]
        assert kwargs["stdin"] is subprocess.DEVNULL
        assert "creationflags" not in kwargs
        assert "startupinfo" not in kwargs
