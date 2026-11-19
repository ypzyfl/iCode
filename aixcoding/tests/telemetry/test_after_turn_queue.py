"""AIxCoding after-turn queue lifecycle experiment; not a production reporter."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Awaitable, Callable
from time import perf_counter

import pytest


class _QueueOwner:
    def __init__(self, reporter: Callable[[dict[str, str]], Awaitable[None]]) -> None:
        self._reporter = reporter
        self._queues: dict[str, asyncio.Queue[dict[str, str]]] = {}
        self._workers: dict[str, asyncio.Task[None]] = {}
        self._closed = False

    def notify(self, session_id: str, turn_id: str) -> None:
        if self._closed:
            raise RuntimeError("owner is closed")
        queue = self._queues.get(session_id)
        if queue is None:
            queue = asyncio.Queue()
            self._queues[session_id] = queue
        queue.put_nowait({"sessionId": session_id, "turnId": turn_id})
        worker = self._workers.get(session_id)
        if worker is None or worker.done():
            self._workers[session_id] = asyncio.create_task(self._run(session_id, queue))

    async def _run(self, session_id: str, queue: asyncio.Queue[dict[str, str]]) -> None:
        while True:
            item = await queue.get()
            try:
                await self._reporter(item)
            except asyncio.CancelledError:
                raise
            except Exception:
                pass
            finally:
                queue.task_done()

    async def flush(self, session_id: str, timeout: float) -> bool:
        queue = self._queues.get(session_id)
        if queue is None:
            return True
        try:
            await asyncio.wait_for(queue.join(), timeout=timeout)
        except TimeoutError:
            return False
        return True

    async def close(self, timeout: float = 0) -> None:
        if self._closed:
            return
        self._closed = True
        if timeout > 0:
            joins = [queue.join() for queue in self._queues.values()]
            if joins:
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(asyncio.gather(*joins), timeout=timeout)
        workers = list(self._workers.values())
        for worker in workers:
            worker.cancel()
        await asyncio.gather(*workers, return_exceptions=True)


@pytest.mark.asyncio
async def test_after_turn_queue_preserves_same_session_fifo() -> None:
    first_started = asyncio.Event()
    release_first = asyncio.Event()
    started: list[str] = []
    finished: list[str] = []

    async def reporter(item: dict[str, str]) -> None:
        started.append(item["turnId"])
        if item["turnId"] == "turn-1":
            first_started.set()
            await release_first.wait()
        finished.append(item["turnId"])

    owner = _QueueOwner(reporter)
    try:
        owner.notify("session-1", "turn-1")
        owner.notify("session-1", "turn-2")
        await asyncio.wait_for(first_started.wait(), timeout=1)
        await asyncio.sleep(0)
        assert started == ["turn-1"]
        assert finished == []
        release_first.set()
        assert await owner.flush("session-1", timeout=1)
        assert started == finished == ["turn-1", "turn-2"]
    finally:
        await owner.close()


@pytest.mark.asyncio
async def test_after_turn_queue_runs_different_sessions_concurrently() -> None:
    release = asyncio.Event()
    entered = {"session-1": asyncio.Event(), "session-2": asyncio.Event()}
    active = 0
    maximum_active = 0

    async def reporter(item: dict[str, str]) -> None:
        nonlocal active, maximum_active
        active += 1
        maximum_active = max(maximum_active, active)
        entered[item["sessionId"]].set()
        try:
            await release.wait()
        finally:
            active -= 1

    owner = _QueueOwner(reporter)
    try:
        owner.notify("session-1", "turn-1")
        owner.notify("session-2", "turn-1")
        await asyncio.wait_for(asyncio.gather(*(event.wait() for event in entered.values())), timeout=1)
        assert maximum_active == 2
        release.set()
        assert await owner.flush("session-1", timeout=1)
        assert await owner.flush("session-2", timeout=1)
    finally:
        await owner.close()


@pytest.mark.asyncio
async def test_after_turn_queue_flush_is_bounded_and_close_cancels_worker() -> None:
    entered = asyncio.Event()
    never_release = asyncio.Event()

    async def reporter(_item: dict[str, str]) -> None:
        entered.set()
        await never_release.wait()

    owner = _QueueOwner(reporter)
    owner.notify("session-1", "turn-1")
    await asyncio.wait_for(entered.wait(), timeout=1)
    started = perf_counter()
    assert not await owner.flush("session-1", timeout=0.02)
    assert perf_counter() - started < 0.2

    await owner.close()
    await owner.close()
    assert all(worker.done() for worker in owner._workers.values())
    with pytest.raises(RuntimeError, match="owner is closed"):
        owner.notify("session-1", "turn-2")
