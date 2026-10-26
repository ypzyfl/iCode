# ruff: noqa: S101
"""Behavior-anchor tests for the LLM login-token header wiring (auth migration).

Design: aixcoding/docs/auth/design.md (signed off 2026-10-26).

Channel 1 anchors drive ``RequestHeaders.stamp()`` directly (unit level);
channel 2 observes the final wire headers through a *real* openai SDK client
over ``httpx.MockTransport`` so the SDK's default_headers x per-request
extra_headers merge — the credential-authoritative semantics — is exercised,
never mocked (DEVELOPMENT.md §5).
"""

from __future__ import annotations

import httpx
import pytest

from chrys.aixcoding.auth import Environment, LoginSession
from chrys.aixcoding.auth.crypto import MemoryBackend
from chrys.aixcoding.auth.types import StoredCredential
from chrys.service.llm.wire_client import RequestHeaders

TOKEN = "login-tok-1"
STATIC_TOKEN = "static-tok"


@pytest.fixture
def logged_in_session(tmp_path, monkeypatch):
    """A session with one live LOCAL credential, pinned as the process session."""
    session = LoginSession(
        environment=Environment.LOCAL,
        config_dir=tmp_path,
        backend=MemoryBackend(),
    )
    session.store.store(
        Environment.LOCAL,
        StoredCredential.issued_now(
            environment_id="local",
            user_id="1234567",
            token=TOKEN,
        ),
    )
    monkeypatch.setattr("chrys.aixcoding.auth.get_login_session", lambda: session)
    return session


def _stamp(extra_headers: dict[str, str] | None = None) -> dict[str, str]:
    """Drive one request through stamp() and return its final extra_headers."""
    request: dict = {"model": "test-model"}
    if extra_headers is not None:
        request["extra_headers"] = extra_headers
    RequestHeaders(session_id="s-1").stamp(request)
    headers = request.get("extra_headers")
    assert isinstance(headers, dict)
    return headers


def test_stamp_injects_token(logged_in_session) -> None:
    headers = _stamp()
    assert headers["token"] == TOKEN


def test_no_session_no_header(monkeypatch) -> None:
    def _raise() -> LoginSession:
        raise RuntimeError("no auth subsystem")

    monkeypatch.setattr("chrys.aixcoding.auth.get_login_session", _raise)
    headers = _stamp()
    assert "token" not in headers
    # The rest of the Chrys metadata is unaffected — the request still goes out.
    assert headers["X-Session-ID"] == "s-1"


def test_login_token_empty_string_means_no_header(monkeypatch, tmp_path) -> None:
    """A session whose store is empty sends no token header (not an empty one)."""
    session = LoginSession(
        environment=Environment.LOCAL,
        config_dir=tmp_path,
        backend=MemoryBackend(),
    )
    monkeypatch.setattr("chrys.aixcoding.auth.get_login_session", lambda: session)
    headers = _stamp()
    assert "token" not in headers


def test_overrides_extra_headers(logged_in_session) -> None:
    """Login credential beats a caller-supplied static token (channel 1)."""
    headers = _stamp({"token": STATIC_TOKEN, "X-Custom": "keep"})
    assert headers["token"] == TOKEN
    assert headers["X-Custom"] == "keep"


def test_stamp_survives_import_failure(monkeypatch) -> None:
    """A broken clients-module import degrades to no token, never a failed request."""
    import sys

    monkeypatch.setitem(sys.modules, "chrys.service.llm.clients", None)
    headers = _stamp()
    assert "token" not in headers
    assert headers["X-Session-ID"] == "s-1"


def test_logout_takes_effect_next_request(logged_in_session) -> None:
    assert _stamp()["token"] == TOKEN
    logged_in_session.logout()
    assert "token" not in _stamp()


async def test_overrides_default_headers_on_wire(logged_in_session) -> None:
    """Channel 2: through a real openai SDK client, the send-time login token
    wins over a construction-time default header (0.28 credential-authoritative
    semantics); the SDK merge itself is real, only the transport is mocked."""
    import openai

    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(request.headers)
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-1",
                "object": "chat.completion",
                "created": 0,
                "model": "test-model",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "ok"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 1,
                    "completion_tokens": 1,
                    "total_tokens": 2,
                },
            },
        )

    client = openai.AsyncOpenAI(
        api_key="k-test",
        base_url="http://llm.test/v1",
        default_headers={"token": STATIC_TOKEN},
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    try:
        # extra_headers here is what stamp() produces on the wire path: the
        # send-time login token (resolved per request, not snapshotted).
        await client.chat.completions.create(
            model="test-model",
            messages=[{"role": "user", "content": "hi"}],
            extra_headers={"token": TOKEN},
        )
    finally:
        await client.close()

    assert seen["token"] == TOKEN
