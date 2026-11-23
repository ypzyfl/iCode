# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Every Chat Completions request carries the gateway queue's ``request_id``.

The id is generated per request into ``extra_body`` (the OpenAI SDK merges
that over the top-level request body) and reused from a profile-provided
value when one is there. Blocking calls carry it too, and it is attached
even when the queue-cancel address cannot be derived from the base URL:
correlation never depended on the cancel endpoint, only the tracker does.
Wire-level checks run through ``scripted_openai`` so the asserted body is
the JSON the SDK actually sent.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import pytest
from openai.types.chat.chat_completion import ChatCompletion, Choice
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk
from openai.types.chat.chat_completion_chunk import Choice as ChunkChoice
from openai.types.chat.chat_completion_chunk import ChoiceDelta as ChunkChoiceDelta
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from tests.support.openai_chat_wire import scripted_openai

from chrys.kernel import Message, ResponseStream
from chrys.service.aixcoding.llm_queue import attach_queue_request_id, track_queue_request
from chrys.service.llm.chat_completions import ChatCompletionsClient

_REQUEST_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")


def _chunk(delta: ChunkChoiceDelta | None, *, finish_reason: str | None = None) -> ChatCompletionChunk:
    choice = ChunkChoice.model_construct(index=0, delta=delta, finish_reason=finish_reason)
    return ChatCompletionChunk.model_construct(
        id="chunk-1",
        object="chat.completion.chunk",
        created=1_717_171_717,
        model="glm-5.2",
        choices=[choice],
        usage=None,
    )


def _blocking_reply() -> ChatCompletion:
    return ChatCompletion(
        id="resp-1",
        object="chat.completion",
        created=1_717_171_717_123,
        model="glm-5.2",
        choices=[
            Choice(
                index=0,
                message=ChatCompletionMessage(role="assistant", content="hi"),
                finish_reason="stop",
            )
        ],
    )


async def _wire_request_body(*, stream: bool, **options: Any) -> dict[str, Any]:
    """The JSON body of one streamed or blocking completion through the production client."""
    reply: list[ChatCompletionChunk] | ChatCompletion = (
        [_chunk(ChunkChoiceDelta.model_construct(role="assistant"), finish_reason="stop")]
        if stream
        else _blocking_reply()
    )
    async with scripted_openai([reply]) as wire:
        client = ChatCompletionsClient(model="glm-5.2", sdk_client=wire.client)
        call = client._inner_get_response(messages=[Message("user", ["hi"])], options=options, stream=stream)
        if stream:
            assert isinstance(call, ResponseStream)
            await call.get_final_response()
        else:
            await call
        return wire.requests[0]


def test_attach_generates_one_request_id_into_extra_body() -> None:
    request: dict[str, Any] = {}

    request_id = attach_queue_request_id(request)

    assert request_id is not None
    assert request["extra_body"]["request_id"] == request_id
    assert _REQUEST_ID_PATTERN.fullmatch(request_id)


def test_attach_logs_request_id_to_main_and_detail_channels(caplog: pytest.LogCaptureFixture) -> None:
    main_logger = "chrys.service.aixcoding.llm_queue.queue_cancel"
    detail_logger = logging.getLogger("aixcoding.detail.llm_queue")
    caplog.set_level(logging.INFO, logger=main_logger)
    caplog.set_level(logging.INFO, logger=detail_logger.name)
    detail_logger.addHandler(caplog.handler)
    try:
        request_id = attach_queue_request_id({})
    finally:
        detail_logger.removeHandler(caplog.handler)

    for logger_name in (main_logger, detail_logger.name):
        messages = [record.getMessage() for record in caplog.records if record.name == logger_name]
        assert any(f"request_id={request_id}" in message for message in messages), logger_name


def test_attach_reuses_a_profile_provided_request_id() -> None:
    request: dict[str, Any] = {"extra_body": {"request_id": "profile-id"}}

    assert attach_queue_request_id(request) == "profile-id"
    assert request["extra_body"] == {"request_id": "profile-id"}


def test_attach_fails_closed_on_a_non_mapping_extra_body() -> None:
    request: dict[str, Any] = {"extra_body": "not-a-mapping"}  # type: ignore[assignment]

    assert attach_queue_request_id(request) is None
    assert request["extra_body"] == "not-a-mapping"


def test_tracker_armed_when_cancel_endpoint_derivable() -> None:
    request: dict[str, Any] = {}

    tracker = track_queue_request(
        request, model="glm-5.2", base_url="https://82.186.176.202:9098/api/v3", api_key="token"
    )

    assert tracker is not None
    assert tracker.request_id == request["extra_body"]["request_id"]


def test_tracker_disarmed_but_request_id_kept_when_cancel_endpoint_underivable() -> None:
    request: dict[str, Any] = {}

    tracker = track_queue_request(request, model="glm-5.2", base_url="localhost:9098", api_key="token")

    assert tracker is None
    assert _REQUEST_ID_PATTERN.fullmatch(request["extra_body"]["request_id"])


@pytest.mark.asyncio
async def test_stream_request_carries_generated_request_id() -> None:
    body = await _wire_request_body(stream=True)

    assert _REQUEST_ID_PATTERN.fullmatch(body["request_id"])


@pytest.mark.asyncio
async def test_blocking_request_carries_generated_request_id() -> None:
    body = await _wire_request_body(stream=False)

    assert _REQUEST_ID_PATTERN.fullmatch(body["request_id"])


@pytest.mark.asyncio
async def test_blocking_request_reuses_a_profile_provided_request_id() -> None:
    body = await _wire_request_body(stream=False, extra_body={"request_id": "profile-id"})

    assert body["request_id"] == "profile-id"
