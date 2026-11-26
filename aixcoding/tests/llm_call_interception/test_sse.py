# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

from __future__ import annotations

import asyncio

import httpx
import pytest
from aixcoding.tests.llm_call_interception.support import ChunkStream

from chrys.service.aixcoding.llm_call_interception import Block, HttpChange
from chrys.service.aixcoding.llm_call_interception.hooks import build_http_hooks
from chrys.service.aixcoding.llm_call_interception.interceptor import HttpStreamBlockError, set_http_policy

FIRST = 'data: {"text":"原original"}\r\n\r\n'.encode()
SECOND = b"data: [DONE]\n\n"
CR_FIRST = FIRST.replace(b"\r\n\r\n", b"\r\r")
CR_SECOND = SECOND.replace(b"\n\n", b"\r\r")


class EventMutation:
    def __init__(self) -> None:
        self.events = []

    async def before_sse_event(self, context, status_code, headers, event):
        self.events.append(event)
        return HttpChange(body=event.replace(b"original", b"modified"))


async def _collect(chunks: list[bytes], policy) -> tuple[list[bytes], ChunkStream]:
    set_http_policy(policy)
    stream = ChunkStream(chunks)

    async def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"Content-Type": "text/event-stream"}, stream=stream)

    hooks = build_http_hooks(provider="openai", model="model-test")
    async with (
        httpx.AsyncClient(transport=httpx.MockTransport(handle), event_hooks=hooks) as client,
        client.stream("GET", "http://llm.test") as response,
    ):
        received = [chunk async for chunk in response.aiter_raw()]
    return received, stream


class GatedStream(httpx.AsyncByteStream):
    def __init__(self) -> None:
        self.release = asyncio.Event()
        self.close_count = 0

    async def __aiter__(self):
        yield FIRST
        await self.release.wait()
        yield SECOND

    async def aclose(self) -> None:
        self.close_count += 1


async def _collect_gated(policy, content_type: str) -> tuple[list[bytes], GatedStream]:
    set_http_policy(policy)
    stream = GatedStream()

    async def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"Content-Type": content_type}, stream=stream)

    hooks = build_http_hooks(provider="openai", model="model-test")
    received = []
    first_received = asyncio.Event()
    async with (
        httpx.AsyncClient(transport=httpx.MockTransport(handle), event_hooks=hooks) as client,
        client.stream("GET", "http://llm.test") as response,
    ):

        async def consume():
            async for chunk in response.aiter_raw():
                received.append(chunk)
                first_received.set()

        task = asyncio.create_task(consume())
        try:
            await asyncio.wait_for(first_received.wait(), timeout=1)
        finally:
            stream.release.set()
            await task
    return received, stream


async def test_content_sniff_dispatches_mislabelled_sse_incrementally() -> None:
    policy = EventMutation()
    received, stream = await _collect_gated(policy, "application/json")
    assert received == [FIRST.replace(b"original", b"modified"), SECOND]
    assert policy.events == [FIRST, SECOND]
    assert stream.close_count == 1


async def test_handler_mismatch_logs_and_preserves_incremental_stream(caplog) -> None:
    class BodyOnly:
        def __init__(self) -> None:
            self.calls = 0

        async def before_response_body(self, context, status_code, headers, body):
            self.calls += 1

    policy = BodyOnly()
    received, stream = await _collect_gated(policy, "text/event-stream")
    assert received == [FIRST, SECOND]
    assert policy.calls == 0
    assert stream.close_count == 1
    assert sum("response_handler_mismatch" in record.getMessage() for record in caplog.records) == 1


