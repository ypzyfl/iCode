# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Legacy telemetry settings and shared wire fields."""

from __future__ import annotations

import asyncio
import json
import subprocess
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


def test_legacy_endpoint_and_disable_precedence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from chrys.service.aixcoding.telemetry.context import load_settings

    (tmp_path / "aixcoding.yaml").write_text(
        "profile: LOCAL\ncustomServerUrl: https://override.invalid/ignored\ntoolParamMode: bogus\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("AIXCODING_EXTENSION_BASE_URL", raising=False)
    monkeypatch.delenv("AIXCODING_EXTENSION_PROFILE", raising=False)
    monkeypatch.setenv("AIXCODING_TELEMETRY_DISABLED", "yes")
    settings = load_settings(tmp_path)
    assert settings.base_url == "https://override.invalid/csas"
    assert settings.full_mode
    assert not settings.enabled
    monkeypatch.setenv("AIXCODING_EXTENSION_BASE_URL", "https://explicit.invalid/api")
    assert load_settings(tmp_path).base_url == "https://explicit.invalid/api"


def test_common_fields_keep_desktop_identity_and_omit_missing_git_fields() -> None:
    from chrys.service.aixcoding.telemetry.context import Channel, GitInfo, common_fields

    fields = common_fields(
        "/work/project",
        channel=Channel("desktop", "studio", "2"),
        user_id="employee",
        git=GitInfo(remote="https://example.invalid/org/project.git", owner="org", repo="project"),
        version="0.35.2",
    )
    assert fields == {
        "pluginVersion": "0.35.2",
        "userId": "employee",
        "channelType": "desktop",
        "channelName": "studio",
        "channelVersion": "2",
        "projectName": "project",
        "gitRemote": "https://example.invalid/org/project.git",
        "gitOwner": "org",
        "gitRepo": "project",
    }


async def test_token_and_user_identity_follow_the_live_login_on_the_same_bus(monkeypatch, telemetry_capture):
    from chrys.foundation.events.bus import EventBus
    from chrys.foundation.events.types import InvocationToolCallStart
    from chrys.foundation.models.invocations import InvocationOrigin
    from chrys.foundation.platform import get_platform
    from chrys.kernel.aixcoding.auth.types import StoredCredential
    from chrys.orchestration.aixcoding.telemetry.lifecycle import attach, detach

    config = get_platform().config_dir
    config.mkdir(parents=True)
    (config / "aixcoding.yaml").write_text("token: config-token\nuserId: config-user\n", encoding="utf-8")
    login = telemetry_capture.login
    bus = EventBus()
    origin = InvocationOrigin("turn", "credential-session", "turn-one", None)

    def sign_in(token, user_id):
        login.store.store(
            login.environment, StoredCredential.issued_now(environment_id="local", token=token, user_id=user_id)
        )

    async def report(call_id, expected_token, expected_user):
        await bus.publish(
            InvocationToolCallStart(origin=origin, call_id=call_id, tool_name="read_file"),
            raise_handler_errors=True,
        )
        save = await asyncio.wait_for(telemetry_capture.received.get(), 2)
        pending = await asyncio.wait_for(telemetry_capture.received.get(), 2)
        assert save.url.path.endswith("/tool-detail/save")
        assert pending.url.path.endswith("/tool-detail/update")
        assert save.headers["token"] == pending.headers["token"] == expected_token
        assert json.loads(save.content)["userId"] == expected_user

    await attach(bus)
    try:
        await report("config", "config-token", "config-user")
        sign_in("login-one", "user-one")
        await report("login", "login-one", "user-one")
        monkeypatch.setenv("AIXCODING_TOKEN", "override-token")
        sign_in("login-two", "user-two")
        await report("override", "override-token", "user-two")
        monkeypatch.delenv("AIXCODING_TOKEN")
        await report("switched", "login-two", "user-two")
        login.store.clear(login.environment)
        await report("cleared", "config-token", "config-user")
    finally:
        await detach(bus)
    assert len(telemetry_capture.clients) == 1


@pytest.mark.parametrize(
    ("remotes", "expected_remote", "branch"),
    [
        ("first\norigin\ncnb\n", "cnb", "main"),
        ("first\norigin\n", "origin", "main"),
        ("first\nother\n", "first", "HEAD"),
    ],
)
async def test_git_remote_precedence_and_detached_head(
    tmp_path,
    monkeypatch,
    remotes,
    expected_remote,
    branch,
    telemetry_capture,
    telemetry_engine,
    telemetry_provider,
):
    from chrys.foundation.events.types import UserMessage
    from chrys.service.aixcoding.telemetry import context

    remote = f"git@example.invalid:team/{expected_remote}.git"
    answers = {
        ("rev-parse", "HEAD"): "abc123",
        ("rev-parse", "--abbrev-ref", "HEAD"): branch,
        ("remote",): remotes,
        ("remote", "get-url", expected_remote): remote,
        ("config", "user.name"): "Git Name",
        ("config", "user.email"): "git@example.invalid",
    }

    def read_git(args, *, cwd, stdin, **kwargs):
        assert cwd == tmp_path.resolve()
        assert stdin == subprocess.DEVNULL
        return subprocess.CompletedProcess(args, 0, stdout=answers[tuple(args[1:])].encode())

    monkeypatch.setattr(context, "subprocess", SimpleNamespace(run=read_git, DEVNULL=subprocess.DEVNULL))
    target = tmp_path / "git-fields.py"
    telemetry_provider.call("git-fields", "write_file", {"path": str(target), "content": "answer = 42\n"})
    engine = telemetry_engine.build()
    try:
        await engine.start(telemetry_engine.profile)
        await engine.event_bus.publish(UserMessage(text="Write the file."), raise_handler_errors=True)
        await asyncio.wait_for(engine.wait_for_run_task(), 10)
    finally:
        await engine.shutdown()

    model_fields = json.loads(telemetry_provider.requests[0].content)["telemetry"]
    save, _, _, code = [json.loads(request.content) for request in telemetry_capture.requests]
    common_fields = {
        "gitRemote": remote,
        "gitOwner": "team",
        "gitRepo": expected_remote,
        "gitRevision": "abc123",
    }
    code_fields = {
        "remoteUrl": remote,
        "gitUserName": "Git Name",
        "gitUserEmail": "git@example.invalid",
    }
    if branch == "HEAD":
        assert all("gitBranch" not in fields for fields in (model_fields, save, code))
        assert "branch" not in code
    else:
        common_fields["gitBranch"] = branch
        code_fields["branch"] = branch
    for fields in (model_fields, save, code):
        assert {name: fields[name] for name in common_fields} == common_fields
    assert {name: code[name] for name in code_fields} == code_fields
