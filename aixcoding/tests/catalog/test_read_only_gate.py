# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""The model-management restore gate (follow-up to catalog-sync + catalog-custom-coexist).

The model configuration screen is writable again (official 0.35.2 behavior):
user profiles can be created, edited, and deleted, while server-synced
profiles are hidden from the management list and refused on the write paths
(management-screen delete/save and ACP write/delete). The screen opens
read-only only while a turn is busy, and the F4 entry is restored.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from chrys.app.tui.screens.models import screen as model_config_screen_module
from chrys.app.tui.screens.models.screen import ModelConfigScreen
from chrys.foundation.config.errors import ConfigError
from chrys.service.profiles.models.registry import ModelProfileRegistry
from chrys.service.profiles.models.schema import ModelProfile

if TYPE_CHECKING:
    from collections.abc import Coroutine

    from chrys.app.tui.screens.main.config_actions import RuntimeConfigController


def _profile(profile_id: str) -> ModelProfile:
    return ModelProfile(id=profile_id, name=profile_id, provider="openai", model_id=f"{profile_id}-m")


class _NoopCallbacks:
    def __getattr__(self, name: str) -> object:
        return lambda *args, **kwargs: None


def _make_controller(
    monkeypatch: pytest.MonkeyPatch,
    *,
    agent_running: bool = False,
    execution_busy: bool = False,
    submit_active: bool = False,
) -> tuple[RuntimeConfigController, list[ModelConfigScreen], list[Coroutine[object, object, None]]]:
    """Build a controller around stubs, mirroring the idle harness of the gate test.

    ``pushed`` collects screens handed to ``push_screen``; ``captured`` collects
    the coroutines handed to ``run_worker`` (the caller drives them, so the
    real ``_open_model_config`` chain runs under the test's event loop).
    """
    from chrys.app.tui.screens.main.config_actions import RuntimeConfigController as _Controller

    registry = ModelProfileRegistry()
    registry.register(_profile("a"))
    pushed: list[ModelConfigScreen] = []
    captured: list[Coroutine[object, object, None]] = []

    class _View:
        def push_screen(self, screen: ModelConfigScreen, _callback: object = None) -> None:
            pushed.append(screen)

        def run_worker(self, worker: Coroutine[object, object, None], **_kwargs: object) -> None:
            captured.append(worker)

        def notify(self, *_args: object, **_kwargs: object) -> None: ...

        def focus_input(self) -> None: ...

    class _Run:
        agent_running = False
        agent_loading = False

    class _Submit:
        active = False

    _Run.agent_running = agent_running
    _Submit.active = submit_active

    class _State:
        run = _Run()
        submit = _Submit()

    class _Services:
        model_registry = registry

        def execution_busy(self) -> bool:
            return execution_busy

    controller = _Controller.__new__(_Controller)
    controller._view = _View()
    controller._state = _State()
    controller._services = _Services()
    controller._callbacks = _NoopCallbacks()
    controller._model_config_opening = False
    monkeypatch.setattr("chrys.service.profiles.models.env_bridge.get_global_default_profile_id", lambda: None)
    return controller, pushed, captured


@pytest.mark.asyncio
async def test_open_model_config_is_writable_when_idle(monkeypatch: pytest.MonkeyPatch) -> None:
    """Idle (no agent, nothing executing): the management screen opens writable again."""
    controller, pushed, _ = _make_controller(monkeypatch)

    await controller._open_model_config()

    assert len(pushed) == 1
    assert pushed[0]._read_only is False, "idle must restore the writable management screen"


@pytest.mark.parametrize(
    ("agent_running", "execution_busy", "submit_active"),
    [
        pytest.param(True, False, False, id="agent-running"),
        pytest.param(False, True, False, id="execution-busy"),
        pytest.param(False, False, True, id="submit-active"),
        pytest.param(True, True, True, id="all-three"),
    ],
)
@pytest.mark.asyncio
async def test_open_model_config_screen_is_read_only_while_busy(
    monkeypatch: pytest.MonkeyPatch,
    agent_running: bool,
    execution_busy: bool,
    submit_active: bool,
) -> None:
    """Each signal of the upstream conditional gate, alone and combined, opens read-only.

    Upstream decides editability from ``agent_running or submit.active or
    execution_busy()``; the restored screen keeps that exact conditional.
    """
    controller, pushed, _ = _make_controller(
        monkeypatch, agent_running=agent_running, execution_busy=execution_busy, submit_active=submit_active
    )

    await controller._open_model_config()

    assert len(pushed) == 1
    assert isinstance(pushed[0], ModelConfigScreen)
    assert pushed[0]._read_only is True, "a busy turn must still open the screen read-only"


@pytest.mark.asyncio
async def test_model_indicator_configure_entry_opens_writable_screen_when_idle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The indicator's configure entry routes through the real open chain to a writable screen."""
    controller, pushed, captured = _make_controller(monkeypatch)

    controller.on_model_tag_clicked("configure")
    assert captured, "open_model_config must hand the open coroutine to run_worker"
    await captured[0]

    assert len(pushed) == 1
    assert isinstance(pushed[0], ModelConfigScreen)
    assert pushed[0]._read_only is False, "the configure entry opens the same writable screen when idle"


def test_read_only_notice_keeps_upstream_agent_running_wording() -> None:
    """The notice explains the transient agent-session condition, not a management policy."""
    fallback = model_config_screen_module._READ_ONLY_NOTICE.fallback
    assert "Agent is running" in fallback
    assert "centrally managed" not in fallback


def test_f4_binding_present_on_main_screen() -> None:
    """F4 opens the model config again: the footer key is restored."""
    from chrys.app.tui.screens.main.screen import MainScreen

    bindings = {(getattr(binding, "key", None), getattr(binding, "action", None)) for binding in MainScreen.BINDINGS}
    assert ("f4", "models_config") in bindings, "the F4 models_config binding must stay restored"


def test_model_config_screen_hides_server_owned_profiles(monkeypatch: pytest.MonkeyPatch) -> None:
    """Server-synced profiles stay selectable in the picker but leave the management list."""
    registry = ModelProfileRegistry()
    registry.register(_profile("srv-model"))
    registry.register(_profile("user-model"))
    monkeypatch.setattr(
        "chrys.service.aixcoding.models.catalog.server_owned_profile_ids",
        lambda: frozenset({"srv-model"}),
    )
    screen = ModelConfigScreen(registry)

    assert [profile.id for profile in screen._listed_profiles()] == ["user-model"]


@pytest.mark.asyncio
async def test_do_delete_refuses_server_owned_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    """A stale sidebar must not let deletion touch a file the catalog owns."""
    registry = ModelProfileRegistry()
    registry.register(_profile("srv-model"))
    screen = ModelConfigScreen(registry)
    monkeypatch.setattr(
        "chrys.service.aixcoding.models.catalog.is_server_owned_profile_id",
        lambda _profile_id: True,
    )

    with pytest.raises(ConfigError):
        await screen._do_delete("srv-model")


@pytest.mark.asyncio
async def test_save_only_refuses_server_owned_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    """A save landing on a server-synced file would strip the marker — refuse it."""
    registry = ModelProfileRegistry()
    registry.register(_profile("srv-model"))
    screen = ModelConfigScreen(registry)
    screen._selected_profile_id = "srv-model"
    monkeypatch.setattr(
        "chrys.service.aixcoding.models.catalog.is_server_owned_profile_id",
        lambda _profile_id: True,
    )

    with pytest.raises(ConfigError):
        await screen._save_only()
