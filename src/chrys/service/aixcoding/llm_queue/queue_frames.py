# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Gateway queue frames and queue rejections inside a Chat Completions stream.

The in-house gateway answers a queued request with SSE *named* events that the
OpenAI SDK parses as ordinary chunks: ``event:queue_status`` arrives with
``choices`` null and the position in the chunk's extra fields, and
``event:queue_rejected`` arrives as a bare ``openai.APIError`` carrying the
gateway's error body. Neither is a completion chunk for the caller:

* a position frame is not an answer — yielding it fails the stream as an
  invalid event — and the gateway's periodic position heartbeat is what keeps
  a queued connection open, so absorbing a frame also restarts the stall
  watchdog's idle timer.
* a terminal queue rejection (``QUEUE_TIMEOUT`` / ``QUEUE_CANCELLED``) must not
  be retried; a full queue (``QUEUE_FULL``) may be, so only the terminal codes
  are translated into ``ProviderResponseError`` and the rest are re-raised
  unchanged.

Known diagnostic gap: a stream that carries only position frames and then ends
makes the caller report "ended without any events", because absorbed frames set
no data-chunk flag. The guard logs that case itself.

Design and evidence: ``aixcoding/docs/batches/model-queue-client/design.md``.
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from chrys.foundation.errors import ProviderResponseError
from chrys.kernel import report_wire_progress

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletionChunk

logger = logging.getLogger(__name__)
_detail_logger = logging.getLogger("aixcoding.detail.llm_queue")
"""File-only technical channel (ADR-0017): unlike the module logger, it reaches
a file on every surface (CLI, TUI and ACP), at DETAIL level."""

TERMINAL_QUEUE_CODES: Final = frozenset({"QUEUE_TIMEOUT", "QUEUE_CANCELLED"})
"""Gateway queue rejection codes that a later attempt cannot fix."""

_QUEUE_STATUS_FIELDS: Final = ("position", "queueSize")


@dataclass(frozen=True, slots=True)
class QueueStatus:
    """One gateway queue position report; ``position`` counts the requests ahead.

    ``position == RELEASED_POSITION`` says the queue let this request through:
    the first data chunk arrived, so a frontend showing a queue note must drop
    it (the turn may still wait later, for reasons that are not the queue).
    ``request_id`` names the request the gateway queued (the per-attempt
    ``Chrys-Request-Attempt-Id``); the guard leaves it ``None`` and the tracker
    fills it before the status reaches a frontend (design v1.4).
    """

    position: int
    queue_size: int
    request_id: str | None = None


RELEASED_POSITION: Final = -1
"""The position reported once, when the first data chunk ends the queue wait."""


def queue_position(chunk: object) -> QueueStatus | None:
    """The queue position *chunk* reports, or ``None`` when it is a data chunk.

    The gateway's position frame is recognised by the current gateway contract:
    ``choices`` null, no completion fields, and both integer position fields in
    the chunk's extra fields. Anything else stays a data chunk, so a contract
    change fails the stream loudly instead of silently dropping usage. A frame
    that *carries* position fields but still fails the contract is reported,
    because the stream will then fail as an invalid response with no other clue.
    """
    choices = getattr(chunk, "choices", None)
    extra = getattr(chunk, "model_extra", None)
    queue_fields_present = isinstance(extra, dict) and any(field in extra for field in _QUEUE_STATUS_FIELDS)
    if choices is not None:
        if queue_fields_present:
            _log_unrecognised_queue_frame(chunk)
        return None
    if not isinstance(extra, dict) or not queue_fields_present:
        return None
    position = extra.get(_QUEUE_STATUS_FIELDS[0])
    queue_size = extra.get(_QUEUE_STATUS_FIELDS[1])
    if (
        type(position) is not int
        or type(queue_size) is not int
        or getattr(chunk, "id", None) is not None
        or getattr(chunk, "usage", None) is not None
    ):
        _log_unrecognised_queue_frame(chunk)
        return None
    return QueueStatus(position=position, queue_size=queue_size)


def _log_unrecognised_queue_frame(chunk: object) -> None:
    """Report a queue-shaped chunk the contract does not accept, without its text.

    Only field names, their shapes and the queue numbers are logged: a data
    chunk's ``choices`` can carry answer text, so its shape replaces its value.
    """
    choices = getattr(chunk, "choices", None)
    extra = getattr(chunk, "model_extra", None)
    position = extra.get(_QUEUE_STATUS_FIELDS[0]) if isinstance(extra, dict) else None
    queue_size = extra.get(_QUEUE_STATUS_FIELDS[1]) if isinstance(extra, dict) else None
    logger.warning(
        "无法识别的网关排队帧：choices=%s id=%r usage=%r position=%r queueSize=%r model_extra=%s；"
        "该帧不符合契约时，流将以 invalid response 失败",
        _choice_shape(choices),
        getattr(chunk, "id", None),
        getattr(chunk, "usage", None),
        position,
        queue_size,
        _preview(extra),
    )
    _detail_logger.warning(
        "无法识别的网关排队帧：choices=%s id=%r usage=%r position=%r queueSize=%r model_extra=%s",
        _choice_shape(choices),
        getattr(chunk, "id", None),
        getattr(chunk, "usage", None),
        position,
        queue_size,
        _preview(extra),
    )


