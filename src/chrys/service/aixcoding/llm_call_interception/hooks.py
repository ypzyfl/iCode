# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""HTTPX hooks with opt-in body processing and content-sniffed SSE streams."""

from __future__ import annotations

import re
from collections.abc import AsyncIterator, Mapping
from typing import Any

import httpx

from .context import Block, HttpCallContext, HttpChange
from .interceptor import get_http_policy, log_failure, log_passthrough, raise_http_block

# An event ends with a blank line: two line endings, each LF, CRLF or CR. The alternatives
# cannot overlap, so one CRLF never counts as two line endings.
_EVENT_BOUNDARY = re.compile(rb"(?:\r\n|\r(?!\n)|\n){2}")
_SNIFF_LIMIT = 512
_SNIFF_SKIPPED = b" \t\r\n\xef\xbb\xbf"
_DOCUMENT_LEADING_BYTES = b"{[<"


def build_http_hooks(*, provider: str, model: str) -> dict[str, list[Any]]:
    async def request_hook(request: httpx.Request) -> None:
        await _handle_request(request, provider=provider, model=model)

    async def response_hook(response: httpx.Response) -> None:
        await _handle_response(response, provider=provider, model=model)

    return {"request": [request_hook], "response": [response_hook]}


async def _handle_request(request: httpx.Request, *, provider: str, model: str) -> None:
    policy = get_http_policy()
    if policy is None:
        return
    context = HttpCallContext.from_request(request, provider=provider, model=model)
    try:
        handler = getattr(policy, "before_request", None)
        if handler is not None and not callable(handler):
            raise TypeError("before_request must be callable")
    except Exception:
        log_failure("request_setup", context)
        return
    if handler is None:
        return

    original_body = await request.aread()
    original_headers = httpx.Headers(request.headers)
    original_stream = request.stream
    try:
        result = await handler(context, httpx.Headers(request.headers), original_body)
        if result is None:
            return
        if isinstance(result, Block):
            _validate_block(result)
        else:
            _apply_request_change(request, _validate_change(result), original_body)
            return
    except Exception:
        request.headers = original_headers
        request._content = original_body
        request.stream = original_stream
        log_failure("request", context)
        return
    raise_http_block(context, result)


def _apply_request_change(request: httpx.Request, change: HttpChange, original_body: bytes) -> None:
    new_headers = httpx.Headers(change.headers) if change.headers is not None else httpx.Headers(request.headers)
    body = original_body if change.body is None else change.body
    if change.body is not None:
        new_headers["Content-Length"] = str(len(body))
    request.headers = new_headers
    request._content = body
    request.stream = httpx.ByteStream(body)


async def _handle_response(response: httpx.Response, *, provider: str, model: str) -> None:
    policy = get_http_policy()
    if policy is None:
        return
    context = HttpCallContext.from_request(response.request, provider=provider, model=model)
    try:
        header_handler = getattr(policy, "before_response", None)
        body_handler = getattr(policy, "before_response_body", None)
        event_handler = getattr(policy, "before_sse_event", None)
        for name, handler in (
            ("before_response", header_handler),
            ("before_response_body", body_handler),
            ("before_sse_event", event_handler),
        ):
            if handler is not None and not callable(handler):
                raise TypeError(f"{name} must be callable")
    except Exception:
        log_failure("response_setup", context)
        return

    if header_handler is not None:
        await _handle_response_headers(response, context, header_handler)
    if body_handler is None and event_handler is None:
        return

    encoding = response.headers.get("Content-Encoding", "identity").strip().lower()
    if encoding not in ("", "identity"):
        content_type = response.headers.get("Content-Type", "").partition(";")[0].strip().lower()
        log_passthrough("sse" if content_type == "text/event-stream" else "response_body", context)
        return

    if hasattr(response, "_content"):
        is_sse = _classify_prefix(response.content, eof=True) is True
        handler = event_handler if is_sse else body_handler
        if handler is None:
            _log_handler_mismatch(context, is_sse=is_sse)
        elif is_sse:
            await _handle_buffered_sse(response, context, handler)
        else:
            await _handle_buffered_body(response, context, handler)
        return
    if not isinstance(response.stream, httpx.AsyncByteStream):
        return

    original_stream = response.stream
    try:
        response.stream = _AdaptiveResponseStream(
            response, original_stream, context, body_handler=body_handler, event_handler=event_handler
        )
    except Exception:
        response.stream = original_stream
        log_failure("response_stream_setup", context)