@pytest.mark.parametrize(("first", "second"), [(FIRST, SECOND), (CR_FIRST, CR_SECOND)])
async def test_buffered_sse_events_are_processed(first: bytes, second: bytes) -> None:
    policy = EventMutation()
    set_http_policy(policy)
    original = first + second

    async def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=original, headers={"Content-Type": "application/json"})

    hooks = build_http_hooks(provider="openai", model="model-test")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle), event_hooks=hooks) as client:
        response = await client.get("http://llm.test")

    assert response.content == original.replace(b"original", b"modified")
    assert policy.events == [first, second]
    assert "Content-Length" not in response.headers


async def test_sniff_skips_bom_and_leading_whitespace_without_losing_bytes() -> None:
    policy = EventMutation()
    prefix = b"\xef\xbb\xbf \r\n\t"
    received, stream = await _collect([prefix + FIRST + SECOND], policy)
    assert b"".join(received) == (prefix + FIRST + SECOND).replace(b"original", b"modified")
    assert policy.events == [prefix + FIRST, SECOND]
    assert stream.close_count == 1


@pytest.mark.parametrize(
    "chunks",
    [
        [FIRST[:20], FIRST[20:25], FIRST[25:], SECOND],
        [FIRST + SECOND],
        [FIRST.replace(b"\r\n\r\n", b"\n\n"), SECOND],
    ],
)
async def test_split_and_coalesced_events_are_processed_as_complete_events(chunks: list[bytes]) -> None:
    policy = EventMutation()
    received, stream = await _collect(chunks, policy)
    assert len(policy.events) == 2
    assert all(event.endswith((b"\n\n", b"\r\n\r\n")) for event in policy.events)
    assert b"".join(received) == b"".join(chunks).replace(b"original", b"modified")
    assert stream.close_count == 1


@pytest.mark.parametrize(
    ("chunks", "events"),
    [
        ([CR_FIRST + CR_SECOND], [CR_FIRST, CR_SECOND]),
        ([CR_FIRST, CR_SECOND], [CR_FIRST, CR_SECOND]),
        ([CR_FIRST[:12], CR_FIRST[12:], CR_SECOND], [CR_FIRST, CR_SECOND]),
        ([FIRST[:-1], FIRST[-1:] + SECOND], [FIRST, SECOND]),
        ([FIRST[:-2], FIRST[-2:] + SECOND], [FIRST, SECOND]),
        ([b"data: a\r\r", b"\ndata: b\r\n\r\n"], [b"data: a\r\r\n", b"data: b\r\n\r\n"]),
    ],
)
async def test_event_boundaries_survive_chunk_splits(chunks: list[bytes], events: list[bytes]) -> None:
    policy = EventMutation()
    received, stream = await _collect(chunks, policy)
    assert policy.events == events
    assert b"".join(received) == b"".join(chunks).replace(b"original", b"modified")
    assert stream.close_count == 1


@pytest.mark.parametrize(
    "terminator", [b"\n\n", b"\r\n\r\n", b"\r\r", b"\r\n\r", b"\r\r\n", b"\r\n\n", b"\n\r\n", b"\n\r"]
)
async def test_blank_line_may_mix_line_endings(terminator: bytes) -> None:
    first = b"data: a" + terminator
    second = b"data: b" + terminator
    policy = EventMutation()
    received, stream = await _collect([first + second], policy)
    assert policy.events == [first, second]
    assert b"".join(received) == first + second
    assert stream.close_count == 1


@pytest.mark.parametrize("line_ending", [b"\n", b"\r\n", b"\r"])
async def test_multiline_event_stays_one_event_when_split(line_ending: bytes) -> None:
    event = b"event: x" + line_ending + b"data: y" + line_ending + line_ending
    policy = EventMutation()
    received, stream = await _collect([event[:9], event[9:]], policy)
    assert policy.events == [event]
    assert b"".join(received) == event
    assert stream.close_count == 1


class FailFirstEvent:
    def __init__(self) -> None:
        self.calls = 0

    async def before_sse_event(self, context, status_code, headers, event):
        self.calls += 1
        if self.calls == 1:
            raise ValueError("bad event")
        return HttpChange(body=event.replace(b"DONE", b"CHANGED"))


