# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Contract tests for the release-check client, driven by the real update mock.

The mock (``aixcoding/mock/update/server.py``) freezes the wire contract, so
these run a true loopback server on an ephemeral port and assert the client
against every contract branch: the strict-mode 400s, 200/204/304, the
malformed-response drills, the ``forceUpgrade`` flag, and the tier/base_url
resolution (with the drift pin against auth's tier table).

Design: aixcoding/docs/batches/auto-update/design.md §3.1, §10
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterator
from types import SimpleNamespace
from typing import Any

import pytest
from aixcoding.mock.update.server import MockUpdateConfig, create_server

from chrys.service.aixcoding.update import client as client_module
from chrys.service.aixcoding.update.client import (
    AppUpdate,
    build_query_params,
    check_for_update,
    check_url,
    resolve_check_base,
)

CURRENT = "0.35.1"


@pytest.fixture
def mock_factory() -> Iterator[Callable[..., Any]]:
    """Start mocks on demand (port 0, background thread) and reap them all."""
    servers: list[Any] = []

    def _factory(**kwargs: Any) -> Any:
        config = kwargs.pop("config", None) or MockUpdateConfig(**kwargs)
        server = create_server(config, port=0)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        thread.start()
        servers.append(server)
        return server

    yield _factory
    for server in servers:
        server.shutdown()
        server.server_close()


def _point_at(monkeypatch: pytest.MonkeyPatch, base_url: str) -> None:
    """Stub the config snapshot so the client resolves to the mock's base."""
    cfg = SimpleNamespace(environment="local", update=SimpleNamespace(base_url=base_url))
    monkeypatch.setattr(client_module, "load_config", lambda: cfg)


async def _check(monkeypatch: pytest.MonkeyPatch, server: Any) -> AppUpdate | None:
    _point_at(monkeypatch, f"{server.mock_config.base_url}/csas")
    return await check_for_update(current_version=CURRENT)


async def test_update_mode_returns_manifest(monkeypatch: pytest.MonkeyPatch, mock_factory: Callable[..., Any]) -> None:
    server = mock_factory(version="0.36.0")
    found = await _check(monkeypatch, server)

    assert found is not None
    assert found.version == "0.36.0"
    assert found.download_url == server.mock_config.artifact_url()
    assert found.force_upgrade is False


async def test_force_upgrade_flag_is_consumed(
    monkeypatch: pytest.MonkeyPatch, mock_factory: Callable[..., Any]
) -> None:
    server = mock_factory(version="0.36.0", force_upgrade=True)

    found = await _check(monkeypatch, server)

    assert found is not None and found.force_upgrade is True


@pytest.mark.parametrize(
    "kwargs",
    [
        pytest.param({"mode": "no_update"}, id="no-update-mode"),
        pytest.param({"version": CURRENT}, id="same-version"),
        pytest.param({"version": "0.1.0"}, id="older-candidate"),
        pytest.param({"mode": "error"}, id="server-error"),
        pytest.param({"mode": "garbage"}, id="garbage-body"),
        pytest.param({"version": "0.36.0", "drop_fields": ["version"]}, id="missing-version"),
        pytest.param({"version": "0.36.0", "drop_fields": ["artifact.url"]}, id="missing-artifact-url"),
        pytest.param({"version": "0.36.0", "raw_body": '{"version": "0.36.0", "arti'}, id="truncated-body"),
    ],
)
async def test_silent_branches_return_none(
    monkeypatch: pytest.MonkeyPatch, mock_factory: Callable[..., Any], kwargs: dict[str, Any]
) -> None:
    server = mock_factory(**kwargs)

    assert await _check(monkeypatch, server) is None


async def test_invalid_current_version_makes_no_request(
    monkeypatch: pytest.MonkeyPatch, mock_factory: Callable[..., Any]
) -> None:
    server = mock_factory(version="0.36.0")
    _point_at(monkeypatch, f"{server.mock_config.base_url}/csas")

    assert await check_for_update(current_version="not-semver") is None
    assert server.mock_state.requests() == [], "an unbuildable query must not reach the wire"


async def test_query_params_reach_the_wire(monkeypatch: pytest.MonkeyPatch, mock_factory: Callable[..., Any]) -> None:
    server = mock_factory(version="0.36.0")

    await _check(monkeypatch, server)

    (request,) = server.mock_state.requests()
    query = request["query"]
    assert query["clientType"] == "cli"
    assert query["currentVersion"] == CURRENT
    assert query["platform"] and query["architecture"], "the platform/arch mapping must fill both"


async def test_total_timeout_bounds_a_slow_answer(
    monkeypatch: pytest.MonkeyPatch, mock_factory: Callable[..., Any]
) -> None:
    server = mock_factory(version="0.36.0", slow_ms=4000)
    _point_at(monkeypatch, f"{server.mock_config.base_url}/csas")
    monkeypatch.setattr(client_module, "_TIMEOUT_SECONDS", 0.3)

    started = time.monotonic()
    assert await check_for_update(current_version=CURRENT) is None
    assert time.monotonic() - started < 2.0, "the 15s budget must be cut short by the test override"


@pytest.mark.parametrize(
    ("environment", "expected"),
    [
        pytest.param("local", "http://127.0.0.1:7778/csas", id="local-mock"),
        pytest.param("dev", "http://81.89.182.150/csas", id="dev"),
        pytest.param("prod", "http://82.187.34.98/csas", id="prod"),
        pytest.param("unknown", "http://82.187.34.98/csas", id="unknown-falls-back-to-prod"),
    ],
)
def test_tier_bases(monkeypatch: pytest.MonkeyPatch, environment: str, expected: str) -> None:
    cfg = SimpleNamespace(environment=environment, update=SimpleNamespace(base_url=""))
    monkeypatch.setattr(client_module, "load_config", lambda: cfg)

    assert resolve_check_base() == expected
    assert check_url() == f"{expected}/api/v2/releases/check"


def test_explicit_base_url_wins_over_the_tier(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = SimpleNamespace(environment="prod", update=SimpleNamespace(base_url="http://10.0.0.9/csas"))
    monkeypatch.setattr(client_module, "load_config", lambda: cfg)

    assert resolve_check_base() == "http://10.0.0.9/csas"


def test_tier_hosts_match_auth() -> None:
    """Drift pin: dev/prod release-check bases share auth's tier hosts (design §2)."""
    from urllib.parse import urlsplit

    from chrys.kernel.aixcoding.auth.environments import _BASE_PATHS
    from chrys.kernel.aixcoding.auth.types import Environment

    assert urlsplit(client_module._TIER_BASES["prod"]).netloc == urlsplit(_BASE_PATHS[Environment.PROD][0]).netloc
    assert urlsplit(client_module._TIER_BASES["dev"]).netloc == urlsplit(_BASE_PATHS[Environment.DEV][0]).netloc


def test_build_query_params_rejects_unmappable_version() -> None:
    assert build_query_params("v1.2") is None
    assert build_query_params("1.2.3.4") is None
    assert build_query_params("") is None

    params = build_query_params("0.35.1-dev-abc123")
    assert params is not None and params["currentVersion"] == "0.35.1-dev-abc123"
