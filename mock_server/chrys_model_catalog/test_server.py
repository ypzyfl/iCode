# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Integration tests for the Chrys model catalog mock (mock_server/chrys_model_catalog/server.py).

Conventions: bind port 0 (kernel-assigned), loopback only, every HTTP call goes
through ``direct_route`` (bypassing environment/system proxies).

The last two tests are contract tests: they feed the mock's output through the
real client parser (``chrys.service.profiles.models.catalog``) so the sample
data cannot silently drift away from what the client accepts. The mock itself
imports nothing from the product — only its tests look at both sides.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest

from mock_server.chrys_model_catalog import server as catalog_server
from mock_server.chrys_model_catalog.server import RunningCatalogMock


@pytest.fixture
def mock_factory() -> Iterator[Callable[..., RunningCatalogMock]]:
    """Start mocks on demand (port 0, quiet) and reap them all."""
    started: list[RunningCatalogMock] = []

    def _factory(**kwargs: Any) -> RunningCatalogMock:
        kwargs.setdefault("quiet", True)
        running = catalog_server.start(**kwargs)
        started.append(running)
        return running

    yield _factory
    for running in started:
        running.close()


@pytest.fixture
def mock(mock_factory: Callable[..., RunningCatalogMock]) -> RunningCatalogMock:
    return mock_factory()


def _catalog(running: RunningCatalogMock) -> str:
    return f"{running.origin}{catalog_server.CATALOG_ROUTE}"


async def _get(url: str) -> httpx.Response:
    async with httpx.AsyncClient() as client:
        return await client.get(url)


async def _control(running: RunningCatalogMock, **config: Any) -> dict[str, Any]:
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{running.origin}/mock/control", json=config)
        assert response.status_code == 200
        return response.json()


async def test_serves_builtin_sample(mock: RunningCatalogMock, direct_route: None) -> None:
    response = await _get(_catalog(mock))
    assert response.status_code == 200
    payload = response.json()
    # The mock serves the reference server's own shape: a ``models`` array, with
    # every other top-level key passed through untouched.
    assert [entry["model"] for entry in payload["models"]] == ["openai/gpt-4o-mini"]
    assert payload["aa"] == {"test": "as"}


async def test_query_string_is_ignored(mock: RunningCatalogMock, direct_route: None) -> None:
    """The client appends scope/userId query params; they must not change the answer."""
    plain = (await _get(_catalog(mock))).json()
    with_query = (await _get(f"{_catalog(mock)}?scopeType=global&scopeValue=config&format=json&userId=someone")).json()
    assert with_query == plain


async def test_removed_routes_answer_404(mock: RunningCatalogMock, direct_route: None) -> None:
    """Only the dispatch path and the control endpoint exist."""
    assert (await _get(f"{mock.origin}/model-catalog")).status_code == 404
    assert (await _get(f"{mock.origin}/mock/state")).status_code == 404


async def test_control_switches_to_error(mock: RunningCatalogMock, direct_route: None) -> None:
    snapshot = await _control(mock, mode="error")
    assert snapshot["mode"] == "error"
    assert snapshot["version"] == "mock-2"  # every switch is a new revision
    assert (await _get(_catalog(mock))).status_code == 500
    assert (await _control(mock, mode="ok"))["mode"] == "ok"
    assert (await _get(_catalog(mock))).status_code == 200


async def test_control_reports_request_count(mock: RunningCatalogMock, direct_route: None) -> None:
    await _get(_catalog(mock))
    snapshot = await _control(mock, mode="ok")  # the snapshot replaces /mock/state
    assert snapshot["mode"] == "ok"
    assert snapshot["requests"] == 2  # the catalog call plus this control call


async def test_unknown_mode_is_rejected(mock: RunningCatalogMock, direct_route: None) -> None:
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{mock.origin}/mock/control", json={"mode": "nope"})
    assert response.status_code == 400
    assert "mode" in response.json()["error"]


async def test_empty_mode_serves_no_models(mock: RunningCatalogMock, direct_route: None) -> None:
    await _control(mock, mode="empty")
    assert (await _get(_catalog(mock))).json()["models"] == []


async def test_invalid_mode_serves_unusable_models(mock: RunningCatalogMock, direct_route: None) -> None:
    await _control(mock, mode="invalid")
    models = (await _get(_catalog(mock))).json()["models"]
    assert len(models) == 2
    assert all(not str(entry.get("model") or "").strip() for entry in models)


async def test_stale_mode_drifts_title_but_keeps_models(mock: RunningCatalogMock, direct_route: None) -> None:
    await _control(mock, mode="stale")
    first = (await _get(_catalog(mock))).json()
    second = (await _get(_catalog(mock))).json()
    assert [entry["model"] for entry in first["models"]] == [entry["model"] for entry in second["models"]]
    assert first["models"] != second["models"], "stale drifts the served title"


