# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Reporter: deliver one ReportBatch in contract order, best-effort.

Within a session the order is LLM → tool-detail → ai-code (N8 ordering). A
failed POST is recorded and delivery continues — the owner's record-level
idempotency (server-side replay tolerance) makes a later retry safe, and a
single transport failure must not drop the rest of the batch.
"""

from __future__ import annotations

import logging
from typing import Any

from chrys.service.aixcoding.telemetry import client
from chrys.service.aixcoding.telemetry.analyzer import ReportBatch

logger = logging.getLogger(__name__)


def deliver(batch: ReportBatch) -> list[str]:
    """Send every DTO; returns the list of failure descriptions (empty = ok)."""
    failures: list[str] = []
    plan: list[tuple[str, str, dict[str, Any]]] = [("llm", client.LLM_SAVE_ROUTE, payload) for payload in batch.llm]
    plan.extend(("tool", client.TOOL_SAVE_ROUTE, payload) for payload in batch.tools)
    plan.extend(("ai-code", client.AI_CODE_SAVE_ROUTE, payload) for payload in batch.ai_codes)
    for kind, route, payload in plan:
        status, body = client.post_save(route, payload)
        if status != 200:
            message = f"{kind}:{payload.get('requestId')}:{status}:{body[:120]}"
            failures.append(message)
            logger.warning("telemetry delivery failed: %s", message)
    return failures