def _choice_shape(choices: object) -> str:
    """The shape of ``choices`` without its values (a data chunk carries answer text)."""
    if choices is None:
        return "null"
    if isinstance(choices, list):
        return f"list[{len(choices)}]"
    return type(choices).__name__


def _chunk_summary(chunk: object) -> str:
    """The SDK-parsed frame as the client sees it, bounded and without answer text."""
    return _preview(
        {
            "id": getattr(chunk, "id", None),
            "choices": _choice_shape(getattr(chunk, "choices", None)),
            "usage": getattr(chunk, "usage", None),
            "model_extra": getattr(chunk, "model_extra", None),
        }
    )


def _exception_summary(exc: BaseException) -> str:
    """The parsed gateway rejection: code, message, body and exception type."""
    return _preview(
        {
            "type": type(exc).__name__,
            "status_code": getattr(exc, "status_code", None),
            "code": _string_field(exc, "code"),
            "message": _string_field(exc, "message"),
            "body": getattr(exc, "body", None),
        }
    )


def _preview(value: object, limit: int = 500) -> str:
    """A bounded ``repr``: enough to identify a frame, never a whole stream."""
    text = repr(value)
    return text if len(text) <= limit else f"{text[:limit]}…"


async def guard_queue_frames(
    chunks: AsyncIterator[ChatCompletionChunk],
    *,
    on_status: Callable[[QueueStatus], Awaitable[None]] | None = None,
) -> AsyncIterator[ChatCompletionChunk]:
    """Yield the provider's chunks, absorbing the gateway's queue frames.

    A position frame is absorbed after restarting the enclosing stall watchdog;
    a terminal queue rejection is translated into :class:`ProviderResponseError`
    with ``retryable=False``. Everything else, including the ``QUEUE_FULL``
    rejection, passes through untouched.

    ``on_status`` receives every absorbed position; it runs after the watchdog
    is restarted so a slow frontend never eats the stall budget, and its
    failure is logged rather than allowed to break the stream.
    """
    iterator = chunks.__aiter__()
    absorbed = 0
    forwarded = 0
    queued_at: float | None = None
    while True:
        try:
            chunk = await anext(iterator)
        except StopAsyncIteration:
            if absorbed and not forwarded:
                message = "网关发送了 %d 个排队帧但没有数据帧，流在没有回答的情况下结束"
                logger.info(message, absorbed)
                _detail_logger.info(message, absorbed)
            return
        except Exception as exc:
            terminal = terminal_queue_rejection(exc)
            if terminal is None:
                if _string_field(exc, "code") == "QUEUE_FULL":
                    _detail_logger.info(
                        "网关队列已满（QUEUE_FULL），交由 wire 重试通道退避；响应解析：%s",
                        _exception_summary(exc),
                    )
                raise
            message = "网关拒绝排队请求：code=%s retryable=False"
            logger.info(message, terminal.code)
            _detail_logger.info(
                "网关拒绝排队请求：code=%s retryable=False，响应解析：%s",
                terminal.code,
                _exception_summary(exc),
            )
            raise terminal from exc
        status = queue_position(chunk)
        if status is None:
            if absorbed and not forwarded:
                # The queue let this request through: tell the frontends once.
                message = "网关已放行排队请求（此前收到 %d 个排队帧）"
                logger.info(message, absorbed)
                if queued_at is not None:
                    _detail_logger.info("网关排队等待 %.1f 秒后放行", time.monotonic() - queued_at)
                _detail_logger.debug("排队放行后收到首个数据帧：%s", _chunk_summary(chunk))
                await _notify(on_status, QueueStatus(position=RELEASED_POSITION, queue_size=0))
            forwarded += 1
            yield chunk
            continue
        absorbed += 1
        if absorbed == 1:
            queued_at = time.monotonic()
            logger.info("网关排队：position=%d queueSize=%d", status.position, status.queue_size)
            _detail_logger.info("网关排队帧（解析后）：%s", _chunk_summary(chunk))
        else:
            _detail_logger.debug(
                "网关排队心跳：position=%d queueSize=%d（第 %d 帧），解析后：%s",
                status.position,
                status.queue_size,
                absorbed,
                _chunk_summary(chunk),
            )
        report_wire_progress()
        await _notify(on_status, status)


async def _notify(
    on_status: Callable[[QueueStatus], Awaitable[None]] | None,
    status: QueueStatus,
) -> None:
    """Hand one status to the frontend; a broken frontend never breaks the stream."""
    if on_status is None:
        return
    try:
        await on_status(status)
    except Exception:
        message = "排队状态回调失败，前端将看不到本次排队更新"
        logger.warning(message, exc_info=True)
        _detail_logger.warning(message, exc_info=True)


def terminal_queue_rejection(exc: BaseException) -> ProviderResponseError | None:
    """The translated failure for a terminal queue rejection, else ``None``."""
    code = _string_field(exc, "code")
    if code not in TERMINAL_QUEUE_CODES:
        return None
    message = _string_field(exc, "message") or f"网关排队拒绝了该请求（{code}）"
    return ProviderResponseError(code, message, retryable=False)


def _string_field(exc: BaseException, name: str) -> str | None:
    try:
        value = getattr(exc, name, None)
    except Exception:
        return None
    return value if isinstance(value, str) else None
