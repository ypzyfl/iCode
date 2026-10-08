# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Endpoint resolution for the AIxCoding auth services.

Auth and user data are two distinct services behind the same host, differing
only in path prefix. Three deployment tiers ship as constants:

=========  ========  ==============================================
Tier       authUrl   dataUrl
=========  ========  ==============================================
LOCAL      :7777     the bundled mock (``mock_server/aixcoding_auth/server.py``)
DEV        81.89.182.150  ``/csas/api/v1`` vs ``/aicoding/api/v1``
PROD       82.187.34.98   ``/csas/api/v1`` vs ``/aicoding/api/v1``
=========  ========  ==============================================

Resolution order (first match wins):

1. ``CHRYS_AUTH_SERVER_URL`` -- replaces protocol + host of **both** URLs,
   keeping each path prefix (a port may be included). Invalid values are
   ignored, never fatal.
2. The tier selected by ``CHRYS_AUTH_ENVIRONMENT`` (``local``/``dev``/``prod``;
   unknown values fall back to ``prod``).

The environment variable names deliberately mirror the ``CHRYS_*`` convention
of the host app; ``bootstrap_runtime`` freezes the process environment before
the TUI starts, so reading ``os.environ`` at call time is stable.
"""

from __future__ import annotations

import os
from urllib.parse import urlsplit

from aixcoding.auth.types import Environment

#: Fallback PROD host kept from the other reference project, for the day the
#: primary intranet address does not answer (see the plan's risk #15).
_BACKUP_PROD_HOST = "22.189.54.139"

_BASE_PATHS: dict[Environment, tuple[str, str]] = {
    Environment.LOCAL: ("http://localhost:7777/api/v1", "http://localhost:7777/api/v1"),
    Environment.DEV: ("http://81.89.182.150/csas/api/v1", "http://81.89.182.150/aicoding/api/v1"),
    Environment.PROD: ("http://82.187.34.98/csas/api/v1", "http://82.187.34.98/aicoding/api/v1"),
}

ENVIRONMENT_VARIABLE = "CHRYS_AUTH_ENVIRONMENT"
SERVER_URL_VARIABLE = "CHRYS_AUTH_SERVER_URL"


def resolve_environment(environ: dict[str, str] | None = None) -> Environment:
    """Read the tier from the environment, defaulting to PROD."""
    env = os.environ if environ is None else environ
    raw = (env.get(ENVIRONMENT_VARIABLE) or "").strip().lower()
    try:
        return Environment(raw)
    except ValueError:
        return Environment.PROD


def _replace_origin(url: str, origin: str) -> str:
    """Swap protocol+host of ``url`` for ``origin``, keeping path and query."""
    split = urlsplit(url)
    replacement = urlsplit(origin)
    if not replacement.scheme or not replacement.netloc:
        return url
    return f"{replacement.scheme}://{replacement.netloc}{split.path}" + (f"?{split.query}" if split.query else "")


def resolve_endpoints(
    environment: Environment | None = None,
    environ: dict[str, str] | None = None,
) -> tuple[str, str]:
    """Return ``(auth_url, data_url)`` for the resolved tier.

    ``CHRYS_AUTH_SERVER_URL`` overrides both origins when it parses as a bare
    ``scheme://host[:port]``; anything else is treated as unset.
    """
    env = os.environ if environ is None else environ
    tier = environment or resolve_environment(env)
    auth_url, data_url = _BASE_PATHS[tier]
    override = (env.get(SERVER_URL_VARIABLE) or "").strip()
    if override:
        candidate = urlsplit(override if "//" in override else f"//{override}", scheme="http")
        # ``urlsplit`` accepts absurd netlocs ("not a url"); demand at least a
        # plausible host: non-empty and free of whitespace.
        if candidate.scheme and candidate.netloc and not any(c.isspace() for c in candidate.netloc):
            origin = f"{candidate.scheme}://{candidate.netloc}"
            auth_url = _replace_origin(auth_url, origin)
            data_url = _replace_origin(data_url, origin)
    return auth_url, data_url
