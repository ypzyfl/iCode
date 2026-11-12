# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Resolve telemetry settings and encode fields shared by independent reports."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import threading
import time
from collections import OrderedDict
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlsplit, urlunsplit

from chrys import __version__
from chrys.foundation.platform import get_platform
from chrys.foundation.platform.process import windows_hidden_subprocess_kwargs
from chrys.service.aixcoding.config import load_config

if TYPE_CHECKING:
    from collections.abc import Sequence

    from chrys.foundation.models.invocations import InvocationOrigin

logger = logging.getLogger("aixcoding.detail.telemetry")
_PROFILE_URLS = {
    "LOCAL": "http://127.0.0.1:4321/csas",
    "DEV": "http://81.89.182.150/csas",
    "PROD": "http://82.187.34.98/csas",
}
_ARG_VALUE_OPTIONS = frozenset({"-s", "-a", "-m", "-C", "--session", "--agent", "--model", "--cwd"})


@dataclass(frozen=True, slots=True)
class TelemetrySettings:
    base_url: str
    enabled: bool
    full_mode: bool
    user_id: str | None
    token: str | None = field(repr=False)


def _text(value: object) -> str | None:
    return (str(value).strip() or None) if value is not None else None


def _legacy_settings(path: Path) -> dict[str, object]:
    import yaml

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except OSError, UnicodeError, yaml.YAMLError:
        logger.debug("Could not read legacy telemetry settings.")
        return {}
    return data if isinstance(data, dict) else {}


def load_settings(config_dir: Path | None = None) -> TelemetrySettings:
    """Read legacy telemetry settings with the shared deployment tier as fallback."""
    directory = get_platform().config_dir if config_dir is None else config_dir
    data = _legacy_settings(directory / "aixcoding.yaml")
    profile = os.environ.get("AIXCODING_EXTENSION_PROFILE") or _text(data.get("profile"))
    if profile is None:
        profile = load_config(directory).environment
    base_url = os.environ.get("AIXCODING_EXTENSION_BASE_URL")
    if not base_url:
        base_url = _PROFILE_URLS.get(profile.strip().upper(), _PROFILE_URLS["PROD"])
        if override := _text(data.get("customServerUrl")):
            try:
                target = urlsplit(override)
            except ValueError:
                target = None
            if target is not None and target.scheme and target.netloc:
                original = urlsplit(base_url)
                base_url = urlunsplit((target.scheme, target.netloc, original.path, original.query, original.fragment))
    forced_off = os.environ.get("AIXCODING_TELEMETRY_DISABLED", "").strip().lower() in {"1", "true", "yes"}
    enabled = str(data.get("telemetryEnabled", True)).strip().lower() not in {"0", "false", "no"}
    return TelemetrySettings(
        base_url=base_url,
        enabled=enabled and not forced_off,
        full_mode=str(data.get("toolParamMode", "")).strip().lower() != "whitelist",
        user_id=_text(data.get("userId")),
        token=_text(data.get("token")),
    )


def telemetry_token(settings: TelemetrySettings) -> str | None:
    from chrys.kernel.aixcoding.auth import login_token_header_value

    return os.environ.get("AIXCODING_TOKEN") or login_token_header_value() or settings.token


def telemetry_user_id(settings: TelemetrySettings) -> str | None:
    try:
        from chrys.kernel.aixcoding.auth import get_login_session

        return get_login_session().stored_user_id or settings.user_id
    except Exception:
        return settings.user_id


@dataclass(frozen=True, slots=True)
class Channel:
    type: str
    name: str
    version: str | None = None


def detect_channel(argv: Sequence[str] | None = None) -> Channel:
    args = iter((sys.argv if argv is None else argv)[1:])
    for arg in args:
        if arg in _ARG_VALUE_OPTIONS:
            next(args, None)
        elif not arg.startswith("-"):
            if arg == "serve":
                break
            return Channel("cli", "icode-acp" if arg == "acp" else "icode-cli")
    return Channel("cli", "icode-tui")


@dataclass(frozen=True, slots=True)
class GitInfo:
    remote: str | None = None
    branch: str | None = None
    revision: str | None = None
    owner: str | None = None
    repo: str | None = None
    user_name: str | None = None
    user_email: str | None = None

    def code_fields(self) -> dict[str, str]:
        return {
            key: value
            for key, value in (
                ("remoteUrl", self.remote),
                ("branch", self.branch),
                ("gitUserName", self.user_name),
                ("gitUserEmail", self.user_email),
            )
            if value
        }


