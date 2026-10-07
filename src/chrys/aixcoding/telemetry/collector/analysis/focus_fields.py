# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Registered focus-field construction (registration table §3.1; M4).

The 7 allowlist-gated fields are implemented ahead of the D1 sign-off
(proceed-by-default decision, 2026-10-06): the analysis layer always
constructs them with the redaction rules below, while the HTTP sink's
``focus_fields_enabled`` switch (default False) keeps them out of the
remote payload until the registration table is approved — the file
sink observes them locally, and flipping the switch plus advancing
``ANALYSIS_VERSION`` releases them in one shot.

Redaction rules (registration table redaction column):
- ``value`` / ``fileName``: relative path (no drive letter / absolute
  prefix) for file-read tools, skill name for skill tools;
- ``extra.mcpUri``: ``mcp://<server>/<tool>`` stitched from
  ``_chrys_tool_context`` (server_name + remote_name/normalized_name;
  the function_call name may carry the local prefix, so the context is
  the source);
- ``funcErrorMessage``: structured ``tool_error_message`` first, the
  result's ``exception`` second, truncated to 512 chars;
- ``blocks[].snippet``: changed after-lines, truncated to 64KB/block;
- ``filepath`` (ai-code): the K5 relativized form (see
  ai_code_events._derive_filepath);
- ``gitRemote``: the repository remote URL (git context, cnb → origin
  → first remote, old plug-in parity).
"""

from __future__ import annotations

import json
import re
from typing import Any

from chrys.aixcoding.telemetry.collector.analysis.util import as_object, read_string

# File-read tools whose ``path`` argument feeds value/fileName (the
# registration purpose is the old interface's file-read statistics;
# ``path`` is the engine's uniform path argument name).
READ_FILE_TOOL_NAMES = frozenset({"read_file", "view_image"})
# Skill tools whose skill name feeds value (skill-load statistics).
SKILL_TOOL_NAMES = frozenset({"load_skill", "read_skill_resource", "run_skill_script"})

MAX_FUNC_ERROR_MESSAGE_CHARS = 512
MAX_SNIPPET_CHARS = 64 * 1024

_BACKSLASH = re.compile(r"\\")
_DRIVE_PREFIX = re.compile(r"^[A-Za-z]:")


def _content_properties(content: dict[str, Any]) -> dict[str, Any]:
    properties = as_object(content.get("additional_properties"))
    return properties if properties is not None else {}


def _call_arguments(call: dict[str, Any]) -> dict[str, Any]:
    """Parse the function_call arguments JSON; a malformed or non-object
    value yields {} — it only affects focus fields, never the other
    event columns (M5 plan §6.1)."""
    raw = read_string(call, "arguments")
    if raw is None:
        return {}
    try:
        parsed = json.loads(raw)
    except ValueError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _split_segments(path: str) -> list[str]:
    return [part for part in _BACKSLASH.sub("/", path).split("/") if part]


def _relative_within(base: str, unified_path: str) -> str | None:
    """Case-insensitive prefix relativization (Windows parity with the
    ai-code filepath logic); None when the path is not under base."""
    base_parts = _split_segments(base)
    file_parts = _split_segments(unified_path)
    if not base_parts or len(base_parts) >= len(file_parts):
        return None
    for index in range(len(base_parts)):
        if base_parts[index].lower() != file_parts[index].lower():
            return None
    return "/".join(file_parts[len(base_parts) :])


def relativize_tool_path(path: str, git_root: str | None, primary_cwd: str | None) -> str | None:
    """Relative path form for value/fileName (registration redaction:
    no drive letter / host prefix). Already-relative inputs only unify
    separators; absolute inputs relativize against the git root, then
    primary_cwd, and as a last resort drop the leading drive segment —
    never an absolute prefix."""
    unified = _BACKSLASH.sub("/", path)
    if unified and not unified.startswith("/") and not _DRIVE_PREFIX.match(unified):
        return unified
    for base in (git_root, primary_cwd):
        if base:
            relative = _relative_within(base, unified)
            if relative is not None:
                return relative
    parts = _split_segments(unified)
    if parts and _DRIVE_PREFIX.fullmatch(parts[0]):
        parts = parts[1:]
    return "/".join(parts) or None


def derive_mcp_uri(call: dict[str, Any]) -> str | None:
    """``extra.mcpUri`` source: ``mcp://<server_name>/<remote_name>``
    stitched from ``_chrys_tool_context`` (remote_name falls back to
    normalized_name)."""
    context = as_object(_content_properties(call).get("_chrys_tool_context"))
    if context is None:
        return None
    server = read_string(context, "server_name")
    tool = read_string(context, "remote_name")
    if tool is None:
        tool = read_string(context, "normalized_name")
    if server is None or tool is None:
        return None
    return f"mcp://{server}/{tool}"


def derive_func_error_message(result: dict[str, Any]) -> str | None:
    """``funcErrorMessage`` (truncated 512): the structured
    ``tool_error_message`` first (no ``Error:`` prefix, engine
    ``tool_result_metadata.py``), the result's ``exception`` second."""
    metadata = as_object(_content_properties(result).get("_chrys_tool_result_metadata"))
    message: str | None = None
    if metadata is not None:
        message = read_string(metadata, "tool_error_message")
    if message is None:
        message = read_string(result, "exception")
    if message is None:
        return None
    return message[:MAX_FUNC_ERROR_MESSAGE_CHARS]


def clip_snippet(text: str) -> str:
    """Snippet redaction: truncate to 64KB per block (registration
    table §3.1)."""
    return text[:MAX_SNIPPET_CHARS]


def derive_save_focus_fields(
    call: dict[str, Any],
    git_root: str | None,
    primary_cwd: str | None,
) -> dict[str, Any]:
    """Focus fields for one tool-use-saved event (contract §3.2):
    file-read tools → value/fileName (relativized path); skill tools →
    value (normalized skill name from ``_chrys_tool_context`` first,
    the raw argument second); MCP calls → extra.mcpUri. Absent sources
    omit the field (two-state distinction)."""
    name = read_string(call, "name")
    if name is None:
        return {}
    fields: dict[str, Any] = {}
    if name in READ_FILE_TOOL_NAMES:
        arguments = _call_arguments(call)
        path = read_string(arguments, "path")
        if path:
            relative = relativize_tool_path(path, git_root, primary_cwd)
            if relative is not None:
                fields["value"] = relative
                fields["fileName"] = relative
    elif name in SKILL_TOOL_NAMES:
        skill_name: str | None = None
        context = as_object(_content_properties(call).get("_chrys_tool_context"))
        if context is not None:
            skill_name = read_string(context, "skill_name")
        if skill_name is None:
            skill_name = read_string(_call_arguments(call), "skill_name")
        if skill_name:
            fields["value"] = skill_name
    mcp_uri = derive_mcp_uri(call)
    if mcp_uri is not None:
        fields["extra"] = {"mcpUri": mcp_uri}
    return fields
