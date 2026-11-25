# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

from __future__ import annotations

import asyncio

import httpx
import pytest
from aixcoding.tests.llm_call_interception.support import ChunkStream

from chrys.service.aixcoding.llm_call_interception import HttpChange, interceptor
from chrys.service.aixcoding.llm_call_interception.hooks import build_http_hooks
from chrys.service.aixcoding.llm_call_interception.interceptor import set_http_policy

EVENT = b"data: original\n\n"


class BusinessError(Exception):
    pass


class StageResult:
    def __init__(self, stage: str, result=None, exception: Exception | None = None) -> None:
        self.stage = stage
        self.result = result
        self.exception = exception

    def __getattr__(self, name: str):
        if name != self.stage:
            raise AttributeError(name)

        async def invoke(*args):
            if self.exception is not None:
                raise self.exception
            return self.result

        return invoke


async def _run(policy, stage: str) -> tuple[bytes, bytes]:
    set_http_policy(policy)
    seen = []

    async def handle(request: httpx.Request) -> httpx.Response:
        seen.append(await request.aread())
        if stage == "before_sse_event":
            return httpx.Response(
                200,
                headers={"Content-Type": "text/event-stream"},
                stream=ChunkStream([EVENT]),
            )
        return httpx.Response(200, content=b"original-response")

    hooks = build_http_hooks(provider="openai", model="model-test")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle), event_hooks=hooks) as client:
        if stage == "before_sse_event":
            async with client.stream("POST", "http://llm.test", content=b"original-request") as response:
                body = b"".join([chunk async for chunk in response.aiter_raw()])
        else:
            response = await client.post("http://llm.test", content=b"original-request")
            body = response.content
    return seen[0], body


@pytest.mark.parametrize("stage", ["before_request", "before_response", "before_response_body", "before_sse_event"])
@pytest.mark.parametrize("exception", [ValueError("bad"), RuntimeError("bad"), BusinessError("custom")])
async def test_business_exceptions_fail_open_at_every_stage(stage: str, exception: Exception, caplog) -> None:
    request_body, response_body = await _run(StageResult(stage, exception=exception), stage)
    assert request_body == b"original-request"
    assert response_body == (EVENT if stage == "before_sse_event" else b"original-response")
    assert type(exception).__name__ in caplog.text


@pytest.mark.parametrize("stage", ["before_request", "before_response", "before_response_body", "before_sse_event"])
async def test_invalid_results_fail_open(stage: str, caplog) -> None:
    request_body, response_body = await _run(StageResult(stage, result=object()), stage)
    assert request_body == b"original-request"
    assert response_body == (EVENT if stage == "before_sse_event" else b"original-response")
    assert "TypeError" in caplog.text


@pytest.mark.parametrize("stage", ["before_request", "before_response", "before_response_body"])
async def test_mutation_application_failure_restores_original(stage: str, caplog) -> None:
    change = HttpChange(
        headers={"X-Invalid": object()},  # type: ignore[dict-item]
        body=None if stage == "before_response" else b"changed",
    )
    request_body, response_body = await _run(StageResult(stage, result=change), stage)
    assert request_body == b"original-request"
    assert response_body == b"original-response"
    assert "TypeError" in caplog.text


async def test_logging_failure_does_not_escape(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken_log(*args, **kwargs):
        raise RuntimeError("logger failed")

    monkeypatch.setattr(interceptor._detail_log, "warning", broken_log)
    request_body, response_body = await _run(
        StageResult("before_response_body", exception=RuntimeError("business failed")),
        "before_response_body",
    )
    assert request_body == b"original-request"
    assert response_body == b"original-response"


async def test_cancellation_is_not_contained() -> None:
    set_http_policy(StageResult("before_request", exception=asyncio.CancelledError()))
    hooks = build_http_hooks(provider="openai", model="model-test")
    request = httpx.Request("POST", "http://llm.test", content=b"original")
    with pytest.raises(asyncio.CancelledError):
        await hooks["request"][0](request)


@pytest.mark.parametrize("stage", ["before_request", "before_response", "before_response_body", "before_sse_event"])
async def test_detail_log_redacts_payload_and_credentials(stage: str, caplog) -> None:
    caplog.set_level("WARNING", logger="aixcoding.detail.llm_call_interception")
    secrets = (
        "synthetic-token-secret",
        "synthetic-prompt-secret",
        "synthetic-tool-argument-secret",
        "synthetic-response-secret",
    )
    exception = RuntimeError("business failed: " + " ".join(secrets))
    request_body, response_body = await _run(StageResult(stage, exception=exception), stage)

    assert request_body == b"original-request"
    assert response_body == (EVENT if stage == "before_sse_event" else b"original-response")
    assert "RuntimeError" in caplog.text
    assert "Traceback" in caplog.text
    assert "RedactedPolicyFailure: <redacted>" in caplog.text
    assert "business failed" not in caplog.text
    assert all(secret not in caplog.text for secret in secrets)
