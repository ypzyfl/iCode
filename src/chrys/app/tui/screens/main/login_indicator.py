# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Pure state computation for the status-bar login indicator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from chrys.foundation.i18n import Localizer, MessageRef, msg
from chrys.foundation.i18n.formatting import sanitize_legacy_scalar

if TYPE_CHECKING:
    from aixcoding.auth.session import LoginSession
    from aixcoding.auth.types import AccountInfo

_LOGGED_OUT_LABEL = msg("tui.login_indicator.logged_out", fallback="Not logged in")
_SIGNED_IN_LABEL = msg("tui.login_indicator.signed_in", fallback="Signed in")
_LOGIN_HINT_TOOLTIP = msg(
    "tui.login_indicator.tooltip.login_hint",
    fallback="Not logged in — run /login to sign in",
)
_SIGNED_IN_TOOLTIP = msg(
    "tui.login_indicator.tooltip.signed_in",
    fallback="Signed in as {name}",
)
_SIGNED_IN_WITH_EHR_TOOLTIP = msg(
    "tui.login_indicator.tooltip.signed_in_with_ehr",
    fallback="Signed in as {name} ({ehr})",
)
_MANAGED_TOOLTIP = msg(
    "tui.login_indicator.tooltip.managed",
    fallback="{name} — login managed by the desktop app",
)


@dataclass(frozen=True, slots=True)
class LoginIndicatorState:
    """Display state for the status-bar account tag.

    ``label`` and ``tooltip`` are fully rendered (localized) strings: the
    widget paints them verbatim, so a locale switch recomputes the state
    instead of re-rendering stored message references.
    """

    label: str
    tooltip: str
    logged_in: bool
    managed: bool


def compute_login_indicator_state(
    session: LoginSession,
    localizer: Localizer,
    *,
    account: AccountInfo | None = None,
) -> LoginIndicatorState:
    """Compute the account tag state from the login session (no network I/O).

    ``account`` is the freshest ``user/info`` result when the caller has one
    (login dialog success, startup silent check); without it the tag falls
    back to the ehr a stored credential carries, so an offline start still
    shows a signed-in chip instead of flashing logged-out.
    """
    delegated = session.delegated_credential
    if delegated is not None:
        name = _delegated_display_name(session, account)
        if not name:
            return LoginIndicatorState(
                label=_render(localizer, _SIGNED_IN_LABEL.bind()),
                tooltip=_render(localizer, _SIGNED_IN_LABEL.bind()),
                logged_in=True,
                managed=True,
            )
        return LoginIndicatorState(
            label=name,
            tooltip=_render(localizer, _MANAGED_TOOLTIP.bind(name=name)),
            logged_in=True,
            managed=True,
        )

    if session.stored_token is None:
        return LoginIndicatorState(
            label=_render(localizer, _LOGGED_OUT_LABEL.bind()),
            tooltip=_render(localizer, _LOGIN_HINT_TOOLTIP.bind()),
            logged_in=False,
            managed=False,
        )

    name = account.display_name if account is not None else ""
    ehr = account.ehr if account is not None else ""
    if not name:
        # Offline fallback: the ehr the credential itself carries.
        name = session.stored_user_id or ""
    if not name:
        return LoginIndicatorState(
            label=_render(localizer, _SIGNED_IN_LABEL.bind()),
            tooltip=_render(localizer, _SIGNED_IN_LABEL.bind()),
            logged_in=True,
            managed=False,
        )
    if ehr and ehr != name:
        tooltip = _render(localizer, _SIGNED_IN_WITH_EHR_TOOLTIP.bind(name=name, ehr=ehr))
    else:
        tooltip = _render(localizer, _SIGNED_IN_TOOLTIP.bind(name=name))
    return LoginIndicatorState(label=name, tooltip=tooltip, logged_in=True, managed=False)


def _delegated_display_name(session: LoginSession, account: AccountInfo | None) -> str:
    """Pick the delegated identity hint: freshest account info beats env hints."""
    if account is not None and account.display_name:
        return account.display_name
    delegated = session.delegated_credential
    if delegated is None:  # pragma: no cover - guarded by the caller's branch
        return ""
    return delegated.display_name or delegated.ehr


def _render(localizer: Localizer, reference: MessageRef) -> str:
    return sanitize_legacy_scalar(localizer.render(reference))
