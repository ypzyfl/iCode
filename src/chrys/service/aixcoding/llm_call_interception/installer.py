# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Install AIxCoding hooks around the shared Chrys HTTP client factory."""

from __future__ import annotations

from functools import update_wrapper
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from chrys.service.profiles.models.schema import ModelProfile

_FACTORY_ATTRIBUTE = "_build_profile_http_client"
_FACTORY_MARKER = "_aixcoding_http_interception_factory"
_CLIENT_MARKER = "_aixcoding_http_interception_hooks"


def install_http_interception() -> None:
    """Idempotently wrap the private factory without changing upstream files."""

    from chrys.service.llm import clients

    current = clients._build_profile_http_client
    if getattr(current, _FACTORY_MARKER, False):
        return

    from chrys.service.llm.request_tracking import _CONTEXT_EXTENSION, REQUEST_ATTEMPT_ID_EXTENSION

    for extension in (_CONTEXT_EXTENSION, REQUEST_ATTEMPT_ID_EXTENSION):
        if not isinstance(extension, str):
            raise TypeError("request tracking extension keys must be strings")

    def build_with_interception(
        profile: ModelProfile,
        timeout: Any,
        *,
        raw_http_log_path: Path | None = None,
        session_id: str | None = None,
        auth: httpx.Auth | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> httpx.AsyncClient:
        client = current(
            profile,
            timeout,
            raw_http_log_path=raw_http_log_path,
            session_id=session_id,
            auth=auth,
            transport=transport,
        )
        try:
            _install_client_hooks(client, provider=profile.provider, model=profile.model_id)
        except Exception:
            from .interceptor import report_client_install_failure

            report_client_install_failure(profile.provider, profile.model_id)
        return client

    update_wrapper(build_with_interception, current)
    setattr(build_with_interception, _FACTORY_MARKER, True)
    # ty rejects cross-module function rebinding even with identical signatures.
    # The follow_wrapped=False signature test is the deliberate drift guard.
    setattr(clients, _FACTORY_ATTRIBUTE, build_with_interception)


def _install_client_hooks(client: httpx.AsyncClient, *, provider: str, model: str) -> None:
    if getattr(client, _CLIENT_MARKER, False):
        return

    from .interceptor import get_http_policy

    if get_http_policy() is None:
        return

    from .hooks import build_http_hooks

    custom = build_http_hooks(provider=provider, model=model)
    event_hooks = {name: list(hooks) for name, hooks in client.event_hooks.items()}
    request_hooks = event_hooks.setdefault("request", [])
    raw_index = next(
        (
            index
            for index, hook in enumerate(request_hooks)
            if getattr(hook, "__module__", "") == "chrys.service.llm.raw_http_log"
        ),
        len(request_hooks),
    )
    request_hooks.insert(raw_index, custom["request"][0])
    event_hooks.setdefault("response", []).append(custom["response"][0])
    client.event_hooks = event_hooks
    setattr(client, _CLIENT_MARKER, True)
