# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Pure state computation for the header login indicator.

Labels and tooltips are Chinese-only constants (ADR-0010): the badge never
re-renders on a locale switch, so a recomputation is only needed when the
session state itself changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chrys.kernel.aixcoding.auth import AccountInfo, LoginSession

_LOGGED_OUT_LABEL = "未登录"
_LOGGED_OUT_TOOLTIP = "未登录 — 运行 /login 登录"
_SIGNED_IN_LABEL = "已登录"
_SIGNED_IN_TOOLTIP = "已登录：{name}"
_SIGNED_IN_WITH_EHR_TOOLTIP = "已登录：{name}（{ehr}）"
_MANAGED_TOOLTIP = "{name} — 登录由桌面端管理"


@dataclass(frozen=True, slots=True)
class LoginIndicatorState:
    """Display state for the header account badge.

    ``label`` and ``tooltip`` are ready-to-paint strings: the widget renders
    them verbatim.
    """

    label: str
    tooltip: str
    logged_in: bool
    managed: bool


def compute_login_indicator_state(
    session: LoginSession,
    *,
    account: AccountInfo | None = None,
) -> LoginIndicatorState:
    """Compute the account badge state from the login session (no network I/O).

    ``account`` is the freshest ``user/info`` result when the caller has one
    (login dialog success, startup silent check); without it the badge falls
    back to the ehr a stored credential carries, so an offline start still
    shows a signed-in chip instead of flashing logged-out.
    """
    delegated = session.delegated_credential
    if delegated is not None:
        name = _delegated_display_name(session, account)
        return LoginIndicatorState(
            label=_SIGNED_IN_LABEL,
            tooltip=_MANAGED_TOOLTIP.format(name=name) if name else _SIGNED_IN_LABEL,
            logged_in=True,
            managed=True,
        )

    if session.stored_token is None:
        return LoginIndicatorState(
            label=_LOGGED_OUT_LABEL,
            tooltip=_LOGGED_OUT_TOOLTIP,
            logged_in=False,
            managed=False,
        )

    name = account.display_name if account is not None else ""
    ehr = account.ehr if account is not None else ""
    if not name:
        # Offline fallback: the ehr the credential itself carries.
        name = session.stored_user_id or ""
    if ehr and ehr != name:
        tooltip = _SIGNED_IN_WITH_EHR_TOOLTIP.format(name=name, ehr=ehr)
    elif name:
        tooltip = _SIGNED_IN_TOOLTIP.format(name=name)
    else:
        tooltip = _SIGNED_IN_LABEL
    return LoginIndicatorState(
        label=_SIGNED_IN_LABEL,
        tooltip=tooltip,
        logged_in=True,
        managed=False,
    )


def _delegated_display_name(session: LoginSession, account: AccountInfo | None) -> str:
    """Pick the delegated identity hint: freshest account info beats env hints."""
    if account is not None and account.display_name:
        return account.display_name
    delegated = session.delegated_credential
    if delegated is None:  # pragma: no cover - guarded by the caller's branch
        return ""
    return delegated.display_name or delegated.ehr
