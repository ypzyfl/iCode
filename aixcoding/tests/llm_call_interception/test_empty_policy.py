# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

from __future__ import annotations

import httpx
import pytest
from aixcoding.tests.llm_call_interception.support import ChunkStream

from chrys.service.aixcoding.llm_call_interception.hooks import build_http_hooks


async def test_request_fast_path_never_reads_or_copies(monkeypatch: pytest.MonkeyPatch) -> None:
    async def forbidden_read(self):
        raise AssertionError("empty policy must not read the request body")

    monkeypatch.setattr(httpx.Request, "aread", forbidden_read)
    hooks = build_http_hooks(provider="openai", model="model-test")
    request = httpx.Request("POST", "http://llm.test", content=b"unchanged")
    original_headers = request.headers

    await hooks["request"][0](request)

    assert request.headers is original_headers
    assert request.content == b"unchanged"


async def test_empty_hooks_leave_request_and_response_unchanged() -> None:
    hooks = build_http_hooks(provider="openai", model="model-test")
    request = httpx.Request("POST", "http://llm.test", content=b"unchanged")
    original_headers = request.headers
    await hooks["request"][0](request)
    assert request.headers is original_headers
    assert request.content == b"unchanged"


async def test_response_fast_path_preserves_stream_identity() -> None:
    hooks = build_http_hooks(provider="openai", model="model-test")
    request = httpx.Request("GET", "http://llm.test")
    stream = ChunkStream([b"unchanged"])
    response = httpx.Response(200, request=request, stream=stream)
    original_headers = response.headers
    await hooks["response"][0](response)
    assert response.stream is stream
    assert response.headers is original_headers
    await response.aclose()
    assert stream.close_count == 1
