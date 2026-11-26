# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

from __future__ import annotations

import inspect
from pathlib import Path

import httpx
import pytest
from aixcoding.tests.llm_call_interception.support import profile

from chrys.service.aixcoding.llm_call_interception import installer
from chrys.service.aixcoding.llm_call_interception.installer import _install_client_hooks, install_http_interception
from chrys.service.aixcoding.llm_call_interception.interceptor import get_http_policy, set_http_policy
from chrys.service.llm import clients


@pytest.mark.parametrize("raw_log", [False, True])
async def test_install_is_idempotent_and_preserves_factory_signature(
    monkeypatch: pytest.MonkeyPatch, tmp_path, raw_log: bool
) -> None:
    original = clients._build_profile_http_client
    monkeypatch.setattr(clients, "_build_profile_http_client", original)
    install_http_interception()
    wrapped = clients._build_profile_http_client
    install_http_interception()
    set_http_policy(object())  # type: ignore[arg-type]

    assert clients._build_profile_http_client is wrapped
    assert inspect.signature(wrapped, follow_wrapped=False) == inspect.signature(original, follow_wrapped=False)
    assert inspect.unwrap(wrapped) is original
    http = wrapped(
        profile(),
        httpx.Timeout(5),
        raw_http_log_path=tmp_path / "raw.jsonl" if raw_log else None,
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"ok": True})),
    )
    try:
        request_modules = [getattr(hook, "__module__", "") for hook in http.event_hooks["request"]]
        response_modules = [getattr(hook, "__module__", "") for hook in http.event_hooks["response"]]
        custom_module = "chrys.service.aixcoding.llm_call_interception.hooks"
        assert request_modules.count(custom_module) == 1
        assert response_modules.count(custom_module) == 1
        assert request_modules.index(custom_module) > request_modules.index("chrys.service.llm.request_tracking")
        if raw_log:
            assert request_modules.index(custom_module) < request_modules.index("chrys.service.llm.raw_http_log")
            assert response_modules.index(custom_module) > response_modules.index("chrys.service.llm.raw_http_log")
        response = await http.get("http://llm.test/contract")
        assert response.json() == {"ok": True}
        _install_client_hooks(http, provider="openai", model="model-test")
        assert len(http.event_hooks["request"]) == len(request_modules)
    finally:
        await http.aclose()


async def test_empty_policy_factory_preserves_upstream_hooks(monkeypatch: pytest.MonkeyPatch) -> None:
    original = clients._build_profile_http_client
    monkeypatch.setattr(clients, "_build_profile_http_client", original)
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"ok": True}))
    expected = original(profile(), httpx.Timeout(5), transport=transport)
    install_http_interception()
    actual = clients._build_profile_http_client(profile(), httpx.Timeout(5), transport=transport)
    try:

        def shape(client):
            return {
                name: [(getattr(hook, "__module__", ""), getattr(hook, "__name__", "")) for hook in hooks]
                for name, hooks in client.event_hooks.items()
            }

        assert shape(actual) == shape(expected)
        assert not getattr(actual, "_aixcoding_http_interception_hooks", False)
    finally:
        await actual.aclose()
        await expected.aclose()


async def test_nonempty_policy_only_applies_to_clients_created_after_registration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = clients._build_profile_http_client
    monkeypatch.setattr(clients, "_build_profile_http_client", original)
    install_http_interception()
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"ok": True}))
    before = clients._build_profile_http_client(profile(), httpx.Timeout(5), transport=transport)
    set_http_policy(object())  # type: ignore[arg-type]
    after = clients._build_profile_http_client(profile(), httpx.Timeout(5), transport=transport)
    try:
        custom_module = "chrys.service.aixcoding.llm_call_interception.hooks"
        assert all(getattr(hook, "__module__", "") != custom_module for hook in before.event_hooks["request"])
        assert any(getattr(hook, "__module__", "") == custom_module for hook in after.event_hooks["request"])
    finally:
        await before.aclose()
        await after.aclose()


