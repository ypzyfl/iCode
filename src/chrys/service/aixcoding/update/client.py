# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Release-check client for the AIxCoding auto-update flow.

One background GET against the frozen ``releases/check`` contract
(``aixcoding/mock/update/`` freezes the wire protocol): four required query
params (strict mode — unknown/missing/invalid is a 400 the client simply
treats as a failed check), a v2 manifest on 200, ``204``/``304`` for "no
applicable release", and the version comparison entirely server-side.  The
client maps the params, parses ``version``/``artifact.url``/``forceUpgrade``
out of a 200 body, and never raises -- a failed check logs a public WARNING
(the user wants to know) and returns None; "no applicable release" (204/304)
and an unbuildable query stay detail-only, so the flow never disturbs startup.

The base URL resolves the way the model catalog's does
(``catalog.py::catalog_base_url``): the shared ``[update].base_url`` from
``aixcoding.toml`` wins, otherwise the deployment tier table below — keyed
by the same shared environment auth and the catalog use, with dev/prod on
auth's own hosts (one deployment, one pair of tiers; see the drift test).
The update command's mirror root derives from the same resolved base
(``app/aixcoding/update/commands.py``), so one ``[update].base_url``
override moves both endpoints.

Design: aixcoding/docs/batches/auto-update/design.md
"""

from __future__ import annotations

import asyncio
import logging
import re
import sys
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from chrys import __version__
from chrys.foundation.platform import get_platform
from chrys.service.aixcoding.config import load_config

# AIxCoding logging (batches/logging-coverage): the update domain rides the
# aixcoding tree -- the main channel carries user-facing events (check
# failures are something the user wants to know and can report), detail
# carries the wire/technical trace (ADR-0017, DEVELOPMENT.md §9).
_log = logging.getLogger("aixcoding.update")
_detail_log = logging.getLogger("aixcoding.detail.update")
_DETAIL_LEVEL = 5  # mirrors diagnostics.logging_support (session.py precedent)

RELEASE_CHECK_URL_PATH = "api/v2/releases/check"
_TIMEOUT_SECONDS = 15.0

# clientType: the TUI is the CLI-shaped client (the desktop app is "desktop").
_CLIENT_TYPE = "cli"

# platform domain: sys.platform values the contract accepts (win64 folded
# into win32; the word size rides on architecture).  Outside it (e.g.
# freebsd) the check is skipped.
_PLATFORMS = ("win32", "darwin", "linux")

# Architecture mapping: the platform info's internal name for x64 is
# ``amd64``; x86 rides along as x64 (the server answers 204 on a mismatch).
_ARCH_MAP = {"arm64": "arm64", "amd64": "x64", "x86": "x64"}

# currentVersion is strictly validated: 1-64 chars, MAJOR.MINOR.PATCH[-PRERELEASE].
# Dev builds (-dev-<sha>) are legal and sent as-is; anything else skips the check.
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$")
_VERSION_MIN_LENGTH, _VERSION_MAX_LENGTH = 1, 64

# Truncation for response bodies in debug logs: enough for failure triage
# (proxy error pages included) without flooding the log.
_BODY_LOG_LIMIT = 2000

#: Release-check base per deployment tier, keyed by the shared environment
#: the same way the model catalog keys its ``_CATALOG_BASES`` — dev and prod
#: are auth's own hosts (``kernel/aixcoding/auth/environments.py``) under
#: the ``/csas`` prefix.  Like ``catalog.py``, ``local`` is the loopback mock
#: served straight off the origin with no prefix (``aixcoding/mock/update/``,
#: port 7778 — not auth's 7777): the deployment prefix belongs to the real
#: hosts, not to the frozen ``api/v2/releases/check`` path.
_TIER_BASES: dict[str, str] = {
    "local": "http://127.0.0.1:7778",
    "dev": "http://81.89.182.150/csas",
    "prod": "http://82.187.34.98/csas",
}
DEFAULT_ENVIRONMENT = "prod"


@dataclass(frozen=True, slots=True)
class AppUpdate:
    """One successful check: the candidate version, its download page, and the force flag."""

    version: str
    download_url: str
    force_upgrade: bool = False


def resolve_check_base() -> str:
    """The shared TOML base, falling back to the deployment tier (catalog-shaped)."""
    config = load_config()
    if config.update.base_url:
        return config.update.base_url
    return _TIER_BASES.get(config.environment, _TIER_BASES[DEFAULT_ENVIRONMENT])


def check_url() -> str:
    """The full release-check endpoint — never empty while a tier exists."""
    return f"{resolve_check_base().rstrip('/')}/{RELEASE_CHECK_URL_PATH}"


def _is_strict_semver(version: str) -> bool:
    return _VERSION_MIN_LENGTH <= len(version) <= _VERSION_MAX_LENGTH and _SEMVER_RE.fullmatch(version) is not None


def build_query_params(current_version: str = __version__) -> dict[str, str] | None:
    """The four required query params, or None when a value cannot be mapped."""
    if sys.platform not in _PLATFORMS:
        return None
    arch = _ARCH_MAP.get(get_platform().arch)
    if arch is None:
        return None
    if not _is_strict_semver(current_version):
        return None
    return {
        "clientType": _CLIENT_TYPE,
        "platform": sys.platform,
        "architecture": arch,
        "currentVersion": current_version,
    }


def _request_headers() -> dict[str, str]:
    """Header hook: the contract asks for no auth; a token header lands here only."""
    return {}


def _body_preview(response: httpx.Response) -> str:
    """Response body preview for failure logs, truncated past the budget."""
    text = response.text if response.content else ""
    if len(text) > _BODY_LOG_LIMIT:
        text = f"{text[:_BODY_LOG_LIMIT]}...(truncated, total {len(text)} chars)"
    return text


def _parse_response(response: httpx.Response) -> AppUpdate | None:
    """200 takes version + artifact.url (+forceUpgrade); 204/304 mean no update; the rest fail silently."""
    if response.status_code == 200:
        try:
            payload = response.json()
            version = payload["version"]
            download_url = payload["artifact"]["url"]
        except Exception as exc:
            _log.warning("自动更新检查失败，本次跳过。")
            _detail_log.log(_DETAIL_LEVEL, "自动更新检查失败，本次跳过。")
            _detail_log.log(
                _DETAIL_LEVEL,
                "更新检查响应解析失败：%s: %s（body=%s）",
                type(exc).__name__,
                exc,
                _body_preview(response),
            )
            return None
        if isinstance(version, str) and version and isinstance(download_url, str) and download_url:
            return AppUpdate(
                version=version,
                download_url=download_url,
                force_upgrade=payload.get("forceUpgrade") is True,
            )
        _log.warning("自动更新检查失败，本次跳过。")
        _detail_log.log(_DETAIL_LEVEL, "自动更新检查失败，本次跳过。")
        _detail_log.log(_DETAIL_LEVEL, "更新检查响应缺少 version/artifact.url（body=%s）", _body_preview(response))
        return None
    if response.status_code in (204, 304):
        return None  # current / platform mismatch / gray-release miss / ETag fallback
    _log.warning("自动更新检查失败，本次跳过。")
    _detail_log.log(_DETAIL_LEVEL, "自动更新检查失败，本次跳过。")
    _detail_log.log(
        _DETAIL_LEVEL, "更新检查响应状态异常：HTTP %s（body=%s）", response.status_code, _body_preview(response)
    )
    return None


async def check_for_update(
    *,
    transport: httpx.AsyncBaseTransport | None = None,
    current_version: str = __version__,
) -> AppUpdate | None:
    """One GET.  Every failure (network/status/parse) returns None; never raises.

    - ``trust_env=False`` like the other aixcoding clients: the intranet
      endpoint is reached directly, untouched by local proxy variables;
    - no ``If-None-Match``: every start is a new process, nothing persists an etag.
    """
    params = build_query_params(current_version)
    if params is None:
        # Not a check failure: this machine's platform/arch/version shape is
        # outside the contract, so the check never runs -- detail only.
        _detail_log.log(_DETAIL_LEVEL, "更新检查查询参数不可构造（平台/架构/版本不匹配），本次不检查。")
        return None
    url = check_url()
    try:
        # asyncio.timeout bounds httpx's per-phase timeouts (connect/read/
        # write/pool, each 15s) with one total ceiling.
        async with asyncio.timeout(_TIMEOUT_SECONDS):
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS, trust_env=False, transport=transport) as client:
                request = client.build_request("GET", url, params=params, headers=_request_headers())
                _detail_log.log(
                    _DETAIL_LEVEL,
                    "更新检查请求：GET %s\n  url: %s\n  headers: %s\n  timeout: %gs",
                    request.method,
                    request.url,
                    dict(request.headers),
                    _TIMEOUT_SECONDS,
                )
                response = await client.send(request)
    except httpx.TimeoutException, TimeoutError:
        _log.warning("自动更新检查失败，本次跳过。")
        _detail_log.log(_DETAIL_LEVEL, "自动更新检查失败，本次跳过。")
        _detail_log.log(
            _DETAIL_LEVEL, "更新检查请求超时（%.0f 秒）：GET %s?%s", _TIMEOUT_SECONDS, url, urlencode(params)
        )
        return None
    except Exception as exc:
        _log.warning("自动更新检查失败，本次跳过。")
        _detail_log.log(_DETAIL_LEVEL, "自动更新检查失败，本次跳过。")
        _detail_log.log(
            _DETAIL_LEVEL,
            "更新检查请求失败：%s: %s（GET %s?%s）",
            type(exc).__name__,
            exc,
            url,
            urlencode(params),
        )
        return None
    _detail_log.log(
        _DETAIL_LEVEL,
        "更新检查收到响应\n  status: %s\n  body: %s",
        response.status_code,
        _body_preview(response),
    )
    return _parse_response(response)
