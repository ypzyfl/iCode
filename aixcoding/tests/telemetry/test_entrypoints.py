# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Exercise telemetry from the headless command and a restored Textual session."""

from __future__ import annotations

import asyncio
import json
import sys
from contextlib import asynccontextmanager
from functools import partial

import pytest

from chrys.foundation.events.types import (
    Error,
    RollbackResult,
    SessionFork,
    SessionForked,
    UserMessage,
    UserRollback,
    Warning,
)


def _saves(capture):
    return [
        json.loads(request.content) for request in capture.requests if request.url.path.endswith("/tool-detail/save")
    ]


def test_headless_command_reports_first_tool_and_drains_at_exit(
    tmp_path,
    monkeypatch,
    capsys,
    telemetry_engine,
    telemetry_provider,
    telemetry_capture,
) -> None:
    from chrys.app.cli import app, headless, run
    from chrys.foundation.config.settings import Settings
    from chrys.foundation.config.settings_store import LoadedSettings
    from chrys.foundation.i18n import Localizer

    target = tmp_path / "headless.py"
    telemetry_provider.call("first-headless", "write_file", {"path": str(target), "content": "answer = 42\n"})
    prepared = headless.PreparedRuntime(
        loaded=LoadedSettings(settings=Settings(model_profile=telemetry_provider.model.id), provenance={}),
        localizer=Localizer("en"),
        pending_warnings=[],
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(headless, "prepare_runtime", lambda **_kwargs: prepared)
    monkeypatch.setattr(
        run,
        "ChrysSessionHost",
        partial(
            run.ChrysSessionHost,
            agent_registry=telemetry_engine.agents,
            model_registry=telemetry_provider.registry,
            state_store=telemetry_engine.store,
        ),
    )
    monkeypatch.setattr(
        sys, "argv", ["aixcoding-cli", "run", "--agent", telemetry_engine.profile.name, "--json", "Write the file."]
    )
    assert app.main() == 0

    output = json.loads(capsys.readouterr().out)
    assert output["result"] == "Finished."
    assert target.read_text(encoding="utf-8") == "answer = 42\n"
    (save,) = _saves(telemetry_capture)
    first = json.loads(telemetry_provider.requests[0].content)["telemetry"]
    assert save["funcId"] == "first-headless"
    assert save["requestId"] == first["requestId"]
    assert save["sessionId"] == first["sessionId"] == output["session_id"]
    assert save["channelName"] == "icode"
    assert "channelVersion" not in save
    assert [request.url.path.split("/api/v1/")[1] for request in telemetry_capture.requests] == [
        "tool-detail/save",
        "tool-detail/update",
        "tool-detail/update",
        "ai-code/save",
    ]
    (client,) = telemetry_capture.clients
    assert client.is_closed


@pytest.mark.parametrize(
    ("target_turn", "refresh_schedule"),
    [
        (0, "idle"),
        (1, "idle"),
        (1, "refresh-after-swap"),
        (1, "in-flight-save"),
        (1, "cancelled-refresh"),
    ],
    ids=["session-start", "keep-first-turn", "refresh-after-swap", "in-flight-save", "cancelled-refresh"],
)
async def test_tui_restore_fork_and_rollback_replay_only_report_new_execution(
    target_turn,
    refresh_schedule,
    tmp_path,
    monkeypatch,
    telemetry_engine,
    telemetry_provider,
    telemetry_capture,
) -> None:
    from chrys.app.tui.app import ChrysApp
    from chrys.app.tui.screens.main.screen import MainScreen
    from chrys.app.tui.util.git_branch import GitBranchMonitor
    from chrys.app.tui.widgets.chat.messages import UserMessage as UserMessageWidget
    from chrys.app.tui.widgets.chat.panel import ChatPanel
    from chrys.app.tui.widgets.chat.tool_call import ToolGroup
    from chrys.app.tui.widgets.chrome.input_bar import InputBar
    from chrys.orchestration.engine.session_lifecycle import SessionLifecycle
    from chrys.orchestration.engine.trajectory import TrajectoryRecorder

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["aixcoding-cli"])
    # The status bar's native watcher is outside the telemetry and replay paths.
    monkeypatch.setattr(GitBranchMonitor, "_start_observer", lambda _monitor, _target: None)
    target = tmp_path / "history.py"
    forked = []
    source = telemetry_engine.build()

    async def record_fork(event: SessionForked) -> None:
        forked.append(event)

    await source.event_bus.subscribe(SessionForked, record_fork)
    try:
        await source.start(telemetry_engine.profile)
        tool_calls = [
            ("write_file", {"path": str(target), "content": "v = 1\n"}),
            ("edit_file", {"path": str(target), "old_string": "v = 1", "new_string": "v = 2"}),
        ]
        for index, (name, arguments) in enumerate(tool_calls, 1):
            telemetry_provider.call(f"source-{index}", name, arguments)
            await source.event_bus.publish(UserMessage(text=f"History turn {index}."), raise_handler_errors=True)
            await asyncio.wait_for(source.wait_for_run_task(), 10)
            assert target.read_text(encoding="utf-8") == f"v = {index}\n"
        await source.event_bus.publish(SessionFork(session_id=source.session_id), raise_handler_errors=True)
    finally:
        await source.shutdown()

    (fork,) = forked
    assert fork.new_session_id != fork.parent_session_id
    assert [item["funcId"] for item in _saves(telemetry_capture)] == ["source-1", "source-2"]
    assert len(telemetry_capture.requests) == 8
    assert len(telemetry_provider.requests) == 4

    restored = telemetry_engine.build()
    rollbacks = []
    diagnostics = []

    async def record_rollback(event: RollbackResult) -> None:
        rollbacks.append(event)

    async def record_diagnostic(event: Error | Warning) -> None:
        diagnostics.append((event.code, event.message))

    await restored.event_bus.subscribe(RollbackResult, record_rollback)
    await restored.event_bus.subscribe(Error, record_diagnostic)
    await restored.event_bus.subscribe(Warning, record_diagnostic)
    app = ChrysApp(
        restored.event_bus,
        restored,
        settings_handle=restored.settings_handle,
        profile_name=telemetry_engine.profile.name,
        state_store=telemetry_engine.store,
        agent_registry=telemetry_engine.agents,
        model_registry=telemetry_provider.registry,
        startup_session_id=fork.new_session_id,
        gc_freeze_enabled=False,
    )
    try:
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            startup = app._startup_task
            assert startup is not None
            await asyncio.wait_for(asyncio.shield(startup), 15)

            async def wait_for_main() -> None:
                async with asyncio.timeout(5):
                    while not isinstance(app.screen, MainScreen):
                        await pilot.pause(0.05)

            await wait_for_main()
            panel = app.screen.query_one(ChatPanel)
            await asyncio.wait_for(panel.wait_replay_complete(), 10)
            assert restored.session_id == fork.new_session_id
            assert len(panel.query(UserMessageWidget)) == 2
            assert len(panel.query(ToolGroup)) == 2
            assert len(telemetry_capture.requests) == 8
            assert len(telemetry_provider.requests) == 4

            turn_ids = [turn.turn_id for turn in restored.turn_records()]
            session_file = telemetry_engine.store.session_dir(fork.new_session_id) / "session.json"
            backup_file = session_file.with_name("session.json.bak")

            def persisted_turns():
                return tuple(
                    json.loads(path.read_text(encoding="utf-8"))["state"]["turn_counter"]
                    for path in (session_file, backup_file)
                )

            if refresh_schedule != "idle":
                coordinator = restored.mutation_coordinator
                assert coordinator is not None
                refresh_task = None

                # Force a pending mutation classification only for the refresh under test.
                monkeypatch.setattr(
                    coordinator, "consume_unsaved_reclassification", lambda: asyncio.current_task() is refresh_task
                )

            async def publish_rollback():
                await restored.event_bus.publish(
                    UserRollback(session_id=fork.new_session_id, target_turn=target_turn, revert_changes=False),
                    raise_handler_errors=True,
                )

            if refresh_schedule == "refresh-after-swap":
                record_trajectory = TrajectoryRecorder.rollback

                async def refresh_after_swap(recorder, **kwargs):
                    nonlocal refresh_task
                    assert persisted_turns() == (1, 1)
                    refresh_task = asyncio.create_task(restored.refresh_mutation_attribution(force=True))
                    await asyncio.wait_for(refresh_task, 5)
                    await record_trajectory(recorder, **kwargs)

                monkeypatch.setattr(TrajectoryRecorder, "rollback", refresh_after_swap)
                await publish_rollback()
            elif refresh_schedule in {"in-flight-save", "cancelled-refresh"}:
                save_started = asyncio.Event()
                release_save = asyncio.Event()
                save_finished = asyncio.Event()
                drain_started = asyncio.Event()
                drain_finished = asyncio.Event()
                save_session = telemetry_engine.store.save_session
                pause_saves = SessionLifecycle.pause_mutation_attribution_saves

                async def hold_save(session_id, state, **kwargs):
                    if session_id != fork.new_session_id or save_started.is_set():
                        return await save_session(session_id, state, **kwargs)
                    assert state["turn_counter"] == 2
                    save_started.set()
                    await release_save.wait()
                    assert persisted_turns() == (2, 2)
                    checkpoint = await save_session(session_id, state, **kwargs)
                    save_finished.set()
                    return checkpoint

                @asynccontextmanager
                async def observe_drain(lifecycle):
                    drain_started.set()
                    async with pause_saves(lifecycle):
                        drain_finished.set()
                        assert save_finished.is_set()
                        yield

                monkeypatch.setattr(telemetry_engine.store, "save_session", hold_save)
                monkeypatch.setattr(SessionLifecycle, "pause_mutation_attribution_saves", observe_drain)
                async with asyncio.timeout(10), asyncio.TaskGroup() as tasks:
                    try:
                        refresh_task = tasks.create_task(restored.refresh_mutation_attribution(force=True))
                        await save_started.wait()
                        if refresh_schedule == "cancelled-refresh":
                            refresh_task.cancel()
                        tasks.create_task(publish_rollback())
                        await drain_started.wait()
                        assert not drain_finished.is_set()
                        assert persisted_turns() == (2, 2)
                    finally:
                        release_save.set()
                assert save_finished.is_set()
                assert refresh_task.cancelled() == (refresh_schedule == "cancelled-refresh")
            else:
                await publish_rollback()

            assert len(rollbacks) == 1, diagnostics
            assert [turn.turn_id for turn in restored.turn_records()] == turn_ids[:target_turn]
            if target_turn:
                assert persisted_turns() == (target_turn, target_turn)
            await wait_for_main()
            try:
                async with asyncio.timeout(5):
                    while (len(panel.query(UserMessageWidget)), len(panel.query(ToolGroup))) != (target_turn,) * 2:
                        await pilot.pause(0.05)
            except TimeoutError as exc:
                raise AssertionError(
                    f"rollback rendered {len(panel.query(UserMessageWidget))} user turns, "
                    f"{len(panel.query(ToolGroup))} tool groups; "
                    f"engine retained {len(restored.turn_records())} turns; {diagnostics=}"
                ) from exc
            await asyncio.wait_for(panel.wait_replay_complete(), 10)
            (rollback,) = rollbacks
            assert rollback.target_turn == target_turn
            assert rollback.discarded_turn_count == 2 - target_turn
            assert rollback.superseded_turn_ids == turn_ids[target_turn:]
            assert len(panel.query(UserMessageWidget)) == target_turn
            assert len(panel.query(ToolGroup)) == target_turn
            assert len(telemetry_capture.requests) == 8
            assert len(telemetry_provider.requests) == 4
            assert target.read_text(encoding="utf-8") == "v = 2\n"

            telemetry_provider.call(
                "source-2", "edit_file", {"path": str(target), "old_string": "v = 2", "new_string": "v = 3"}
            )
            composer = app.screen.query_one(InputBar)
            composer.value = "A new execution after rollback."
            await composer.action_submit()
            await pilot.pause()
            await asyncio.wait_for(restored.wait_for_run_task(), 10)
            assert target.read_text(encoding="utf-8") == "v = 3\n"
    finally:
        await restored.shutdown()

    first, second, new = _saves(telemetry_capture)
    assert len(telemetry_capture.requests) == 12
    assert len(telemetry_provider.requests) == 6
    assert first["sessionId"] == second["sessionId"] == fork.parent_session_id
    assert new["sessionId"] == fork.new_session_id
    assert new["funcId"] == second["funcId"] == "source-2"
    first_live_model = json.loads(telemetry_provider.requests[4].content)["telemetry"]
    assert new["requestId"] == first_live_model["requestId"] != second["requestId"]
    assert new["channelVersion"] == new["pluginVersion"]
