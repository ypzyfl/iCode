# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Bounded, ordered delivery for the independent telemetry endpoints."""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import suppress
from time import monotonic
from typing import TYPE_CHECKING

from chrys.foundation.util.once_close import OnceClose
from chrys.kernel.aixcoding.diagnostics.telemetry_reports import record_report, report_logging_enabled
from chrys.service.aixcoding.telemetry.reporters import Report

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

logger = logging.getLogger(__name__)
_REPORT_PEER = "aixcoding.telemetry.peer"


def _peer_address(response: httpx.Response) -> tuple[str, int] | None:
    stream = response.extensions.get("network_stream")
    if stream is not None:
        with suppress(Exception):
            address = stream.get_extra_info("server_addr")
            if isinstance(address, tuple) and len(address) >= 2:
                host, port = address[:2]
                if isinstance(host, str) and isinstance(port, int):
                    return host, port
    return None


async def _capture_report_peer(response: httpx.Response) -> None:
    # HTTPX invokes response hooks before consuming the body and possibly closing the socket.
    response.extensions[_REPORT_PEER] = _peer_address(response)


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
        self.diagnostic_failures = 0

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
        started_at = monotonic() if report_logging_enabled() else None
        if self._client is None:
            import httpx

            self._client = httpx.AsyncClient(
                timeout=10.0,
                trust_env=False,
                event_hooks={"response": [_capture_report_peer]} if started_at is not None else None,
            )
        token = self._token_provider()
        response = None
        failure = None
        try:
            response = await self._client.post(
                f"{self._url}/{report.endpoint}", json=dict(report.payload), headers={"token": token} if token else None
            )
        except (asyncio.CancelledError, Exception) as exc:
            failure = exc
            raise
        finally:
            if started_at is not None:
                self._log_report(report, started_at, response, failure)
        if response.status_code >= 400:
            self.failed += 1
            logger.debug("Telemetry endpoint %s returned %s", report.endpoint, response.status_code)
        else:
            self.sent += 1

    def _log_report(
        self,
        report: Report,
        started_at: float,
        response: httpx.Response | None,
        failure: BaseException | None,
    ) -> None:
        duration_ms = (monotonic() - started_at) * 1000
        try:
            request = None
            with suppress(RuntimeError):
                request = response.request if response is not None else getattr(failure, "request", None)
            peer = None
            if response is not None:
                peer = response.extensions.get(_REPORT_PEER) or _peer_address(response)
            record_report(
                url=str(request.url) if request is not None else f"{self._url}/{report.endpoint}",
                endpoint=report.endpoint.partition("?")[0],
                payload=json.loads(request.content) if request is not None else dict(report.payload),
                status_code=response.status_code if response is not None else None,
                peer=peer,
                error_type=type(failure).__name__ if failure is not None else None,
                duration_ms=duration_ms,
            )
        except Exception as exc:
            self.diagnostic_failures += 1
            # A diagnostic failure must not change delivery accounting or expose the report.
            with suppress(Exception):
                logger.warning("Telemetry report diagnostics failed: %s", type(exc).__name__)

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
