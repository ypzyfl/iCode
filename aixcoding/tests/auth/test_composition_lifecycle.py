"""Composition test: the credential lifecycle through the production assembly.

Design: aixcoding/docs/batches/composition-tests/design.md (signed off 2026-11-01).

One client built by the real ``create_client`` factory spans three requests
across a real login/logout cycle. A loopback LLM stub captures the final
credential headers per request; snapshots hold mock values only, live in
memory and never reach a persistent log (the stub itself logs nothing).
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest
from aixcoding.mock.auth.server import MockAuthConfig, create_server

import chrys.kernel.aixcoding.auth.session as auth_session
from chrys.kernel import Message
from chrys.kernel.aixcoding.auth import Environment, LoginSession, detect_delegation, get_login_session
from chrys.kernel.aixcoding.auth.crypto import MemoryBackend
from chrys.service.llm.clients import create_client
from chrys.service.profiles.models.schema import ModelProfile

#: Delegation activation channels (design: 实施硬约束 - 环境前置). Display-hint
#: variables do not activate delegation alone and are not cleared.
_DELEGATION_CHANNELS = (
    "AIXCODING_AUTH_DELEGATED_TOKEN",
    "OPENAI_API_KEY",
    "AIXCODING_USER_EHR",
)


class _AuthMock:
    """Loopback auth mock on an ephemeral port (test_auth_session.py shape)."""

    def __init__(self, **config: object) -> None:
        self.server = create_server(MockAuthConfig(**config), host="127.0.0.1", port=0)  # type: ignore[arg-type]
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}/api/v1"

    def __enter__(self) -> _AuthMock:
        self.thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.server.shutdown()
        self.server.server_close()


class _LoopbackLLM:
    """In-process OpenAI-compatible stub; snapshots credential headers per request.

    Loopback-only test double (DIRECTORY.md §6 keeps in-process stubs under
    ``aixcoding/tests/``): plain 200 chat completions with no tool calls, so
    each awaited ``get_response`` drives exactly one HTTP request. Snapshots
    are memory-only and dropped with the object; the server writes no log.
    """

    def __init__(self) -> None:
        self.snapshots: list[dict[str, Any]] = []
        outer = self

        class _Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", "0"))
                self.rfile.read(length)
                outer.snapshots.append(
                    {
                        "seq": len(outer.snapshots),
                        "token": self.headers.get("token"),
                        "authorization": self.headers.get("Authorization"),
                    }
                )
                body = json.dumps(
                    {
                        "id": "chatcmpl-stub",
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
                        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                    }
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: object) -> None:
                # The stub promises no log output of its own.
                return

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}/v1"

    def __enter__(self) -> _LoopbackLLM:
        self.thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.server.shutdown()
        self.server.server_close()


async def test_credential_lifecycle_through_production_stack(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Login -> request carries the issued token -> logout -> it never rides again.

    The client comes from the real factory and spans all three requests; login
    state is built only by the real device-code flow (no injected headers, no
    direct store writes); the login session the wire reads is proven to be the
    very instance the test drove through login and logout.
    """
    # --- Environment preconditions (before any session construction) -------
    for variable in _DELEGATION_CHANNELS:
        monkeypatch.delenv(variable, raising=False)
    # Real detector via the package namespace: the auth conftest pins the
    # session-module name only, so this assertion proves the cleanup (F-03).
    assert detect_delegation() is None

    with _AuthMock(mode="auto", interval=0) as auth_mock, _LoopbackLLM() as llm:
        session = LoginSession(
            environment=Environment.LOCAL,
            endpoints=(auth_mock.base_url, auth_mock.base_url),
            config_dir=tmp_path,
            backend=MemoryBackend(),
        )
        # Keep the real get_login_session(); pin the singleton slot it reads
        # (F-02). The identity assert below goes through the real function.
        monkeypatch.setattr(auth_session, "_default_session", session)
        assert get_login_session() is session

        profile = ModelProfile(
            id="composition-test",
            name="composition-test",
            provider="openai",
            model_id="test-model",
            base_url=llm.base_url,
            api_key="k-test",
            bypass_proxy=True,
        )
        client = await create_client(profile)
        try:
            # Request 1: before login -- no login credential on the wire yet.
            await client.get_response([Message("user", ["hi"])], stream=False)

            code = await session.request_device_code()
            await session.complete_login(code)
            issued = session.stored_token
            assert issued is not None and issued.startswith("mock-token-")

            # Request 2: after login -- the issued credential rides the request.
            await client.get_response([Message("user", ["hi"])], stream=False)

            session.logout()

            # Request 3: after logout -- the old login credential is gone,
            # the static profile credential legitimately remains.
            await client.get_response([Message("user", ["hi"])], stream=False)
        finally:
            await client.aclose()

        # Count baseline first: a mismatch is a fact to report, not to mask.
        assert len(llm.snapshots) == 3
        first, second, third = llm.snapshots
        assert first["token"] is None
        assert first["authorization"] == "Bearer k-test"
        assert second["token"] == issued
        assert second["authorization"] == "Bearer k-test"
        assert third["token"] is None
        assert third["authorization"] == "Bearer k-test"
