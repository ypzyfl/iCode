# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Protocol client tests: envelope quirks and the poll state machine.

Unit level drives :class:`httpx.MockTransport`; an integration test at the
bottom runs the full flow against the real loopback mock server.
"""

from __future__ import annotations

import asyncio
import threading

import httpx
import pytest
from aixcoding.auth import AccountInfo, AuthClient, DeviceCode
from aixcoding.auth.client import MAX_POLL_INTERVAL_SECONDS
from aixcoding.auth.errors import (
    AuthNetworkError,
    AuthServerError,
    DevicePollCancelled,
    DevicePollDenied,
    DevicePollTimeout,
)

AUTH_URL = "http://auth.test/api/v1"
DATA_URL = "http://data.test/api/v1"

DEVICE_CODE_RESULT = {
    "interval": 5,
    "device_code": "dc-1",
    "user_code": "YX8S-NOHS",
    "verification_uri": "http://auth.test/device/verify",
    "verification_uri_complete": "http://auth.test/device/verify?user_code=YX8S-NOHS",
    "expires_in": 600,
}
TOKEN_OK = {
    "error": None,
    "token": "tok-1",
    "access_token": "fallback",
    "refresh_token": "ref-1",
    "token_type": "AICoding",
    "expires_in": 0,
    "scope": None,
}
USER_DATA = {
    "ehr": "8769092",
    "name": "大熊猫",
    "region": None,
    "deptName": "上海分中心技术平台研发部",
    "deptId": None,
    "isStWg": 1,
    "userType": 1,
}


def make_client(handler) -> AuthClient:
    transport = httpx.MockTransport(handler)
    http = httpx.AsyncClient(transport=transport)
    return AuthClient(AUTH_URL, DATA_URL, http)


class FakeClock:
    """Monotonic clock the fake sleep advances."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.slept: list[float] = []

    def __call__(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.now += seconds
        self.slept.append(seconds)


async def test_request_device_code_parses_result() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/auth/device/code"
        assert b'"client_id":78' in request.read()
        return httpx.Response(200, json={"success": True, "result": DEVICE_CODE_RESULT})

    code = await make_client(handler).request_device_code()
    assert isinstance(code, DeviceCode)
    assert code.device_code == "dc-1"
    assert code.user_code == "YX8S-NOHS"
    assert code.interval == 5


async def test_request_device_code_missing_result_raises() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"success": False, "message": "boom"})

    with pytest.raises(AuthServerError, match="device_code"):
        await make_client(handler).request_device_code()


async def test_non_json_body_raises_server_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"<html>gateway error</html>")

    with pytest.raises(AuthServerError, match="non-JSON"):
        await make_client(handler).request_device_code()


async def test_transport_failure_raises_network_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    with pytest.raises(AuthNetworkError):
        await make_client(handler).request_device_code()


async def test_poll_token_pending_then_success() -> None:
    answers = [
        {
            "success": True,
            "result": {**TOKEN_OK, "token": None, "access_token": None, "error": "authorization_pending"},
        },
        {"success": True, "result": TOKEN_OK},
    ]

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/auth/device/token"
        assert b"urn:ietf:params:oauth:grant-type:device_code" in request.read()
        return httpx.Response(200, json=answers.pop(0))

    clock = FakeClock()
    token = await make_client(handler).poll_token("dc-1", interval=5, sleep=clock.sleep, clock=clock)
    assert token.token == "tok-1"
    assert token.refresh_token == "ref-1"
    assert clock.slept == [5]


async def test_poll_token_slow_down_grows_interval_capped() -> None:
    answers = [
        {"success": True, "result": {**TOKEN_OK, "token": None, "error": "slow_down"}},
        {"success": True, "result": {**TOKEN_OK, "token": None, "error": "slow_down"}},
        {"success": True, "result": {**TOKEN_OK, "token": None, "error": "slow_down"}},
        {"success": True, "result": {**TOKEN_OK, "token": None, "error": "slow_down"}},
        {"success": True, "result": {**TOKEN_OK, "token": None, "error": "slow_down"}},
        {"success": True, "result": {**TOKEN_OK, "token": None, "error": "slow_down"}},
        {"success": True, "result": TOKEN_OK},
    ]

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=answers.pop(0))

    clock = FakeClock()
    token = await make_client(handler).poll_token("dc-1", interval=25, sleep=clock.sleep, clock=clock)
    assert token.token == "tok-1"
    # The first sleep already includes the +5 bump: 25 -> 30, then capped.
    assert clock.slept == [30, 30, 30, 30, 30, 30]
    assert MAX_POLL_INTERVAL_SECONDS == 30


