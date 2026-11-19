"""AIxCoding M1 experiments: Responses continuation and concurrent identity scopes."""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Callable, Mapping
from dataclasses import replace
from typing import Any
from uuid import UUID

import httpx
import pytest
from openai import AsyncOpenAI

from chrys.foundation.trajectory.context import (
    TRAJECTORY_EXCHANGE_KWARG,
    ExchangeTrace,
    TrajectoryContext,
    main_actor,
)
from chrys.foundation.trajectory.envelope import EventDraft
from chrys.foundation.trajectory.ids import new_analytics_id
from chrys.foundation.trajectory.writer import EmitResult
from chrys.foundation.util.chrys_headers import REQUEST_ATTEMPT_ID_HEADER
from chrys.kernel import Message
from chrys.service.llm.chat_completions.client import ChatCompletionsClient
from chrys.service.llm.clients import _build_profile_http_client
from chrys.service.llm.observer import WireCallObserver
from chrys.service.llm.openai_responses.client import ResponsesApiClient
from chrys.service.llm.request_tracking import REQUEST_ATTEMPT_ID_METADATA
from chrys.service.profiles.models.schema import ModelProfile


class _Sink:
    def __init__(self) -> None:
        self.drafts: list[EventDraft] = []
        self.fingerprint_key = b"k" * 32

    def _record(
        self,
        draft: EventDraft,
        payload_factory: Callable[[int], Mapping[str, Any]] | None,
    ) -> EmitResult:
        if payload_factory is not None:
            draft = replace(draft, payload=dict(payload_factory(len(self.drafts) + 1)))
        self.drafts.append(draft)
        return EmitResult.WRITTEN

    async def emit(
        self,
        draft: EventDraft,
        *,
        payload_factory: Callable[[int], Mapping[str, Any]] | None = None,
    ) -> EmitResult:
        return self._record(draft, payload_factory)

    def emit_blocking(
        self,
        draft: EventDraft,
        *,
        payload_factory: Callable[[int], Mapping[str, Any]] | None = None,
    ) -> EmitResult:
        return self._record(draft, payload_factory)

    def emit_soon(
        self,
        draft: EventDraft,
        *,
        payload_factory: Callable[[int], Mapping[str, Any]] | None = None,
    ) -> EmitResult:
        return self._record(draft, payload_factory)


def _trace(session_id: str) -> ExchangeTrace:
    context = TrajectoryContext(
        sink=_Sink(),
        session_id=session_id,
        actor=main_actor(session_id),
        turn_id=new_analytics_id(),
        run_operation_id=new_analytics_id(),
    )
    return ExchangeTrace(context.with_exchange(new_analytics_id()))


def _http(handler: Any) -> httpx.AsyncClient:
    profile = ModelProfile(id="telemetry-m1", name="M1", provider="openai", model_id="m1-model", api_key="test")
    return _build_profile_http_client(profile, httpx.Timeout(5), transport=httpx.MockTransport(handler))


def _external_uuid(raw: str) -> str:
    if re.fullmatch(r"[0-9a-f]{32}", raw) is None:
        raise ValueError("expected raw lowercase 32hex identity")
    return str(UUID(hex=raw))


def _response_payload(status: str, output: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "id": "resp_m1",
        "object": "response",
        "created_at": 1_700_000_000,
        "status": status,
        "model": "m1-model",
        "output": output or [],
        "parallel_tool_calls": True,
        "tool_choice": "auto",
        "tools": [],
        "error": None,
        "incomplete_details": None,
        "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
    }


def _completion(label: str) -> dict[str, Any]:
    return {
        "id": f"chatcmpl-{label}",
        "object": "chat.completion",
        "created": 1_700_000_000,
        "model": "m1-model",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": f"answer-{label}"},
                "finish_reason": "stop",
                "logprobs": None,
            }
        ],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }


