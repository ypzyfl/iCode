# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Exercise the engine, Responses SDK and enterprise sender with isolated HTTP."""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest
from aixcoding.tests.telemetry._engine import mock_provider_profile, run_tool_reports
from aixcoding.tests.telemetry._responses import Script, blocking, mcp_item, resp_message

from chrys.foundation.events.types import InvocationMessage
from chrys.orchestration.engine.run.bindings import TurnBindings
from chrys.service.profiles.models.schema import API_STYLE_CHAT_COMPLETIONS, API_STYLE_RESPONSES, ModelProfile


@pytest.fixture(autouse=True)
def enabled_telemetry(monkeypatch, isolated_config):
    monkeypatch.delenv("AIXCODING_TELEMETRY_DISABLED", raising=False)


def _payloads(requests):
    return [json.loads(request.content)["telemetry"] for request in requests]


async def _responses_turn(tmp_path, agent_engine, monkeypatch, *replies, stream):
    monkeypatch.setattr(TurnBindings, "_BACKOFF_SCHEDULE", (0,))
    model = mock_provider_profile(
        "openai", stream=stream, api_style=API_STYLE_RESPONSES, chat_options='{"store": true}'
    )
    retries = []
    requests, reports, terminal = await run_tool_reports(
        tmp_path, monkeypatch, agent_engine, list(replies), builtins=[], user_text="hello", model=model, retries=retries
    )
    answer = terminal.text if isinstance(terminal, InvocationMessage) else None
    return requests, reports, answer, retries


def _anthropic_reply(content, *, stream=False, stop="end_turn"):
    usage = {"input_tokens": 10, "output_tokens": 2}
    message = {
        "type": "message",
        "id": "msg_answer",
        "role": "assistant",
        "model": "test-model",
        "content": content,
        "stop_reason": stop,
        "stop_sequence": None,
        "usage": usage,
    }
    if not stream:
        return httpx.Response(200, json=message)
    events = []

    def emit(kind, **fields):
        events.append(f"event: {kind}\ndata: {json.dumps({'type': kind, **fields})}\n\n")

    emit("message_start", message={**message, "content": [], "stop_reason": None})
    for index, block in enumerate(content):
        kind = block["type"]
        if kind == "text":
            start = {"type": "text", "text": ""}
            deltas = [{"type": "text_delta", "text": block["text"]}]
        elif kind == "thinking":
            start = {"type": "thinking", "thinking": "", "signature": ""}
            deltas = [
                {"type": "thinking_delta", "thinking": block["thinking"]},
                {"type": "signature_delta", "signature": block["signature"]},
            ]
        else:
            start = {**block, "input": {}}
            deltas = [{"type": "input_json_delta", "partial_json": json.dumps(block["input"])}]
        emit("content_block_start", index=index, content_block=start)
        for delta in deltas:
            emit("content_block_delta", index=index, delta=delta)
        emit("content_block_stop", index=index)
    emit("message_delta", delta={"stop_reason": stop, "stop_sequence": None}, usage=usage)
    emit("message_stop")
    return httpx.Response(200, text="".join(events), headers={"content-type": "text/event-stream"})


def _completion(protocol, text):
    if protocol == "messages":
        return _anthropic_reply([{"type": "text", "text": text}])
    if protocol == "responses":
        reply = blocking(resp_message("msg_answer", text))
        return httpx.Response(200, content=reply.body, headers=dict(reply.headers))
    return httpx.Response(
        200,
        json={
            "id": "chatcmpl-answer",
            "object": "chat.completion",
            "created": 1,
            "model": "test-model",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
        },
    )


def _profile(protocol, *, stream=False, sdk_retries=0, read_timeout=300.0):
    return ModelProfile(
        id="telemetry-wire",
        name="Telemetry wire",
        provider="anthropic" if protocol == "messages" else "openai",
        api_style=API_STYLE_RESPONSES if protocol == "responses" else API_STYLE_CHAT_COMPLETIONS,
        model_id="test-model",
        base_url="https://provider.invalid",
        api_key="test-key",
        http_max_retries=sdk_retries,
        http_read_timeout=read_timeout,
        stream=stream,
    )