@pytest.mark.parametrize("error", ["access_denied", "expired_token"])
async def test_poll_token_denied_and_expired_are_terminal(error: str) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"success": True, "result": {"error": error, "token": None}})

    with pytest.raises(DevicePollDenied) as exc_info:
        await make_client(handler).poll_token("dc-1", interval=1, sleep=_no_sleep, clock=FakeClock())
    assert exc_info.value.error == error


async def test_poll_token_overall_timeout() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"success": True, "result": {"error": "authorization_pending", "token": None}})

    clock = FakeClock()
    with pytest.raises(DevicePollTimeout, match="10"):
        await make_client(handler).poll_token("dc-1", interval=4, total_timeout=10, sleep=clock.sleep, clock=clock)


async def test_poll_token_cancel_event_short_circuits() -> None:
    called = {"polls": 0}
    event = asyncio.Event()
    event.set()

    async def handler(request: httpx.Request) -> httpx.Response:
        called["polls"] += 1
        return httpx.Response(200, json={"success": True, "result": {"error": "authorization_pending", "token": None}})

    with pytest.raises(DevicePollCancelled):
        await make_client(handler).poll_token(
            "dc-1", interval=1, cancel_event=event, sleep=_no_sleep, clock=FakeClock()
        )
    assert called["polls"] == 0


async def test_poll_token_success_without_token_raises() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"success": True, "result": {"error": None, "token": None, "access_token": None}}
        )

    with pytest.raises(AuthServerError, match="neither token nor error"):
        await make_client(handler).poll_token("dc-1", interval=1, sleep=_no_sleep, clock=FakeClock())


async def test_fetch_user_info_reads_data_not_result() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/user/info"
        assert b'"token":"tok-1"' in request.read()
        return httpx.Response(200, json={"success": True, "data": USER_DATA})

    info = await make_client(handler).fetch_user_info("tok-1")
    assert isinstance(info, AccountInfo)
    assert info.ehr == "8769092"
    assert info.name == "大熊猫"
    assert info.dept_name == "上海分中心技术平台研发部"


async def test_fetch_user_info_rejected_token_raises() -> None:
    # The real backend answers a bad token with no `success` key at all.
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": "用户不存在", "code": 400, "data": None})

    with pytest.raises(AuthServerError, match="rejected the token"):
        await make_client(handler).fetch_user_info("bogus")


async def _no_sleep(seconds: float) -> None:
    return None


class TestLoopbackMockIntegration:
    """Full flow against the real ``mock_server/aixcoding_auth/server.py`` on loopback."""

    def _start_server(self, mode: str) -> tuple[str, object]:
        from mock_server.aixcoding_auth.server import MockAuthConfig, create_server

        server = create_server(MockAuthConfig(mode=mode), host="127.0.0.1", port=0)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        thread.start()
        return f"http://127.0.0.1:{port}/api/v1", server

    async def test_auto_mode_full_flow(self) -> None:
        base_url, server = self._start_server("auto")
        try:
            client = AuthClient(base_url, base_url)
            code = await client.request_device_code()
            assert code.interval == 5
            token = await client.poll_token(code.device_code, interval=0.05, total_timeout=10)
            assert token.token.startswith("mock-token-")
            assert token.token_type == "AICoding"
            info = await client.fetch_user_info(token.token)
            assert info.ehr == "8769092"
            assert info.display_name == "大熊猫"
        finally:
            server.shutdown()
            server.server_close()

    async def test_manual_mode_stays_pending_until_confirm(self) -> None:
        base_url, server = self._start_server("manual")
        try:
            client = AuthClient(base_url, base_url)
            code = await client.request_device_code()

            async def cancel_after_pending() -> None:
                await asyncio.sleep(0.2)
                server.mock_state.confirm(code.user_code, "allow")

            confirmer = asyncio.create_task(cancel_after_pending())
            token = await client.poll_token(code.device_code, interval=0.05, total_timeout=10)
            await confirmer
            assert token.token.startswith("mock-token-")

            with pytest.raises(DevicePollDenied) as exc_info:
                await client.poll_token("unknown-device-code", interval=0.05, total_timeout=5)
            assert exc_info.value.error == "expired_token"
        finally:
            server.shutdown()
            server.server_close()
