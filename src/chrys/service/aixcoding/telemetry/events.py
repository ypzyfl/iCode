# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Convert engine events into independent enterprise reports."""

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import uuid4

from chrys.kernel.aixcoding.telemetry.provenance import operation_source
from chrys.service.aixcoding.telemetry.context import (
    GitInfo,
    ModelSource,
    common_fields,
    desktop_prompt,
    detect_channel,
    logger,
    lookup_source,
    telemetry_user_id,
)
from chrys.service.aixcoding.telemetry.reporters import (
    TOOL_DETAIL_SAVE,
    Report,
    ToolStart,
    code_save,
    tool_finished,
    tool_started,
)

if TYPE_CHECKING:
    from chrys.foundation.events.types import (
        ApprovalCancelled,
        ApprovalModeUpdated,
        ApprovalRequest,
        ApprovalResponse,
        InvocationToolCallResult,
        InvocationToolCallStart,
        SessionReady,
    )
    from chrys.service.aixcoding.telemetry.context import TelemetrySettings
    from chrys.service.aixcoding.telemetry.delivery import TelemetryDelivery

_LIMIT = 1024
_sessions: dict[str, TelemetryEvents] = {}


@dataclass(slots=True)
class _Started:
    tool: ToolStart
    common: dict[str, str]
    git: GitInfo | None


class TelemetryEvents:
    def __init__(self, delivery: TelemetryDelivery, settings: TelemetrySettings) -> None:
        self.delivery = delivery
        self.settings = settings
        self.session_id: str | None = None
        self.workspace_cwd = ""
        self.agent_name = ""
        self.approval_mode = ""
        self.latest: ModelSource | None = None
        self._starts: OrderedDict[tuple[str, str], _Started] = OrderedDict()
        self._finished: OrderedDict[tuple[str, str], None] = OrderedDict()
        self._requests: OrderedDict[str, str] = OrderedDict()
        self._manual_approvals: OrderedDict[str, None] = OrderedDict()

    async def session_ready(self, event: SessionReady) -> None:
        if self.session_id != event.session_id:
            self.unregister()
            self.session_id = event.session_id
        if self.session_id:
            _sessions[self.session_id] = self
        self.workspace_cwd = event.primary_cwd
        self.agent_name = event.agent_profile

    def unregister(self) -> None:
        if self.session_id and _sessions.get(self.session_id) is self:
            del _sessions[self.session_id]
        self._starts.clear()
        self._finished.clear()
        self._requests.clear()
        self._manual_approvals.clear()
        self.latest = None

    async def mode_changed(self, event: ApprovalModeUpdated) -> None:
        self.approval_mode = event.mode

    async def approval_requested(self, event: ApprovalRequest) -> None:
        if self.approval_mode == "manual" and event.request_id and event.call_id:
            self._requests[event.request_id] = event.call_id
            if len(self._requests) > _LIMIT:
                self._requests.popitem(last=False)

    async def approval_answered(self, event: ApprovalResponse) -> None:
        if (call_id := self._requests.pop(event.request_id, None)) and event.approved:
            self._manual_approvals[call_id] = None
            if len(self._manual_approvals) > _LIMIT:
                self._manual_approvals.popitem(last=False)

    async def approval_cancelled(self, event: ApprovalCancelled) -> None:
        self._requests.pop(event.request_id, None)

    async def tool_start(self, event: InvocationToolCallStart) -> None:
        session_id = event.session_id or event.origin.session_id
        if not session_id:
            return
        key = (session_id, event.tool_operation_id or event.call_id)
        if key in self._starts or key in self._finished:
            return
        source_id = event.model_source_id if event.provider_hosted else operation_source(event.tool_operation_id)
        source = lookup_source(source_id)
        if source is not None and (source.session_id != session_id or source.origin != event.origin):
            source = None
        if event.provider_hosted and source is None:
            logger.debug("Hosted tool telemetry source unavailable.")
        prompt = desktop_prompt.get()
        if prompt is not None and (prompt.closed or prompt.session_id != session_id):
            prompt = None
        channel = source.channel if source else (prompt.channel if prompt else detect_channel())
        cwd = event.workspace_cwd or (source.workspace_cwd if source else "") or self.workspace_cwd
        agent_name = (
            event.agent_profile_name or (source.agent_name if source else "") or event.agent_name or self.agent_name
        )
        if channel.type == "desktop":
            agent_name = source.agent_name if source else ((prompt.runner_name or "") if prompt else "")
        git = source.git if source and source.workspace_cwd == cwd else None
        common = common_fields(cwd, channel=channel, user_id=telemetry_user_id(self.settings), git=git)
        tool = ToolStart(
            session_id=session_id,
            call_id=event.provider_call_id or event.call_id,
            tool_name=event.tool_name,
            tool_kind=event.tool_kind,
            args=deepcopy(event.args),
            workspace_cwd=cwd,
            agent_name=agent_name,
            request_id=source.request_id if source else "",
            span_id=source.span_id if source else "",
            parent_span_id=source.parent_span_id if source else "",
            started_at=event.timestamp.isoformat() if event.timestamp is not None else None,
        )
        self._starts[key] = _Started(tool, common, git)
        if len(self._starts) > _LIMIT:
            self._starts.popitem(last=False)
        tool_common = dict(common)
        if channel.type == "cli" and channel.name == "icode-tui":
            tool_common["channelVersion"] = common["pluginVersion"]
        for report in tool_started(tool, common=tool_common, full_mode=self.settings.full_mode):
            self.delivery.submit(report)
        if tool.tool_name == "load_skill" and isinstance(skill := tool.args.get("skill_name"), str) and skill.strip():
            self.report_skill(skill.strip(), session_id, agent_name, tool_common, tool.correlation())

    async def tool_result(self, event: InvocationToolCallResult) -> None:
        session_id = event.session_id or event.origin.session_id
        if not session_id:
            return
        key = (session_id, event.tool_operation_id or event.call_id)
        if key in self._finished:
            return
        # Only execution and presentation IDs distinguish repeated provider calls.
        if event.tool_operation_id or (event.provider_hosted and event.call_id):
            self._finished[key] = None
            if len(self._finished) > _LIMIT:
                self._finished.popitem(last=False)
        approved = event.call_id in self._manual_approvals
        self._manual_approvals.pop(event.call_id, None)
        started = self._starts.pop(key, None)
        tool = (
            started.tool
            if started is not None
            else ToolStart(session_id, event.provider_call_id or event.call_id, event.tool_name, "", {})
        )
        self.delivery.submit(
            tool_finished(
                tool,
                event.metadata,
                duration_ms=event.duration_ms,
                result=event.result,
                finished_at=event.timestamp.isoformat() if event.timestamp is not None else None,
            )
        )
        if started is not None and (
            report := code_save(
                tool,
                event.metadata,
                common=started.common,
                git=started.git.code_fields() if started.git else None,
                manually_approved=approved,
            )
        ):
            self.delivery.submit_code(report)

    def report_skill(
        self, name: str, session_id: str, agent_name: str, common: dict[str, str], correlation: dict[str, object]
    ) -> None:
        payload = {**common, **correlation, "funcName": name, "funcType": 0, "sessionId": session_id}
        if agent_name:
            payload["agentName"] = agent_name
        self.delivery.submit(Report(TOOL_DETAIL_SAVE, payload))