@pytest.mark.asyncio
async def test_m1_responses_retrieve_attempt_is_the_success_identity() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "POST":
            payload = _response_payload("in_progress")
        else:
            assert request.method == "GET"
            assert request.url.path.endswith("/responses/resp_m1")
            payload = _response_payload(
                "completed",
                [
                    {
                        "type": "message",
                        "id": "msg_m1",
                        "role": "assistant",
                        "status": "completed",
                        "content": [{"type": "output_text", "text": "Done", "annotations": []}],
                    }
                ],
            )
        return httpx.Response(200, json=payload, request=request)

    http = _http(handler)
    client = ResponsesApiClient.from_sdk_client(
        AsyncOpenAI(api_key="test", http_client=http, max_retries=0),
        model="m1-model",
        observer=WireCallObserver(),
    )
    trace = _trace("12345678-1234-1234-1234-123456789abc")
    options: dict[str, Any] = {"background": True, "timeout": 0.1}
    try:
        pending = await client.get_response(
            [Message("user", ["Run"])],
            options=options,
            client_kwargs={TRAJECTORY_EXCHANGE_KWARG: trace},
        )
        token = pending.continuation_token
        assert token is not None
        options["continuation_token"] = token
        completed = await client.get_response(
            [Message("user", ["Run"])],
            options=options,
            client_kwargs={TRAJECTORY_EXCHANGE_KWARG: trace},
        )
    finally:
        await client.aclose()

    assert [request.method for request in requests] == ["POST", "GET"]
    create_raw = requests[0].headers[REQUEST_ATTEMPT_ID_HEADER]
    retrieve_raw = requests[1].headers[REQUEST_ATTEMPT_ID_HEADER]
    assert create_raw != retrieve_raw
    assert completed.continuation_token is None
    assert completed.additional_properties["request_attempt_id"] == retrieve_raw
    assert completed.messages[0].additional_properties[REQUEST_ATTEMPT_ID_METADATA] == retrieve_raw
    assert completed.messages[0].additional_properties[REQUEST_ATTEMPT_ID_METADATA] != create_raw

    original_success_records = [{"requestId": _external_uuid(retrieve_raw)}]
    turn_id = trace.context.turn_id
    assert turn_id is not None
    independent_llm_records = [
        {
            "schemaVersion": 1,
            "sessionId": trace.context.session_id,
            "eventType": "llm",
            "eventSubType": "success",
            "requestId": _external_uuid(retrieve_raw),
            "spanId": _external_uuid(turn_id),
        }
    ]
    assert original_success_records[0]["requestId"] == independent_llm_records[0]["requestId"]
    assert UUID(independent_llm_records[0]["requestId"]).hex == retrieve_raw


@pytest.mark.asyncio
async def test_m1_concurrent_chat_scopes_form_disjoint_identity_records() -> None:
    sent: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        label = body["messages"][-1]["content"]
        sent[label] = request.headers[REQUEST_ATTEMPT_ID_HEADER]
        return httpx.Response(200, json=_completion(label), request=request)

    http = _http(handler)
    client = ChatCompletionsClient.from_sdk_client(
        AsyncOpenAI(api_key="test", http_client=http, max_retries=0),
        model="m1-model",
        observer=WireCallObserver(),
    )
    traces = {
        label: _trace(f"12345678-1234-1234-1234-123456789ab{index}") for index, label in enumerate(("alpha", "beta"))
    }

    async def run(label: str) -> Any:
        return await client.get_response(
            [Message("user", [label])],
            client_kwargs={TRAJECTORY_EXCHANGE_KWARG: traces[label]},
        )

    try:
        responses = await asyncio.gather(*(run(label) for label in traces))
    finally:
        await client.aclose()

    assert len(sent) == 2
    assert len(set(sent.values())) == 2
    records: dict[str, dict[str, str]] = {}
    for label, response in zip(traces, responses, strict=True):
        trace = traces[label]
        raw = response.messages[0].additional_properties[REQUEST_ATTEMPT_ID_METADATA]
        assert raw == sent[label]
        assert response.additional_properties["request_attempt_id"] == raw
        turn_id = trace.context.turn_id
        assert turn_id is not None
        original = {"sessionId": trace.context.session_id, "requestId": _external_uuid(raw)}
        independent = {
            "sessionId": trace.context.session_id,
            "spanId": _external_uuid(turn_id),
            "requestId": _external_uuid(raw),
        }
        assert original["requestId"] == independent["requestId"]
        records[label] = independent

    assert records["alpha"]["sessionId"] != records["beta"]["sessionId"]
    assert records["alpha"]["spanId"] != records["beta"]["spanId"]
    assert records["alpha"]["requestId"] != records["beta"]["requestId"]
