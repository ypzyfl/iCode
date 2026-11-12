# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Flow tests: the gate matrix, the D2 failure gates, and the state transitions.

The dialog and the network fetch are stubbed — their contracts are pinned by
``test_dialog.py`` and ``test_client.py``; here the sequencing is the object
under test (design §3.5).

Design: aixcoding/docs/batches/auto-update/design.md §3.5
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from chrys import __version__ as CURRENT_VERSION
from chrys.app.aixcoding.update import flow as flow_module
from chrys.app.aixcoding.update.dialog import LATER, UpdateConfirmDialog
from chrys.service.aixcoding.update.state import (
    UpdateState,
    failures_path,
    read_state,
    skip_today_path,
    write_state,
)

DAY = 24 * 60 * 60


class _FakeApp:
    """The surface the flow touches on ChrysApp, recorded."""

    def __init__(self, *, update_check: bool = True, settings_error: bool = False) -> None:
        self._settings_error = settings_error
        self._settings = SimpleNamespace(update_check=update_check)
        self.notifications: list[str] = []
        self.exited: list[bool] = []

    @property
    def settings_handle(self) -> Any:
        if self._settings_error:
            raise RuntimeError("unreadable settings")
        return SimpleNamespace(settings=self._settings)

    def notify(self, message: str, **_kwargs: Any) -> None:
        self.notifications.append(message)

    def exit(self, *_args: Any, **_kwargs: Any) -> None:
        self.exited.append(True)


class _FakeScreen:
    chat_session_id = "sess-1"


def _ungate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear every gate the flow checks, so the test drives the logic itself."""
    monkeypatch.setattr(flow_module, "_running_under_pytest", lambda: False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setattr(flow_module, "running_under_textual_web_driver", lambda: False)
    monkeypatch.setattr(flow_module, "detect_install_flavor", lambda: flow_module.InstallFlavor.PIP)
    monkeypatch.setattr(flow_module, "get_platform", lambda: SimpleNamespace(config_dir=Path("/fake-config")))


@pytest.fixture
def board(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Any:
    """An ungated flow over ``tmp_path``: answers scripted, fetch stubbed, update stubbed."""
    _ungate(monkeypatch)
    monkeypatch.setattr(flow_module, "get_platform", lambda: SimpleNamespace(config_dir=tmp_path))

    state: dict[str, Any] = {
        "answers": [],  # what the dialog will say, in order (None = not shown)
        "shown": [],  # what the dialog was asked about
        "found": [],  # what the network fetch will return, in order
        "updates": [],  # start_update_and_exit calls
    }

    async def _ask(app: Any, snap: UpdateState, *, now: float) -> str | None:
        state["shown"].append(snap)
        if not state["answers"]:
            return None
        answer = state["answers"].pop(0)
        return None if answer is None else answer

    async def _fetch() -> Any:
        if not state["found"]:
            return None
        return state["found"].pop(0)

    monkeypatch.setattr(flow_module, "_ask", _ask)
    monkeypatch.setattr(flow_module, "_fetch_in_background", _fetch)

    def _update(session_id: Any, config_dir: Any, exit_app: Any, **_kwargs: Any) -> bool:
        state["updates"].append((session_id, config_dir))
        exit_app()
        return True

    monkeypatch.setattr(flow_module, "start_update_and_exit", _update)
    return SimpleNamespace(state=state, tmp_path=tmp_path, monkeypatch=monkeypatch)


async def test_gates_silence_the_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each exemption alone keeps the flow from even reading the state files."""
    for gate in ("pytest", "ci", "served", "source", "settings-off", "settings-error"):
        _ungate(monkeypatch)
        monkeypatch.setattr(flow_module, "read_state", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError()))
        app = _FakeApp()
        if gate == "pytest":
            monkeypatch.setattr(flow_module, "_running_under_pytest", lambda: True)
        elif gate == "ci":
            monkeypatch.setenv("CI", "true")
        elif gate == "served":
            monkeypatch.setattr(flow_module, "running_under_textual_web_driver", lambda: True)
        elif gate == "source":
            monkeypatch.setattr(flow_module, "detect_install_flavor", lambda: flow_module.InstallFlavor.SOURCE)
        elif gate == "settings-off":
            app = _FakeApp(update_check=False)
        else:
            app = _FakeApp(settings_error=True)

        await flow_module._flow(app, _FakeScreen())  # must not touch read_state


