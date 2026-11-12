# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Attach enterprise fields to one model call and retain its source identity."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import NAMESPACE_DNS, uuid4, uuid5

from chrys import __version__
from chrys.foundation.trajectory.context import current_trajectory
from chrys.foundation.trajectory.envelope import ActorKind
from chrys.kernel import ChatMiddleware, ChatResponse, ResponseStream, in_internal_side_call
from chrys.kernel.aixcoding.telemetry.context import current_pass
from chrys.kernel.aixcoding.telemetry.provenance import remember_local_source
from chrys.service.aixcoding.telemetry.context import (
    ModelSource,
    collect_git_info,
    desktop_prompt,
    detect_channel,
    load_settings,
    remember_source,
)
from chrys.service.aixcoding.telemetry.events import record_main_source, report_desktop_usage

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from chrys.kernel import ChatContext
    from chrys.service.aixcoding.telemetry.context import GitInfo

logger = logging.getLogger("aixcoding.detail.telemetry")
_ROOT_NAMESPACE = uuid5(NAMESPACE_DNS, "chrys-aixcoding-telemetry")


@dataclass(frozen=True, slots=True)
class _BuildFacts:
    agent_name: str
    workspace_cwd: str


_build_facts: ContextVar[_BuildFacts | None] = ContextVar("aixcoding_telemetry_build", default=None)


def for_agent_build[**P, T](
    factory: Callable[P, Awaitable[T]], agent_name: str, workspace_cwd: str
) -> Callable[P, Awaitable[T]]:
    async def create(*args: P.args, **kwargs: P.kwargs) -> T:
        facts = None
        try:
            if load_settings().enabled:
                if workspace_cwd:
                    await asyncio.to_thread(collect_git_info, workspace_cwd)
                facts = _BuildFacts(agent_name, workspace_cwd)
        except Exception:
            logger.debug("Telemetry build context unavailable.")
        token = _build_facts.set(facts)
        try:
            return await factory(*args, **kwargs)
        finally:
            _build_facts.reset(token)

    return create


def build_middleware(session_id: str | None) -> list[ChatMiddleware] | None:
    if not session_id or not load_settings().enabled:
        return None
    return [TelemetryModelMiddleware(session_id, _build_facts.get())]


class TelemetryModelMiddleware(ChatMiddleware):
    def __init__(self, session_id: str, facts: _BuildFacts | None) -> None:
        self._session_id = session_id
        self._facts = facts

    async def process(self, context: ChatContext, call_next: Callable[[], Awaitable[None]]) -> None:
        trace = current_trajectory()
        side_call = in_internal_side_call() or (trace is not None and trace.actor.kind == ActorKind.SIDE_CALL)
        prompt = desktop_prompt.get()
        source = None
        try:
            cwd = self._facts.workspace_cwd if self._facts else ""
            git = await asyncio.to_thread(collect_git_info, cwd) if cwd else None
            source = self._prepare(context, side_call=side_call, git=git)
        except Exception:
            logger.debug("Model telemetry preparation failed.")
        await call_next()
        if source is None or side_call:
            return

        def record(response: ChatResponse) -> None:
            try:
                remember_local_source(response, source.request_id)
                if source.origin is not None and source.origin.kind == "turn":
                    record_main_source(source)
                if (
                    prompt is not None
                    and not prompt.closed
                    and prompt.session_id == source.session_id
                    and source.origin is not None
                    and source.origin.kind == "turn"
                ):
                    prompt.latest = source
            except Exception:
                logger.debug("Model telemetry response association failed.")

        result = context.result
        if isinstance(result, ResponseStream):
            result.with_result_hook(record)
        elif isinstance(result, ChatResponse):
            record(result)

    def _prepare(self, context: ChatContext, *, side_call: bool, git: GitInfo | None) -> ModelSource:
        facts = self._facts
        scope = current_pass()
        prompt = desktop_prompt.get()
        origin = scope.origin if scope is not None else None
        session_id = origin.session_id if origin is not None and origin.session_id else self._session_id
        if prompt is not None and (prompt.closed or prompt.session_id != session_id):
            prompt = None
        channel = prompt.channel if prompt is not None else detect_channel()
        trace = current_trajectory()
        turn_id = trace.turn_id if trace is not None else None
        source = ModelSource(
            request_id=str(uuid4()),
            session_id=session_id,
            span_id=str(uuid5(_ROOT_NAMESPACE, f"{session_id}:{turn_id}")) if turn_id else "",
            parent_span_id=str(uuid4()),
            channel=channel,
            agent_name=(prompt.runner_name or "")
            if prompt is not None and channel.type == "desktop"
            else (facts.agent_name if facts else ""),
            workspace_cwd=facts.workspace_cwd if facts else "",
            git=git,
            origin=origin,
            pass_id=scope.pass_id if scope is not None else "",
        )
        payload: dict[str, object] = {
            "requestId": source.request_id,
            "sessionId": session_id,
            "eventType": "llm",
            "eventSubType": "system" if side_call else "agent",
            "channelType": channel.type,
            "channelName": "icode",
            "pluginVersion": __version__,
        }
        if source.span_id:
            payload["spanId"] = source.span_id
        if channel.version:
            payload["channelVersion"] = channel.version
        if source.agent_name and channel.type != "desktop":
            payload["agentName"] = source.agent_name
        if source.workspace_cwd:
            from chrys.service.aixcoding.telemetry.context import common_fields

            shared = common_fields(source.workspace_cwd, channel=channel, git=source.git)
            payload["projectName"] = shared["projectName"]
            payload.update({key: value for key, value in shared.items() if key.startswith("git")})
        options = dict(context.options or {})
        extra = options.get("extra_body")
        options["extra_body"] = {**(extra if isinstance(extra, Mapping) else {}), "telemetry": payload}
        context.options = options
        if not side_call:
            remember_source(source)
            context.model_source_id = source.request_id
            if (
                prompt is not None
                and prompt.selected_agent
                and not prompt.usage_reported
                and origin is not None
                and origin.kind == "turn"
            ):
                prompt.usage_reported = report_desktop_usage(prompt.selected_agent, source)
        return source
