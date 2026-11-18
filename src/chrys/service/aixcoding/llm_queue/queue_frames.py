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

Design and evidence: ``aixcoding/docs/batches/model-queue-client/design.md``.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from chrys.foundation.errors import ProviderResponseError
from chrys.kernel import report_wire_progress

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletionChunk

TERMINAL_QUEUE_CODES: Final = frozenset({"QUEUE_TIMEOUT", "QUEUE_CANCELLED"})
"""Gateway queue rejection codes that a later attempt cannot fix."""

_QUEUE_STATUS_FIELDS: Final = ("position", "queueSize")


@dataclass(frozen=True, slots=True)
class QueueStatus:
    """One gateway queue position report; ``position`` counts the requests ahead."""

    position: int
    queue_size: int
    observed_at: float


class _QueueStatusRecorder:
    """Holds the newest report for a frontend that shows queue progress."""

    latest: QueueStatus | None = None


_recorder = _QueueStatusRecorder()


def latest_queue_status() -> QueueStatus | None:
    """The most recent queue position this process observed, if any."""
    return _recorder.latest


def queue_position(chunk: object) -> QueueStatus | None:
    """The queue position *chunk* reports, or ``None`` when it is a data chunk.

    The gateway's position frame is the only chunk-shaped event that carries
    both integer fields and no completion fields at all; anything else stays a
    data chunk so a shape change fails the stream loudly instead of silently
    dropping usage.
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
    return QueueStatus(position=position, queue_size=queue_size, observed_at=time.monotonic())


async def guard_queue_frames(chunks: AsyncIterator[ChatCompletionChunk]) -> AsyncIterator[ChatCompletionChunk]:
    """Yield the provider's chunks, absorbing the gateway's queue frames.

    A position frame is absorbed after restarting the enclosing stall watchdog;
    a terminal queue rejection is translated into :class:`ProviderResponseError`
    with ``retryable=False``. Everything else, including the ``QUEUE_FULL``
    rejection, passes through untouched.
    """
    iterator = chunks.__aiter__()
    while True:
        try:
            chunk = await anext(iterator)
        except StopAsyncIteration:
            return
        except Exception as exc:
            terminal = terminal_queue_rejection(exc)
            if terminal is None:
                raise
            raise terminal from exc
        status = queue_position(chunk)
        if status is None:
            yield chunk
            continue
        report_wire_progress()
        _recorder.latest = status


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
