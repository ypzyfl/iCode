# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Leave the gateway queue when a queued request is abandoned.

``/api/v3/chat/completions/cancel`` is the queue's side channel: a request still
waiting in the FIFO queue is taken out by the ``request_id`` its completion
request carried (``ModelQueueFrontend.md`` §3.6, ``LlmRequestFlow.md`` §5).
This client does not write that id into the request body: it is the per-attempt
``Chrys-Request-Attempt-Id`` header upstream stamps on every HTTP attempt
(``service/llm/request_tracking.py``), read back from the request that produced
the response. A released request cannot be cancelled (``409``) and an unknown
one is a no-op (``404``), so this only fires while the guard has seen a position
and no release.

Wired from ``chrys.service.llm.chat_completions.client`` (registered as
``model-queue-client:queue-cancel``).
Design: ``aixcoding/docs/batches/model-queue-client/design.md``.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Final

import httpx

from chrys.foundation.util.chrys_headers import REQUEST_ATTEMPT_ID_HEADER
from chrys.service.aixcoding.llm_queue.queue_frames import RELEASED_POSITION, QueueStatus

logger = logging.getLogger(__name__)
_detail_logger = logging.getLogger("aixcoding.detail.llm_queue")
"""File-only technical channel (ADR-0017): unlike the module logger, it reaches
a file on every surface (CLI, TUI and ACP), at DETAIL level."""

CANCEL_PATH: Final = "/api/v3/chat/completions/cancel"
"""The gateway's queue-cancel endpoint, resolved against the gateway root."""

CANCEL_TIMEOUT_SECONDS: Final = 2.0
"""Upper bound on one cancel call: it must never hold up the interrupt."""

_COMPLETION_SUFFIXES: Final = ("/api/v3", "/api/v2", "/api/v1", "/v1")
"""What an OpenAI-compatible base URL may end with; none of it belongs to the cancel URL."""

_PENDING_CANCELS: set[asyncio.Task[None]] = set()
"""Cancel calls still in flight; a strong reference keeps them from being collected."""


def cancel_endpoint(base_url: str) -> str | None:
    """The cancel URL for a completion base URL, or ``None`` when it cannot be derived."""
    root = base_url.strip().rstrip("/")
    if not root.startswith(("http://", "https://")):
        return None
    while True:
        stripped = next((root[: -len(suffix)] for suffix in _COMPLETION_SUFFIXES if root.endswith(suffix)), None)
        if stripped is None:
            break
        root = stripped.rstrip("/")
    return f"{root}{CANCEL_PATH}" if root else None


