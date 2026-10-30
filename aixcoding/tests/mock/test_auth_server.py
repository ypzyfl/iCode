# (contract test — asserts are pytest idiom; urllib opens only the loopback mock under test)
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Minimal wire-contract tests for the auth mock (aixcoding/mock/auth).

They anchor the mock's byte-level reproduction of the reference backend
envelopes (the reason this mock exists at all, per DIRECTORY.md §6 "every
mock must have contract tests"):

* ``device/code`` / ``device/token`` answer under ``result`` with
  ``success: true`` even while the poll reports ``authorization_pending`` —
  the outcome lives in ``result.error``;
* ``user/info`` answers under ``data``; an unknown token drops ``success``
  entirely and returns ``code: 400`` in the body while HTTP stays 200.

The mock itself imports nothing from the product; neither do these tests
(stdlib urllib, direct connection — same isolation approach as the update
contract tests, no fixtures needed).
"""

from __future__ import annotations

import json
import threading
import urllib.request
from collections.abc import Iterator

import pytest
from aixcoding.mock.auth.server import (
    DEVICE_CODE_ROUTE,
    DEVICE_TOKEN_ROUTE,
    USER_INFO_ROUTE,
    MockAuthConfig,
    create_server,
)

_INVALID_TOKEN_MESSAGE = "用户不存在"


@pytest.fixture
def base_url() -> Iterator[str]:
    """A running auth mock (auto mode) on an ephemeral loopback port."""
    server = create_server(MockAuthConfig(mode="auto"), host="127.0.0.1", port=0)
    threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.05}, name="chrys-mock-auth-test", daemon=True
    ).start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def _post(base_url: str, path: str, body: dict[str, object]) -> tuple[int, dict[str, object]]:
    """POST JSON straight to the mock, bypassing any system proxy."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request(
        base_url + path,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with opener.open(request, timeout=5) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def _issue_device_code(base_url: str) -> str:
    _status, body = _post(base_url, DEVICE_CODE_ROUTE, {})
    return str(body["result"]["device_code"])


def test_device_code_result_envelope(base_url: str) -> None:
    """device/code wraps its answer in ``result`` under the success envelope."""
    status, body = _post(base_url, DEVICE_CODE_ROUTE, {})

    assert status == 200
    assert body["success"] is True
    assert body["code"] == 200
    assert body["message"] is None
    result = body["result"]
    assert isinstance(result["device_code"], str) and result["device_code"]
    assert isinstance(result["user_code"], str) and result["user_code"]
    assert result["interval"] == MockAuthConfig().interval
    assert result["expires_in"] == MockAuthConfig().expires_in
    assert result["verification_uri"].endswith("/device/verify")


def test_token_poll_stays_success_true_while_pending(base_url: str) -> None:
    """The first auto-mode poll is pending: success stays true, error carries the outcome."""
    device_code = _issue_device_code(base_url)

    status, body = _post(base_url, DEVICE_TOKEN_ROUTE, {"device_code": device_code})

    assert status == 200
    assert body["success"] is True  # pending is not a transport failure
    result = body["result"]
    assert result["error"] == "authorization_pending"
    assert result["token"] is None

    # Second poll (auto mode alternates): authorized — error nulls out, token arrives.
    status, body = _post(base_url, DEVICE_TOKEN_ROUTE, {"device_code": device_code})
    assert status == 200
    assert body["result"]["error"] is None
    assert isinstance(body["result"]["token"], str) and body["result"]["token"]


def test_user_info_envelope_and_unknown_token_quirk(base_url: str) -> None:
    """user/info uses the ``data`` envelope; unknown tokens drop ``success`` with HTTP still 200."""
    device_code = _issue_device_code(base_url)
    _post(base_url, DEVICE_TOKEN_ROUTE, {"device_code": device_code})  # pending
    _status, body = _post(base_url, DEVICE_TOKEN_ROUTE, {"device_code": device_code})  # authorized
    token = str(body["result"]["token"])

    status, body = _post(base_url, USER_INFO_ROUTE, {"token": token})
    assert status == 200
    assert body["success"] is True
    assert isinstance(body["data"], dict)

    status, body = _post(base_url, USER_INFO_ROUTE, {"token": "not-a-known-token"})
    assert status == 200  # HTTP stays 200 — the client must read the envelope
    assert "success" not in body
    assert body["code"] == 400
    assert body["message"] == _INVALID_TOKEN_MESSAGE
    assert body["data"] is None


def test_second_instance_on_a_taken_port_is_refused() -> None:
    """The Windows port-hijack hole stays closed: a live listener — even one
    bound with SO_REUSEADDR, i.e. another mock instance, the stale-process
    case — must block a second bind (fail-fast, never a silent second copy)."""
    first = create_server(MockAuthConfig(mode="auto"), host="127.0.0.1", port=0)
    try:
        with pytest.raises(OSError):
            create_server(MockAuthConfig(mode="auto"), host="127.0.0.1", port=first.server_address[1])
    finally:
        first.server_close()
