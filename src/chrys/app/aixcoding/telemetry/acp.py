# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Validate desktop ACP envelopes and scope them to one prompt."""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
from typing import TYPE_CHECKING
from uuid import UUID

from chrys.service.aixcoding.telemetry.context import Channel, DesktopPrompt, desktop_prompt, detect_channel

if TYPE_CHECKING:
    from collections.abc import Generator


def _field(metadata: Mapping[str, object], envelope: str, key: str) -> str | None:
    value = metadata.get(f"agent-studio.dev/{envelope}")
    if not isinstance(value, Mapping) or value.get("schemaVersion") != 1:
        return None
    field = value.get(key)
    if not isinstance(field, str) or not field or len(field) > 512:
        return None
    return None if any(ord(char) < 32 or ord(char) == 127 for char in field) else field


@contextmanager
def prompt_scope(session_id: str, metadata: Mapping[str, object]) -> Generator[DesktopPrompt]:
    ide = _field(metadata, "ide-name", "ideName")
    channel = Channel("desktop", ide, _field(metadata, "ide-version", "ideVersion")) if ide else detect_channel()
    market_id = _field(metadata, "selected-agent", "agentMarketSkillId")
    attribution = _field(metadata, "response-attribution", "spanId")
    if attribution:
        try:
            UUID(attribution)
        except ValueError:
            attribution = None
    prompt = DesktopPrompt(
        session_id,
        channel,
        _field(metadata, "function-name", "functionName"),
        _field(metadata, "selected-agent", "agentName") if ide and market_id else None,
        attribution,
    )
    token = desktop_prompt.set(prompt)
    try:
        yield prompt
    finally:
        prompt.closed = True
        desktop_prompt.reset(token)
