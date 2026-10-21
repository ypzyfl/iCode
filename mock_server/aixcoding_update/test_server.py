# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Contract tests for the AIxCoding update-detection mock (mock_server/aixcoding_update/server.py).

Conventions: bind port 0 (kernel-assigned), loopback only. Requests go through
stdlib ``urllib`` with an empty ``ProxyHandler`` — no environment or system
proxy can intercept loopback traffic, the same guarantee ``chrys_model_catalog``
gets from its ``direct_route`` fixture without importing any test fixtures.
"""

from __future__ import annotations

import hashlib
import json
import threading
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator
from typing import Any

import pytest

from mock_server.aixcoding_update import server as update_server
from mock_server.aixcoding_update.server import INVALID_QUERY_BODY, MockUpdateConfig

VALID_QUERY = "clientType=cli&platform=darwin&architecture=arm64&currentVersion=0.28.0"

_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


@pytest.fixture
def mock_factory() -> Iterator[Callable[..., Any]]:
    """Start mocks on demand (port 0, background thread) and reap them all."""
    servers: list[Any] = []

    def _factory(**kwargs: Any) -> Any:
        config = kwargs.pop("config", None) or MockUpdateConfig(**kwargs)
        server = update_server.create_server(config, port=0)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        thread.start()
        servers.append(server)
        return server

    yield _factory
    for server in servers:
        server.shutdown()
        server.server_close()


def _base(server: Any) -> str:
    return server.mock_config.base_url


def _release(server: Any) -> str:
    """The release route with a default valid query (strict mode rejects bare requests)."""
    return f"{_base(server)}{update_server.RELEASE_ROUTE}?{VALID_QUERY}"


def _request(url: str, headers: dict[str, str] | None = None) -> tuple[int, Any, bytes]:
    """GET via urllib, normalizing HTTP errors to ``(status, headers, body)``."""
    request = urllib.request.Request(url, headers=headers or {})
    try:
        with _OPENER.open(request, timeout=5) as response:
            return response.status, response.headers, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.headers, error.read()


def _post(url: str, payload: dict[str, Any]) -> tuple[int, Any, bytes]:
    """POST a JSON body via urllib, normalizing HTTP errors the same way."""
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}
    )
    try:
        with _OPENER.open(request, timeout=5) as response:
            return response.status, response.headers, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.headers, error.read()


def test_valid_query_returns_manifest(mock_factory: Callable[..., Any]) -> None:
    server = mock_factory()
    status, headers, body = _request(_release(server))
    assert status == 200
    assert headers["Content-Type"].startswith("application/json")
    manifest = json.loads(body)
    # v2 manifest shape, mirroring the caller's clientType/platform.
    assert manifest["schemaVersion"] == 2
    assert manifest["kind"] == "cli"
    assert manifest["environmentId"] == "production"
    assert manifest["channelId"] == "stable"  # channel param dropped from the contract
    assert manifest["version"] == "999.0.0"  # out-of-the-box default: newer than any plausible client
    assert manifest["releaseId"] == "cli-999.0.0-macos-arm64"
    assert manifest["forceUpgrade"] is False
    assert isinstance(manifest["releaseNotes"], str) and manifest["releaseNotes"]
    assert manifest["artifact"]["platform"] == "macos"  # friendly spelling derived from the darwin query value
    assert manifest["artifact"]["architecture"] == "arm64"
    assert manifest["artifact"]["url"].startswith("http://127.0.0.1")
    assert set(manifest["artifact"]) == {"platform", "architecture", "url"}  # v2 dropped distribution/hashes
    # The contract's ETag is the SHA-256 of the manifest body.
    assert headers["ETag"] == hashlib.sha256(body).hexdigest()


def test_windows_query_is_valid(mock_factory: Callable[..., Any]) -> None:
    """win64 merged into win32; bitness lives solely in ``architecture``."""
    server = mock_factory()
    url = f"{_base(server)}{update_server.RELEASE_ROUTE}?clientType=cli&platform=win32&architecture=x64&currentVersion=0.28.0"
    status, _, body = _request(url)
    assert status == 200
    manifest = json.loads(body)
    assert manifest["artifact"]["platform"] == "windows"
    assert manifest["artifact"]["architecture"] == "x64"


@pytest.mark.parametrize("extra", ["distribution=macos", "channel=beta"])
def test_dropped_params_are_unknown(mock_factory: Callable[..., Any], extra: str) -> None:
    """``distribution`` / ``channel`` were removed from the final contract — sending them is a 400."""
    server = mock_factory()
    status, _, body = _request(f"{_release(server)}&{extra}")
    assert status == 400
    assert json.loads(body) == INVALID_QUERY_BODY


def test_missing_parameter_is_400(mock_factory: Callable[..., Any]) -> None:
    server = mock_factory()
    url = f"{_base(server)}{update_server.RELEASE_ROUTE}?clientType=cli&platform=darwin&architecture=arm64"
    status, _, body = _request(url)
    assert status == 400
    assert json.loads(body) == INVALID_QUERY_BODY


def test_unknown_parameter_is_400(mock_factory: Callable[..., Any]) -> None:
    server = mock_factory()
    status, _, body = _request(f"{_release(server)}&foo=1")
    assert status == 400
    assert json.loads(body) == INVALID_QUERY_BODY


@pytest.mark.parametrize(
    "query",
    [
        # clientType: the contract wants desktop/cli.
        "clientType=mobile&platform=darwin&architecture=arm64&currentVersion=0.28.0",
        # platform: the contract wants win32/darwin/linux — "windows" is the artifact spelling.
        "clientType=cli&platform=windows&architecture=arm64&currentVersion=0.28.0",
        # platform: win64 was merged into win32 in the final contract.
        "clientType=cli&platform=win64&architecture=arm64&currentVersion=0.28.0",
        # architecture: the contract wants x64, not the client-internal amd64 spelling.
        "clientType=cli&platform=darwin&architecture=amd64&currentVersion=0.28.0",
        # currentVersion: not SemVer, missing patch, and empty all reject.
        "clientType=cli&platform=darwin&architecture=arm64&currentVersion=latest",
        "clientType=cli&platform=darwin&architecture=arm64&currentVersion=0.28",
        "clientType=cli&platform=darwin&architecture=arm64&currentVersion=",
        # an otherwise valid query with one unknown parameter still rejects.
        "clientType=cli&platform=darwin&architecture=arm64&currentVersion=0.28.0&extra=1",
    ],
)
def test_invalid_queries_are_400(mock_factory: Callable[..., Any], query: str) -> None:
    server = mock_factory()
    status, _, body = _request(f"{_base(server)}{update_server.RELEASE_ROUTE}?{query}")
    assert status == 400
    assert json.loads(body) == INVALID_QUERY_BODY


def test_no_update_mode_returns_204(mock_factory: Callable[..., Any]) -> None:
    server = mock_factory(mode="no_update")
    status, headers, body = _request(_release(server))
    assert status == 204
    assert body == b""
    assert headers.get("Content-Length") is None


def test_error_mode_returns_500(mock_factory: Callable[..., Any]) -> None:
    server = mock_factory(mode="error")
    status, _, _ = _request(_release(server))
    assert status == 500


def test_garbage_mode_returns_unparseable_body(mock_factory: Callable[..., Any]) -> None:
    server = mock_factory(mode="garbage")
    status, headers, body = _request(_release(server))
    assert status == 200
    assert headers["Content-Type"].startswith("application/json")
    with pytest.raises(json.JSONDecodeError):
        json.loads(body)


def test_drop_fields_omit_manifest_fields(mock_factory: Callable[..., Any]) -> None:
    """The structure-mismatch drill: the 200 body parses but misses consumed fields."""
    server = mock_factory(drop_fields=["version"])
    status, _, body = _request(_release(server))
    assert status == 200
    assert "version" not in json.loads(body)


def test_drop_fields_dotted_path_removes_artifact_url(mock_factory: Callable[..., Any]) -> None:
    server = mock_factory(drop_fields=["artifact.url"])
    _, _, body = _request(_release(server))
    manifest = json.loads(body)
    assert manifest["artifact"] == {"platform": "macos", "architecture": "arm64"}


def test_drop_fields_ignore_unknown_paths(mock_factory: Callable[..., Any]) -> None:
    server = mock_factory(drop_fields=["nope", "artifact.nope"])
    _, _, body = _request(_release(server))
    manifest = json.loads(body)
    assert manifest["version"] == "999.0.0"
    assert manifest["artifact"]["url"].startswith("http://127.0.0.1")


def test_debug_config_switches_malformed_response_drills(mock_factory: Callable[..., Any]) -> None:
    server = mock_factory()
    control = f"{_base(server)}{update_server.DEBUG_CONFIG_ROUTE}"
    assert "version" in json.loads(_request(_release(server))[2])
    status, _, body = _post(control, {"drop_fields": ["version", "artifact.url"]})
    assert status == 200
    assert json.loads(body)["drop_fields"] == ["version", "artifact.url"]
    manifest = json.loads(_request(_release(server))[2])
    assert "version" not in manifest
    assert "url" not in manifest["artifact"]
    # raw_body replaces the manifest wholesale — the truncated-answer drill.
    status, _, _ = _post(control, {"drop_fields": [], "raw_body": '{"version": "0.29.'})
    assert status == 200
    _, _, body = _request(_release(server))
    assert body == '{"version": "0.29.'.encode("utf-8")
    with pytest.raises(json.JSONDecodeError):
        json.loads(body)


def test_debug_config_rejects_invalid_drop_fields(mock_factory: Callable[..., Any]) -> None:
    server = mock_factory()
    status, _, body = _post(f"{_base(server)}{update_server.DEBUG_CONFIG_ROUTE}", {"drop_fields": "version"})
    assert status == 400
    assert "drop_fields" in json.loads(body)["error"]


def test_equal_candidate_version_answers_204(mock_factory: Callable[..., Any]) -> None:
    """update mode mirrors the real service: an equal currentVersion is "already latest"."""
    server = mock_factory(version="0.28.0")
    status, _, body = _request(_release(server))
    assert status == 204
    assert body == b""


def test_older_candidate_version_answers_204(mock_factory: Callable[..., Any]) -> None:
    server = mock_factory(version="0.1.1")
    assert _request(_release(server))[0] == 204


def test_prerelease_current_version_still_gets_the_release(mock_factory: Callable[..., Any]) -> None:
    """A release outranks a prerelease of the same core — the dev-build spelling stays detectable."""
    server = mock_factory(version="0.28.0")
    url = (
        f"{_base(server)}{update_server.RELEASE_ROUTE}"
        "?clientType=cli&platform=darwin&architecture=arm64&currentVersion=0.28.0-dev-abc1234"
    )
    assert _request(url)[0] == 200


def test_force_update_serves_manifest_without_comparison(mock_factory: Callable[..., Any]) -> None:
    """``force_update`` keeps the dirty-data drill available: 200 with a candidate older than the client."""
    server = mock_factory(version="0.1.1", force_update=True)
    status, _, body = _request(_release(server))
    assert status == 200
    assert json.loads(body)["version"] == "0.1.1"


def test_debug_config_switches_version_and_force_at_runtime(mock_factory: Callable[..., Any]) -> None:
    server = mock_factory(version="0.29.0")
    assert _request(_release(server))[0] == 200
    control = f"{_base(server)}{update_server.DEBUG_CONFIG_ROUTE}"
    status, _, body = _post(control, {"version": "0.1.1", "force_update": False})
    assert status == 200
    snapshot = json.loads(body)
    assert snapshot["version"] == "0.1.1"
    assert snapshot["force_update"] is False
    assert _request(_release(server))[0] == 204  # a 0.28.0 client vs a 0.1.1 candidate: no update
    status, _, body = _post(control, {"force_update": True})
    assert status == 200
    assert json.loads(body)["force_update"] is True
    assert _request(_release(server))[0] == 200


def test_debug_config_rejects_invalid_version(mock_factory: Callable[..., Any]) -> None:
    server = mock_factory()
    status, _, body = _post(f"{_base(server)}{update_server.DEBUG_CONFIG_ROUTE}", {"version": "latest"})
    assert status == 400
    assert "version" in json.loads(body)["error"]


def test_debug_config_switches_force_upgrade_at_runtime(mock_factory: Callable[..., Any]) -> None:
    server = mock_factory()
    status, _, body = _post(f"{_base(server)}{update_server.DEBUG_CONFIG_ROUTE}", {"force_upgrade": True})
    assert status == 200
    assert json.loads(body)["force_upgrade"] is True
    _, _, body = _request(_release(server))
    assert json.loads(body)["forceUpgrade"] is True


@pytest.mark.parametrize(
    ("candidate", "current", "expected"),
    [
        ("0.29.0", "0.28.0", True),
        ("0.28.0", "0.28.0", False),
        ("0.27.9", "0.28.0", False),
        ("1.0.0", "0.99.99", True),
        # a release outranks every prerelease of the same core
        ("0.28.0", "0.28.0-dev-abc1234", True),
        ("0.28.0-dev-abc1234", "0.28.0", False),
        # numeric prerelease identifiers compare numerically, not lexically
        ("0.28.0-beta.10", "0.28.0-beta.2", True),
        ("0.28.0-beta.2", "0.28.0-beta.10", False),
        # numeric identifiers rank below alphanumeric ones
        ("0.28.0-1", "0.28.0-alpha", False),
        ("0.28.0-alpha", "0.28.0-1", True),
        # alphanumeric identifiers compare in ASCII order
        ("0.28.0-beta", "0.28.0-alpha", True),
        # a longer identifier list outranks its equal prefix
        ("0.28.0-alpha.1", "0.28.0-alpha", True),
    ],
)
def test_semver_precedence_matrix(candidate: str, current: str, expected: bool) -> None:
    assert update_server._is_newer(candidate, current) is expected


def test_if_none_match_hits_304(mock_factory: Callable[..., Any]) -> None:
    server = mock_factory()
    _, headers, _ = _request(_release(server))
    etag = headers["ETag"]
    status, _, body = _request(_release(server), headers={"If-None-Match": etag})
    assert status == 304
    assert body == b""
    # A different (weak-prefixed, quoted) tag misses and serves 200 again.
    status, _, _ = _request(_release(server), headers={"If-None-Match": f'W/"{etag[:-1]}x"'})
    assert status == 200


def test_debug_config_switches_mode_at_runtime(mock_factory: Callable[..., Any]) -> None:
    server = mock_factory()
    assert _request(_release(server))[0] == 200
    status, _, body = _post(f"{_base(server)}{update_server.DEBUG_CONFIG_ROUTE}", {"mode": "no_update"})
    assert status == 200
    snapshot = json.loads(body)
    assert snapshot["mode"] == "no_update"
    assert snapshot["requests"] == 1  # the release request so far; the control call is not logged
    assert _request(_release(server))[0] == 204


def test_debug_config_rejects_unknown_mode(mock_factory: Callable[..., Any]) -> None:
    server = mock_factory()
    status, _, body = _post(f"{_base(server)}{update_server.DEBUG_CONFIG_ROUTE}", {"mode": "nope"})
    assert status == 400
    assert "mode" in json.loads(body)["error"]


def test_request_log_records_status_and_query(mock_factory: Callable[..., Any]) -> None:
    server = mock_factory()
    _request(_release(server))
    _request(f"{_base(server)}{update_server.RELEASE_ROUTE}?clientType=cli&platform=darwin&architecture=arm64")
    status, _, body = _request(f"{_base(server)}{update_server.DEBUG_REQUESTS_ROUTE}")
    assert status == 200
    entries = json.loads(body)["requests"]
    assert [entry["status"] for entry in entries] == [200, 400]
    assert entries[0]["query"]["currentVersion"] == "0.28.0"
    assert entries[1]["query"] == {}


def test_post_reset_restores_defaults_and_empties_log(mock_factory: Callable[..., Any]) -> None:
    """``/debug/reset`` undoes every knob (even ones set at build time) and clears the log."""
    server = mock_factory(
        mode="error",
        version="0.1.1",
        slow_ms=25,
        force_update=True,
        force_upgrade=True,
        raw_body='{"broken',
        drop_fields=["version"],
    )
    assert _request(_release(server))[0] == 500
    status, _, body = _post(f"{_base(server)}{update_server.DEBUG_RESET_ROUTE}", {})
    assert status == 200
    snapshot = json.loads(body)
    assert snapshot["mode"] == "update"
    assert snapshot["version"] == "999.0.0"
    assert snapshot["slow_ms"] == 0
    assert snapshot["force_update"] is False
    assert snapshot["force_upgrade"] is False
    assert snapshot["raw_body"] == ""
    assert snapshot["drop_fields"] == []
    assert snapshot["requests"] == 0  # the log was dropped too
    # back to out-of-the-box behaviour: 999.0.0 > 0.28.0 → a fresh manifest
    assert _request(_release(server))[0] == 200


def test_unknown_route_is_404(mock_factory: Callable[..., Any]) -> None:
    server = mock_factory()
    assert _request(f"{_base(server)}/nope")[0] == 404
    assert _request(f"{_base(server)}/health")[0] == 404  # /health was removed


def test_rejects_non_loopback_bind() -> None:
    with pytest.raises(ValueError, match="loopback"):
        update_server.create_server(host="0.0.0.0")


def test_rejects_invalid_startup_mode() -> None:
    with pytest.raises(ValueError, match="mode"):
        update_server.create_server(MockUpdateConfig(mode="nope"))


def test_rejects_invalid_startup_version() -> None:
    with pytest.raises(ValueError, match="version"):
        update_server.create_server(MockUpdateConfig(version="latest"))


def test_rejects_invalid_startup_drop_fields() -> None:
    with pytest.raises(ValueError, match="drop_fields"):
        update_server.create_server(MockUpdateConfig(drop_fields="version"))  # type: ignore[arg-type]
