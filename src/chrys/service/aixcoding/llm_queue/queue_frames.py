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
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from chrys.foundation.errors import ProviderResponseError
from chrys.kernel import report_wire_progress

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletionChunk

logger = logging.getLogger(__name__)

TERMINAL_QUEUE_CODES: Final = frozenset({"QUEUE_TIMEOUT", "QUEUE_CANCELLED"})
"""Gateway queue rejection codes that a later attempt cannot fix."""

_QUEUE_STATUS_FIELDS: Final = ("position", "queueSize")


@dataclass(frozen=True, slots=True)
class QueueStatus:
    """One gateway queue position report; ``position`` counts the requests ahead."""

    position: int
    queue_size: int


def queue_position(chunk: object) -> QueueStatus | None:
    """The queue position *chunk* reports, or ``None`` when it is a data chunk.

    The gateway's position frame is recognised by the current gateway contract:
    ``choices`` null, no completion fields, and both integer position fields in
    the chunk's extra fields. Anything else stays a data chunk, so a contract
    change fails the stream loudly instead of silently dropping usage.
    """
    if getattr(chunk, "choices", None) is not None:
        return None
    if getattr(chunk, "id", None) is not None or getattr(chunk, "usage", None) is not None:
        return None
    extra = getattr(chunk, "model_extra", None)
    if not isinstance(extra, dict):
        return None
    position = extra.get(_QUEUE_STATUS_FIELDS[0])
    queue_size = extra.get(_QUEUE_STATUS_FIELDS[1])
    if type(position) is not int or type(queue_size) is not int:
        return None
    return QueueStatus(position=position, queue_size=queue_size)


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
    while True:
        try:
            chunk = await anext(iterator)
        except StopAsyncIteration:
            if absorbed and not forwarded:
                logger.info(
                    "gateway sent %d queue frame(s) and no data chunk; the stream ends without an answer",
                    absorbed,
                )
            return
        except Exception as exc:
            terminal = terminal_queue_rejection(exc)
            if terminal is None:
                raise
            raise terminal from exc
        status = queue_position(chunk)
        if status is None:
            forwarded += 1
            yield chunk
            continue
        absorbed += 1
        report_wire_progress()
        if on_status is not None:
            try:
                await on_status(status)
            except Exception:
                logger.debug("queue status callback failed", exc_info=True)


def terminal_queue_rejection(exc: BaseException) -> ProviderResponseError | None:
    """The translated failure for a terminal queue rejection, else ``None``."""
    code = _string_field(exc, "code")
    if code not in TERMINAL_QUEUE_CODES:
        return None
    message = _string_field(exc, "message") or f"the model queue rejected the request ({code})"
    return ProviderResponseError(code, message, retryable=False)


def _string_field(exc: BaseException, name: str) -> str | None:
    try:
        value = getattr(exc, name, None)
    except Exception:
        return None
    return value if isinstance(value, str) else None