def common_fields(
    workspace_cwd: str = "",
    *,
    channel: Channel,
    user_id: str | None = None,
    git: GitInfo | None = None,
    tool_detail: bool = False,
    version: str = __version__,
) -> dict[str, str]:
    """Encode shared fields from captured facts, without performing I/O."""
    cwd = workspace_cwd or str(Path.cwd())
    project = cwd.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1] or cwd
    fields = {
        "pluginVersion": version,
        "channelType": channel.type,
        "channelName": "icode" if channel.type == "cli" else channel.name,
        "projectName": project,
    }
    if user_id:
        fields["userId"] = user_id
    channel_version = (
        version if tool_detail and channel.type == "cli" and channel.name == "icode-tui" else channel.version
    )
    if channel_version:
        fields["channelVersion"] = channel_version
    if git is not None:
        fields.update(
            {
                key: value
                for key, value in (
                    ("gitRemote", git.remote),
                    ("gitBranch", git.branch),
                    ("gitRevision", git.revision),
                    ("gitOwner", git.owner),
                    ("gitRepo", git.repo),
                )
                if value
            }
        )
    return fields


_git_cache: OrderedDict[Path, tuple[float, GitInfo | None]] = OrderedDict()
_git_lock = threading.Lock()


def collect_git_info(workspace_cwd: str) -> GitInfo | None:
    """Resolve and cache Git facts for an actual workspace. Call outside bus handlers."""
    try:
        cwd = Path(workspace_cwd or Path.cwd()).resolve()
    except OSError, ValueError:
        return None
    now = time.monotonic()
    with _git_lock:
        cached = _git_cache.get(cwd)
        if cached is not None and now - cached[0] < 300:
            _git_cache.move_to_end(cwd)
            return cached[1]
    info = _collect_git(cwd)
    with _git_lock:
        _git_cache[cwd] = (now, info)
        _git_cache.move_to_end(cwd)
        if len(_git_cache) > 256:
            _git_cache.popitem(last=False)
    return info


def _collect_git(cwd: Path) -> GitInfo | None:
    git = shutil.which("git")
    if git is None:
        return None

    def query(*args: str) -> str | None:
        try:
            result = subprocess.run(  # noqa: S603
                [git, *args],
                cwd=cwd,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                check=False,
                timeout=5,
                **windows_hidden_subprocess_kwargs(),
            )
        except OSError, subprocess.TimeoutExpired:
            return None
        return (result.stdout.decode("utf-8", errors="replace").strip() or None) if result.returncode == 0 else None

    revision = query("rev-parse", "HEAD")
    branch = query("rev-parse", "--abbrev-ref", "HEAD")
    if revision is None and branch is None:
        return None
    names = (query("remote") or "").split()
    chosen = next((name for name in ("cnb", "origin") if name in names), names[0] if names else None)
    remote = query("remote", "get-url", chosen) if chosen else None
    parts = []
    if remote and remote.startswith(("http://", "https://")):
        parts = remote.removesuffix(".git").split("/")[3:]
    elif remote and ":" in remote:
        parts = remote.removesuffix(".git").split(":", 1)[1].split("/")
    parts = [part for part in parts if part]
    return GitInfo(
        remote=remote,
        branch=None if branch == "HEAD" else branch,
        revision=revision,
        owner=parts[-2] if len(parts) >= 2 else None,
        repo=parts[-1] if len(parts) >= 2 else None,
        user_name=query("config", "user.name"),
        user_email=query("config", "user.email"),
    )


@dataclass(slots=True)
class DesktopPrompt:
    session_id: str
    channel: Channel
    runner_name: str | None = None
    selected_agent: str | None = None
    attribution_span_id: str | None = None
    latest: ModelSource | None = None
    usage_reported: bool = False
    closed: bool = False

    def response_meta(self) -> dict[str, object] | None:
        source = self.latest
        if source is None:
            return None
        telemetry: dict[str, object] = {"schemaVersion": 1, "requestId": source.request_id}
        if source.span_id:
            telemetry["spanId"] = source.span_id
        result: dict[str, object] = {"agent-studio.dev/telemetry": telemetry}
        if self.attribution_span_id:
            result["agent-studio.dev/final-model-identity"] = {
                "schemaVersion": 1,
                "spanId": self.attribution_span_id,
                "requestId": source.request_id,
                "source": "model_request_id",
            }
        return result


@dataclass(frozen=True, slots=True)
class ModelSource:
    request_id: str
    session_id: str
    span_id: str
    parent_span_id: str
    channel: Channel
    agent_name: str
    workspace_cwd: str
    git: GitInfo | None
    origin: InvocationOrigin | None
    pass_id: str = ""


desktop_prompt: ContextVar[DesktopPrompt | None] = ContextVar("aixcoding_desktop_prompt", default=None)
_sources: OrderedDict[str, tuple[float, ModelSource]] = OrderedDict()


def remember_source(source: ModelSource) -> None:
    _sources[source.request_id] = (time.monotonic() + 1800, source)
    _sources.move_to_end(source.request_id)
    if len(_sources) > 4096:
        _sources.popitem(last=False)


def lookup_source(source_id: str | None) -> ModelSource | None:
    if source_id is None or (row := _sources.get(source_id)) is None:
        return None
    if row[0] <= time.monotonic():
        _sources.pop(source_id, None)
        return None
    return row[1]


def forget_session_sources(session_id: str) -> None:
    for key, (_, source) in tuple(_sources.items()):
        if source.session_id == session_id:
            del _sources[key]
