# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""⑤ Common field assembly (TS ``context.ts``; M5 plan §7; contract §3.1).

spanId deterministic derivation, attribution channel fields,
projectName (``working_dirs[0]`` basename), pluginVersion
(``meta.app_version``).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

from chrys.aixcoding.telemetry.collector.analysis.git_context import GitRepositoryInfo

# Cross-platform separators, TS parity (split on both regardless of host).
_PATH_SPLIT = re.compile(r"[\\/]")


@dataclass(frozen=True, slots=True)
class ReportAttribution:
    """Channel attribution input (userId comes from attribution.json's
    account_id; channelType is derived from scope by the run layer)."""

    channel_type: str  # "desktop" | "cli"
    user_id: str | None = None
    channel_name: str | None = None
    channel_version: str | None = None
    plugin_version: str | None = None


def derive_span_id(session_id: str, turn_id: str) -> str:
    """Turn-scoped stable id (contract §3.1): sha256(session_id + ':' +
    turn_id), first 32 hex digits formatted as a UUID (8-4-4-4-12).
    spanId identifies the turn position, never the content version — a
    rollback producing new content under the same spanId is by design."""
    hex_digest = hashlib.sha256(f"{session_id}:{turn_id}".encode()).hexdigest()[:32]
    return f"{hex_digest[:8]}-{hex_digest[8:12]}-{hex_digest[12:16]}-{hex_digest[16:20]}-{hex_digest[20:]}"


def first_working_dir(meta: dict[str, Any]) -> str | None:
    """First working directory of the session (``working_dirs[0]``); the
    productName/projectName locator input (K3)."""
    dirs = meta.get("working_dirs")
    if not isinstance(dirs, list):
        return None
    first = dirs[0] if dirs else None
    if isinstance(first, str) and first:
        return first
    return None


def derive_project_name(meta: dict[str, Any]) -> str | None:
    """projectName: basename of ``working_dirs[0]`` (cross-platform
    separators)."""
    first = first_working_dir(meta)
    if first is None:
        return None
    parts = [part for part in _PATH_SPLIT.split(first) if part]
    return parts[-1] if parts else None


@dataclass(frozen=True, slots=True)
class EventCommonContext:
    session_id: str
    attribution: ReportAttribution | None
    # Git repository folder name; '' outside git (contract §2.2,
    # tool-detail/save required).
    product_name: str
    project_name: str | None
    plugin_version: str | None
    # Session primary working directory (meta.primary_cwd; the ai-code
    # filepath fallback basis).
    primary_cwd: str | None
    # tool-detail git context (resolved once per run per primary_cwd;
    # M5 plan §7). remoteUrl feeds the registration-focus gitRemote
    # common field (M4, gated behind the HTTP sink's
    # focus_fields_enabled switch).
    git: GitRepositoryInfo | None
    # Repository root of primary_cwd (relativization basis for the
    # focus-field value/fileName, focus_fields.relativize_tool_path);
    # resolved through the same per-run cache as productName's root.
    git_root: str | None = None


def build_event_common(context: EventCommonContext, turn_id: str) -> dict[str, Any]:
    """Assemble event common fields (ReportEventCommon subset;
    None/missing omitted)."""
    attribution = context.attribution
    git = context.git
    common: dict[str, Any] = {
        "sessionId": context.session_id,
        "spanId": derive_span_id(context.session_id, turn_id),
        "productName": context.product_name,
    }
    if context.project_name is not None:
        common["projectName"] = context.project_name
    # channelType is derived from scope by the run layer (acp→desktop,
    # tui→cli); desktop is the fallback default.
    common["channelType"] = attribution.channel_type if attribution is not None else "desktop"
    if attribution is not None:
        if attribution.channel_name is not None:
            common["channelName"] = attribution.channel_name
        if attribution.channel_version is not None:
            common["channelVersion"] = attribution.channel_version
        if attribution.user_id is not None:
            common["userId"] = attribution.user_id
    if context.plugin_version is not None:
        common["pluginVersion"] = context.plugin_version
    if git is not None:
        if git.remote_url is not None:
            common["gitRemote"] = git.remote_url
        if git.branch is not None:
            common["gitBranch"] = git.branch
        if git.revision is not None:
            common["gitRevision"] = git.revision
        if git.owner is not None:
            common["gitOwner"] = git.owner
        if git.repo is not None:
            common["gitRepo"] = git.repo
    return common
