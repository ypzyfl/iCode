# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Keep existing engine reference hooks compatible without reporting usage."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chrys.orchestration.engine.state.active_session import ActiveSession


def record_skill_reference(name: str, session: ActiveSession) -> None:
    """References only guide input; actual load_skill execution reports usage.

    Keep this no-op entrypoint for existing upstream input hooks until those
    integration points can be retired in a separately approved upstream change.
    """
