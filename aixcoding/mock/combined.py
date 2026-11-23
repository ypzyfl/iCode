# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Single-port mock combo (mock design 2026-11-20: unified port 15678).

The launcher's default form: one server, one port, every migrated sub-service's
routes. Path ownership splits cleanly — the update mock owns ``/api/v2/**``
(the frozen release-check path has no deployment prefix by design), the
telemetry mock owns ``/csas/telemetry/**`` (mock 1B), and the
catalog(+embedded auth) handler answers everything else. Each sub-package's
independent factory (``create_server``/CLI) stays for low-level tests and
debugging (DIRECTORY §6); this module is the composition layer only.

Port rationale (mock/design.md, 2026-11-20 decision): 15678 sits in the
15001-49151 safe band - above this machine's measured Windows dynamic range
(1024-15000, where 7777/7778 lived and 7778 was really taken once) and below
the standard ephemeral range (49152+), and no known service claims it.
"""

from __future__ import annotations

import logging
import threading
from http.server import BaseHTTPRequestHandler
from typing import Any
from urllib.parse import urlsplit

from aixcoding.mock.auth.server import MockAuthConfig, MockAuthState
from aixcoding.mock.model_catalog import server as catalog_server
from aixcoding.mock.model_catalog.server import CatalogMockServer
from aixcoding.mock.model_catalog.source import CatalogSource
from aixcoding.mock.model_catalog.state import CatalogMockState
from aixcoding.mock.telemetry import server as telemetry_server
from aixcoding.mock.telemetry.server import MockTelemetryState
from aixcoding.mock.update import server as update_server
from aixcoding.mock.update.server import MockUpdateConfig, MockUpdateState

logger = logging.getLogger(__name__)

DEFAULT_COMBINED_PORT = 15678
DEFAULT_HOST = "127.0.0.1"

#: Paths owned by the update mock; the telemetry mock owns
#: ``/csas/telemetry/**``; everything else falls through to the
#: catalog(+auth) handler, which knows its own auth/catalog split.
UPDATE_ROUTE_PREFIXES = ("/api/v2/",)
TELEMETRY_ROUTE_PREFIXES = ("/csas/telemetry/",)


class CombinedMockServer(CatalogMockServer):
    """One threading server carrying every sub-service's state.

    Inherits the catalog server's bind hardening (Windows SO_EXCLUSIVEADDRUSE
    — the fail-fast promise) and its state/source attributes; adds the auth,
    update and telemetry states the combined handlers read.
    """

    def __init__(
        self,
        address: tuple[str, int],
        handler: type[BaseHTTPRequestHandler],
        *,
        catalog_state: CatalogMockState,
        catalog_source: CatalogSource,
        quiet: bool,
        auth_state: MockAuthState | None,
        update_state: MockUpdateState,
        telemetry_state: MockTelemetryState | None = None,
    ) -> None:
        super().__init__(address, handler, state=catalog_state, source=catalog_source, quiet=quiet)
        self.auth_state = auth_state
        self.update_state = update_state
        self.telemetry_state = telemetry_state
        # BR-1 capture hook: the catalog chat handler calls this for every
        # request when present (mock 1B design §3.6).
        if telemetry_state is not None:
            self.telemetry_capture = telemetry_state.capture_model_request


def _is_update_route(target: str) -> bool:
    return urlsplit(target).path.startswith(UPDATE_ROUTE_PREFIXES)


def _is_telemetry_route(target: str) -> bool:
    return urlsplit(target).path.startswith(TELEMETRY_ROUTE_PREFIXES)


def build_single_port_handler(
    *,
    auth_state: MockAuthState | None,
    update_state: MockUpdateState,
    telemetry_state: MockTelemetryState | None = None,
) -> type[BaseHTTPRequestHandler]:
    """Compose the sub-service handler classes into one.

    Same arbitration pattern as the catalog's own embedded-auth combiner
    (``build_combined_handler_class``): every parent is a
    ``BaseHTTPRequestHandler`` subclass, the combined class only says who
    answers a request — update owns ``/api/v2/**``, telemetry owns
    ``/csas/telemetry/**`` (when mounted), the catalog side answers the rest
    (its auth/catalog split is already resolved inside it).
    """
    update_cls = update_server.build_handler_class(update_state)
    if auth_state is not None:
        catalog_cls = catalog_server.build_combined_handler_class(auth_state)
    else:
        catalog_cls = catalog_server.build_handler_class()
    telemetry_cls = telemetry_server.build_handler_class(telemetry_state) if telemetry_state is not None else None
    parents: tuple[type[BaseHTTPRequestHandler], ...] = (
        (update_cls, telemetry_cls, catalog_cls) if telemetry_cls is not None else (update_cls, catalog_cls)
    )

    class SinglePortHandler(*parents):  # type: ignore[misc]
        server_version = "ChrysMockCombo/1.0"

        def _telemetry_handler(self) -> type[BaseHTTPRequestHandler] | None:
            return telemetry_cls if telemetry_cls is not None and _is_telemetry_route(self.path) else None

        def do_GET(self) -> None:  # type: ignore[override]
            telemetry = self._telemetry_handler()
            if _is_update_route(self.path):
                update_cls.do_GET(self)
            elif telemetry is not None:
                telemetry.do_GET(self)
            else:
                catalog_cls.do_GET(self)

        def do_POST(self) -> None:  # type: ignore[override]
            telemetry = self._telemetry_handler()
            if _is_update_route(self.path):
                update_cls.do_POST(self)
            elif telemetry is not None:
                telemetry.do_POST(self)
            else:
                catalog_cls.do_POST(self)

        def _send_json(self, *args: Any) -> None:
            """update and catalog(+auth) spell this with different signatures."""
            if _is_update_route(self.path):
                update_cls._send_json(self, *args)
            else:
                catalog_cls._send_json(self, *args)

        def log_message(self, format: str, *args: object) -> None:
            telemetry = self._telemetry_handler()
            if _is_update_route(self.path):
                update_cls.log_message(self, format, *args)
            elif telemetry is not None:
                telemetry.log_message(self, format, *args)
            else:
                catalog_cls.log_message(self, format, *args)

    return SinglePortHandler


def create_combined_server(
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_COMBINED_PORT,
    quiet: bool = False,
    with_auth: bool = True,
    auth_mode: str = "auto",
    with_telemetry: bool = True,
) -> CombinedMockServer:
    """Build a stopped combined server ready for ``serve_forever()``."""
    auth_config = MockAuthConfig(mode=auth_mode) if with_auth else None
    auth_state = MockAuthState(auth_config) if auth_config is not None else None
    update_state = MockUpdateState(MockUpdateConfig())
    telemetry_state = MockTelemetryState() if with_telemetry else None
    handler = build_single_port_handler(
        auth_state=auth_state, update_state=update_state, telemetry_state=telemetry_state
    )
    server = CombinedMockServer(
        (host, port),
        handler,
        catalog_state=CatalogMockState(),
        catalog_source=CatalogSource(),
        quiet=quiet,
        auth_state=auth_state,
        update_state=update_state,
        telemetry_state=telemetry_state,
    )
    server.auth_config = auth_config  # type: ignore[attr-defined]
    return server


def start_combined(
    *,
    host: str = DEFAULT_HOST,
    port: int = 0,
    quiet: bool = False,
    with_auth: bool = True,
    with_telemetry: bool = True,
) -> tuple[str, CombinedMockServer, threading.Thread]:
    """Start the combined mock; returns (origin, server, thread) once bound."""
    server = create_combined_server(
        host=host, port=port, quiet=quiet, with_auth=with_auth, with_telemetry=with_telemetry
    )
    thread = threading.Thread(target=server.serve_forever, name="chrys-mock-combo", daemon=True)
    thread.start()
    displayed = f"[{host}]" if ":" in host else host
    origin = f"http://{displayed}:{server.server_address[1]}"
    auth_config = getattr(server, "auth_config", None)
    if auth_config is not None:
        # Same late-binding rule as the catalog's own start(): a --port 0
        # instance still hands the verify page a URL pointing back at itself.
        auth_config.base_url = origin
    return origin, server, thread