async def test_event_failure_passes_current_event_through_and_continues(caplog) -> None:
    policy = FailFirstEvent()
    received, stream = await _collect([FIRST + SECOND], policy)
    assert b"".join(received) == FIRST + SECOND.replace(b"DONE", b"CHANGED")
    assert policy.calls == 2
    assert "sse_event" in caplog.text
    assert stream.close_count == 1


class BlockSecondEvent:
    def __init__(self) -> None:
        self.calls = 0

    async def before_sse_event(self, context, status_code, headers, event):
        self.calls += 1
        if self.calls == 2:
            return Block("private block reason")
        return None


@pytest.mark.parametrize(("first", "second"), [(FIRST, SECOND), (CR_FIRST, CR_SECOND)])
async def test_event_block_stops_remaining_stream_without_replay(caplog, first: bytes, second: bytes) -> None:
    policy = BlockSecondEvent()
    set_http_policy(policy)
    stream = ChunkStream([first + second + first])

    async def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"Content-Type": "text/event-stream"}, stream=stream)

    hooks = build_http_hooks(provider="openai", model="model-test")
    received = []
    async with (
        httpx.AsyncClient(transport=httpx.MockTransport(handle), event_hooks=hooks) as client,
        client.stream("GET", "http://llm.test") as response,
    ):
        with pytest.raises(HttpStreamBlockError) as caught:
            async for chunk in response.aiter_raw():
                received.append(chunk)

    assert received == [first]
    assert policy.calls == 2
    assert stream.close_count == 1
    assert str(caught.value) == "AIxCoding blocked the model HTTP call."
    assert "private block reason" not in str(caught.value)
    assert "private block reason" in caplog.text


async def test_incomplete_trailing_event_is_forwarded_once_without_policy_call() -> None:
    policy = EventMutation()
    received, stream = await _collect([FIRST + b"data: incomplete"], policy)
    assert policy.events == [FIRST]
    assert b"".join(received) == FIRST.replace(b"original", b"modified") + b"data: incomplete"
    assert stream.close_count == 1


async def test_underlying_stream_error_is_not_swallowed() -> None:
    policy = EventMutation()
    set_http_policy(policy)
    stream = ChunkStream([FIRST], error=RuntimeError("network read failed"))

    async def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"Content-Type": "text/event-stream"}, stream=stream)

    hooks = build_http_hooks(provider="openai", model="model-test")
    async with (
        httpx.AsyncClient(transport=httpx.MockTransport(handle), event_hooks=hooks) as client,
        client.stream("GET", "http://llm.test") as response,
    ):
        with pytest.raises(RuntimeError, match="network read failed"):
            _ = [chunk async for chunk in response.aiter_raw()]
    assert stream.close_count == 1


async def test_early_close_closes_original_stream() -> None:
    set_http_policy(EventMutation())
    stream = ChunkStream([FIRST + SECOND])

    async def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"Content-Type": "text/event-stream"}, stream=stream)

    hooks = build_http_hooks(provider="openai", model="model-test")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle), event_hooks=hooks) as client:
        response = await client.send(httpx.Request("GET", "http://llm.test"), stream=True)
        iterator = response.aiter_raw()
        assert await anext(iterator) == FIRST.replace(b"original", b"modified")
        await response.aclose()
        await iterator.aclose()
    assert stream.close_count == 1


async def test_cancellation_is_not_contained_and_closes_original_stream() -> None:
    class StalledStream(httpx.AsyncByteStream):
        def __init__(self) -> None:
            self.close_count = 0

        async def __aiter__(self):
            yield FIRST
            await asyncio.Event().wait()

        async def aclose(self) -> None:
            self.close_count += 1

    policy = EventMutation()
    set_http_policy(policy)
    stream = StalledStream()

    async def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"Content-Type": "text/event-stream"}, stream=stream)

    hooks = build_http_hooks(provider="openai", model="model-test")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle), event_hooks=hooks) as client:
        response = await client.send(httpx.Request("GET", "http://llm.test"), stream=True)

        async def consume():
            return [chunk async for chunk in response.aiter_raw()]

        task = asyncio.create_task(consume())
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await response.aclose()
    assert policy.events == [FIRST]
    assert stream.close_count == 1


