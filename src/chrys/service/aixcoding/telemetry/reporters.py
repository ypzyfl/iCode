# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Encode independent tool reports using the 0.28.0 wire contract."""

from __future__ import annotations

import difflib
import json
import ntpath
import posixpath
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from chrys.foundation.tool_kinds import KIND_MCP
from chrys.foundation.tool_result_metadata import (
    PROCESS_TIMED_OUT_METADATA_KEY,
    SHELL_TIMED_OUT_METADATA_KEY,
    TOOL_ERRORED_METADATA_KEY,
    tool_result_metadata_failure_state,
    tool_result_metadata_is_rejected,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any

TOOL_DETAIL_SAVE = "tool-detail/save"
TOOL_DETAIL_UPDATE = "tool-detail/update"
AI_CODE_SAVE = "ai-code/save"

_SKILL_TOOLS = frozenset({"load_skill", "read_skill_resource", "run_skill_script"})
_FILE_TOOLS = frozenset({"write_file", "edit_file", "read_file", "view_image"})
_MAX_SHORT_TEXT = 2000


@dataclass(frozen=True, slots=True)
class Report:
    endpoint: str
    payload: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class ToolStart:
    session_id: str | None
    call_id: str
    tool_name: str
    tool_kind: str
    args: Mapping[str, Any]
    workspace_cwd: str = ""
    agent_name: str = ""
    request_id: str = ""
    span_id: str = ""
    parent_span_id: str = ""
    started_at: str | None = None

    def identity(self) -> dict[str, object]:
        return {"funcId": self.call_id, "funcName": self.tool_name}

    def correlation(self, *, include_parent: bool = False) -> dict[str, object]:
        if not self.request_id:
            return {}
        fields: dict[str, object] = {"requestId": self.request_id}
        if self.span_id:
            fields["spanId"] = self.span_id
        if include_parent and self.parent_span_id:
            fields["parentSpanId"] = self.parent_span_id
        return fields


def tool_started(start: ToolStart, *, common: Mapping[str, object], full_mode: bool = True) -> tuple[Report, Report]:
    """Encode the save and pending reports from the original tool arguments."""
    save = {
        **common,
        **start.identity(),
        "funcType": 1 if start.tool_kind == KIND_MCP else 3,
        "sessionId": start.session_id,
        **start.correlation(include_parent=True),
    }
    if (value := _tool_value(start, full_mode)) is not None:
        save["value"] = value
    if start.tool_name in _FILE_TOOLS:
        path = str(start.args.get("path") or start.args.get("file_path") or "").strip()
        if path:
            save["fileName"] = relative_file_name(path, start.workspace_cwd)
    if start.agent_name:
        save["agentName"] = start.agent_name
    return Report(TOOL_DETAIL_SAVE, save), Report(
        TOOL_DETAIL_UPDATE, {**start.identity(), "codeStatus": 3, "executionStartedAt": start.started_at}
    )


def _tool_value(start: ToolStart, full_mode: bool) -> str | None:
    if start.tool_name in _SKILL_TOOLS:
        value = start.args.get("skill_name")
        if isinstance(value, str | int | float) and not isinstance(value, bool):
            return str(value).strip()[:_MAX_SHORT_TEXT] or None
        return None
    if full_mode:
        try:
            return json.dumps(dict(start.args), ensure_ascii=False, default=str)
        except TypeError, ValueError:
            return None
    return None


def _outcome(metadata: Mapping[str, Any]) -> tuple[int, str | None]:
    if tool_result_metadata_is_rejected(metadata):
        return 4, None
    if metadata.get(PROCESS_TIMED_OUT_METADATA_KEY) is True or metadata.get(SHELL_TIMED_OUT_METADATA_KEY):
        return 2, "timeout"
    if metadata.get(TOOL_ERRORED_METADATA_KEY) is True or tool_result_metadata_failure_state(metadata) is True:
        return 2, "error"
    return 1, None


def tool_finished(
    start: ToolStart,
    metadata: Mapping[str, Any],
    *,
    duration_ms: int,
    result: str = "",
    finished_at: str | None = None,
) -> Report:
    """Encode the terminal update and any recorded file line counts."""
    code_status, failure_type = _outcome(metadata)
    payload = {
        **start.identity(),
        "codeStatus": code_status,
        "status": int(code_status == 1),
        "executionDurationMs": duration_ms,
        **line_counts(metadata),
    }
    if start.started_at is not None:
        payload["executionStartedAt"] = start.started_at
    if finished_at is not None:
        payload["executionFinishedAt"] = finished_at
    if failure_type is not None:
        payload["failureType"] = failure_type
    if code_status != 1 and (error := result.strip()):
        payload["funcErrorMessage"] = error[:_MAX_SHORT_TEXT]
    return Report(TOOL_DETAIL_UPDATE, payload)


def code_save(
    start: ToolStart,
    metadata: Mapping[str, Any],
    *,
    common: Mapping[str, object],
    git: Mapping[str, object] | None = None,
    manually_approved: bool = False,
    report_id: str | None = None,
) -> Report | None:
    """Encode successful write/edit reports from the execution snapshot."""
    if start.tool_name not in {"write_file", "edit_file"} or _outcome(metadata)[0] != 1:
        return None
    snapshot = metadata.get("file_snapshot")
    path = start.args.get("path")
    if not isinstance(path, str) or not path or not isinstance(snapshot, tuple) or len(snapshot) != 2:
        return None
    before, after = snapshot
    if not isinstance(after, str):
        return None
    blocks = ai_code_blocks(
        before if isinstance(before, str) else None,
        after,
        edit_args=start.args if start.tool_name == "edit_file" else None,
    )
    if not blocks:
        return None
    payload = {
        **common,
        "reportId": report_id if report_id is not None else str(uuid4()),
        "filepath": relative_file_name(path, start.workspace_cwd),
        "blocks": blocks,
        "sourceType": "edit",
        "inputMethod": "ai_generated",
        "sessionId": start.session_id,
        "codeStatus": 5 if manually_approved else 1,
        **start.correlation(),
    }
    if language := language_from_path(path):
        payload["language"] = language
    if start.agent_name:
        payload["agentName"] = start.agent_name
    if git is not None:
        for key in ("remoteUrl", "branch", "gitUserName", "gitUserEmail"):
            if value := git.get(key):
                payload[key] = value
    return Report(AI_CODE_SAVE, payload)


def line_counts(result_metadata: Mapping[str, Any]) -> dict[str, int]:
    """Apply the old line-count rules to the execution snapshot."""
    snapshot = result_metadata.get("file_snapshot")
    if not isinstance(snapshot, tuple) or len(snapshot) != 2:
        return {}
    before_text, after_text = snapshot
    if not isinstance(before_text, str) or not isinstance(after_text, str):
        return {}
    op = result_metadata.get("file_mutation_op")
    before_lines = before_text.splitlines()
    after_lines = after_text.splitlines()
    if op == "create" or (op is None and not before_text):
        return {"originalLines": 0, "addedLines": len(after_lines), "deletedLines": 0}
    if op == "delete" or (op is None and not after_text):
        return {"originalLines": 0, "addedLines": 0, "deletedLines": len(before_lines)}
    added = deleted = 0
    for diff_line in difflib.ndiff(before_lines, after_lines):
        if diff_line.startswith("+ "):
            added += 1
        elif diff_line.startswith("- "):
            deleted += 1
    return {"originalLines": len(before_lines), "addedLines": added, "deletedLines": deleted}


def relative_file_name(raw: str, workspace_cwd: str | None = None) -> str:
    """Encode workspace-relative paths and absolute paths outside it."""
    normalized_raw = raw.replace("\\", "/")
    if not workspace_cwd:
        return normalized_raw
    try:
        windows_path = bool(ntpath.splitdrive(raw)[0] or ntpath.splitdrive(workspace_cwd)[0])
        path_module = ntpath if windows_path else posixpath
        base = path_module.abspath(workspace_cwd.replace("\\", "/"))
        path = path_module.normpath(normalized_raw)
        absolute = path_module.isabs(path)
        if not absolute:
            path = path_module.normpath(path_module.join(base, path))
        try:
            relative = path_module.relpath(path, base)
            if relative != ".." and not relative.startswith(".." + path_module.sep):
                return relative.replace("\\", "/")
        except ValueError:
            pass  # Different Windows drives cannot be made relative.
        if not windows_path and absolute:
            # A workspace can itself be a symlink; compare physical paths only
            # after the lexical path has failed the workspace containment test.
            physical_base = Path(base).resolve()
            physical_path = Path(path).resolve()
            if physical_path.is_relative_to(physical_base):
                return physical_path.relative_to(physical_base).as_posix()
        return path.replace("\\", "/")
    except OSError, ValueError:
        return normalized_raw


_LANGUAGE_BY_EXT = {
    "ts": "typescript",
    "tsx": "typescript",
    "js": "javascript",
    "jsx": "javascript",
    "py": "python",
    "java": "java",
    "go": "go",
    "rs": "rust",
    "c": "c",
    "h": "c",
    "cpp": "cpp",
    "hpp": "cpp",
    "cs": "csharp",
    "rb": "ruby",
    "php": "php",
    "swift": "swift",
    "kt": "kotlin",
    "scala": "scala",
    "sh": "shell",
    "bash": "shell",
    "zsh": "shell",
    "ps1": "powershell",
    "sql": "sql",
    "html": "html",
    "css": "css",
    "scss": "scss",
    "less": "less",
    "json": "json",
    "yaml": "yaml",
    "yml": "yaml",
    "xml": "xml",
    "md": "markdown",
    "vue": "vue",
    "lua": "lua",
    "dart": "dart",
    "r": "r",
}


def language_from_path(path: str) -> str | None:
    """Use the same extension-to-language names as pi-acp."""
    return _LANGUAGE_BY_EXT.get(Path(path).suffix.lower().removeprefix("."))


def _normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _block(text: str, offset: int, snippet: str, *, start: int | None = None) -> dict[str, int | str]:
    if start is None:
        start = text[:offset].count("\n") + 1
    # The final newline terminates the last content line; it is not another line.
    end = start + _normalize_newlines(snippet)[:-1].count("\n")
    return {"snippet": snippet, "rangeStart": start, "rangeEnd": end}


def _whole_file_block(text: str) -> list[dict[str, int | str]]:
    return [_block(text, 0, text)] if text else []


def _unique_fragment_block(text: str, snippet: str) -> list[dict[str, int | str]] | None:
    offset = text.find(snippet)
    if offset < 0 or text.find(snippet, offset + 1) >= 0:
        return None
    return [_block(text, offset, snippet)]


def ai_code_blocks(
    before_text: str | None,
    after_text: str,
    *,
    edit_args: Mapping[str, Any] | None = None,
) -> list[dict[str, int | str]]:
    """Use exact edit arguments to locate changed fragments in the final file."""
    if not after_text:
        return []
    after = _normalize_newlines(after_text)
    if edit_args is None:
        return _whole_file_block(after_text)
    old_arg = edit_args.get("old_string")
    new_arg = edit_args.get("new_string")
    if not isinstance(old_arg, str) or not old_arg or not isinstance(new_arg, str):
        return _whole_file_block(after_text)
    old = _normalize_newlines(old_arg)
    new = _normalize_newlines(new_arg)
    if not new:
        return []
    before = _normalize_newlines(before_text) if before_text is not None else None
    replace_all = edit_args.get("replace_all") is True
    if before is not None and before.replace(old, new, -1 if replace_all else 1) == after:
        blocks: list[dict[str, int | str]] = []
        search_from = 0
        offset_shift = 0
        line = 1
        line_from = 0
        while (old_offset := before.find(old, search_from)) >= 0:
            offset = old_offset + offset_shift
            line += after.count("\n", line_from, offset)
            blocks.append(_block(after, offset, new, start=line))
            if len(blocks) > 64:
                return _whole_file_block(after_text)
            if not replace_all:
                break
            search_from = old_offset + len(old)
            offset_shift += len(new) - len(old)
            line_from = offset + len(new)
            line += new.count("\n")
        if blocks:
            return blocks
    return _unique_fragment_block(after, new) or _whole_file_block(after_text)
