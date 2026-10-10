# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Tests for the status-bar model indicator state computation."""

from __future__ import annotations

from chrys.app.tui.screens.main.model_indicator import compute_model_indicator_state
from chrys.foundation.events.types import RuntimeModelDetails
from chrys.foundation.i18n import Localizer
from chrys.service.profiles.models.registry import ModelProfileRegistry
from chrys.service.profiles.models.schema import API_STYLE_CHAT_COMPLETIONS, ModelProfile


def _profile(profile_id: str, name: str) -> ModelProfile:
    return ModelProfile(
        id=profile_id,
        name=name,
        provider="openai",
        api_style=API_STYLE_CHAT_COMPLETIONS,
        model_id="openai/gpt-test",
    )


def _details(name: str, profile_id: str = "p1") -> RuntimeModelDetails:
    return RuntimeModelDetails(
        profile_id=profile_id,
        name=name,
        provider="openai",
        api_style=API_STYLE_CHAT_COMPLETIONS,
        model_id="openai/gpt-test",
        selection_source="active",
    )


def test_label_tracks_registry_when_profile_renamed() -> None:
    """A catalog sync can rewrite the profile file; the label must follow it."""
    registry = ModelProfileRegistry()
    registry.register(_profile("p1", "New Name"))

    state = compute_model_indicator_state(
        _details("Old Name"),
        has_selectable_profile=True,
        agent_label="agent",
        localizer=Localizer("en"),
        model_registry=registry,
    )

    assert state.label == "New Name"


def test_label_falls_back_to_details_when_profile_removed() -> None:
    """When the active profile disappears from the registry, the snapshot name still displays."""
    state = compute_model_indicator_state(
        _details("Snapshot Name"),
        has_selectable_profile=True,
        agent_label="agent",
        localizer=Localizer("en"),
        model_registry=ModelProfileRegistry(),
    )

    assert state.label == "Snapshot Name"


def test_label_uses_details_without_registry() -> None:
    """Callers that pass no registry keep the previous behavior."""
    state = compute_model_indicator_state(
        _details("Snapshot Name"),
        has_selectable_profile=True,
        agent_label="agent",
        localizer=Localizer("en"),
    )

    assert state.label == "Snapshot Name"
