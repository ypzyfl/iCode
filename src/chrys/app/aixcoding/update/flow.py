# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Startup orchestration for the internal update flow (design §3.5).

One asyncio task started next to the upstream update check once the main
screen is pushed.  Order: the gate (settings/CI/serve/pytest/source — the
same exemptions the upstream check grants), the D2 failure gates (the
skip-today marker, then the wrapper's tally), the cached verdict's dialog,
and a fresh check when the daily budget is due.  Everything is fail-safe:
any problem ends the task silently and the TUI starts exactly as it would
without it.

Design: aixcoding/docs/batches/auto-update/design.md
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import threading
import time
from dataclasses import replace
from typing import TYPE_CHECKING

from chrys import __version__
from chrys.app.install_flavor import InstallFlavor, detect_install_flavor
from chrys.app.tui.terminal.title import running_under_textual_web_driver
from chrys.foundation.platform import get_platform
from chrys.service.aixcoding.update import (
    AppUpdate,
    check_for_update,
    read_failure_tally,
    read_state,
    write_state,
)
from chrys.service.aixcoding.update.state import (
    CHECK_INTERVAL_SECONDS,
    FAILURES_THRESHOLD,
    create_skip_today,
    drop_failure_tally,
    drop_skip_today,
    is_today,
    mark_skipped,
    skip_today_active,
    skip_today_path,
)

from .dialog import CONFIRM, SKIP, UpdateConfirmDialog
from .runner import start_update_and_exit

if TYPE_CHECKING:
    from chrys.app.tui.app import ChrysApp
    from chrys.app.tui.screens.main.screen import MainScreen

logger = logging.getLogger(__name__)

#: Startup-modal wait budgets (revision 13): how long phase 1 waits for the
#: agent-load dialog to appear, and how long phase 2 waits for every modal
#: to clear.  Constants (not magic literals) so tests can shrink them.
STARTUP_MODAL_GRACE_SECONDS = 5.0
STARTUP_MODAL_TIMEOUT_SECONDS = 600.0
_POLL_SECONDS = 0.25

_SKIP_NOTICE = "更新今日已连续失败 {threshold} 次，今日跳过、明日自动重试；如需立即重试，删除 {path} 后重启软件。"
_LAUNCH_FAILED_NOTICE = "自动更新未能启动，请稍后重试或手动更新。"


def start_internal_update_flow(app: ChrysApp, screen: MainScreen) -> asyncio.Task[None]:
    """Wire the flow as one background task; the task itself never raises."""
    return asyncio.create_task(_run_flow(app, screen))


def _running_in_ci() -> bool:
    return os.environ.get("CI", "").strip().lower() not in {"", "0", "false", "no"}


def _running_under_pytest() -> bool:
    """True under pytest — the wiring must not fire real requests from the upstream TUI tests.

    A function of its own (not an inline env read) so tests can turn the guard
    off and drive the flow's logic: pytest re-sets ``PYTEST_CURRENT_TEST``
    between the fixture and the call phase, so a fixture-time ``delenv`` is
    undone before the test body runs.
    """
    return bool(os.environ.get("PYTEST_CURRENT_TEST"))


def _forced_for_local_smoke() -> bool:
    """Manual-smoke escape hatch: run the flow from a dev checkout anyway.

    ``AIXCODING_UPDATE_FORCE=1`` overrides only the SOURCE-flavour gate (the
    other exemptions — settings off, CI, serve, pytest — still hold), so the
    dialog chain can be driven by hand against the update mock from a repo
    checkout (design §3.5, revision 7).
    """
    return os.environ.get("AIXCODING_UPDATE_FORCE", "").strip().lower() not in {"", "0", "false", "no"}


def _gated(app: ChrysApp) -> bool:
    """The exemptions the upstream check grants, plus the pytest guard (design §3.5)."""
    if _running_under_pytest():
        # The C140 guard install uses the same marker to stay offline in tests.
        return True
    if _running_in_ci():
        return True
    if running_under_textual_web_driver():
        return True
    if detect_install_flavor() is InstallFlavor.SOURCE and not _forced_for_local_smoke():
        return True
    try:
        return not app.settings_handle.settings.update_check
    except Exception:
        # A settings read that cannot happen means the flow cannot be trusted
        # to respect its switch — stay quiet rather than guess.
        return True


def _notify(app: ChrysApp, message: str) -> None:
    with contextlib.suppress(Exception):
        app.notify(message, timeout=10)


def _notify_skipped(app: ChrysApp, config_dir) -> None:
    # The marker (not the tally) is the file to delete: at notice time the
    # tally is already consumed, and the marker is what keeps the day off.
    _notify(app, _SKIP_NOTICE.format(threshold=FAILURES_THRESHOLD, path=skip_today_path(config_dir)))


def _should_ask(state) -> bool:
    """The cached verdict's display rule (design §3.2, revision 9).

    "Remind next time" answers every start again: while a newer candidate
    exists and was not skipped, the dialog shows on each launch — the old
    once-per-calendar-day suppression is gone (owner decision, 2026-11-11).
    """
    if not state.latest or state.latest == __version__:
        return False
    return state.latest != state.skipped_version


async def _wait_for_startup_window(app: ChrysApp) -> None:
    """Hold the dialog until the startup modal window has passed (revision 13).

    The agent-load dialog (engine/tools build progress) is pushed right
    after the main screen — possibly *after* this flow starts — and eats
    every key while it is top, which reads as "Tab does not switch" on the
    update dialog.  Phase 1 waits briefly for it to appear (a fast build
    may never show one); phase 2 waits until no modal is on the stack at
    all.  Bounded both ways: a stuck build means no update dialog, never a
    broken one.
    """
    from chrys.app.tui.screens.dialogs.agent_load import AgentLoadDialog

    def _has_startup_modal() -> bool:
        with contextlib.suppress(Exception):
            return any(isinstance(screen, AgentLoadDialog) for screen in app.screen_stack)
        return False

    def _stack_clean() -> bool:
        with contextlib.suppress(Exception):
            return not any(screen.is_modal for screen in app.screen_stack)
        return False

    for _ in range(round(STARTUP_MODAL_GRACE_SECONDS / _POLL_SECONDS)):
        if _has_startup_modal():
            break
        await asyncio.sleep(_POLL_SECONDS)
    for _ in range(round(STARTUP_MODAL_TIMEOUT_SECONDS / _POLL_SECONDS)):
        if _stack_clean():
            return
        await asyncio.sleep(_POLL_SECONDS)


async def _ask(app: ChrysApp, state, *, now: float) -> str | None:
    """Show the dialog when the verdict warrants it; None when it does not."""
    if not _should_ask(state):
        return None
    await _wait_for_startup_window(app)
    loop = asyncio.get_running_loop()
    answered: asyncio.Future[str] = loop.create_future()

    def deliver(answer: str) -> None:
        if not answered.done():
            answered.set_result(answer)

    update = AppUpdate(version=state.latest, download_url="", force_upgrade=state.force_upgrade)
    app.push_screen(UpdateConfirmDialog(update, deliver))
    return await answered


async def _run_flow(app: ChrysApp, screen: MainScreen) -> None:
    try:
        await _flow(app, screen)
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.debug("auto-update flow failed", exc_info=True)


async def _flow(app: ChrysApp, screen: MainScreen) -> None:
    if _gated(app):
        return
    config_dir = get_platform().config_dir

    # D2 gate 1: the skip-today marker — off for the whole day, notice only.
    if skip_today_active(config_dir, now=time.time()):
        _notify_skipped(app, config_dir)
        return
    drop_skip_today(config_dir)

    # D2 gate 2: the wrapper's tally — stale means yesterday's, gone wholesale.
    count, mtime = read_failure_tally(config_dir)
    if mtime is not None and not is_today(mtime, now=time.time()):
        drop_failure_tally(config_dir)
        count = 0
    if count >= FAILURES_THRESHOLD:
        create_skip_today(config_dir, now=time.time())
        drop_failure_tally(config_dir)
        _notify_skipped(app, config_dir)
        return

    # The cached verdict shows at once (after the startup-modal wait inside
    # _ask); a fresh check follows when due.
    state = read_state(config_dir)
    while True:
        answer = await _ask(app, state, now=time.time())
        if answer == CONFIRM:
            _start_update(app, screen, config_dir)
            return
        # LATER needs no record: the dialog shows again on the next start
        # (revision 9).  SKIP persists the version.
        if answer == SKIP:
            state = mark_skipped(config_dir, state, state.latest, now=time.time())
        now = time.time()
        if state.checked_at > 0 and 0 <= now - state.checked_at < CHECK_INTERVAL_SECONDS:
            return
        # Stamp the attempt first: a check that fails or is cut short by
        # quitting waits a day too (the upstream cache's own rule).
        state = replace(state, checked_at=now)
        if not write_state(config_dir, state):
            return
        found = await _fetch_in_background()
        if found is None:
            return
        state = replace(state, checked_at=now, latest=found.version, force_upgrade=found.force_upgrade)
        write_state(config_dir, state)


def _start_update(app: ChrysApp, screen: MainScreen, config_dir) -> None:
    session_id = (screen.chat_session_id or "").strip() or None
    if not start_update_and_exit(session_id, config_dir, app.exit):
        _notify(app, _LAUNCH_FAILED_NOTICE)


async def _fetch_in_background() -> AppUpdate | None:
    """``check_for_update`` on a daemon thread of its own (upstream's pattern).

    A hanging name lookup cannot be cancelled; on the event loop's worker
    threads it would hold up the app's exit until it gave up — a daemon
    thread is simply left behind.
    """
    loop = asyncio.get_running_loop()
    answer: asyncio.Future[AppUpdate | None] = loop.create_future()

    def deliver(found: AppUpdate | None) -> None:
        if not answer.done():
            answer.set_result(found)

    def work() -> None:
        try:
            found = asyncio.run(check_for_update())
        except Exception:
            logger.debug("update check failed", exc_info=True)
            found = None
        with contextlib.suppress(RuntimeError):  # the loop closed while the check ran
            loop.call_soon_threadsafe(deliver, found)

    threading.Thread(target=work, name="aixcoding-update-check", daemon=True).start()
    return await answer