async def test_slow_mode_stalls_before_answering(
    mock_factory: Callable[..., RunningCatalogMock],
    direct_route: None,
) -> None:
    running = mock_factory(mode="slow", delay=0.3)
    started = time.monotonic()
    response = await _get(_catalog(running))
    assert response.status_code == 200
    assert time.monotonic() - started >= 0.25


async def test_catalog_file_is_reread_per_request(
    mock_factory: Callable[..., RunningCatalogMock],
    tmp_path: Path,
    direct_route: None,
) -> None:
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps({"items": [{"id": "first", "name": "First", "provider": "mock"}]}))
    running = mock_factory(catalog_file=path)

    first = await _get(_catalog(running))
    assert [item["id"] for item in first.json()["items"]] == ["first"]

    path.write_text(json.dumps({"items": [{"id": "second", "name": "Second", "provider": "mock"}]}))
    second = await _get(_catalog(running))
    assert [item["id"] for item in second.json()["items"]] == ["second"]


async def test_unreadable_catalog_file_answers_500(
    mock_factory: Callable[..., RunningCatalogMock],
    tmp_path: Path,
    direct_route: None,
) -> None:
    path = tmp_path / "catalog.json"
    path.write_text("{ not json")
    running = mock_factory(catalog_file=path)
    response = await _get(_catalog(running))
    assert response.status_code == 500
    assert "not valid JSON" in response.json()["error"]


def test_non_loopback_bind_is_rejected() -> None:
    with pytest.raises(ValueError):
        catalog_server.start(host="0.0.0.0")
    with pytest.raises(ValueError):
        catalog_server.create_server(host="0.0.0.0")


async def test_sample_payload_is_accepted_by_the_client_parser(mock: RunningCatalogMock, direct_route: None) -> None:
    from chrys.service.profiles.models.catalog import parse_catalog

    payload = (await _get(_catalog(mock))).json()
    catalog = parse_catalog(payload)
    assert len(catalog.items) == 1
    assert catalog.items[0].id == "openai-gpt-4o-mini"
    assert catalog.version, "a version-less payload is fingerprinted"
    assert catalog.version != "mock-1"


async def test_empty_and_invalid_payloads_are_refused_by_the_client_parser(
    mock: RunningCatalogMock,
    direct_route: None,
) -> None:
    from chrys.service.profiles.models.catalog import ModelCatalogError, parse_catalog

    await _control(mock, mode="empty")
    with pytest.raises(ModelCatalogError):
        parse_catalog((await _get(_catalog(mock))).json())

    await _control(mock, mode="invalid")
    with pytest.raises(ModelCatalogError):
        parse_catalog((await _get(_catalog(mock))).json())


async def _post_chat(running: RunningCatalogMock, body: dict[str, Any]) -> httpx.Response:
    async with httpx.AsyncClient() as client:
        return await client.post(f"{running.origin}{catalog_server.LLM_ROUTE}", json=body)


async def test_llm_chat_non_streaming(mock: RunningCatalogMock, direct_route: None) -> None:
    """A non-streaming chat request gets a minimal valid ChatCompletion back."""
    response = await _post_chat(
        mock,
        {
            "model": "mock-model",
            "stream": False,
            "temperature": 0.2,
            "messages": [{"role": "user", "content": "ping"}],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["model"] == "mock-model"
    assert payload["object"] == "chat.completion"
    choice = payload["choices"][0]
    assert choice["message"]["role"] == "assistant"
    assert choice["message"]["content"] == catalog_server.LLM_MOCK_REPLY
    assert choice["finish_reason"] == "stop"


async def test_llm_chat_streaming(mock: RunningCatalogMock, direct_route: None) -> None:
    """A ``stream: True`` request is answered on the SSE wire and ends with [DONE]."""
    response = await _post_chat(
        mock,
        {
            "model": "mock-model",
            "stream": True,
            "messages": [{"role": "user", "content": "ping"}],
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    text = response.text
    assert "chat.completion.chunk" in text
    assert catalog_server.LLM_MOCK_REPLY in text
    assert text.endswith("data: [DONE]\n\n")


def test_llm_params_log_drops_telemetry_and_prompt_content() -> None:
    """The parameter line carries model settings, not provenance or prompt text."""
    params = catalog_server._llm_params_for_log(
        {
            "model": "openai/gpt-4o-mini",
            "max_completion_tokens": 16000,
            "stream": False,
            "messages": [
                {"role": "system", "content": "SECRET SYSTEM PROMPT"},
                {"role": "user", "content": "SECRET USER PROMPT"},
            ],
            "tools": [{"type": "function", "function": {"name": "read_file"}}],
            "telemetry": {"sessionId": "b997cdd0ace95fb6ab7aaf71bba3952a"},
        }
    )
    assert params == {
        "model": "openai/gpt-4o-mini",
        "max_completion_tokens": 16000,
        "stream": False,
        "messages": "<2 message(s): system, user>",
        "tools": "<1 tool(s)>",
    }
    assert "telemetry" not in params
    assert "SECRET" not in str(params)
    assert catalog_server._llm_params_for_log({"messages": "SECRET"}) == {"messages": "<omitted str>"}
