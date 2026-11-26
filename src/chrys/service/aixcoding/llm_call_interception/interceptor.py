# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Process-local policy holder, safe detail logging and non-retry block errors."""

from __future__ import annotations

import logging
import sys
import traceback
from contextlib import suppress
from functools import lru_cache
from typing import TYPE_CHECKING, NoReturn, Protocol

if TYPE_CHECKING:
    import httpx

    from .context import Block, HttpCallContext, HttpChange

_PUBLIC_BLOCK_MESSAGE = "AIxCoding blocked the model HTTP call."
_public_log = logging.getLogger("aixcoding.llm_call_interception")
_detail_log = logging.getLogger("aixcoding.detail.llm_call_interception")
_policy: HttpPolicy | None = None


class HttpPolicy(Protocol):
    """Optional async callbacks; normal documents use body and SSE uses event callbacks.

    The protocol declares all four stages, so only a policy that defines every stage satisfies
    its type; a policy that leaves stages out still works, and those stages are not run.

    ``before_sse_event`` gets one complete event, ending with the blank line that terminates
    it (two line endings, each LF, CRLF or CR); a replacement body must keep that terminator
    or it will stick to the next event.

    ``headers`` is an ``httpx.Headers`` mapping with lower-case keys. Replace an existing
    header by assigning it on an ``httpx.Headers`` copy: adding a differently cased key to a
    ``dict`` sends that header twice. Response body and SSE callbacks only run on identity
    responses, so a policy that must read or rewrite a response body negotiates
    ``Accept-Encoding: identity`` in ``before_request``.
    """

    async def before_request(
        self, context: HttpCallContext, headers: httpx.Headers, body: bytes
    ) -> HttpChange | Block | None: ...

    async def before_response(
        self, context: HttpCallContext, status_code: int, headers: httpx.Headers
    ) -> HttpChange | Block | None: ...

    async def before_response_body(
        self, context: HttpCallContext, status_code: int, headers: httpx.Headers, body: bytes
    ) -> HttpChange | Block | None: ...

    async def before_sse_event(
        self, context: HttpCallContext, status_code: int, headers: httpx.Headers, event: bytes
    ) -> HttpChange | Block | None: ...


class HttpStreamBlockError(Exception):
    """A deliberate block raised after the SDK request retry loop has exited."""


def set_http_policy(policy: HttpPolicy | None) -> None:
    """Replace the policy; registering a non-empty policy installs the factory wrapper once."""

    global _policy
    if policy is not None:
        _ensure_factory_wrapped()
    _policy = policy


def _ensure_factory_wrapped() -> None:
    try:
        from .installer import install_http_interception

        install_http_interception()
    except Exception:
        report_install_failure()


def report_install_failure() -> None:
    """Fail open with public WARNING and sanitized detail; registration and the host continue."""

    exc = sys.exc_info()[1]
    message = f"HTTP interception installation failed ({type(exc).__name__}); continuing without hooks."
    with suppress(Exception):
        _public_log.warning("%s", message)
    log_failure("registration_install")


def get_http_policy() -> HttpPolicy | None:
    return _policy


def _safe_stack(exc: BaseException | None) -> str | None:
    if exc is None or exc.__traceback__ is None:
        return None
    frames = traceback.extract_tb(exc.__traceback__)
    locations = "".join(f'  File "{frame.filename}", line {frame.lineno}, in {frame.name}\n' for frame in frames)
    return f"Traceback (most recent call last):\n{locations}RedactedPolicyFailure: <redacted>"


def log_failure(
    stage: str,
    context: HttpCallContext | None = None,
    *,
    provider: str | None = None,
    model: str | None = None,
) -> None:
    """Keep stack frames and the original type, but redact exception text."""

    exc = sys.exc_info()[1]
    with suppress(Exception):
        _detail_log.warning(
            "HTTP policy failure; stage=%s provider=%s model=%s session=%s turn=%s cycle=%s exchange=%s "
            "attempt=%s actor=%s error=%s\n%s",
            stage,
            context.provider if context is not None else provider,
            context.model if context is not None else model,
            context.session_id if context is not None else None,
            context.turn_id if context is not None else None,
            context.cycle_operation_id if context is not None else None,
            context.exchange_operation_id if context is not None else None,
            context.request_attempt_id if context is not None else None,
            context.actor.role if context is not None and context.actor is not None else None,
            type(exc).__name__ if exc is not None else None,
            _safe_stack(exc),
        )


def report_client_install_failure(provider: str, model: str) -> None:
    """Fail open with public WARNING and sanitized detail evidence."""

    exc = sys.exc_info()[1]
    message = f"HTTP interception installation failed ({type(exc).__name__}); continuing without hooks."
    with suppress(Exception):
        _public_log.warning("%s provider=%s model=%s", message, provider, model)
    log_failure("client_install", provider=provider, model=model)


def log_passthrough(stage: str, context: HttpCallContext, *, reason: str = "unsupported_content_encoding") -> None:
    with suppress(Exception):
        _detail_log.warning(
            "HTTP policy passthrough; stage=%s provider=%s model=%s attempt=%s reason=%s",
            stage,
            context.provider,
            context.model,
            context.request_attempt_id,
            reason,
        )


def raise_http_block(context: HttpCallContext, block: Block, *, stream: bool = False) -> NoReturn:
    """Raise a fixed public error outside business-exception containment."""

    with suppress(Exception):
        _detail_log.warning(
            "HTTP call blocked; provider=%s model=%s session=%s turn=%s cycle=%s exchange=%s attempt=%s reason=%s",
            context.provider,
            context.model,
            context.session_id,
            context.turn_id,
            context.cycle_operation_id,
            context.exchange_operation_id,
            context.request_attempt_id,
            block.reason[:256],
        )
    if stream:
        raise HttpStreamBlockError(_PUBLIC_BLOCK_MESSAGE) from None
    raise _sdk_block_type(context.provider)(_PUBLIC_BLOCK_MESSAGE) from None


def _sdk_block_type(provider: str) -> type[Exception]:
    family = "anthropic" if provider.lower() == "anthropic" else "openai"
    return _sdk_block_type_for_family(family)


@lru_cache(maxsize=2)
def _sdk_block_type_for_family(family: str) -> type[Exception]:
    if family == "anthropic":
        from anthropic import AnthropicError

        class AnthropicHttpBlock(AnthropicError):
            pass

        return AnthropicHttpBlock

    from openai import OpenAIError

    class OpenAIHttpBlock(OpenAIError):
        pass

    return OpenAIHttpBlock
