# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""HTTP client for the AIxCoding device-code protocol.

Three endpoints, all ``POST`` + ``application/json`` (see the plan's section
1.1). The wire contract never uses the HTTP status code to signal failure --
even ``authorization_pending`` arrives with ``success: true`` -- so every
decision branches on the envelope:

=====================  ==========================  =========================
Endpoint               Request body                Answer envelope
=====================  ==========================  =========================
``{auth}/auth/device/code``     ``{"client_id": 78}``          ``result``
``{auth}/auth/device/token``    device_code + grant type       ``result``
``{data}/user/info``            ``{"token": T}``               ``data``
=====================  ==========================  =========================

The poll loop matches the production reference (aixcoding-continue's
``WorkOsAuthProvider``): a fixed 1-second cadence regardless of any
server-sent interval, ``slow_down`` still backs off 5s at a time capped at
30s, terminal errors end the wait immediately, and a 5-minute overall budget
guards against a forgotten browser tab.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from aixcoding.auth.errors import (
    AuthNetworkError,
    AuthServerError,
    DevicePollCancelled,
    DevicePollDenied,
    DevicePollTimeout,
)
from aixcoding.auth.types import AccountInfo, DeviceCode, TokenResult

CLIENT_ID = 78
DEVICE_CODE_GRANT = "urn:ietf:params:oauth:grant-type:device_code"

#: Overall polling budget: 5 minutes, the production reference's hard timeout.
TOTAL_POLL_TIMEOUT_SECONDS = 5 * 60

#: ``slow_down`` grows the interval by this much, up to the cap.
SLOW_DOWN_STEP_SECONDS = 5
MAX_POLL_INTERVAL_SECONDS = 30

#: Terminal OAuth device-flow errors.
_DENIED_ERRORS = ("access_denied", "expired_token")

Sleep = Callable[[float], Awaitable[None]]
Clock = Callable[[], float]


class AuthClient:
    """The three protocol calls plus the poll loop around the second one."""

    def __init__(
        self,
        auth_url: str,
        data_url: str,
        http: httpx.AsyncClient | None = None,
        *,
        timeout: float = 10.0,
    ) -> None:
        self._auth_url = auth_url.rstrip("/")
        self._data_url = data_url.rstrip("/")
        self._http = http
        self._timeout = timeout

    async def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        if self._http is not None:
            return await self._post_on(self._http, url, payload)
        # A self-created client lives for exactly one request: the poll loop
        # used to leak one client (and its SSL context) per iteration. Also
        # ``trust_env=False``: proxy env vars must not hijack auth traffic --
        # these endpoints are intranet/loopback services a proxy cannot reach,
        # and a dev proxy answering 502 + plain text would masquerade as a
        # server error and silently log the user out.
        async with httpx.AsyncClient(timeout=self._timeout, trust_env=False) as client:
            return await self._post_on(client, url, payload)

    async def _post_on(self, client: httpx.AsyncClient, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = await client.post(url, json=payload)
        except httpx.HTTPError as exc:
            raise AuthNetworkError(f"request to {url} failed: {exc}") from exc
        try:
            body = response.json()
        except ValueError as exc:
            raise AuthServerError(f"{url} returned a non-JSON body (HTTP {response.status_code})") from exc
        if not isinstance(body, dict):
            raise AuthServerError(f"{url} returned a non-object JSON body")
        return body

    async def request_device_code(self) -> DeviceCode:
        """Start a device authorization and return the code to confirm."""
        body = await self._post_json(f"{self._auth_url}/auth/device/code", {"client_id": CLIENT_ID})
        result = body.get("result")
        if not isinstance(result, dict) or not result.get("device_code"):
            raise AuthServerError("device/code response missing result.device_code")
        return DeviceCode.from_payload(result)

    async def poll_token(
        self,
        device_code: str,
        *,
        interval: float = 1.0,
        total_timeout: float = TOTAL_POLL_TIMEOUT_SECONDS,
        cancel_event: asyncio.Event | None = None,
        sleep: Sleep = asyncio.sleep,
        clock: Clock = time.monotonic,
    ) -> TokenResult:
        """Poll until the grant resolves; every ending is an exception or a token.

        ``interval`` seeds the wait; the production reference polls on a fixed
        1-second cadence and ignores the server-sent ``result.interval``. The
        wait grows by 5s on ``slow_down`` up to 30s, and the whole loop must
        finish inside ``total_timeout``. ``cancel_event`` short-circuits the
        wait the moment a dialog closes.
        """
        started = clock()
        wait = max(float(interval), 0.0)
        payload: dict[str, Any] = {"grant_type": DEVICE_CODE_GRANT, "device_code": device_code}
        while True:
            if cancel_event is not None and cancel_event.is_set():
                raise DevicePollCancelled("login dialog closed before authorization")
            body = await self._post_json(f"{self._auth_url}/auth/device/token", payload)
            result = body.get("result")
            if not isinstance(result, dict):
                raise AuthServerError("device/token response missing result")
            error = result.get("error")
            if not error:
                token = TokenResult.from_payload(result)
                if not token.token:
                    raise AuthServerError("device/token response carried neither token nor error")
                return token
            if error in _DENIED_ERRORS:
                raise DevicePollDenied(str(error))
            if error == "slow_down":
                wait = min(wait + SLOW_DOWN_STEP_SECONDS, MAX_POLL_INTERVAL_SECONDS)
            # ``authorization_pending`` (or anything unknown): wait and retry.
            if clock() - started + wait >= total_timeout:
                raise DevicePollTimeout(f"no authorization within {total_timeout}s")
            if cancel_event is not None and cancel_event.is_set():
                raise DevicePollCancelled("login dialog closed before authorization")
            await sleep(wait)

    async def fetch_user_info(self, token: str) -> AccountInfo:
        """Resolve the token to the user's identity (``ehr`` is the stable id).

        A rejected token (``data: null``, or the no-``success`` business
        failure) raises :class:`AuthServerError`; callers treat that as
        "credential dead, force re-login".
        """
        body = await self._post_json(f"{self._data_url}/user/info", {"token": token})
        data = body.get("data")
        if not isinstance(data, dict) or not data:
            raise AuthServerError(f"user/info rejected the token: {body.get('message') or 'empty data'}")
        return AccountInfo.from_payload(data)
