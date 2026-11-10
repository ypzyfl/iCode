# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Behavior-anchor tests for the keyless-tolerant OpenAI SDK client.

The wire-level test drives the production construction path
(``_build_openai_sdk_client`` with no profile key and no env key) over
``httpx.MockTransport`` so the SDK's own header merge and validation run for
real — never mocked (DEVELOPMENT.md §5).
"""

from __future__ import annotations

from typing import Any

import pytest


async def test_keyless_client_sends_unauthenticated_request_on_purpose(monkeypatch: pytest.MonkeyPatch) -> None:
    """A client built with no key anywhere sends its request without Authorization.

    The SDK's per-request header validation refuses a bearer request
    carrying neither the header nor an explicit omission, so the keyless
    build skips the check: the request reaches the wire instead of raising
    locally, and it carries no Authorization header.
    """
    import httpx

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    seen: dict[str, Any] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["authorization"] = request.headers.get("Authorization")
        return httpx.Response(
            200,
            json={
                "id": "cmpl-1",
                "object": "chat.completion",
                "created": 0,
                "model": "gpt-test",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "ok"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
        )

    from chrys.service.llm.clients import _build_openai_sdk_client

    client = _build_openai_sdk_client(
        api_key="",
        base_url="http://llm.test/v1",
        timeout=5.0,
        max_retries=0,
        default_headers=None,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    try:
        await client.chat.completions.create(
            model="gpt-test",
            messages=[{"role": "user", "content": "hi"}],
        )
    finally:
        await client.close()

    assert seen["authorization"] is None


async def test_keyed_client_keeps_the_stock_validation() -> None:
    """A client with a static key keeps the stock header validation intact.

    The exemption is scoped to the credential-free build only: a keyed
    client must not lose the SDK's credential check.
    """
    from chrys.service.llm.clients import _empty_openai_api_key_provider
    from chrys.service.llm.sdk_openai import RetryGuardedAsyncOpenAI

    keyed = RetryGuardedAsyncOpenAI(api_key="sk-test")
    keyless = RetryGuardedAsyncOpenAI(api_key=_empty_openai_api_key_provider)
    try:
        # Keyed: a request whose headers carry no Authorization is still refused.
        with pytest.raises(TypeError):
            keyed._validate_headers({}, {})
        # Keyless: the same request passes — unauthenticated on purpose.
        keyless._validate_headers({}, {})
    finally:
        await keyed.close()
        await keyless.close()
