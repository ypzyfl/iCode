# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Report a skill reference resolved by the engine."""

from __future__ import annotations

from typing import TYPE_CHECKING

from chrys.service.aixcoding.telemetry.events import report_skill_reference

if TYPE_CHECKING:
    from chrys.orchestration.engine.state.active_session import ActiveSession


def record_skill_reference(name: str, session: ActiveSession) -> None:
    if session.session_id:
        report_skill_reference(
            name,
            session.session_id,
            session.agent_profile.name if session.agent_profile is not None else "",
            session.workspace.primary_cwd if session.workspace is not None else "",
        )
