# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Process-level telemetry owner: per-session queues, workers, bounded flush.

Design §3.2/N3 §14.3 semantics:

- one process-wide owner; per-session ``asyncio.Queue`` + single worker task
  (FIFO within a session — LLM → tool-detail → ai-code ordering is a worker
  concern), cross-session concurrency allowed;
- same-pass duplicate notices merge while the first task is pending/running;
  a new pass is never dropped (F2 ruling);
- ``flush_session`` drains already-enqueued work with a bound and does NOT do
  trailing-save final analysis; ``close_session`` is idempotent; a dispatch
  after a failed delete recreates the session's worker;
- no persistent high-water mark; offsets are in-process caches only.

The worker pipeline is fully wired (design §8 step 4): reader → model-source
filter → analyzer → reporter run per notice in a worker thread
(``_deliver_notice``); ai-code blocks stay in content-reference form until
the B8 field-level pass (batch 3).
"""

from __future__ import annotations

import asyncio
import logging

from chrys.service.aixcoding.telemetry.notice import TurnTelemetryNotice

_logger = logging.getLogger(__name__)

_MERGE_KEY = tuple[str, str, str]


def _deliver_notice(notice: TurnTelemetryNotice) -> None:
    """Reader -> filter -> analyzer -> reporter (blocking I/O; runs in a thread)."""
    from chrys.service.aixcoding.telemetry.analyzer import build_report_batch
    from chrys.service.aixcoding.telemetry.filtering import is_server_dispatched_model
    from chrys.service.aixcoding.telemetry.reader import read_turn_facts
    from chrys.service.aixcoding.telemetry.reporter import deliver

    if notice.session_dir is None:  # dispatch() already skips dir-less notices; belt and braces
        return
    facts = read_turn_facts(
        notice.session_dir,
        session_id=notice.session_id,
        logical_turn_id=notice.logical_turn_id,
        pass_id=notice.pass_id,
    )
    if facts is None:
        _logger.debug(
            "telemetry: turn not found in log, skipping: session=%s logical=%s",
            notice.session_id,
            notice.logical_turn_id,
        )
        return
    if not facts.llm:
        _logger.debug(
            "telemetry: no reportable model calls (skipped: %s): session=%s logical=%s",
            facts.skipped,
            notice.session_id,
            notice.logical_turn_id,
        )
        return
    undetermined = [
        fact.model_profile or "" for fact in facts.llm if not is_server_dispatched_model(fact.model_profile)
    ]
    if undetermined:
        _logger.info(
            "telemetry: model source not server-dispatched, batch skipped (%s): session=%s logical=%s",
            undetermined,
            notice.session_id,
            notice.logical_turn_id,
        )
        return
    batch = build_report_batch(notice.session_dir, facts)
    failures = deliver(batch)
    _logger.debug(
        "telemetry: delivered llm=%d tools=%d ai=%d failures=%d skipped=%s: session=%s logical=%s",
        len(batch.llm),
        len(batch.tools),
        len(batch.ai_codes),
        len(failures),
        batch.skipped,
        notice.session_id,
        notice.logical_turn_id,
    )


async def _process_notice(notice: TurnTelemetryNotice) -> None:
    """Worker body: run the pipeline in a worker thread; errors stay contained."""
    await asyncio.to_thread(_deliver_notice, notice)


class _SessionWorker:
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.queue: asyncio.Queue[TurnTelemetryNotice] = asyncio.Queue()
        self.task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self.task is None or self.task.done():
            self.task = asyncio.create_task(_run_worker(self.queue), name=f"chrys-telemetry-{self.session_id}")


async def _run_worker(queue: asyncio.Queue[TurnTelemetryNotice]) -> None:
    while True:
        notice = await queue.get()
        try:
            await _process_notice(notice)
        except Exception:
            _logger.debug("telemetry worker contained an error", exc_info=True)
        finally:
            queue.task_done()


class TelemetryOwner:
    """Process-level owner; dispatch is synchronous, lifecycle methods async."""

    def dispatch(self, notice: TurnTelemetryNotice) -> None:
        if not notice.saved or notice.session_dir is None:
            _logger.debug(
                "telemetry notice skipped (saved=%s, has_dir=%s): session=%s logical=%s",
                notice.saved,
                notice.session_dir is not None,
                notice.session_id,
                notice.logical_turn_id,
            )
            return
        key: _MERGE_KEY = (notice.session_id, notice.logical_turn_id, notice.pass_id)
        if key in self._pending:
            _logger.debug("telemetry same-pass notice merged: %s", key)
            return
        self._pending[key] = None
        worker = self._workers.get(notice.session_id)
        if worker is None:
            worker = _SessionWorker(notice.session_id)
            self._workers[notice.session_id] = worker
        worker.start()
        worker.queue.put_nowait(notice)

    _workers: dict[str, _SessionWorker]
    # Merge-key lifecycle = session lifecycle: entries are dropped in
    # close_session; a long-lived session (TUI kept open, never deleted)
    # accumulates one small tuple per (turn, pass) — bounded by session use,
    # no high-water mark by design (review F4 note).
    _pending: dict[_MERGE_KEY, None]

    def __init__(self) -> None:
        self._workers = {}
        self._pending = {}

    async def flush_session(self, session_id: str, timeout: float) -> None:
        """Drain already-enqueued work for one session, bounded by *timeout*."""
        worker = self._workers.get(session_id)
        if worker is None:
            return
        try:
            await asyncio.wait_for(worker.queue.join(), timeout=timeout)
        except TimeoutError:
            _logger.warning("telemetry flush timed out after %.1fs: session=%s", timeout, session_id)

    def close_session(self, session_id: str) -> None:
        """Idempotently stop one session's worker; a later dispatch recreates it."""
        worker = self._workers.pop(session_id, None)
        if worker is None:
            return
        if worker.task is not None and not worker.task.done():
            worker.task.cancel()
        for key in [key for key in self._pending if key[0] == session_id]:
            del self._pending[key]


_OWNER: TelemetryOwner | None = None


def get_telemetry_owner() -> TelemetryOwner:
    """Process-wide singleton (lazy; first call may happen inside the loop)."""
    global _OWNER
    if _OWNER is None:
        _OWNER = TelemetryOwner()
    return _OWNER


def reset_telemetry_owner_for_tests() -> None:
    """Drop the singleton (tests only)."""
    global _OWNER
    _OWNER = None
