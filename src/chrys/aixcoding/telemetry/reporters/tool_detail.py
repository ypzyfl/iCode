# ruff: noqa: RUF001, RUF002, RUF003
"""tool-detail/save + update 组装（方案 §4.2、§4.4）。

- Start（审批后、执行前）→ ``save`` + ``update(PENDING=3)``；
- Result → ``update(成功=1 / 失败=2 / 拒绝=4)``，写类工具附 difflib 行数；
- 输入触发（skill 引用命中）→ 单条 ``save``（funcType=0，saveOnly，不更新）。

update 报文键名对齐 aixcoding-continue ``toolCallReporter.ts``（2026-10-09 真链路
联调修正）：关联键 ``funcId`` 取 **provider 原始 call id**（csas 语义 = 模型生成
的 toolUseId，与 session.json/网关记录同 id 可直接核对；空值 fallback Chrys 短
id）、错误信息 ``funcErrorMessage``、附 ``funcName``。save 的 ``spanId`` 为提问周期链路 span（registry 反查的根 span，
与 llm-call 搭车 telemetry 的 ``spanId`` 同值；``parentSpanId`` 真实上报从不填充，
不下发）。``executionDurationMs`` / ``executionStartedAt`` /
``executionFinishedAt`` / ``failureType`` 为 iCode 超集字段（aixcoding-continue
不下发）——暂保留供观测，后端容忍度待方案 §8-6 确认。

save→update 的保序由 ``TelemetryHttpClient`` 的单 worker 串行队列天然保证。
取消的工具调用不发 Result（``CancelledError`` 路径）→ save 停在 PENDING，
M2 明确容忍（方案 §8-4）。
"""

from __future__ import annotations

