# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Tests for the startup update-detection client (``update_detection.py``).

Covers the dev doc's unit matrix (parameter mapping, strict-SemVer gate,
response parsing, error swallowing) plus end-to-end runs against the
loopback mock server in ``mock_server/aixcoding_update/`` — the real backend
does not exist yet, so the mock freezes the wire contract.
"""

from __future__ import annotations

import sys
import threading
from http.server import HTTPServer
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from mock_server.aixcoding_update.server import MockUpdateConfig, create_server

from chrys.aixcoding import update_detection
from chrys.aixcoding.update_detection import AppUpdate, build_query_params, check_for_update
from chrys.foundation.platform import PlatformInfo, ShellInfo

# --- helpers --------------------------------------------------------------- #


def _platform(arch: str, os_name: str = "macos") -> PlatformInfo:
    return PlatformInfo(
        os_name=os_name,
        arch=arch,
        os_version="",
        shell=ShellInfo(name="sh", path="/bin/sh", args=["-c"]),
        config_dir=Path("/tmp"),
        data_dir=Path("/tmp"),
    )


@pytest.fixture
def fake_platform(monkeypatch: pytest.MonkeyPatch):
    """Patch the module-level ``get_platform`` and ``__version__`` probes."""

    def _install(arch: str = "arm64", os_name: str = "macos", version: str = "0.28.0") -> PlatformInfo:
        info = _platform(arch, os_name)
        monkeypatch.setattr(update_detection, "get_platform", lambda: info)
        monkeypatch.setattr(update_detection, "__version__", version)
        return info

    return _install


@pytest.fixture
def mock_update_server():
    """Start a loopback mock on an ephemeral port; yield (base_url, server)."""
    server = create_server(MockUpdateConfig(), host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/csas", server
    finally:
        server.shutdown()
        HTTPServer.server_close(server)


# --- parameter mapping (§3.5) ---------------------------------------------- #


class TestBuildQueryParams:
    def test_darwin_arm64_maps_directly(self, fake_platform, monkeypatch) -> None:
        fake_platform(arch="arm64", os_name="macos")
        # platform 取自 sys.platform 原值, 与 get_platform mock 无关, 须一并钉住。
        monkeypatch.setattr(sys, "platform", "darwin")
        assert build_query_params() == {
            "clientType": "cli",
            "platform": "darwin",
            "architecture": "arm64",
            "currentVersion": "0.28.0",
        }

    @pytest.mark.parametrize(("arch", "expected"), [("amd64", "x64"), ("x86", "x64"), ("arm64", "arm64")])
    def test_arch_mapping(self, fake_platform, arch: str, expected: str) -> None:
        fake_platform(arch=arch, os_name="linux")
        params = build_query_params()
        assert params is not None
        assert params["architecture"] == expected

    def test_unknown_arch_skips_detection(self, fake_platform) -> None:
        fake_platform(arch="riscv")
        assert build_query_params() is None

    def test_unsupported_sys_platform_skips_detection(self, fake_platform, monkeypatch) -> None:
        fake_platform()
        monkeypatch.setattr(sys, "platform", "freebsd")
        assert build_query_params() is None

    def test_linux_platform_params(self, fake_platform, monkeypatch) -> None:
        fake_platform(arch="amd64", os_name="linux")
        monkeypatch.setattr(sys, "platform", "linux")
        params = build_query_params()
        assert params == {
            "clientType": "cli",
            "platform": "linux",
            "architecture": "x64",
            "currentVersion": "0.28.0",
        }

    def test_windows_platform_params(self, fake_platform, monkeypatch) -> None:
        """win64 merged into win32: Windows always reports sys.platform verbatim."""
        fake_platform(arch="amd64", os_name="windows")
        monkeypatch.setattr(sys, "platform", "win32")
        assert build_query_params() == {
            "clientType": "cli",
            "platform": "win32",
            "architecture": "x64",
            "currentVersion": "0.28.0",
        }

    def test_windows_arm64_also_reports_win32_platform(self, fake_platform, monkeypatch) -> None:
        fake_platform(arch="arm64", os_name="windows")
        monkeypatch.setattr(sys, "platform", "win32")
        params = build_query_params()
        assert params is not None
        assert params["platform"] == "win32"
        assert params["architecture"] == "arm64"


# --- strict SemVer gate (§3.6) ---------------------------------------------- #


class TestStrictSemver:
    # Note: "0.28.0-dev-" is a *valid* SemVer 2.0.0 prerelease ("dev-" is a
    # single hyphen-bearing identifier) and the doc §3.6 regex accepts it —
    # the §6 checklist item conflicting with that stays with the regex.
    @pytest.mark.parametrize("version", ["0.28.0", "0.28.0-dev-abc1234", "999.0.0", "1.2.3-x.7.z.92", "0.28.0-dev-"])
    def test_accepts(self, version: str) -> None:
        assert update_detection._is_strict_semver(version) is True

    @pytest.mark.parametrize("version", ["latest", "", "0.28", "0.28.0-", "0.28.0-dev.", "v0.28.0", "0.28.0 "])
    def test_rejects(self, version: str) -> None:
        assert update_detection._is_strict_semver(version) is False

    def test_overlong_version_rejected(self) -> None:
        assert update_detection._is_strict_semver("1." + "0" * 64) is False

    def test_invalid_local_version_skips_detection(self, fake_platform) -> None:
        fake_platform(version="latest")
        assert build_query_params() is None


# --- response parsing (§3.7) ------------------------------------------------- #


class TestParseResponse:
    def _response(self, status: int, body: bytes = b"") -> httpx.Response:
        return httpx.Response(status, content=body, headers={"content-type": "application/json"})

    def test_manifest_yields_update(self) -> None:
        body = b'{"version": "0.29.0", "artifact": {"url": "https://example.com/dl"}}'
        update = update_detection._parse_response(self._response(200, body))
        assert update == AppUpdate(version="0.29.0", download_url="https://example.com/dl")

    @pytest.mark.parametrize("body", [b"not json", b'{"version": "0.29.0"}', b'{"artifact": {"url": "x"}}', b"{}"])
    def test_malformed_manifest_yields_none(self, body: bytes) -> None:
        assert update_detection._parse_response(self._response(200, body)) is None

    @pytest.mark.parametrize("status", [204, 304])
    def test_no_update_statuses(self, status: int) -> None:
        assert update_detection._parse_response(self._response(status)) is None

    @pytest.mark.parametrize("status", [400, 401, 500])
    def test_error_statuses_yield_none(self, status: int) -> None:
        assert update_detection._parse_response(self._response(status, b"{}")) is None

    def test_non_string_fields_yield_none(self) -> None:
        body = b'{"version": 29, "artifact": {"url": "https://example.com/dl"}}'
        assert update_detection._parse_response(self._response(200, body)) is None


# --- end-to-end against the mock server ------------------------------------- #


class TestCheckForUpdateE2E:
    @pytest.fixture
    def client_against(self, fake_platform, monkeypatch):
        """Point the client at the given base URL with darwin/arm64 probes."""

        def _install(base_url: str) -> None:
            fake_platform(arch="arm64", os_name="macos")
            # E2E 全程假定 darwin/arm64 探针: platform 参数来自 sys.platform, 须钉住。
            monkeypatch.setattr(sys, "platform", "darwin")
            monkeypatch.setattr(update_detection, "load_settings", lambda: SimpleNamespace(base_url=base_url))

        return _install

    async def test_update_mode_hit(self, client_against, mock_update_server) -> None:
        base_url, server = mock_update_server
        client_against(base_url)
        update = await check_for_update()
        assert update is not None
        assert update.version == "999.0.0"
        # The mock derives the artifact URL from its own bound address (no
        # /csas prefix — that is the client's API path, not the mock's).
        assert update.download_url.startswith("http://127.0.0.1:")
        assert update.download_url.endswith("AIxCoding-999.0.0-arm64.zip")
        (recorded,) = server.mock_state.requests()
        assert recorded["query"] == {
            "clientType": "cli",
            "platform": "darwin",
            "architecture": "arm64",
            "currentVersion": update_detection.__version__,
        }
        assert recorded["status"] == 200

    async def test_equal_version_is_no_update(self, client_against, mock_update_server) -> None:
        base_url, server = mock_update_server
        client_against(base_url)
        server.mock_config.version = "0.28.0"
        assert await check_for_update() is None
        assert server.mock_state.requests()[-1]["status"] == 204

    async def test_error_mode_is_silent(self, client_against, mock_update_server) -> None:
        base_url, server = mock_update_server
        client_against(base_url)
        server.mock_config.mode = "error"
        assert await check_for_update() is None

    async def test_garbage_mode_is_silent(self, client_against, mock_update_server) -> None:
        base_url, server = mock_update_server
        client_against(base_url)
        server.mock_config.mode = "garbage"
        assert await check_for_update() is None

    async def test_connection_refused_is_silent(self, client_against) -> None:
        client_against("http://127.0.0.1:1/csas")  # nothing listens on port 1
        assert await check_for_update() is None

    async def test_unmappable_arch_never_sends_a_request(self, client_against, mock_update_server, monkeypatch) -> None:
        base_url, server = mock_update_server
        client_against(base_url)
        monkeypatch.setattr(update_detection, "get_platform", lambda: _platform(arch="riscv"))
        assert await check_for_update() is None
        assert server.mock_state.requests() == []