@pytest.mark.parametrize("protocol", ["completions", "responses", "messages"])
@pytest.mark.parametrize("lane", ["sdk", "wire", "blank", "connection"])
async def test_retry_request_identity_at_sdk_and_kernel_boundaries(tmp_path, agent_engine, monkeypatch, protocol, lane):
    monkeypatch.setattr(TurnBindings, "_BACKOFF_SCHEDULE", (0,))
    calls = 0

    async def respond(request):
        nonlocal calls
        calls += 1
        if calls == 1:
            if lane == "connection":
                raise httpx.ConnectError("Connection refused", request=request)
            if lane != "blank":
                return httpx.Response(429, json={"error": {"message": "rate limited"}}, headers={"retry-after-ms": "1"})
            return _completion(protocol, "")
        return _completion(protocol, "Done.")

    requests, reports, terminal = await run_tool_reports(
        tmp_path,
        monkeypatch,
        agent_engine,
        respond,
        builtins=[],
        user_text="Say done",
        model=_profile(protocol, sdk_retries=int(lane == "sdk")),
        max_transient_retries=1,
    )
    assert isinstance(terminal, InvocationMessage) and terminal.text == "Done."
    assert reports == []
    first_payload, second_payload = _payloads(requests)
    assert first_payload["sessionId"] == second_payload["sessionId"]
    assert first_payload["spanId"] == second_payload["spanId"]
    assert (first_payload["requestId"] == second_payload["requestId"]) == (lane == "sdk")


async def test_responses_recreate_generates_a_new_request_id(tmp_path, agent_engine, monkeypatch):
    failed = blocking(status="failed", error={"code": "server_error", "message": "The model failed."})
    requests, _, answer, _ = await _responses_turn(
        tmp_path, agent_engine, monkeypatch, failed, blocking(resp_message("msg_answer", "Done.")), stream=False
    )
    assert answer == "Done."
    assert [request.method for request in requests] == ["POST", "POST"]
    first, second = _payloads(requests)
    assert first["requestId"] != second["requestId"]
    assert first["spanId"] == second["spanId"]


async def test_responses_never_replays_a_request_after_answer_text_was_shown(tmp_path, agent_engine, monkeypatch):
    cut = Script().started().text(0, "msg_partial", "Partial answer.").reply()
    requests, _, answer, retries = await _responses_turn(tmp_path, agent_engine, monkeypatch, cut, stream=True)
    assert [request.method for request in requests] == ["POST"]
    assert _payloads(requests)[0]["requestId"]
    assert answer is None
    assert retries == []


@pytest.mark.parametrize("stream", [False, True])
async def test_anthropic_overflow_and_thinking_resends_use_their_own_boundaries(monkeypatch, stream):
    from chrys.kernel import Message, StallExhaustedAction, tool
    from chrys.orchestration.invoker.attempts import WireRecipe
    from chrys.service.llm import clients
    from chrys.service.profiles.models.options import effective_chat_options

    def rejection(message):
        return httpx.Response(
            400, json={"type": "error", "error": {"type": "invalid_request_error", "message": message}}
        )

    refusal = (
        "messages.1.content.2: Invalid `signature` in `thinking` block. The block is bound to a different "
        "conversation. Remove the block, or set `thinking.block_binding.prefix_mismatch_behavior` to `drop_block`."
    )
    replies = iter(
        [
            _anthropic_reply(
                [
                    {"type": "thinking", "thinking": "Let me look it up.", "signature": "sig-call"},
                    {"type": "tool_use", "id": "toolu_1", "name": "lookup", "input": {"city": "Paris"}},
                ],
                stream=stream,
                stop="tool_use",
            ),
            rejection(refusal),
            rejection("prompt is too long: 213462 tokens > 200000 maximum"),
            rejection(refusal),
            _anthropic_reply([{"type": "text", "text": "Done."}], stream=stream),
        ]
    )
    requests = []

    def respond(request):
        requests.append(request)
        return next(replies)

    class Overflow:
        async def __call__(self, messages, context=None):
            return False

        def note_context_overflow(self, exc=None):
            return True

    @tool
    async def lookup(city: str) -> str:
        """Look up the weather in a city."""
        return f"Sunny in {city}."

    async def no_delay(_seconds):
        return False

    async def on_retry(*_args):
        return None

    policy = WireRecipe(
        max_retries=0,
        stall_timeout_seconds=5,
        stall_max_retries=0,
        stall_exhausted_action=StallExhaustedAction.BLOCKING_FALLBACK,
        backoff_schedule=(0,),
        interrupted=lambda: False,
        interruptible_sleep=no_delay,
        publish_retry=on_retry,
        prepare_retry=None,
        hosted_commits_in_flight=None,
        answer_shown=None,
    ).build()
    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    monkeypatch.setattr(clients, "_build_profile_http_client", lambda *args, **kwargs: client)
    profile = _profile("messages")
    stack = await clients.create_client(profile, session_id="anthropic-telemetry")
    try:
        result = stack.get_response(
            [Message("user", ["What is the weather in Paris?"])],
            stream=stream,
            options={**(effective_chat_options(profile) or {}), "tools": [lookup]},
            compaction_strategy=Overflow(),
            client_kwargs={"wire_retry_policy": policy},
        )
        response = await (result.get_final_response() if stream else result)
    finally:
        await stack.aclose()
    assert response.text == "Done."
    tool_call, first, thinking_resend, overflow_resend, final = _payloads(requests)
    assert first["requestId"] == thinking_resend["requestId"]
    assert overflow_resend["requestId"] == final["requestId"]
    assert len({item["requestId"] for item in (tool_call, first, overflow_resend)}) == 3