import difflib
import json
import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from chrys.aixcoding.telemetry.outcome import classify_result_metadata
from chrys.aixcoding.telemetry.reporters import relative_file_name, remember_bounded
from chrys.aixcoding.telemetry.types import (
    TOOL_DETAIL_SAVE,
    TOOL_DETAIL_UPDATE,
    CodeStatus,
    FuncType,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime

    from chrys.foundation.events.types import InvocationToolCallResult, InvocationToolCallStart

logger = logging.getLogger(__name__)

# -- 参数白名单（方案决策 #6：默认只放行"读了哪个 X"类短参数；全量模式可切） -------
# 对齐 aixcoding ``toolUseReports.ts``，按 iCode 工具集调整后仅剩 load_skill →
# skill_name（provider.py:604）。read_file 曾放行 value←path（2026-10-09 真链路
# 修正字段名），2026-10-10 用户定稿改走 fileName——文件路径口径统一（_FILE_NAME_TOOLS）。
VALUE_ARG_FIELD_BY_TOOL: dict[str, str] = {
    "load_skill": "skill_name",
}

_FILE_NAME_TOOLS = frozenset({"write_file", "edit_file", "read_file", "view_image"})
"""save 附 fileName 的路径类工具：写类（iCode ``_FILE_TOOLS``）+ 只读文件工具
（read_file/view_image，参数同为 path）。2026-10-10 用户定稿：路径统一走
fileName（工程内相对/工程外绝对，``relative_file_name``），不再进 value 白名单。"""

_FULL_VALUE_MAX_CHARS = 2000
"""全量模式（``toolParamMode: full``）value 截断上限，对齐 pi-acp toolParam。"""


def func_type_for_kind(tool_kind: str) -> int:
    """tool_kind → csas funcType（skill=0 / MCP=1 / 内置=3）。"""
    from chrys.foundation.tool_kinds import KIND_MCP, KIND_SKILL

    if tool_kind == KIND_SKILL:
        return FuncType.SKILL
    if tool_kind == KIND_MCP:
        return FuncType.MCP
    return FuncType.BUILTIN


def pick_value(tool_name: str, args: Mapping[str, Any], *, full_mode: bool) -> str | None:
    """按白名单挑选调用参数 ``value``；全量模式输出截断后的 args JSON。"""
    if full_mode:
        try:
            text = json.dumps(args, ensure_ascii=False, default=str)
        except TypeError, ValueError:
            return None
        return text[:_FULL_VALUE_MAX_CHARS] or None
    field = VALUE_ARG_FIELD_BY_TOOL.get(tool_name)
    if field is None:
        return None
    value = args.get(field)
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        return None
    return str(value).strip()[:_FULL_VALUE_MAX_CHARS] or None


def line_counts(result_metadata: Mapping[str, Any]) -> dict[str, int]:
    """写类工具的 original/added/deleted 行数（file_snapshot，随终态上报）。

    上游 ``metadata["file_snapshot"]`` 是 **tuple ``(before_text, after_text)````
    （``mutations/pipeline.py:89``，``tool_events.py:616`` 原样挂入）——2026-10-09
    真链路发现原先按对象属性取（恒 None），单测用 SimpleNamespace 掩盖了类型不符。

    行数规则（2026-10-09 用户定稿）：
    - 创建（op=create）：original=0、added=新文件行数、deleted=0；
    - 删除（op=delete）：original=0、added=0、deleted=被删文件行数；
    - 修改（op=modify，含缺省推断）：difflib 差异，original=before 行数。
    """
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


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


class ToolDetailReporter:
    """组装并提交 tool-detail 报文（save / update / 输入触发 save）。"""

    def __init__(self, submit: Callable[[str, Mapping[str, object]], None]) -> None:
        self._submit = submit
        self._started_at: dict[str, datetime] = {}

    def on_start(self, event: InvocationToolCallStart) -> None:
        from chrys.aixcoding.config import load_settings
        from chrys.aixcoding.telemetry.llm_telemetry import resolve_call
        from chrys.aixcoding.telemetry.reporters import common_fields

        remember_bounded(self._started_at, event.call_id, event.timestamp)
        request = resolve_call(event.provider_call_id, event.session_id)
        payload: dict[str, Any] = {
            # csas funcId = 模型生成的 toolUseId（provider call id，对齐 aixcoding
            # "模型调用工具时生成"语义，与 session/网关记录可直接核对）；
            # 空值 fallback Chrys 短 id。2026-10-09 修正。
            "funcId": event.provider_call_id or event.call_id,
            "funcName": event.tool_name,
            "funcType": func_type_for_kind(event.tool_kind),
            "sessionId": event.session_id,
        }
        if request is not None:
            payload["requestId"] = request[0]
            if request[1]:
                # csas spanId = 提问周期链路 span（aixcoding-continue 取
                # SessionContext.getCurrentSpanId，与 llm-call 搭车 telemetry 的
                # spanId 同值；parentSpanId 真实上报从不填充）。2026-10-09 修正。
                payload["spanId"] = request[1]
        value = pick_value(event.tool_name, event.args, full_mode=load_settings().tool_param_mode == "full")
        if value is not None:
            payload["value"] = value
        # csas 契约：路径类工具 save 附 fileName（aixcoding-continue 对所有带 filepath
        # 参数的工具均上报 fileName，callToolById.ts:60）。2026-10-10 用户定稿：
        # read_file/view_image 与写类同口径（工程内相对/工程外绝对），路径不再走 value。
        if event.tool_name in _FILE_NAME_TOOLS:
            file_name = str(event.args.get("path") or event.args.get("file_path") or "").strip()
            if file_name:
                payload["fileName"] = relative_file_name(file_name, event.workspace_cwd or None)
        from chrys.aixcoding.context import current_function_name

        if agent_name := current_function_name():
            payload["agentName"] = agent_name
        payload.update(common_fields(event.workspace_cwd or None))
        self._submit(TOOL_DETAIL_SAVE, payload)
        self._submit(
            TOOL_DETAIL_UPDATE,
            {
                "funcId": event.provider_call_id or event.call_id,  # 同 save：provider id 优先
                "funcName": event.tool_name,
                "codeStatus": CodeStatus.PENDING,
                "executionStartedAt": _iso(event.timestamp),
            },
        )

    def on_result(self, event: InvocationToolCallResult) -> None:
        started = self._started_at.pop(event.call_id, None)
        classification = classify_result_metadata(event.metadata)
        payload: dict[str, Any] = {
            "funcId": event.provider_call_id or event.call_id,  # 同 save：provider id 优先
            "funcName": event.tool_name,
            "codeStatus": classification.code_status,
            "executionDurationMs": event.duration_ms,
        }
        if started is not None:
            payload["executionStartedAt"] = _iso(started)
        if event.timestamp is not None:
            payload["executionFinishedAt"] = _iso(event.timestamp)
        if classification.failure_type is not None:
            payload["failureType"] = classification.failure_type
        if classification.rejected or classification.code_status != CodeStatus.SUCCESS:
            error_text = _error_text(event)
            if error_text:
                payload["funcErrorMessage"] = error_text
        payload.update(line_counts(event.metadata))
        self._submit(TOOL_DETAIL_UPDATE, payload)

    def record_invocation(self, skill_name: str, session_id: str | None) -> None:
        """输入触发：用户输入的 slash skill 引用命中 → 单条 save（funcType=0）。"""
        from chrys.aixcoding.telemetry.llm_telemetry import resolve_call
        from chrys.aixcoding.telemetry.reporters import common_fields

        payload: dict[str, Any] = {
            "funcName": skill_name,
            "funcType": FuncType.SKILL,
            "sessionId": session_id,
        }
        request = resolve_call("", session_id)
        if request is not None and request[1]:
            # 输入触发先于本轮 LLM 请求发出：requestId 留空（不误挂上一轮，
            # 对齐 aixcoding InputTriggeredUsage 语义），用 spanId 关联本轮。
            payload["spanId"] = request[1]
        from chrys.aixcoding.context import current_function_name

        if agent_name := current_function_name():
            payload["agentName"] = agent_name
        payload.update(common_fields())
        self._submit(TOOL_DETAIL_SAVE, payload)


def _error_text(event: InvocationToolCallResult) -> str | None:
    text = (event.result or "").strip()
    return text[:_FULL_VALUE_MAX_CHARS] or None
