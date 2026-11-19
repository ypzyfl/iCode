# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Keep installation paths out of the final enterprise projectName field."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest


@pytest.fixture
def packaged_paths(tmp_path, monkeypatch):
    from chrys.service.aixcoding.telemetry import context

    launcher_dir = tmp_path / "installed" / "aixcoding"
    version_dir = tmp_path / "runtime" / "0.35.2"
    prefix = version_dir / "python"
    executable_dir = prefix / "bin"
    scripts_dir = prefix / "Scripts"
    project = tmp_path / "projects" / "aixcoding"
    runtime_child = prefix / "lib" / "python3.14" / "site-packages"
    for path in (launcher_dir, executable_dir, scripts_dir, project, runtime_child):
        path.mkdir(parents=True)
    monkeypatch.setenv("PYAPP", str(launcher_dir / "aixcoding-cli"))
    monkeypatch.setattr(
        context,
        "sys",
        SimpleNamespace(
            prefix=str(prefix),
            exec_prefix=str(prefix),
            executable=str(executable_dir / "python3"),
            argv=[str(launcher_dir / "aixcoding-cli")],
        ),
    )
    return SimpleNamespace(
        launcher=launcher_dir,
        version=version_dir,
        prefix=prefix,
        executable=executable_dir,
        project=project,
        runtime_child=runtime_child,
        scripts=scripts_dir,
    )


@pytest.mark.parametrize(
    "location", ["launcher", "version", "prefix", "executable", "scripts", "runtime_child", "project"]
)
def test_project_name_rejects_current_installation_but_keeps_a_real_project(packaged_paths, location):
    from chrys.service.aixcoding.telemetry.context import Channel, GitInfo, common_fields

    fields = common_fields(
        str(getattr(packaged_paths, location)),
        channel=Channel("cli", "icode-tui"),
        git=GitInfo(branch="unchanged-branch", revision="unchanged-revision"),
    )
    assert fields["projectName"] == ("aixcoding" if location == "project" else "")
    assert fields["gitBranch"] == "unchanged-branch"
    assert fields["gitRevision"] == "unchanged-revision"


def test_project_name_recognizes_a_symlink_to_the_launcher_directory(tmp_path, packaged_paths, monkeypatch):
    from pathlib import Path

    from chrys.service.aixcoding.telemetry.context import Channel, common_fields

    alias = tmp_path / "install-alias"
    resolve = Path.resolve

    def resolve_alias(path, *args, **kwargs):
        return packaged_paths.launcher if path == alias else resolve(path, *args, **kwargs)

    # Simulate OS path canonicalization without requiring symlink privileges.
    monkeypatch.setattr(Path, "resolve", resolve_alias)
    assert common_fields(str(alias), channel=Channel("cli", "icode-tui"))["projectName"] == ""


@pytest.mark.parametrize("location", ["prefix", "executable", "project"])
def test_project_name_excludes_interpreter_installation_without_pyapp(packaged_paths, monkeypatch, location):
    from chrys.service.aixcoding.telemetry.context import Channel, common_fields

    monkeypatch.delenv("PYAPP")
    fields = common_fields(str(getattr(packaged_paths, location)), channel=Channel("cli", "icode-tui"))
    assert fields["projectName"] == ("aixcoding" if location == "project" else "")


def test_project_name_excludes_both_the_launcher_symlink_directory_and_its_target(
    tmp_path, packaged_paths, monkeypatch
):
    from pathlib import Path

    from chrys.service.aixcoding.telemetry.context import Channel, common_fields

    alias_dir = tmp_path / "command-alias"
    alias_dir.mkdir()
    alias = alias_dir / "aixcoding-cli"
    resolve = Path.resolve

    def resolve_alias(path, *args, **kwargs):
        return packaged_paths.launcher / "aixcoding-cli" if path == alias else resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", resolve_alias)
    monkeypatch.setenv("PYAPP", str(alias))
    for path in (alias_dir, packaged_paths.launcher):
        assert common_fields(str(path), channel=Channel("cli", "icode-tui"))["projectName"] == ""


@pytest.mark.parametrize("location", ["launcher", "version", "prefix", "project"])
async def test_final_model_tool_skill_and_code_requests_do_not_use_the_installation_name(
    packaged_paths, location, monkeypatch, telemetry_engine, telemetry_provider, telemetry_capture
):
    from chrys.foundation.events.types import UserMessage
    from chrys.service.profiles.agents.schema import SkillConfig

    workspace = getattr(packaged_paths, location)
    monkeypatch.chdir(packaged_paths.launcher)
    telemetry_engine.workspace.primary_cwd = str(workspace)
    telemetry_engine.profile.skills.inline.append(
        SkillConfig(name="review", description="Review files", instructions="Review carefully.")
    )
    target = workspace / "wire-test.py"
    telemetry_provider.call("write-call", "write_file", {"path": str(target), "content": "answer = 42\n"})
    telemetry_provider.call("skill-call", "load_skill", {"skill_name": "review"})
    engine = telemetry_engine.build()
    try:
        await engine.start(telemetry_engine.profile, workspace=telemetry_engine.workspace)
        await engine.event_bus.publish(UserMessage(text="Write and review."), raise_handler_errors=True)
        await asyncio.wait_for(engine.wait_for_run_task(), 10)
    finally:
        await engine.shutdown()

    assert target.read_text(encoding="utf-8") == "answer = 42\n"
    expected = "aixcoding" if location == "project" else ""
    model_fields = [json.loads(request.content)["telemetry"] for request in telemetry_provider.requests]
    assert len(model_fields) == 3
    assert all(fields["projectName"] == expected for fields in model_fields)
    reports = [(request.url.path, json.loads(request.content)) for request in telemetry_capture.requests]
    saves = [body for path, body in reports if path.endswith("/tool-detail/save")]
    assert sorted(body["funcType"] for body in saves) == [0, 3, 3]
    [code] = [body for path, body in reports if path.endswith("/ai-code/save")]
    assert all(body["projectName"] == expected for body in [*saves, code])
    [skill] = [body for body in saves if body["funcType"] == 0]
    assert skill["requestId"] == model_fields[1]["requestId"]
    assert code["requestId"] == model_fields[0]["requestId"]