async def _handle_response_headers(response: httpx.Response, context: HttpCallContext, handler: Any) -> None:
    original_headers = httpx.Headers(response.headers)
    try:
        result = await handler(context, response.status_code, httpx.Headers(response.headers))
        if result is None:
            return
        if isinstance(result, Block):
            _validate_block(result)
        else:
            change = _validate_change(result, allow_body=False)
            if change.headers is not None:
                response.headers = httpx.Headers(change.headers)
            return
    except Exception:
        response.headers = original_headers
        log_failure("response_headers", context)
        return
    raise_http_block(context, result)


async def _handle_buffered_body(response: httpx.Response, context: HttpCallContext, handler: Any) -> None:
    original_body = response.content
    original_headers = httpx.Headers(response.headers)
    try:
        result = await handler(context, response.status_code, httpx.Headers(response.headers), original_body)
        if result is None:
            return
        if isinstance(result, Block):
            _validate_block(result)
        else:
            _apply_response_change(response, _validate_change(result), original_body=original_body)
            return
    except Exception:
        response.headers = original_headers
        response._content = original_body
        log_failure("response_body", context)
        return
    raise_http_block(context, result)


async def _handle_buffered_sse(response: httpx.Response, context: HttpCallContext, handler: Any) -> None:
    original_body = response.content
    original_headers = httpx.Headers(response.headers)
    transformed = bytearray()
    cursor = 0
    for match in _EVENT_BOUNDARY.finditer(original_body):
        end = match.end()
        event = original_body[cursor:end]
        transformed.extend(await _process_sse_event(response, context, handler, event, stream=False))
        cursor = end
    transformed.extend(original_body[cursor:])
    if transformed == original_body:
        return
    try:
        response._content = bytes(transformed)
        response.headers.pop("Content-Length", None)
        response.__dict__.pop("_text", None)
    except Exception:
        response.headers = original_headers
        response._content = original_body
        log_failure("sse_event", context)


def _apply_response_change(response: httpx.Response, change: HttpChange, *, original_body: bytes | None) -> None:
    new_headers = httpx.Headers(change.headers) if change.headers is not None else httpx.Headers(response.headers)
    if change.body is not None:
        new_headers["Content-Length"] = str(len(change.body))
    response.headers = new_headers
    if change.body is not None and original_body is not None:
        response._content = change.body
        response.__dict__.pop("_text", None)


def _validate_block(result: Block) -> None:
    if not isinstance(result.reason, str):
        raise TypeError("Block.reason must be str")


def _validate_change(result: Any, *, allow_body: bool = True, allow_headers: bool = True) -> HttpChange:
    if not isinstance(result, HttpChange):
        raise TypeError("policy result must be None, HttpChange, or Block")
    if not allow_body and result.body is not None:
        raise TypeError("this stage cannot replace the body")
    if not allow_headers and result.headers is not None:
        raise TypeError("this stage cannot replace headers")
    if result.body is not None and not isinstance(result.body, bytes):
        raise TypeError("HttpChange.body must be bytes")
    if result.headers is not None and not isinstance(result.headers, Mapping):
        raise TypeError("HttpChange.headers must be a mapping")
    return result


def _classify_prefix(prefix: bytes | bytearray, *, eof: bool = False) -> bool | None:
    sample = prefix[:_SNIFF_LIMIT].lstrip(_SNIFF_SKIPPED)
    if not sample:
        return False if eof or len(prefix) >= _SNIFF_LIMIT else None
    if sample[0] in _DOCUMENT_LEADING_BYTES:
        return False
    if b":" in sample:
        return True
    if eof or len(prefix) >= _SNIFF_LIMIT:
        return False
    return None


def _log_handler_mismatch(context: HttpCallContext, *, is_sse: bool) -> None:
    log_passthrough(
        "response_handler_mismatch",
        context,
        reason=f"response_handler_mismatch:{'sse' if is_sse else 'normal'}",
    )


class _PrefixedStream(httpx.AsyncByteStream):
    def __init__(self, prefix: bytes, stream: httpx.AsyncByteStream, iterator: AsyncIterator[bytes]) -> None:
        self._prefix = prefix
        self._stream = stream
        self._iterator = iterator
        self._closed = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        if self._prefix:
            yield self._prefix
        async for chunk in self._iterator:
            yield chunk

    async def aclose(self) -> None:
        if not self._closed:
            self._closed = True
            await self._stream.aclose()


