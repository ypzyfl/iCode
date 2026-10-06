# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""GitContextResolver (TS ``git-context.ts``; M5 plan §7; contract
§2.2/§2.5).

best-effort: git unavailable / not a git directory / timeout → fields
None (consumers omit them, contract §2.1 two-state distinction). Remote
selection aligns with the legacy plugin mapGitRepoInfo: cnb → origin →
first (internal repositories recognized first); gitOwner/gitRepo take
the last two of the `/`- and `:`-separated segments after stripping
``.git`` (legacy parity, D-M5-5). Cached once per repository root per
run (cache keys normalized per the platform matrix: Windows/macOS
case-insensitive + both separators, Linux as-is); git spawns without a
shell, decodes UTF-8, 3s timeout.
"""

from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass

type GitCommandRunner = Callable[[str, list[str]], str]

_SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")
_GIT_SUFFIX = re.compile(r"\.git$")
_SEGMENT_SPLIT = re.compile(r"[/:]")
_LAST_SEPARATOR = re.compile(r"[\\/][^\\/]*$")
_REMOTE_PREFERENCE = ("cnb", "origin")


@dataclass(frozen=True, slots=True)
class GitRepositoryInfo:
    remote_url: str | None
    revision: str | None
    branch: str | None
    user_name: str | None
    user_email: str | None
    owner: str | None
    repo: str | None


EMPTY_GIT_INFO = GitRepositoryInfo(
    remote_url=None,
    revision=None,
    branch=None,
    user_name=None,
    user_email=None,
    owner=None,
    repo=None,
)


@dataclass(frozen=True, slots=True)
class GitFileContext(GitRepositoryInfo):
    """File-level resolution result: nearest repository root attached
    (filepath relativization basis, K5)."""

    root: str | None


def create_git_command_runner(timeout_ms: int = 3_000) -> GitCommandRunner:
    """Git command executor (injectable for tests); returns trimmed
    stdout, '' on failure."""

    def run_git(cwd: str, args: list[str]) -> str:
        try:
            completed = subprocess.run(  # noqa: S603 — fixed git binary, fixed args, no shell
                ["git", *args],  # noqa: S607 — PATH-resolved git, same lookup as the TS spawnSync('git')
                cwd=cwd,
                # The child must never read the parent's stdin — under
                # ACP that stream is the JSON-RPC pipe.
                stdin=subprocess.DEVNULL,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                timeout=timeout_ms / 1000,
                # No console on Windows: the collector itself runs console-less
                # (pythonw), and ANY console creation on a machine whose default
                # terminal is Windows Terminal opens a visible window (SW_HIDE
                # is ignored). DETACHED_PROCESS never creates one; stdio flows
                # through the capture pipes above.
                **({"creationflags": subprocess.DETACHED_PROCESS} if sys.platform == "win32" else {}),
            )
        except OSError, subprocess.SubprocessError:
            return ""
        if completed.returncode != 0:
            return ""
        return (completed.stdout or "").strip()

    return run_git


def parse_git_owner_and_repo(remote_url: str) -> tuple[str, str] | None:
    """gitOwner/gitRepo parsing (legacy plugin ReportInfoHelper
    .parseGitOwnerAndRepo parity): strip the ``.git`` suffix, then take
    the last two of the ``/``- and ``:``-separated segments. Known
    limitation (the cost of legacy parity): GitLab subgroups yield the
    last two, SSH yields owner/repo, self-hosted multi-level paths yield
    the last two; if the backend ever needs full group paths, both
    old and new parity must switch together (D-M5-5)."""
    # Strip the scheme first (`https://`; the SSH form `git@host:owner/repo`
    # has no scheme — its first colon lacks `//` and is never stripped).
    without_scheme = _SCHEME.sub("", remote_url, count=1)
    without_suffix = _GIT_SUFFIX.sub("", without_scheme)
    segments = [segment for segment in _SEGMENT_SPLIT.split(without_suffix) if segment]
    if len(segments) < 2:
        return None
    repo = segments[-1]
    owner = segments[-2]
    if not repo or not owner:
        return None
    return owner, repo


def _select_remote_name(remotes: list[str]) -> str | None:
    for preferred in _REMOTE_PREFERENCE:
        if preferred in remotes:
            return preferred
    return remotes[0] if remotes else None


class GitContextResolver:
    def __init__(self, run_git: GitCommandRunner, platform: str) -> None:
        self._run_git = run_git
        self._case_insensitive = platform in ("win32", "darwin")
        # Once per repository root per run (M5 plan §7): root resolution
        # and repository info never spawn twice.
        self._root_cache: dict[str, str | None] = {}
        self._cache: dict[str, GitRepositoryInfo] = {}

    def _cache_key(self, path: str) -> str:
        # Platform matrix (M5 plan §7): Windows/macOS normalize case +
        # both separators; Linux as-is — on a case-sensitive filesystem
        # differently-cased directories are different, never merged.
        return path.replace("\\", "/").lower() if self._case_insensitive else path

    def _resolve_root(self, directory: str) -> str | None:
        key = self._cache_key(directory)
        if key in self._root_cache:
            return self._root_cache[key]
        root = self._run_git(directory, ["rev-parse", "--show-toplevel"])
        value = root or None
        self._root_cache[key] = value
        return value

    def _read_value(self, root: str, args: list[str]) -> str | None:
        value = self._run_git(root, args)
        return value or None

    def _resolve_repository(self, root: str) -> GitRepositoryInfo:
        remotes = [line.strip() for line in self._run_git(root, ["remote"]).split("\n") if line.strip()]
        remote_name = _select_remote_name(remotes)
        remote_url = (
            self._run_git(root, ["config", "--get", f"remote.{remote_name}.url"]) if remote_name is not None else ""
        )
        owner_and_repo = parse_git_owner_and_repo(remote_url) if remote_url else None
        return GitRepositoryInfo(
            remote_url=remote_url or None,
            revision=self._read_value(root, ["rev-parse", "HEAD"]),
            branch=self._read_value(root, ["branch", "--show-current"]),
            user_name=self._read_value(root, ["config", "user.name"]),
            user_email=self._read_value(root, ["config", "user.email"]),
            owner=owner_and_repo[0] if owner_and_repo is not None else None,
            repo=owner_and_repo[1] if owner_and_repo is not None else None,
        )

    def _resolve_cached(self, root: str) -> GitRepositoryInfo:
        key = self._cache_key(root)
        if key not in self._cache:
            self._cache[key] = self._resolve_repository(root)
        return self._cache[key]

    def for_directory(self, directory: str) -> GitRepositoryInfo:
        root = self._resolve_root(directory)
        if root is None:
            return EMPTY_GIT_INFO
        return self._resolve_cached(root)

    def for_file(self, file_path: str) -> GitFileContext:
        # The engine records paths on the same machine the analysis runs
        # on; plain string semantics apply.
        directory = _LAST_SEPARATOR.sub("", file_path) or file_path
        root = self._resolve_root(directory)
        if root is None:
            return _as_file_context(EMPTY_GIT_INFO, None)
        return _as_file_context(self._resolve_cached(root), root)


def _as_file_context(info: GitRepositoryInfo, root: str | None) -> GitFileContext:
    return GitFileContext(
        remote_url=info.remote_url,
        revision=info.revision,
        branch=info.branch,
        user_name=info.user_name,
        user_email=info.user_email,
        owner=info.owner,
        repo=info.repo,
        root=root,
    )


def create_git_context_resolver(
    run_git: GitCommandRunner | None = None,
    platform: str | None = None,
) -> GitContextResolver:
    return GitContextResolver(
        run_git if run_git is not None else create_git_command_runner(),
        platform if platform is not None else sys.platform,
    )


def _never_run_git(cwd: str, args: list[str]) -> str:
    return ""


NULL_GIT_CONTEXT = GitContextResolver(run_git=_never_run_git, platform=sys.platform)
"""Null resolver: git unavailable → related fields omitted."""