async def test_stream_stall_fallback_starts_a_new_model_request(tmp_path, agent_engine, monkeypatch):
    class SilentStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            await asyncio.Event().wait()
            yield b""

    requests, _, terminal = await run_tool_reports(
        tmp_path,
        monkeypatch,
        agent_engine,
        [
            httpx.Response(200, stream=SilentStream(), headers={"content-type": "text/event-stream"}),
            _completion("completions", "Done."),
        ],
        builtins=[],
        user_text="Say done",
        model=_profile("completions", stream=True, read_timeout=0.1),
        max_transient_retries=0,
    )
    assert isinstance(terminal, InvocationMessage) and terminal.text == "Done."
    assert [json.loads(request.content)["stream"] for request in requests] == [True, False]
    first, second = _payloads(requests)
    assert first["requestId"] != second["requestId"]
    assert first["spanId"] == second["spanId"]


@pytest.mark.parametrize(
    ("poll", "stream", "failed"),
    [("", True, False), ("get-start", True, False), ("post-start", True, False), ("", False, False), ("", True, True)],
    ids=["post", "get-first-observation", "post-start-get-terminal", "blocking", "hosted-failure"],
)
async def test_hosted_reports_join_the_request_that_observed_the_tool(
    tmp_path, agent_engine, monkeypatch, poll, stream, failed
) -> None:
    hosted = mcp_item("mcp_1")
    if failed:
        hosted.update(output=None, error="Service failed.", status="failed")
    final = (
        Script()
        .started()
        .hosted(0, hosted)
        .text(1, "msg_1", "Sunny.")
        .finished(hosted, resp_message("msg_1", "Sunny."))
        .reply()
        if stream
        else blocking(hosted, resp_message("msg_1", "Sunny."))
    )
    replies = [final]
    if poll:
        cut = Script().started()
        if poll == "post-start":
            pending_item = {key: value for key, value in hosted.items() if key != "output"}
            cut.emit("response.output_item.added", output_index=0, item={**pending_item, "status": "in_progress"})
        replies.insert(0, cut.reply())
    requests, reports, answer, _ = await _responses_turn(tmp_path, agent_engine, monkeypatch, *replies, stream=stream)

    assert answer == "Sunny."
    payload = json.loads(requests[0].content)["telemetry"]
    assert payload["eventType"] == "llm"
    assert [path for path, _ in reports] == ["tool-detail/save", "tool-detail/update", "tool-detail/update"]
    save, pending, terminal = (body for _, body in reports)
    if poll:
        assert [req.method for req in requests] == ["POST", "GET"]
        assert requests[1].content == b""
    if poll == "get-start":
        assert save["requestId"] != payload["requestId"]
    else:
        assert save["requestId"] == payload["requestId"]
    assert save["funcId"] == pending["funcId"] == terminal["funcId"] == "mcp_1"
    assert [pending["codeStatus"], terminal["codeStatus"]] == [3, 2 if failed else 1]
    if failed:
        assert terminal["status"] == 0
        assert terminal["failureType"] == "error"
        assert "Service failed." in terminal["funcErrorMessage"]
