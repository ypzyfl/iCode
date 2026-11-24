# ruff: noqa: T201
# (CLI launcher — print is the intended user-facing output channel)
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""One-command launcher for the local mock backends (dev tool, never shipped).

``python -m aixcoding.mock`` starts the single-port combo (mock design
2026-11-20 decision): one server on :15678 serving every migrated sub-service
— the model catalog with the device-code auth mock mounted on the same origin
(login + catalog + LLM chat), and the update release-check under ``/api/v2/``.
Point ``AIXCODING_ENVIRONMENT=local`` (and the update/catalog base defaults
with the telemetry-after-turn-slice batch) at :15678 and you are done.

The old multi-port combo is retired: one port, one command. Each sub-package
keeps its independent ``create_server``/CLI for low-level tests and debugging
(DIRECTORY §6). Ports fail fast on purpose — a taken port names the service
and the CLI exits rather than silently moving and leaving the client talking
to nothing. ``--port 0`` picks an OS-assigned ephemeral port (used by tests;
the server factories natively support it). ``--only auth`` still starts the
standalone login mock on its own port (it shares :7777's route space with the
catalog's embedded auth, hence the mutual exclusion). Ctrl+C stops everything
that was started.
"""

from __future__ import annotations

import argparse
import logging
import sys
import threading
from collections.abc import Callable

from aixcoding.mock.auth.server import DEFAULT_PORT as AUTH_PORT
from aixcoding.mock.auth.server import MockAuthConfig
from aixcoding.mock.auth.server import create_server as create_auth_server
from aixcoding.mock.combined import DEFAULT_COMBINED_PORT, start_combined

_LOGGER = logging.getLogger("chrys.mock_launcher")

#: Sub-services that share the single combo port (``--only`` subset members).
_COMBO_MEMBERS = ("model_catalog", "update", "telemetry")
#: ``--list`` rows: name, where it answers, one-line description.
_REGISTRY: tuple[tuple[str, str, str], ...] = (
    ("model_catalog", f":{DEFAULT_COMBINED_PORT} (combo)", "catalog dispatch + embedded auth + LLM chat /v1"),
    ("update", f":{DEFAULT_COMBINED_PORT} (combo, /api/v2/)", "release-check /api/v2/releases/check"),
    (
        "telemetry",
        f":{DEFAULT_COMBINED_PORT} (combo, /csas/telemetry/)",
        "llm/tool/ai-code save + _test/join + model capture",
    ),
    ("auth", f":{AUTH_PORT} (standalone)", "standalone device-code login mock"),
)


def _resolve_selection(only: str) -> list[str] | None:
    """Return combo members to mount; None on unknown names or auth/catalog clash."""
    if not only:
        return list(_COMBO_MEMBERS)
    names = [name.strip() for name in only.split(",") if name.strip()]
    known = {name for name, _port, _description in _REGISTRY}
    unknown = [name for name in names if name not in known]
    if unknown:
        _LOGGER.error("unknown mock(s): %s (known: %s)", ", ".join(unknown), ", ".join(sorted(known)))
        return None
    if "auth" in names and "model_catalog" in names:
        _LOGGER.error(
            "auth and model_catalog share the auth route space — pick one (model_catalog embeds the auth routes)"
        )
        return None
    return names


def _print_registry() -> None:
    print(f"single-port combo (default): model_catalog(+auth) + update on :{DEFAULT_COMBINED_PORT}")
    print("sub-services:")
    for name, where, description in _REGISTRY:
        print(f"  {name:<14} {where:<28} {description}")
    print("--only takes a comma-separated subset; --port overrides the combo port")


def _start_combo(port: int) -> tuple[str, Callable[[], None]]:
    origin, server, _thread = start_combined(port=port, with_auth=True)

    def stop() -> None:
        server.shutdown()
        server.server_close()

    return origin, stop


def _start_auth(port: int = AUTH_PORT) -> tuple[str, Callable[[], None]]:
    server = create_auth_server(MockAuthConfig(mode="manual"), port=port)
    threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.2}, name="chrys-mock-auth", daemon=True
    ).start()
    origin = f"http://127.0.0.1:{server.server_address[1]}"

    def stop() -> None:
        server.shutdown()
        server.server_close()

    return origin, stop


def main(argv: list[str] | None = None) -> int:
    """Start the selected mocks and block until interrupted. Returns an exit code."""
    parser = argparse.ArgumentParser(
        prog="python -m aixcoding.mock",
        description="Start the local AIxCoding mock backends (single-port combo by default).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_COMBINED_PORT,
        help=f"combo bind port (default {DEFAULT_COMBINED_PORT}); 0 picks a free port",
    )
    parser.add_argument("--only", metavar="NAMES", help="comma-separated subset of: model_catalog, update, auth")
    parser.add_argument("--list", action="store_true", help="list sub-services, ports and routes, then exit")
    args = parser.parse_args(argv)

    if args.list:
        _print_registry()
        return 0

    names = _resolve_selection(args.only or "")
    if names is None:
        return 2

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

    combo_members = [name for name in names if name in _COMBO_MEMBERS]
    stopped: list[tuple[str, Callable[[], None]]] = []
    if combo_members:
        try:
            origin, stop = _start_combo(args.port)
        except OSError as exc:
            _LOGGER.error("cannot start combo on 127.0.0.1:%s: %s", args.port, exc)
            _LOGGER.error(
                'port taken? find the holder: netstat -ano | findstr :%s  (then tasklist /fi "PID eq <pid>")', args.port
            )
            return 1
        stopped.append((f"combo({'+'.join(combo_members)})", stop))
        _LOGGER.info("%s on %s", "+".join(combo_members), origin)
    if "auth" in names:
        try:
            origin, stop = _start_auth()
        except OSError as exc:
            _LOGGER.error("cannot start auth on 127.0.0.1:%s: %s", AUTH_PORT, exc)
            _LOGGER.error(
                'port taken? find the holder: netstat -ano | findstr :%s  (then tasklist /fi "PID eq <pid>")', AUTH_PORT
            )
            for entry, entry_stop in stopped:
                entry_stop()
                _LOGGER.info("stopped %s (rolled back)", entry)
            return 1
        stopped.append(("auth", stop))
        _LOGGER.info("auth on %s", origin)

    print()
    print("Point the client at the mocks, e.g.:")
    print(f"  AIXCODING_ENVIRONMENT=local + local base defaults → http://127.0.0.1:{DEFAULT_COMBINED_PORT}")
    print("Ctrl+C stops everything.")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        _LOGGER.info("shutting down")
    finally:
        for _name, stop in stopped:
            stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
