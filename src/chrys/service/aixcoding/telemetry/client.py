# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Telemetry HTTP client: stdlib urllib, direct loopback, ordered POSTs.

The mock and the future real backend share this wire shape. ``mock passed``
never means ``real backend passed`` (intranet acceptance stays its own gate).
The base URL defaults to the single-port mock's local origin; override with
``AIXCODING_TELEMETRY_BASE_URL`` (the escape hatch mirrors the other mocks).
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

DEFAULT_BASE_URL = "http://127.0.0.1:15678"
_TIMEOUT_SECONDS = 5.0
#: One backoff retry on transient failures (transport errors, timeouts, 5xx,
#: 429) — safe because every save is idempotent (same key + same content
#: replays as 200, never duplicates). Definite rejections (4xx incl. 409)
#: are not retried: resending the same bytes cannot change the verdict.
_RETRY_BACKOFF_SECONDS = 0.5

LLM_SAVE_ROUTE = "/csas/telemetry/api/v1/llm-report/save"
TOOL_SAVE_ROUTE = "/csas/telemetry/api/v1/tool-detail/save"
AI_CODE_SAVE_ROUTE = "/csas/telemetry/api/v1/ai-code/save"

_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def telemetry_base_url() -> str:
    return os.environ.get("AIXCODING_TELEMETRY_BASE_URL") or DEFAULT_BASE_URL


def _post_once(route: str, payload: dict[str, Any]) -> tuple[int, str]:
    request = urllib.request.Request(  # noqa: S310 - fixed http base + constant routes
        telemetry_base_url() + route,
        data=json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with _OPENER.open(request, timeout=_TIMEOUT_SECONDS) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")
    except OSError as exc:
        return 0, f"transport: {exc}"


def _transient(status: int) -> bool:
    return status == 0 or status == 429 or status >= 500


def post_save(route: str, payload: dict[str, Any]) -> tuple[int, str]:
    """POST one DTO with one backoff retry on transient failures.

    Returns (status, body-text); never raises for HTTP or transport errors.
    """
    status, body = _post_once(route, payload)
    if _transient(status):
        time.sleep(_RETRY_BACKOFF_SECONDS)
        status, body = _post_once(route, payload)
    return status, body