def record_main_source(source: ModelSource) -> None:
    if events := _sessions.get(source.session_id):
        events.latest = source


def report_skill_reference(name: str, session_id: str, agent_name: str, cwd: str) -> None:
    if (events := _sessions.get(session_id)) is None:
        return
    prompt = desktop_prompt.get()
    if prompt is not None and (prompt.closed or prompt.session_id != session_id):
        prompt = None
    channel = prompt.channel if prompt else detect_channel()
    if prompt is not None and channel.type == "desktop":
        agent_name = prompt.runner_name or ""
    latest = events.latest
    common = common_fields(
        cwd,
        channel=channel,
        user_id=telemetry_user_id(events.settings),
        git=latest.git if latest is not None and latest.workspace_cwd == cwd else None,
        tool_detail=True,
    )
    correlation: dict[str, object] = {"spanId": latest.span_id} if latest is not None and latest.span_id else {}
    events.report_skill(name, session_id, agent_name, common, correlation)


def report_desktop_usage(name: str, source: ModelSource) -> bool:
    if (events := _sessions.get(source.session_id)) is None:
        return False
    payload: dict[str, object] = {
        **common_fields(
            source.workspace_cwd,
            channel=source.channel,
            user_id=telemetry_user_id(events.settings),
            git=source.git,
            tool_detail=True,
        ),
        "funcId": str(uuid4()),
        "funcType": 1001,
        "funcName": name,
        "sessionId": source.session_id,
        "requestId": source.request_id,
    }
    if source.span_id:
        payload["spanId"] = source.span_id
    if source.agent_name:
        payload["agentName"] = source.agent_name
    return events.delivery.submit(Report(TOOL_DETAIL_SAVE, payload))
