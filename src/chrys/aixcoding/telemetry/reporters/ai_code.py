# ruff: noqa: RUF001, RUF002
"""ai-code/save 组装（方案 §4.3）：写类工具成功后的 AI 代码块上报。

数据源：``write_file`` / ``edit_file``（``_FILE_TOOLS``；shell 隐式写不报）。
before/after 全文取 Result 事件 ``metadata["file_snapshot"]``。edit_file 优先
使用工具参数中的 old_string/new_string 定位执行后片段；write_file 上报全文。

codeStatus 采纳语义（§4.3；五态映射待 §8-3 定稿）：
- 拒绝（Result metadata ``approval=user_rejected``）→ 4——注意拒绝时工具不
  执行、无 mutation，本 reporter 不触发；4 落在 tool-detail update（M2 已实现）；
- 批准且经用户对话框（请求时 mode=manual）→ 5；
- judge 批准（mode=auto）/ bypass / 无审批 → 1。

mode 真值源与批准事件均来自 EventBus（``ApprovalModeUpdated`` /
``ApprovalRequest`` / ``ApprovalResponse``），由 ``ApprovalTracker`` 维护。
批量缓冲对齐 pi-acp batchSize 机制（``BatchBuffer`` 满 N 条或 T 秒 flush）。
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

from chrys.aixcoding.telemetry.reporters import relative_file_name, remember_bounded
from chrys.aixcoding.telemetry.types import CodeStatus

if TYPE_CHECKING:
    from collections.abc import Callable

    from chrys.foundation.events.types import (
        ApprovalModeUpdated,
        ApprovalRequest,
        ApprovalResponse,
        InvocationToolCallResult,
        InvocationToolCallStart,
    )

logger = logging.getLogger(__name__)

FILE_WRITE_TOOLS = frozenset({"write_file", "edit_file"})
"""触发 ai-code 上报的写类工具（对齐 service 层 ``_FILE_TOOLS``；shell 隐式写不报）。"""

_MODE_MANUAL = "manual"

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


class ApprovalTracker:
    """从审批事件流维护 call_id → 采纳语义 codeStatus 所需的事实。

    四张表均为有界记忆（超限丢最旧）——长驻进程防泄漏。
    """

    def __init__(self) -> None:
        self._modes: dict[str, str] = {}
        self._request_mode: dict[str, str] = {}
        self._request_call_id: dict[str, str] = {}
        self._approved: dict[str, bool] = {}

    def on_mode_updated(self, event: ApprovalModeUpdated) -> None:
        if event.session_id:
            remember_bounded(self._modes, event.session_id, event.mode)

    def on_request(self, event: ApprovalRequest) -> None:
        remember_bounded(self._request_mode, event.request_id, self._modes.get(event.session_id or "", ""))
        if event.call_id:
            remember_bounded(self._request_call_id, event.request_id, event.call_id)

    def on_response(self, event: ApprovalResponse) -> None:
        remember_bounded(self._approved, event.request_id, event.approved)

    def adopted_code_status(self, call_id: str, session_id: str | None, *, rejected: bool) -> int:
        """写类工具执行成功后的采纳 codeStatus（5=用户批准 / 1=其他）。"""
        if rejected:
            return CodeStatus.USER_REJECTED
        for request_id, approved in self._approved.items():
            if approved and self._request_call_id.get(request_id) == call_id:
                if self._request_mode.get(request_id) == _MODE_MANUAL:
                    return CodeStatus.USER_APPROVED
                return CodeStatus.SUCCESS
        return CodeStatus.SUCCESS


class AiCodeReporter:
    """组装 ai-code/save 报文并经批量缓冲提交。"""

    def __init__(self, add: Callable[[Mapping[str, object]], None]) -> None:
        self._add = add
        self._args_by_call: dict[str, dict[str, Any]] = {}

    def on_start(self, event: InvocationToolCallStart) -> None:
        if event.tool_name in FILE_WRITE_TOOLS:
            remember_bounded(self._args_by_call, event.call_id, dict(event.args or {}))

    def on_result(
        self,
        event: InvocationToolCallResult,
        *,
        code_status: int,
        errored: bool,
    ) -> None:
        args = self._args_by_call.pop(event.call_id, None)
        if args is None or event.tool_name not in FILE_WRITE_TOOLS or errored:
            return
        snapshot = event.metadata.get("file_snapshot")
        # file_snapshot 是 tuple(before, after) (pipeline.py:89) — 同 tool_detail 修正.
        before_text = snapshot[0] if isinstance(snapshot, tuple) and len(snapshot) == 2 else None
        after_text = snapshot[1] if isinstance(snapshot, tuple) and len(snapshot) == 2 else None
        if not isinstance(after_text, str) or not after_text:
            return
        path = args.get("path")
        if not isinstance(path, str) or not path:
            return
        blocks = ai_code_blocks(
            before_text if isinstance(before_text, str) else None,
            after_text,
            edit_args=args if event.tool_name == "edit_file" else None,
        )
        if not blocks:
            return

        from chrys.aixcoding.telemetry.llm_telemetry import resolve_call
        from chrys.aixcoding.telemetry.reporters import common_fields

        workspace = event.workspace_cwd or None
        payload: dict[str, Any] = {
            "reportId": str(uuid.uuid4()),
            "filepath": relative_file_name(path, workspace),
            "blocks": blocks,
            "sourceType": "edit",
            "inputMethod": "ai_generated",
            "sessionId": event.session_id,
            "codeStatus": code_status,
        }
        if language := language_from_path(path):
            payload["language"] = language
        request = resolve_call(event.provider_call_id, event.session_id)
        if request is not None:
            payload["requestId"] = request[0]
            if request[1]:
                # spanId = 提问周期链路 span (同 tool-detail 语义修正, 2026-10-09).
                payload["spanId"] = request[1]
        from chrys.aixcoding.context import current_function_name

        if agent_name := current_function_name():
            payload["agentName"] = agent_name
        payload.update(
            {
                key: value
                for key, value in (
                    ("remoteUrl", _git_field("git_remote", workspace)),
                    ("branch", _git_field("git_branch", workspace)),
                    ("gitUserName", _git_field("git_user_name", workspace)),
                    ("gitUserEmail", _git_field("git_user_email", workspace)),
                )
                if value
            }
        )
        payload.update(common_fields(workspace))
        self._add(payload)


def _git_field(name: str, workspace_cwd: str | None = None) -> str | None:
    from chrys.aixcoding.git_info import collect_git_info

    info = collect_git_info(Path(workspace_cwd) if workspace_cwd else Path.cwd())
    if info is None:
        return None
    return getattr(info, name, None)
