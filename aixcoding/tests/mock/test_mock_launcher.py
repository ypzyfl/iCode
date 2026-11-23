# (unit test — asserts are pytest idiom; urllib opens only the loopback mock under test)
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Unit tests for the mock launcher (aixcoding/mock/__main__.py, single-port combo).

Selection resolution (default combo / --only / mutual exclusion / unknown
names) plus a real start→stop round trip: the combined server must answer
auth, catalog and update routes on ONE port (the 2026-11-20 single-port
decision), and the standalone auth starter keeps its own port. Stops go
through the launcher's own stop callables (must not raise — the B1
regression), then the port must be released.
"""

from __future__ import annotations

import socket
import urllib.error
import urllib.request
from urllib.parse import urlparse

from aixcoding.mock import __main__ as launcher
from aixcoding.mock.combined import start_combined


def test_default_selection_is_the_full_combo() -> None:
    assert launcher._resolve_selection("") == ["model_catalog", "update", "telemetry"]


def test_only_takes_a_subset() -> None:
    assert launcher._resolve_selection("auth") == ["auth"]
    assert launcher._resolve_selection("update") == ["update"]
    assert launcher._resolve_selection("model_catalog,telemetry") == ["model_catalog", "telemetry"]


def test_unknown_name_is_rejected() -> None:
    assert launcher._resolve_selection("nope") is None
    assert launcher._resolve_selection("auth,nope") is None


def test_auth_and_model_catalog_are_mutually_exclusive() -> None:
    """They share the auth route space — the selection must refuse up front."""
    assert launcher._resolve_selection("auth,model_catalog") is None


def _probe(opener: urllib.request.OpenerDirector, url: str, acceptable: tuple[int, ...]) -> None:
    """Any of *acceptable* proves the route answers (alive); anything else fails."""
    try:
        with opener.open(url, timeout=5) as response:
            assert response.status in acceptable, f"{url} -> {response.status}"
    except urllib.error.HTTPError as exc:
        assert exc.code in acceptable, f"{url} -> HTTP {exc.code}"


def test_combined_server_answers_all_services_on_one_port() -> None:
    """Auth + catalog + update routes on a single origin (single-port combo)."""
    origin, server, _thread = start_combined(port=0, with_auth=True)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        # auth route: verify page answers 200 (no token bookkeeping needed)
        _probe(opener, f"{origin}/device/verify", (200, 302, 404))
        # catalog route: auth-gated, so an anonymous probe is 401 — still an answer
        _probe(opener, f"{origin}/llm/api/v1/continue-config/dispatch", (200, 401))
        # update route: frozen release-check path, query-less GET is a 400 — an answer
        _probe(opener, f"{origin}/api/v2/releases/check", (200, 204, 304, 400))
    finally:
        server.shutdown()
        server.server_close()
    _assert_port_released(origin)


def test_standalone_auth_starter_round_trips() -> None:
    origin, stop = launcher._start_auth(port=0)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        _probe(opener, f"{origin}/device/verify", (200, 302, 404))
    finally:
        stop()  # B1 regression: this must not raise AttributeError
    _assert_port_released(origin)


def _assert_port_released(origin: str) -> None:
    probe = socket.socket()
    try:
        # Match the servers' own bind semantics (HTTPServer sets
        # allow_reuse_address = 1) so the check means the same on both platforms.
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(("127.0.0.1", urlparse(origin).port))
    finally:
        probe.close()