class _AdaptiveResponseStream(httpx.AsyncByteStream):
    def __init__(
        self,
        response: httpx.Response,
        stream: httpx.AsyncByteStream,
        context: HttpCallContext,
        *,
        body_handler: Any,
        event_handler: Any,
    ) -> None:
        self._response = response
        self._stream = stream
        self._context = context
        self._body_handler = body_handler
        self._event_handler = event_handler
        self._prefixed: _PrefixedStream | None = None
        self._closed = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        try:
            prefix, is_sse, iterator = await self._read_prefix()
            prefixed = _PrefixedStream(prefix, self._stream, iterator)
            self._prefixed = prefixed
            handler = self._event_handler if is_sse else self._body_handler
            if handler is None:
                _log_handler_mismatch(self._context, is_sse=is_sse)
                async for chunk in prefixed:
                    yield chunk
                return
            processor: httpx.AsyncByteStream
            if is_sse:
                processor = _SSEEventStream(self._response, prefixed, self._context, handler)
            else:
                processor = _NormalBodyStream(self._response, prefixed, self._context, handler)
            async for chunk in processor:
                yield chunk
        finally:
            await self.aclose()

    async def _read_prefix(self) -> tuple[bytes, bool, AsyncIterator[bytes]]:
        prefix = bytearray()
        iterator = self._stream.__aiter__()
        async for chunk in iterator:
            prefix.extend(chunk)
            verdict = _classify_prefix(prefix)
            if verdict is not None:
                return bytes(prefix), verdict, iterator
        return bytes(prefix), False, iterator

    async def aclose(self) -> None:
        if not self._closed:
            self._closed = True
            if self._prefixed is not None:
                await self._prefixed.aclose()
            else:
                await self._stream.aclose()


class _NormalBodyStream(httpx.AsyncByteStream):
    def __init__(self, response: httpx.Response, stream: httpx.AsyncByteStream, context: HttpCallContext, handler: Any):
        self._response = response
        self._stream = stream
        self._context = context
        self._handler = handler
        self._closed = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        try:
            chunks = [chunk async for chunk in self._stream]
            original_body = b"".join(chunks)
            original_headers = httpx.Headers(self._response.headers)
            try:
                result = await self._handler(
                    self._context,
                    self._response.status_code,
                    httpx.Headers(self._response.headers),
                    original_body,
                )
                if result is None:
                    yield original_body
                    return
                if isinstance(result, Block):
                    _validate_block(result)
                else:
                    change = _validate_change(result)
                    _apply_response_change(self._response, change, original_body=None)
                    yield original_body if change.body is None else change.body
                    return
            except Exception:
                self._response.headers = original_headers
                log_failure("response_body", self._context)
                yield original_body
                return
            raise_http_block(self._context, result)
        finally:
            await self.aclose()

    async def aclose(self) -> None:
        if not self._closed:
            self._closed = True
            await self._stream.aclose()


async def _process_sse_event(
    response: httpx.Response,
    context: HttpCallContext,
    handler: Any,
    event: bytes,
    *,
    stream: bool,
) -> bytes:
    try:
        result = await handler(context, response.status_code, httpx.Headers(response.headers), event)
    except Exception:
        log_failure("sse_event", context)
        return event
    if result is None:
        return event
    try:
        if isinstance(result, Block):
            _validate_block(result)
        else:
            change = _validate_change(result, allow_headers=False)
            if change.body is not None:
                response.headers.pop("Content-Length", None)
            return event if change.body is None else change.body
    except Exception:
        log_failure("sse_event", context)
        return event
    return raise_http_block(context, result, stream=stream)


class _SSEEventStream(httpx.AsyncByteStream):
    def __init__(self, response: httpx.Response, stream: httpx.AsyncByteStream, context: HttpCallContext, handler: Any):
        self._response = response
        self._stream = stream
        self._context = context
        self._handler = handler
        self._closed = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        buffer = bytearray()
        try:
            async for chunk in self._stream:
                buffer.extend(chunk)
                async for event in self._take_events(buffer, final=False):
                    yield event
            async for event in self._take_events(buffer, final=True):
                yield event
            if buffer:
                yield bytes(buffer)
        finally:
            await self.aclose()

    async def _take_events(self, buffer: bytearray, *, final: bool) -> AsyncIterator[bytes]:
        while (match := _EVENT_BOUNDARY.search(buffer)) is not None:
            # A CR that ends the buffered bytes may be the first half of a CRLF the next chunk completes.
            if not final and match.end() == len(buffer) and buffer[-1:] == b"\r":
                return
            end = match.end()
            event = bytes(buffer[:end])
            del buffer[:end]
            yield await _process_sse_event(self._response, self._context, self._handler, event, stream=True)

    async def aclose(self) -> None:
        if not self._closed:
            self._closed = True
            await self._stream.aclose()