async def test_source_gate_yields_to_the_local_smoke_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """AIXCODING_UPDATE_FORCE=1 overrides only the SOURCE gate (design §3.5 rev 7)."""
    _ungate(monkeypatch)
    monkeypatch.setattr(flow_module, "detect_install_flavor", lambda: flow_module.InstallFlavor.SOURCE)

    monkeypatch.delenv("AIXCODING_UPDATE_FORCE", raising=False)
    assert flow_module._gated(_FakeApp()) is True, "a source checkout stays gated without the override"

    monkeypatch.setenv("AIXCODING_UPDATE_FORCE", "1")
    assert flow_module._gated(_FakeApp()) is False, "the override lets a source checkout run the flow"

    monkeypatch.setenv("CI", "true")
    assert flow_module._gated(_FakeApp()) is True, "no other gate is weakened by the override"


async def test_skip_today_marker_keeps_the_day_off(board: Any) -> None:
    now = time.time()
    marker = board.tmp_path / "update-skip-today"
    marker.write_text("x\n", encoding="utf-8")
    os.utime(marker, (now, now))

    app = _FakeApp()
    await flow_module._flow(app, _FakeScreen())

    assert board.state["shown"] == [], "a live skip-today marker means no dialog at all"
    assert app.notifications, "the user is told why the day is off"
    assert str(skip_today_path(board.tmp_path)) in app.notifications[0], (
        "the notice names the marker — the file whose deletion resumes the check"
    )


async def test_stale_marker_is_dropped_and_flow_continues(board: Any) -> None:
    write_state(board.tmp_path, UpdateState(latest="999.0.0"))
    board.state["answers"] = [LATER]

    await flow_module._flow(_FakeApp(), _FakeScreen())

    assert not skip_today_path(board.tmp_path).exists(), "a stale marker is removed"


async def test_tally_at_threshold_creates_marker_and_drops_tally(board: Any) -> None:
    tally = failures_path(board.tmp_path)
    tally.write_text("1\n2\n3\n", encoding="utf-8")

    app = _FakeApp()
    await flow_module._flow(app, _FakeScreen())

    assert skip_today_path(board.tmp_path).exists(), "three failures turn into the skip-today marker"
    assert not tally.exists(), "the tally is consumed"
    assert board.state["shown"] == [], "no dialog that day"
    assert app.notifications, "the user is told why"
    assert str(skip_today_path(board.tmp_path)) in app.notifications[0], (
        "the notice names the marker, never the already-consumed tally"
    )
    assert str(failures_path(board.tmp_path)) not in app.notifications[0]


async def test_tally_below_threshold_proceeds(board: Any) -> None:
    failures_path(board.tmp_path).write_text("1\n2\n", encoding="utf-8")
    write_state(board.tmp_path, UpdateState(latest="999.0.0"))
    board.state["answers"] = [LATER]

    await flow_module._flow(_FakeApp(), _FakeScreen())

    assert board.state["shown"], "two failures do not gate the dialog"


async def test_yesterdays_tally_is_dropped_wholesale(board: Any) -> None:
    now = time.time()
    tally = failures_path(board.tmp_path)
    tally.write_text("1\n2\n3\n", encoding="utf-8")
    os.utime(tally, (now - 2 * DAY, now - 2 * DAY))
    write_state(board.tmp_path, UpdateState(latest="999.0.0"))
    board.state["answers"] = [LATER]

    await flow_module._flow(_FakeApp(), _FakeScreen())

    assert not tally.exists(), "the count does not carry across days"
    assert board.state["shown"], "yesterday's failures do not gate today"


def test_should_ask_rules() -> None:
    newer = "999.0.0" if CURRENT_VERSION != "999.0.0" else "999.0.1"

    assert flow_module._should_ask(UpdateState(latest=newer)) is True
    assert flow_module._should_ask(UpdateState(latest=CURRENT_VERSION)) is False
    assert flow_module._should_ask(UpdateState(latest="")) is False
    assert flow_module._should_ask(UpdateState(latest=newer, skipped_version=newer)) is False
    # "Remind next time" suppresses nothing: the dialog shows on every start
    # while a newer candidate exists (design revision 9).
    assert flow_module._should_ask(UpdateState(latest=newer, force_upgrade=True)) is True


