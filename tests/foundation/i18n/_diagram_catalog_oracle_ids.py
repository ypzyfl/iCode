# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Pinned diagram and markdown message ids extending the live catalog oracle."""

from __future__ import annotations

DIAGRAM_MESSAGE_IDS = frozenset(
    {
        "tui.diagram.copied_source",
        "tui.diagram.diagnostic.conflicting_declaration",
        "tui.diagram.diagnostic.empty_source",
        "tui.diagram.diagnostic.error_at_line",
        "tui.diagram.diagnostic.invalid_syntax",
        "tui.diagram.diagnostic.limit_exceeded",
        ("tui.diagram.diagnostic.more", "tui.diagram.diagnostic.more#plural"),
        "tui.diagram.diagnostic.no_nodes",
        "tui.diagram.diagnostic.unable_to_render",
        "tui.diagram.diagnostic.unsupported_type",
        "tui.diagram.diagnostic.warning_at_line",
        "tui.diagram.presentation.architecture_layout",
        "tui.diagram.presentation.sankey_layout",
        "tui.diagram.title",
        "tui.diagram.view_hint",
        "tui.markdown.diagram.open",
    }
)
