# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Workspace path attribution in AIxCoding model telemetry."""

from __future__ import annotations

from chrys.aixcoding.telemetry.llm_telemetry import AixTelemetryMiddleware
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
