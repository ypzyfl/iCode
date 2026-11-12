# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Bounded, ordered delivery for the independent telemetry endpoints."""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from typing import TYPE_CHECKING

from chrys.foundation.util.once_close import OnceClose
from chrys.service.aixcoding.telemetry.reporters import Report

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

logger = logging.getLogger(__name__)


class TelemetryDelivery:
    """Send independent reports serially, resolving credentials at send time."""

    def __init__(
        self,
        extension_base_url: str,
        *,
        token_provider: Callable[[], str | None],
        client: httpx.AsyncClient | None = None,
        capacity: int = 1024,
        drain_timeout: float = 2.0,
        code_flush_size: int = 20,
        code_flush_interval: float = 10.0,
    ) -> None:
        if capacity < 1 or drain_timeout <= 0:
            raise ValueError("Telemetry capacity and drain timeout must be positive.")
        if code_flush_size < 1 or code_flush_interval <= 0:
            raise ValueError("Telemetry code flush size and interval must be positive.")
        self._code_reports: list[Report] = []
        self._code_timer: asyncio.TimerHandle | None = None
        self._code_flush_size = code_flush_size
        self._code_flush_interval = code_flush_interval
        self._url = f"{extension_base_url.rstrip('/')}/telemetry/api/v1"
        self._token_provider = token_provider
        self._client = client
        self._queue: asyncio.Queue[Report] = asyncio.Queue(maxsize=capacity)
        self._worker: asyncio.Task[None] | None = None
        self._drain_timeout = drain_timeout
        self._close = OnceClose(self._shutdown)
        self.sent = self.failed = self.dropped = 0

    def submit(self, report: Report) -> bool:
        """Queue a payload without waiting for network work."""
        if self._close.started or self._queue.full():
            self.dropped += 1
            logger.debug("Telemetry report dropped: %s", report.endpoint)
            return False
        loop = asyncio.get_running_loop()
        self._queue.put_nowait(Report(report.endpoint, dict(report.payload)))
        if self._worker is None:
            self._worker = loop.create_task(self._run())
        return True

    def submit_code(self, report: Report) -> bool:
        """Buffer code reports, then enqueue individual POSTs in insertion order."""
        if self._close.started:
            self.dropped += 1
            return False
        self._code_reports.append(Report(report.endpoint, dict(report.payload)))
        if len(self._code_reports) >= self._code_flush_size:
            self._flush_code()
        elif self._code_timer is None:
            self._code_timer = asyncio.get_running_loop().call_later(self._code_flush_interval, self._flush_code)
        return True

    def _flush_code(self) -> None:
        if self._code_timer is not None:
            self._code_timer.cancel()
            self._code_timer = None
        reports, self._code_reports = self._code_reports, []
        for report in reports:
            self.submit(report)

    async def _run(self) -> None:
        while True:
            report = await self._queue.get()
            try:
                await self._send(report)
            except asyncio.CancelledError:
                self.dropped += 1
                raise
            except Exception:
                self.failed += 1
                logger.debug("Telemetry delivery failed: %s", report.endpoint)
            finally:
                self._queue.task_done()

    async def _send(self, report: Report) -> None:
        if self._client is None:
            import httpx

            self._client = httpx.AsyncClient(timeout=10.0, trust_env=False)
        token = self._token_provider()
        response = await self._client.post(
            f"{self._url}/{report.endpoint}", json=dict(report.payload), headers={"token": token} if token else None
        )
        if response.status_code >= 400:
            self.failed += 1
            logger.debug("Telemetry endpoint %s returned %s", report.endpoint, response.status_code)
        else:
            self.sent += 1

    async def aclose(self) -> None:
        self._flush_code()
        await self._close()

    async def _shutdown(self) -> None:
        if self._worker is not None:
            try:
                async with asyncio.timeout(self._drain_timeout):
                    await self._queue.join()
            except TimeoutError:
                logger.debug("Telemetry drain timed out with %d queued reports", self._queue.qsize())
            finally:
                self._worker.cancel()
                with suppress(asyncio.CancelledError):
                    await self._worker
                self.dropped += self._queue.qsize()
                while not self._queue.empty():
                    self._queue.get_nowait()
                    self._queue.task_done()
        if self._client is not None:
            await self._client.aclose()
