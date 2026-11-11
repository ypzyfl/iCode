# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Release-check client for the AIxCoding auto-update flow.

One background GET against the frozen ``releases/check`` contract
(``aixcoding/mock/update/`` freezes the wire protocol): four required query
params (strict mode — unknown/missing/invalid is a 400 the client simply
treats as a failed check), a v2 manifest on 200, ``204``/``304`` for "no
applicable release", and the version comparison entirely server-side.  The
client maps the params, parses ``version``/``artifact.url``/``forceUpgrade``
out of a 200 body, and stays silent on every failure — the flow must never
disturb startup.

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

logger = logging.getLogger(__name__)

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
#: the ``/csas`` prefix; local is the loopback update mock
#: (``aixcoding/mock/update/``, port 7778 — not auth's 7777).
_TIER_BASES: dict[str, str] = {
    "local": "http://127.0.0.1:7778/csas",
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
            logger.debug(
                "update check: unparseable manifest body: %s: %s (body=%s)",
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
        logger.debug("update check: manifest missing version/artifact.url (body=%s)", _body_preview(response))
        return None
    if response.status_code in (204, 304):
        return None  # current / platform mismatch / gray-release miss / ETag fallback
    logger.debug("update check: unexpected status %s (body=%s)", response.status_code, _body_preview(response))
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
        logger.debug("update check skipped: unbuildable query params")
        return None
    url = check_url()
    try:
        # asyncio.timeout bounds httpx's per-phase timeouts (connect/read/
        # write/pool, each 15s) with one total ceiling.
        async with asyncio.timeout(_TIMEOUT_SECONDS):
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS, trust_env=False, transport=transport) as client:
                request = client.build_request("GET", url, params=params, headers=_request_headers())
                logger.debug(
                    "update check: sending request\n  method: %s\n  url: %s\n  headers: %s\n  timeout: %gs",
                    request.method,
                    request.url,
                    dict(request.headers),
                    _TIMEOUT_SECONDS,
                )
                response = await client.send(request)
    except httpx.TimeoutException, TimeoutError:
        logger.debug("update check: timed out after %gs (GET %s?%s)", _TIMEOUT_SECONDS, url, urlencode(params))
        return None
    except Exception as exc:
        logger.debug(
            "update check: request failed: %s: %s (GET %s?%s)",
            type(exc).__name__,
            exc,
            url,
            urlencode(params),
        )
        return None
    logger.debug(
        "update check: got response\n  status: %s\n  elapsed: %gs\n  body: %s",
        response.status_code,
        response.elapsed.total_seconds(),
        _body_preview(response),
    )
    return _parse_response(response)