async def test_encoded_stream_passes_through() -> None:
    policy = EventMutation()
    set_http_policy(policy)
    stream = ChunkStream([b"encoded-chunk"])

    async def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Type": "text/event-stream", "Content-Encoding": "gzip"},
            stream=stream,
        )

    hooks = build_http_hooks(provider="openai", model="model-test")
    async with (
        httpx.AsyncClient(transport=httpx.MockTransport(handle), event_hooks=hooks) as client,
        client.stream("GET", "http://llm.test") as response,
    ):
        received = [chunk async for chunk in response.aiter_raw()]
    assert received == [b"encoded-chunk"]
    assert policy.events == []
    assert stream.close_count == 1


async def test_event_mutation_removes_stale_content_length() -> None:
    set_http_policy(EventMutation())
    original = FIRST + SECOND
    stream = ChunkStream([original])

    async def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Type": "text/event-stream", "Content-Length": str(len(original))},
            stream=stream,
        )

    hooks = build_http_hooks(provider="openai", model="model-test")
    async with (
        httpx.AsyncClient(transport=httpx.MockTransport(handle), event_hooks=hooks) as client,
        client.stream("GET", "http://llm.test") as response,
    ):
        assert response.headers["Content-Length"] == str(len(original))
        received = b"".join([chunk async for chunk in response.aiter_raw()])
        assert "Content-Length" not in response.headers
    assert received == original.replace(b"original", b"modified")


class UndecidedGateStream(httpx.AsyncByteStream):
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.close_count = 0

    async def __aiter__(self):
        yield b"da"
        self.started.set()
        await self.release.wait()

    async def aclose(self) -> None:
        self.close_count += 1
        self.release.set()


async def test_cancellation_during_sniff_closes_original_stream() -> None:
    policy = EventMutation()
    set_http_policy(policy)
    stream = UndecidedGateStream()

    async def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=stream)

    hooks = build_http_hooks(provider="openai", model="model-test")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle), event_hooks=hooks) as client:
        response = await client.send(httpx.Request("GET", "http://llm.test"), stream=True)
        task = asyncio.create_task(response.aiter_raw().__aiter__().__anext__())
        await stream.started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await response.aclose()
    assert policy.events == []
    assert stream.close_count == 1


async def test_underlying_error_during_sniff_closes_original_stream() -> None:
    policy = EventMutation()
    set_http_policy(policy)
    stream = ChunkStream([b"da"], error=RuntimeError("sniff network failed"))

    async def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=stream)

    hooks = build_http_hooks(provider="openai", model="model-test")
    async with (
        httpx.AsyncClient(transport=httpx.MockTransport(handle), event_hooks=hooks) as client,
        client.stream("GET", "http://llm.test") as response,
    ):
        with pytest.raises(RuntimeError, match="sniff network failed"):
            _ = [chunk async for chunk in response.aiter_raw()]
    assert policy.events == []
    assert stream.close_count == 1


async def test_early_close_during_sniff_closes_original_stream() -> None:
    policy = EventMutation()
    set_http_policy(policy)
    stream = UndecidedGateStream()

    async def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=stream)

    hooks = build_http_hooks(provider="openai", model="model-test")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle), event_hooks=hooks) as client:
        response = await client.send(httpx.Request("GET", "http://llm.test"), stream=True)
        task = asyncio.create_task(response.aiter_raw().__aiter__().__anext__())
        await stream.started.wait()
        await response.aclose()
        assert await task == b"da"
    assert policy.events == []
    assert stream.close_count == 1
