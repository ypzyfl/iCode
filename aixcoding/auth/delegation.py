# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Desktop-delegated login: the parent app owns the session, iCode inherits it.

When iCode runs embedded -- today the AIxCoding desktop spawns ``chrys acp``
as an ACP child per session -- the parent already walked the device-code flow
and hands the very same token to the child through the environment.  That
token is model credential and account credential in one (the desktop's
``modelCredential``), so iCode treats it as "already logged in" instead of
running its own login::

    session = get_login_session()             # delegation detected at build
    session.stored_token                      # => the parent's token
    await session.check_silent()              # => AccountInfo from /user/info

The delegated credential is read-only and RAM-only.  It is never written to
the credential store, a server-side rejection only stops it from shadowing
the store (the parent must re-login and respawn the child), and ``logout()``
is a no-op while it is active: the parent owns that session's lifecycle.

Environment contract, in detection order:

``CHRYS_AUTH_DELEGATED_TOKEN`` (primary; newer desktop builds)
    The parent's account token.  Optional display hints:
    ``CHRYS_AUTH_DELEGATED_EHR`` and ``CHRYS_AUTH_DELEGATED_NAME`` carry
    identity for surfaces that render before the first ``user/info`` trip.
``AIXCODING_USER_EHR`` + ``OPENAI_API_KEY`` (compat, desktop <= fix-1008)
    The desktop already injects the login token as the provider credential
    and stamps the user's EHR next to it; when both are present and the
    primary variable is absent, the pair is accepted as a delegation.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

#: Primary transport: the parent app's account token, plus display hints.
DELEGATED_TOKEN_VARIABLE = "CHRYS_AUTH_DELEGATED_TOKEN"
DELEGATED_EHR_VARIABLE = "CHRYS_AUTH_DELEGATED_EHR"
DELEGATED_NAME_VARIABLE = "CHRYS_AUTH_DELEGATED_NAME"

#: Compat transport for desktop builds that predate the variables above: the
#: model credential *is* the login token, and the user's EHR rides along.
COMPAT_EHR_VARIABLE = "AIXCODING_USER_EHR"
COMPAT_TOKEN_VARIABLE = "OPENAI_API_KEY"


@dataclass(frozen=True, slots=True)
class DelegatedCredential:
    """A parent-provided credential: read-only, never persisted, no local TTL.

    ``source`` names the environment variable the token arrived in, so
    diagnostics can say which contract a given child speaks.
    """

    token: str
    ehr: str = ""
    display_name: str = ""
    source: str = ""


def detect_delegation(
    environ: Mapping[str, str] | None = None,
) -> DelegatedCredential | None:
    """Read the delegation variables; ``None`` when the process is standalone.

    ``bootstrap_runtime`` freezes the process env before the app starts, so
    reading once at session construction is stable for the process lifetime;
    a parent that re-logins spawns a new child rather than editing our env.
    """
    env = os.environ if environ is None else environ
    token = (env.get(DELEGATED_TOKEN_VARIABLE) or "").strip()
    if token:
        return DelegatedCredential(
            token=token,
            ehr=(env.get(DELEGATED_EHR_VARIABLE) or "").strip(),
            display_name=(env.get(DELEGATED_NAME_VARIABLE) or "").strip(),
            source=DELEGATED_TOKEN_VARIABLE,
        )
    compat_token = (env.get(COMPAT_TOKEN_VARIABLE) or "").strip()
    compat_ehr = (env.get(COMPAT_EHR_VARIABLE) or "").strip()
    if compat_token and compat_ehr:
        return DelegatedCredential(token=compat_token, ehr=compat_ehr, source=COMPAT_TOKEN_VARIABLE)
    return None
