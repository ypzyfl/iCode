# (unit test — asserts are pytest idiom; urllib opens only the loopback mock under test)
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for the mock launcher (aixcoding/mock/__main__.py).

Selection resolution (default combo / --all / --only / mutual exclusion /
unknown names) plus — the B1 regression — a real start→stop round trip for
every service starter: the catalog stop once called a non-existent
``running.server`` attribute and raised AttributeError on every stop path
(Ctrl+C shutdown and the occupied-port rollback alike).
"""

from __future__ import annotations

import socket
import urllib.error
import urllib.request
from urllib.parse import urlparse

from aixcoding.mock import __main__ as launcher


def test_default_combo_is_catalog_plus_update() -> None:
    assert launcher._resolve_selection("", False) == ["model_catalog", "update"]


def test_all_currently_equals_the_default_combo() -> None:
    # telemetry (:4321) joins --all when its mock migrates.
    assert launcher._resolve_selection("", True) == ["model_catalog", "update"]


def test_only_takes_a_subset_in_given_order() -> None:
    assert launcher._resolve_selection("auth", False) == ["auth"]
    assert launcher._resolve_selection("update,model_catalog", False) == ["update", "model_catalog"]


def test_unknown_name_is_rejected() -> None:
    assert launcher._resolve_selection("telemetry", False) is None
    assert launcher._resolve_selection("auth,telemetry", False) is None


def test_auth_and_model_catalog_are_mutually_exclusive() -> None:
    """Both bind :7777 — the selection must refuse the combination up front."""
    assert launcher._resolve_selection("auth,model_catalog", False) is None


def test_every_starter_round_trips() -> None:
    """Start every registered service for real, probe it, stop it via the
    launcher's own stop callable (must not raise — B1), then confirm the port
    is released.

    Iterates ``_SERVICES`` so a newly registered mock joins the round trip
    automatically (telemetry will, per its design notes). One test (not
    parametrized) on purpose: the round trips share the launcher's daemon
    threads and must run sequentially inside one worker. Each starter takes
    ``port=0`` — the OS-assigned ephemeral port the server factories support
    for tests (their base_url/origin read the bound port back) — so the round
    trip never depends on the fixed dev ports (7777/7778), which the CLI path
    keeps fail-fast on purpose (DIRECTORY.md §6).
    """
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for _port, _description, starter in launcher._SERVICES.values():
        origin, stop = starter(port=0)
        try:
            try:
                with opener.open(origin, timeout=5) as response:
                    # Any HTTP answer proves the server is up (a bare origin
                    # path 404s on catalog/update, answers 200 on auth).
                    assert response.status in (200, 404)
            except urllib.error.HTTPError as exc:
                assert exc.code in (200, 404)
        finally:
            stop()  # B1 regression: this must not raise AttributeError
        probe = socket.socket()
        try:
            # Match the servers' own bind semantics (HTTPServer sets
            # allow_reuse_address = 1): on Linux a bare bind into leftover
            # TIME_WAIT tuples fails with EADDRINUSE even though the port is
            # free for a server, while Windows allows it — aligning the probe
            # makes the check mean the same thing on both platforms.
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # released for the next round trip (port actually bound above)
            probe.bind(("127.0.0.1", urlparse(origin).port))
        finally:
            probe.close()