class QueueRequestTracker:
    """Ties one wire request to the gateway queue so an interrupt can leave it."""

    __slots__ = ("_api_key", "_endpoint", "_model", "_position_seen", "_released", "_request_id", "_transport")

    def __init__(
        self,
        *,
        request_id: str,
        model: str,
        endpoint: str | None,
        api_key: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._request_id = request_id
        self._model = model
        self._endpoint = endpoint
        self._api_key = api_key
        self._transport = transport
        self._position_seen = False
        self._released = False

    @property
    def request_id(self) -> str:
        """The id the gateway knows this request by."""
        return self._request_id

    @property
    def queued(self) -> bool:
        """Whether the gateway may still hold this request in its queue."""
        return self._position_seen and not self._released

    def observing(
        self, on_status: Callable[[QueueStatus], Awaitable[None]] | None
    ) -> Callable[[QueueStatus], Awaitable[None]]:
        """The status callback for the guard: track the queue phase, then forward to the frontend."""

        async def observe(status: QueueStatus) -> None:
            if status.position == RELEASED_POSITION:
                self._released = True
                _detail_logger.info("网关已放行排队请求（request_id=%s）", self._request_id)
            elif not self._position_seen:
                self._position_seen = True
                _detail_logger.info(
                    "网关排队：position=%d queueSize=%d（request_id=%s）",
                    status.position,
                    status.queue_size,
                    self._request_id,
                )
            if on_status is not None:
                await on_status(status)

        return observe

    async def cancel_on_close(self) -> None:
        """Leave the queue if this request is still waiting; never raises on its own.

        Shielded, because the usual caller is a stream being cancelled: the cancel
        request must outlive the await that cancelled the stream. The task is kept
        in ``_PENDING_CANCELS`` so it is never collected mid-flight.
        """
        if not self.queued:
            if self._position_seen:
                _detail_logger.debug(
                    "网关排队取消跳过：请求在中断前已被放行（request_id=%s）",
                    self._request_id,
                )
            return
        if self._endpoint is None:
            _detail_logger.warning("网关排队取消跳过：没有可用的取消地址（request_id=%s）", self._request_id)
            return
        if not self._api_key:
            message = "网关排队取消跳过：没有 api_key，请求将留在队列中（request_id=%s）"
            logger.warning(message, self._request_id)
            _detail_logger.warning(message, self._request_id)
            return
        message = "正在离开网关队列：POST %s，model=%s，request_id=%s"
        logger.info(message, self._endpoint, self._model, self._request_id)
        _detail_logger.info(message, self._endpoint, self._model, self._request_id)
        task = asyncio.ensure_future(self._post_cancel())
        _PENDING_CANCELS.add(task)
        task.add_done_callback(_PENDING_CANCELS.discard)
        current = asyncio.current_task()
        if current is not None and current.cancelling():
            # Already being cancelled: the request still leaves, the interrupt is not delayed.
            return
        await asyncio.shield(task)

    async def _post_cancel(self) -> None:
        endpoint = self._endpoint
        if endpoint is None:  # narrowed here too: the checker does not follow cancel_on_close's guard
            return
        payload = {"model": self._model, "request_id": self._request_id}
        _detail_logger.info(
            "发送取消排队请求：POST %s，body=%s，token=%s",
            endpoint,
            _preview(payload),
            "已携带" if self._api_key else "空",
        )
        try:
            async with httpx.AsyncClient(timeout=CANCEL_TIMEOUT_SECONDS, transport=self._transport) as client:
                response = await client.post(endpoint, json=payload, headers={"token": self._api_key})
        except httpx.TransportError:
            # Also the symptom of a cancel URL derived from an unexpected base_url: loud on purpose.
            message = "网关排队取消无法连接 %s（request_id=%s），请求可能仍在队列中"
            logger.warning(message, endpoint, self._request_id, exc_info=True)
            _detail_logger.warning(message, endpoint, self._request_id, exc_info=True)
            return
        except Exception:
            logger.debug("网关排队取消失败（request_id=%s）", self._request_id, exc_info=True)
            _detail_logger.warning(
                "网关排队取消在收到响应前失败（request_id=%s，endpoint=%s）",
                self._request_id,
                endpoint,
                exc_info=True,
            )
            return
        if response.status_code == httpx.codes.NO_CONTENT:
            logger.info("已离开网关队列（request_id=%s）", self._request_id)
            _detail_logger.info(
                "取消排队响应：status=204，请求已出队（request_id=%s，endpoint=%s）",
                self._request_id,
                endpoint,
            )
        elif response.status_code in (httpx.codes.NOT_FOUND, httpx.codes.CONFLICT):
            # The contract's normal no-ops: already released, finished, or already cancelled.
            logger.debug(
                "网关排队取消为正常 no-op（status=%s，request_id=%s，endpoint=%s）",
                response.status_code,
                self._request_id,
                endpoint,
            )
            _detail_logger.info(
                "取消排队响应：status=%s，body=%s（request_id=%s，endpoint=%s）",
                response.status_code,
                _preview(response.text),
                self._request_id,
                endpoint,
            )
        else:
            message = "网关排队取消返回 %s（request_id=%s）"
            logger.warning(message, response.status_code, self._request_id)
            _detail_logger.warning(
                "取消排队响应：status=%s，body=%s（request_id=%s，endpoint=%s）",
                response.status_code,
                _preview(response.text),
                self._request_id,
                endpoint,
            )


def track_queue_request(
    request: httpx.Request,
    *,
    model: str,
    base_url: str,
    api_key: str,
    transport: httpx.AsyncBaseTransport | None = None,
) -> QueueRequestTracker | None:
    """Tie the queue entry of *request* to the id the gateway saw, when a cancel can be sent.

    *request* is the attempt whose response arrived (``raw.http_response.request``),
    so its ``Chrys-Request-Attempt-Id`` is the id the gateway queued. ``None``
    means no tracker is armed: no model, no such header on the attempt (a client
    built without the upstream tracking hooks), or a cancel endpoint that cannot
    be derived from *base_url*. The stream works either way; only the
    leave-the-queue call is lost. ``transport`` exists so tests can observe the
    cancel call; production passes none.
    """
    if not model:
        _detail_logger.debug("网关排队取消未启用：请求没有 model")
        return None
    request_id = request.headers.get(REQUEST_ATTEMPT_ID_HEADER)
    if not request_id:
        message = "网关排队取消不可用：本次尝试没有 %s 请求头，中断后请求会留在队列中"
        logger.warning(message, REQUEST_ATTEMPT_ID_HEADER)
        _detail_logger.warning(message, REQUEST_ATTEMPT_ID_HEADER)
        return None
    endpoint = cancel_endpoint(base_url)
    if endpoint is None:
        logger.debug("网关排队取消跳过：base_url %r 无法推导取消地址（request_id=%s）", base_url, request_id)
        _detail_logger.warning(
            "网关排队取消不可用：base_url %r 无法推导取消地址（request_id=%s）", base_url, request_id
        )
        return None
    _detail_logger.debug(
        "网关排队取消已就绪：request_id=%s endpoint=%s model=%s base_url=%r",
        request_id,
        endpoint,
        model,
        base_url,
    )
    return QueueRequestTracker(
        request_id=request_id,
        model=model,
        endpoint=endpoint,
        api_key=str(api_key or ""),
        transport=transport,
    )


def _preview(value: object, limit: int = 500) -> str:
    """A bounded ``repr`` for a cancel body: enough to identify it, never a whole payload."""
    text = repr(value)
    return text if len(text) <= limit else f"{text[:limit]}…"