def test_policy_snapshot_is_atomic() -> None:
    first = object()
    second = object()
    set_http_policy(first)  # type: ignore[arg-type]
    assert get_http_policy() is first
    set_http_policy(second)  # type: ignore[arg-type]
    assert get_http_policy() is second


async def test_client_hook_install_failure_is_visible_and_fail_open(
    monkeypatch: pytest.MonkeyPatch, capsys, caplog
) -> None:
    original = clients._build_profile_http_client
    monkeypatch.setattr(clients, "_build_profile_http_client", original)
    install_http_interception()
    set_http_policy(object())  # type: ignore[arg-type]

    def fail_install(*args, **kwargs):
        raise RuntimeError("synthetic install secret")

    monkeypatch.setattr(installer, "_install_client_hooks", fail_install)
    caplog.set_level("WARNING")
    http = clients._build_profile_http_client(
        profile(),
        httpx.Timeout(5),
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b"host-ok")),
    )
    try:
        response = await http.get("http://llm.test")
        assert response.content == b"host-ok"
    finally:
        await http.aclose()

    captured = capsys.readouterr()
    assert captured.err == ""
    assert "HTTP interception installation failed (RuntimeError)" in caplog.text
    assert any(record.name == "aixcoding.llm_call_interception" and record.levelno == 30 for record in caplog.records)
    assert any(
        record.name == "aixcoding.detail.llm_call_interception" and "stage=client_install" in record.getMessage()
        for record in caplog.records
    )
    assert "provider=openai" in caplog.text
    assert "model=model-test" in caplog.text
    assert "synthetic install secret" not in caplog.text


def test_tracking_extension_drift_fails_during_installation(monkeypatch: pytest.MonkeyPatch) -> None:
    from chrys.service.llm import request_tracking

    original = clients._build_profile_http_client
    monkeypatch.setattr(clients, "_build_profile_http_client", original)
    monkeypatch.delattr(request_tracking, "_CONTEXT_EXTENSION")

    with pytest.raises(ImportError):
        install_http_interception()
    assert clients._build_profile_http_client is original


def test_registering_a_policy_installs_the_factory_once() -> None:
    original = clients._build_profile_http_client

    set_http_policy(None)
    assert clients._build_profile_http_client is original

    set_http_policy(object())  # type: ignore[arg-type]
    wrapped = clients._build_profile_http_client
    assert wrapped is not original
    assert inspect.unwrap(wrapped) is original
    set_http_policy(object())  # type: ignore[arg-type]
    assert clients._build_profile_http_client is wrapped


def test_registration_install_failure_is_logged_and_not_raised(monkeypatch: pytest.MonkeyPatch, capsys, caplog) -> None:
    from chrys.service.llm import request_tracking

    original = clients._build_profile_http_client
    monkeypatch.delattr(request_tracking, "_CONTEXT_EXTENSION")
    policy = object()
    caplog.set_level("WARNING")

    set_http_policy(policy)  # type: ignore[arg-type]

    assert get_http_policy() is policy
    assert clients._build_profile_http_client is original
    assert capsys.readouterr().err == ""
    assert "HTTP interception installation failed (ImportError)" in caplog.text
    assert any(record.name == "aixcoding.llm_call_interception" and record.levelno == 30 for record in caplog.records)
    detail = [record for record in caplog.records if record.name == "aixcoding.detail.llm_call_interception"]
    assert any("stage=registration_install" in record.getMessage() for record in detail)
    assert "cannot import name" not in caplog.text


def test_startup_never_references_http_interception() -> None:
    from chrys.app.aixcoding import startup

    assert (startup._configure_environment, startup._ensure_file_sink) == startup._TASKS
    package_dir = Path(startup.__file__).parent
    assert not any("llm_call_interception" in path.read_text(encoding="utf-8") for path in package_dir.rglob("*.py"))