async def test_confirm_starts_the_update_with_the_current_session(board: Any) -> None:
    write_state(board.tmp_path, UpdateState(latest="999.0.0"))
    board.state["answers"] = [flow_module.CONFIRM]

    await flow_module._flow(_FakeApp(), _FakeScreen())

    (session_id, config_dir), *_ = board.state["updates"]
    assert session_id == "sess-1", "the relaunch restores the current session (design Q3)"
    assert config_dir == board.tmp_path


async def test_later_records_nothing_and_stamps_the_check(board: Any) -> None:
    write_state(board.tmp_path, UpdateState(latest="999.0.0"))
    board.state["answers"] = [LATER]

    await flow_module._flow(_FakeApp(), _FakeScreen())

    state = read_state(board.tmp_path)
    assert not hasattr(state, "asked_at"), "remind-next-time must not suppress anything (revision 9)"
    assert state.checked_at > 0, "the check attempt is stamped even though the fetch returns nothing"


async def test_ask_waits_for_the_startup_modal_to_clear() -> None:
    """The dialog must not race the agent-load modal: it eats every Tab while top (revision 11)."""
    from chrys.app.tui.screens.dialogs.agent_load import AgentLoadDialog

    class _StackApp(_FakeApp):
        def __init__(self, stack: list[object]) -> None:
            super().__init__()
            self._stack = stack
            self.pushed: list[object] = []

        @property
        def screen_stack(self) -> list[object]:
            return self._stack

        def push_screen(self, dialog: object, _callback: object | None = None) -> None:
            self.pushed.append(dialog)

    # Covered: _ask must not push the dialog while an AgentLoadDialog is on the stack.
    app = _StackApp([object(), AgentLoadDialog()])
    ask_task = asyncio.create_task(flow_module._ask(app, UpdateState(latest="999.0.0"), now=1.0))
    await asyncio.sleep(0.2)
    assert app.pushed == [], "no dialog while the startup modal covers the stack"

    # The modal clears: the pending _ask proceeds and pushes.
    app._stack.clear()
    for _ in range(50):
        if app.pushed:
            break
        await asyncio.sleep(0.05)
    ask_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await ask_task

    assert len(app.pushed) == 1 and isinstance(app.pushed[0], UpdateConfirmDialog), (
        "the dialog pushes as soon as the stack is clean"
    )


async def test_ask_pushes_at_once_when_the_stack_is_already_clean(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(flow_module, "STARTUP_MODAL_GRACE_SECONDS", 0.0)

    class _CleanApp(_FakeApp):
        def __init__(self) -> None:
            super().__init__()
            self._stack: list[object] = []
            self.pushed: list[object] = []

        @property
        def screen_stack(self) -> list[object]:
            return self._stack

        def push_screen(self, dialog: object, _callback: object | None = None) -> None:
            self.pushed.append(dialog)

    app = _CleanApp()
    ask_task = asyncio.create_task(flow_module._ask(app, UpdateState(latest="999.0.0"), now=1.0))
    for _ in range(50):
        if app.pushed:
            break
        await asyncio.sleep(0.05)
    ask_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await ask_task

    assert len(app.pushed) == 1, "a clean stack shows the dialog without waiting"


async def test_skip_records_the_version(board: Any) -> None:
    write_state(board.tmp_path, UpdateState(latest="999.0.0"))
    board.state["answers"] = [flow_module.SKIP]

    await flow_module._flow(_FakeApp(), _FakeScreen())

    state = read_state(board.tmp_path)
    assert state.skipped_version == "999.0.0"


async def test_fresh_check_updates_the_cache(board: Any) -> None:
    write_state(board.tmp_path, UpdateState(checked_at=time.time()))  # fresh: no re-check
    board.state["found"] = [flow_module.AppUpdate(version="999.0.0", download_url="http://m/x.zip")]

    await flow_module._flow(_FakeApp(), _FakeScreen())

    assert board.state["found"], "a fresh cache does not trigger a network check (the stub stays unconsumed)"
    assert read_state(board.tmp_path).latest == ""

    # Now with a stale cache, the fetch result lands in the state and re-asks.
    write_state(board.tmp_path, UpdateState(checked_at=time.time() - 2 * DAY))
    board.state["answers"] = [None, LATER]

    await flow_module._flow(_FakeApp(), _FakeScreen())

    state = read_state(board.tmp_path)
    assert state.latest == "999.0.0", "the fetched candidate is cached for tomorrow"
