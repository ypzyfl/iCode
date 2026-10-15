# ruff: noqa: RUF002, RUF003, S101
"""M3 测试：ai-code blocks / codeStatus 采纳语义 / reporter 报文（方案 §4.3）。"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from chrys.aixcoding.config import clear_settings_cache
from chrys.aixcoding.telemetry import subscriber
from chrys.aixcoding.telemetry.llm_telemetry import clear_call_registry
from chrys.aixcoding.telemetry.reporters.ai_code import (
    AiCodeReporter,
    ApprovalTracker,
    ai_code_blocks,
    language_from_path,
)
from chrys.aixcoding.telemetry.types import CodeStatus
from chrys.foundation.events.bus import EventBus
from chrys.foundation.events.types import (
    ApprovalModeUpdated,
    ApprovalRequest,
    ApprovalResponse,
    InvocationToolCallResult,
    InvocationToolCallStart,
)
from chrys.foundation.models.invocations import InvocationOrigin
from chrys.service.tools.builtins.filesystem import EditFilePlan, plan_edit_file


@pytest.fixture(autouse=True)
def _clean_state():
    clear_call_registry()
    clear_settings_cache()
    subscriber.reset_for_tests()
    yield
    clear_call_registry()
    clear_settings_cache()
    subscriber.reset_for_tests()


def _origin() -> InvocationOrigin:
    return InvocationOrigin(kind="turn", session_id="sess-1", invocation_id="inv-7", parent=None)


def _write_start(
    call_id: str = "c1", *, tool_name: str = "write_file", args: dict | None = None
) -> InvocationToolCallStart:
    return InvocationToolCallStart(
        origin=_origin(),
        tool_name=tool_name,
        tool_kind="",
        args=dict(args if args is not None else {"path": "src/a.py", "content": "new"}),
        call_id=call_id,
        session_id="sess-1",
    )


def _write_result(
    call_id: str = "c1",
    *,
    tool_name: str = "write_file",
    before: str | None = None,
    after: str = "hello\nworld",
    errored: bool = False,
) -> InvocationToolCallResult:
    # 真链路 file_snapshot 是 tuple(before, after)（pipeline.py:89）。
    snapshot = (before if before is not None else "", after)
    metadata: dict[str, Any] = {"file_snapshot": snapshot}
    if errored:
        metadata["errored"] = True
    return InvocationToolCallResult(
        origin=_origin(),
        tool_name=tool_name,
        call_id=call_id,
        result="ok",
        duration_ms=50,
        session_id="sess-1",
        metadata=metadata,
    )


class _CaptureAdd:
    def __init__(self) -> None:
        self.payloads: list[dict[str, Any]] = []

    def __call__(self, payload: dict[str, object]) -> None:
        self.payloads.append(dict(payload))


# -- blocks 计算 ---------------------------------------------------------------


def test_blocks_new_file():
    blocks = ai_code_blocks(None, "a\nb\nc")
    assert blocks == [{"snippet": "a\nb\nc", "rangeStart": 1, "rangeEnd": 3}]


def test_blocks_edit_inserts_line_in_100_line_file():
    before = "\n".join(f"line {number}" for number in range(1, 101))
    after = before.replace("line 50", "line 50\ninserted", 1)
    blocks = ai_code_blocks(
        before,
        after,
        edit_args={"old_string": "line 50", "new_string": "line 50\ninserted"},
    )
    assert blocks == [{"snippet": "line 50\ninserted", "rangeStart": 50, "rangeEnd": 51}]


def test_blocks_match_real_edit_file_plan(tmp_path):
    path = tmp_path / "example.py"
    path.write_text("first\nold\nlast\n", encoding="utf-8")
    plan = plan_edit_file(str(path), "old", "new")
    assert isinstance(plan, EditFilePlan)
    blocks = ai_code_blocks(
        plan.before_text,
        plan.after_text,
        edit_args={"old_string": "old", "new_string": "new"},
    )
    assert blocks == [{"snippet": "new", "rangeStart": 2, "rangeEnd": 2}]


def test_blocks_replace_all_uses_each_tool_fragment():
    before = "head\nold\nmiddle\nold\ntail"
    after = before.replace("old", "new\nline")
    blocks = ai_code_blocks(
        before,
        after,
        edit_args={"old_string": "old", "new_string": "new\nline", "replace_all": True},
    )
    assert blocks == [
        {"snippet": "new\nline", "rangeStart": 2, "rangeEnd": 3},
        {"snippet": "new\nline", "rangeStart": 5, "rangeEnd": 6},
    ]


def test_blocks_edit_crlf_and_trailing_newline():
    before = "first\r\nold\r\nlast\r\n"
    after = "first\r\nnew\r\nlast\r\n"
    blocks = ai_code_blocks(before, after, edit_args={"old_string": "old", "new_string": "new"})
    assert blocks == [{"snippet": "new", "rangeStart": 2, "rangeEnd": 2}]
    assert ai_code_blocks(None, after)[0]["rangeEnd"] == 3
    assert ai_code_blocks(None, after)[0]["snippet"] == after


def test_blocks_ambiguous_fallback_reports_whole_file():
    blocks = ai_code_blocks("old", "same\nsame", edit_args={"old_string": "old", "new_string": "same"})
    assert blocks == [{"snippet": "same\nsame", "rangeStart": 1, "rangeEnd": 2}]


def test_blocks_deletion_only_has_no_generated_code():
    assert ai_code_blocks("keep\nremove", "keep\n", edit_args={"old_string": "remove", "new_string": ""}) == []


def test_blocks_empty_after():
    assert ai_code_blocks("x", "") == []


def test_language_from_path_uses_reference_extension_mapping():
    assert language_from_path("src/Module.TSX") == "typescript"
    assert language_from_path("src/component.vue") == "vue"
    assert language_from_path("script.sh") == "shell"
    assert language_from_path("README") is None


# -- codeStatus 采纳语义 --------------------------------------------------------


def _tracker_with(*, mode: str, approved: bool) -> ApprovalTracker:
    tracker = ApprovalTracker()
    tracker.on_mode_updated(SimpleNamespace(session_id="sess-1", mode=mode))
    tracker.on_request(SimpleNamespace(session_id="sess-1", request_id="r1", call_id="c1"))
    tracker.on_response(SimpleNamespace(request_id="r1", approved=approved))
    return tracker


def test_adopted_no_approval_is_success():
    tracker = ApprovalTracker()
    assert tracker.adopted_code_status("c1", "sess-1", rejected=False) == CodeStatus.SUCCESS


def test_adopted_manual_approval_maps_to_five():
    assert (
        _tracker_with(mode="manual", approved=True).adopted_code_status("c1", "sess-1", rejected=False)
        == CodeStatus.USER_APPROVED
    )


def test_adopted_auto_judge_maps_to_one():
    assert (
        _tracker_with(mode="auto", approved=True).adopted_code_status("c1", "sess-1", rejected=False)
        == CodeStatus.SUCCESS
    )


def test_adopted_rejected_maps_to_four():
    assert (
        _tracker_with(mode="manual", approved=True).adopted_code_status("c1", "sess-1", rejected=True)
        == CodeStatus.USER_REJECTED
    )


# -- reporter -------------------------------------------------------------------


def test_reporter_write_success_emits_payload():
    add = _CaptureAdd()
    reporter = AiCodeReporter(add)
    reporter.on_start(_write_start())
    reporter.on_result(_write_result(before=None, after="hello\nworld"), code_status=5, errored=False)

    assert len(add.payloads) == 1
    payload = add.payloads[0]
    assert payload["filepath"] == "src/a.py"
    assert payload["sourceType"] == "edit"
    assert payload["inputMethod"] == "ai_generated"
    assert payload["language"] == "python"
    assert payload["codeStatus"] == 5
    # spanId 语义修正（2026-10-09）：来自 registry 根 span，无记录时不带
    # （原 invocation_id 退出报文——与 tool-detail 同款修正）。
    assert "spanId" not in payload
    assert payload["blocks"] == [{"snippet": "hello\nworld", "rangeStart": 1, "rangeEnd": 2}]
    assert payload["reportId"]
    assert payload["pluginVersion"]
    assert payload["projectName"]


def test_reporter_edit_uses_tool_arguments_for_block_range():
    before = "first\nold\nlast"
    after = "first\nnew\nlast"
    add = _CaptureAdd()
    reporter = AiCodeReporter(add)
    reporter.on_start(
        _write_start(tool_name="edit_file", args={"path": "src/a.py", "old_string": "old", "new_string": "new"})
    )
    reporter.on_result(_write_result(tool_name="edit_file", before=before, after=after), code_status=1, errored=False)
    assert add.payloads[0]["blocks"] == [{"snippet": "new", "rangeStart": 2, "rangeEnd": 2}]


def test_reporter_skips_errored_and_non_write_tools():
    add = _CaptureAdd()
    reporter = AiCodeReporter(add)
    reporter.on_start(_write_start())
    reporter.on_result(_write_result(errored=True), code_status=2, errored=True)
    assert add.payloads == []

    reporter.on_start(_write_start(call_id="c2", tool_name="read_file"))
    reporter.on_result(_write_result(call_id="c2"), code_status=1, errored=False)
    assert add.payloads == []


def test_reporter_missing_path_skips():
    add = _CaptureAdd()
    reporter = AiCodeReporter(add)
    reporter.on_start(_write_start(args={}))
    reporter.on_result(_write_result(), code_status=1, errored=False)
    assert add.payloads == []


# -- subscriber 端到端 -----------------------------------------------------------


async def _publish_approval_flow(bus: EventBus, *, mode: str) -> None:
    await bus.publish(ApprovalModeUpdated(mode=mode, session_id="sess-1"))
    await bus.publish(ApprovalRequest(request_id="r1", call_id="c1", tool_name="write_file", session_id="sess-1"))
    await bus.publish(ApprovalResponse(request_id="r1", approved=True, session_id="sess-1"))


async def test_subscriber_ai_code_manual_approval_end_to_end():
    bus = EventBus()
    add = _CaptureAdd()
    subscriber._ai_code = AiCodeReporter(add)  # 注入测试替身
    subscriber.attach(bus)
    await asyncio_sleep_zero()

    await _publish_approval_flow(bus, mode="manual")
    await bus.publish(_write_start())
    await bus.publish(_write_result())

    assert len(add.payloads) == 1
    assert add.payloads[0]["codeStatus"] == CodeStatus.USER_APPROVED


async def test_subscriber_ai_code_auto_judge_end_to_end():
    bus = EventBus()
    add = _CaptureAdd()
    subscriber._ai_code = AiCodeReporter(add)  # 注入测试替身
    subscriber.attach(bus)
    await asyncio_sleep_zero()

    await _publish_approval_flow(bus, mode="auto")
    await bus.publish(_write_start())
    await bus.publish(_write_result())

    assert len(add.payloads) == 1
    assert add.payloads[0]["codeStatus"] == CodeStatus.SUCCESS


async def asyncio_sleep_zero() -> None:
    import asyncio

    await asyncio.sleep(0)
