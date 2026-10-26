# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Workspace path attribution in AIxCoding model telemetry."""

from __future__ import annotations

import pytest

from chrys.aixcoding.telemetry.acp_meta import read_ide_channel_meta
from chrys.aixcoding.telemetry.llm_telemetry import AixTelemetryMiddleware
from chrys.aixcoding.telemetry.reporters import common_fields
from chrys.kernel.middleware import ChatContext


def test_model_telemetry_omits_project_and_git_without_workspace(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    context = ChatContext(client=None, messages=[], options={})

    AixTelemetryMiddleware(session_id="session", workspace_cwd=None)._inject_telemetry(context, "request", "")

    telemetry = context.options["extra_body"]["telemetry"]
    assert "projectName" not in telemetry
    assert all(key not in telemetry for key in ("gitRemote", "gitBranch", "gitRevision", "gitOwner", "gitRepo"))


def test_model_telemetry_uses_explicit_workspace(tmp_path) -> None:
    project = tmp_path / "chosen-project"
    project.mkdir()
    context = ChatContext(client=None, messages=[], options={})

    AixTelemetryMiddleware(session_id="session", workspace_cwd=str(project))._inject_telemetry(context, "request", "")

    assert context.options["extra_body"]["telemetry"]["projectName"] == "chosen-project"


@pytest.mark.parametrize("args", [[], ["-s", "session"], ["run", "prompt"], ["serve"], ["acp"]])
def test_cli_model_telemetry_uses_icode_channel_name(monkeypatch, args) -> None:
    monkeypatch.setattr("sys.argv", ["aixcoding-cli", *args])
    monkeypatch.setattr("chrys.aixcoding.context._desktop_channel", None)
    context = ChatContext(client=None, messages=[], options={})

    AixTelemetryMiddleware(session_id="session")._inject_telemetry(context, "request", "")

    telemetry = context.options["extra_body"]["telemetry"]
    assert telemetry["channelType"] == "cli"
    assert telemetry["channelName"] == "icode"


@pytest.mark.parametrize("args", [[], ["-s", "session"], ["run", "prompt"], ["serve"], ["acp"]])
@pytest.mark.parametrize("tool_detail", [False, True])
def test_cli_reporter_telemetry_uses_icode_channel_name(monkeypatch, args, tool_detail) -> None:
    monkeypatch.setattr("sys.argv", ["aixcoding-cli", *args])
    monkeypatch.setattr("chrys.aixcoding.context._desktop_channel", None)

    fields = common_fields(tool_detail=tool_detail)

    assert fields["channelType"] == "cli"
    assert fields["channelName"] == "icode"


@pytest.mark.parametrize("tool_detail", [False, True])
def test_desktop_reporter_telemetry_preserves_client_channel(monkeypatch, tool_detail) -> None:
    monkeypatch.setattr("chrys.aixcoding.context._desktop_channel", None)
    read_ide_channel_meta(
        {
            "agent-studio.dev/ide-name": {"schemaVersion": 1, "ideName": "AgentStudio"},
            "agent-studio.dev/ide-version": {"schemaVersion": 1, "ideVersion": "1.2.3"},
        }
    )

    fields = common_fields(tool_detail=tool_detail)

    assert fields["channelType"] == "desktop"
    assert fields["channelName"] == "AgentStudio"
    assert fields["channelVersion"] == "1.2.3"


def test_desktop_icode_model_telemetry_uses_icode_channel_name(monkeypatch) -> None:
    monkeypatch.setattr("chrys.aixcoding.context._desktop_channel", None)
    context = ChatContext(client=None, messages=[], options={})
    read_ide_channel_meta(
        {
            "agent-studio.dev/ide-name": {"schemaVersion": 1, "ideName": "desktop"},
            "agent-studio.dev/ide-version": {"schemaVersion": 1, "ideVersion": "1.2.3"},
        }
    )

    AixTelemetryMiddleware(session_id="session")._inject_telemetry(context, "request", "")

    telemetry = context.options["extra_body"]["telemetry"]
    assert telemetry["channelType"] == "desktop"
    assert telemetry["channelName"] == "icode"
    assert telemetry["channelVersion"] == "1.2.3"
