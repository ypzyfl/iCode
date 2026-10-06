# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""AIxCoding session-telemetry hook installer (fork-local, unified hook path).

Design: agent_studio_new ``docs/adr/0041`` and the unified-hook proposal
(rev.4d) §5. Both TUI and ACP sessions collect through the SAME engine hook
mechanism; this module is the single writer that keeps the two collector hook
entries present in the CURRENT process's config dir:

- TUI/CLI process → user-global config dir;
- ACP engine process → account-private HOME (the desktop injects
  ``HOME``/``APPDATA``), so the same code path covers both scenes with zero
  mode awareness (only the ``--scope`` argv differs).

Called once per session start (``SessionHookFactory.__call__``, upstream
modification M-001) BEFORE ``load_hooks_dir`` so written entries take effect
for the very session being started. Every session start re-aligns, which also
makes the entries self-heal after user edits (acceptance scenario 10).

The four duties per call (bounded: a few small-file reads and at most three
atomic writes; never raises — any failure degrades to a WARNING):

1. refresh attribution (``<config_dir>/telemetry/attribution.json``) from the
   desktop-injected identity env (ACP scene) — the engine login state (TUI
   scene) is not wired yet (D4a), so the TUI attribution stays absent and the
   collector degrades to ``account_id: "unknown"``;
2. refresh ``report-config.json`` auth/endpoint from the same env;
3. verify the collector Python module is importable (fail-closed: no
   install when missing); the hook argv runs it via
   ``pythonw-or-sys.executable -s -m chrys.aixcoding.telemetry.collector``
   — the module ships inside the wheel (no vendored binary, no manifest);
4. align the two ``aixcoding-collector-*`` hook entries in
   ``<config_dir>/hooks/hooks.{yaml,yml,json}`` idempotently (zero write when
   unchanged; user entries are never touched).
"""

from __future__ import annotations

import contextlib
import importlib.util
import json
import logging
import os
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_ACCOUNT_ID_ENV = "AIXCOLLECT_ACCOUNT_ID"
_TELEMETRY_TOKEN_ENV = "AIXCOLLECT_TELEMETRY_TOKEN"
_TELEMETRY_URL_ENV = "AIXCOLLECT_TELEMETRY_URL"

_SESSION_ID_ENV_KEY = "AIXCOLLECT_SESSION_ID"
_OWNED_ID_PREFIX = "aixcoding-collector-"
_TURN_HOOK_ID = "aixcoding-collector-turn"
_SESSION_END_HOOK_ID = "aixcoding-collector-session-end"
_ENTRY_VERSION = "v1"

# Backend contract path (agent_studio_new collector http-sink endpoint suffix).
_TELEMETRY_API_PREFIX = "/csas/telemetry/api/v1"
_REPORT_RETRIES = "2"
_MAX_RUNTIME_MS = 30_000
# Placeholder only — meaningless for detached hooks; the real guard is the
# collector's ``--max-runtime-ms`` forced self-exit.
_HOOK_TIMEOUT_SECONDS = 60


# ---------------------------------------------------------------------------
# Public entry (production)
# ---------------------------------------------------------------------------


def ensure_telemetry_hooks() -> None:
    """Idempotent, bounded, failure-silent hook installation (per session start)."""
    try:
        from chrys.foundation.platform import get_platform

        _install_into(Path(get_platform().config_dir), _identity_env())
    except Exception:
        # Never block a session start: telemetry is secondary to the engine.
        logger.warning("aixcoding telemetry hook installation failed", exc_info=True)


def _identity_env() -> Mapping[str, str]:
    """Read the desktop-injected identity env through the frozen snapshot.

    ``bootstrap_runtime(dotenv_override=True)`` can overwrite ``os.environ``
    from a user-controlled ``config_dir/.env``; the pre-bootstrap snapshot
    (ACP scene: the desktop spawn overlay, unmodified) is the trustworthy
    source. Falls back to the live environment before bootstrap.
    """
    from chrys.foundation.config.env_layers import process_env_snapshot

    snapshot = process_env_snapshot()
    return snapshot.values if snapshot is not None else os.environ


# ---------------------------------------------------------------------------
# Installation core (parameterized for tests)
# ---------------------------------------------------------------------------


def _install_into(config_dir: Path, env: Mapping[str, str]) -> None:
    # Scope by KEY PRESENCE (an empty value still counts — the desktop always
    # injects both keys, logged-out included); a TUI process has neither key.
    # Judging scope by "value non-empty" would misclassify a logged-out ACP
    # engine as TUI and miswrite --scope/--sessions-root.
    is_acp = _ACCOUNT_ID_ENV in env or _TELEMETRY_TOKEN_ENV in env
    scope = "acp" if is_acp else "tui"
    state_dir = _state_dir_for(scope, config_dir)
    sessions_root = _resolve_sessions_root(config_dir)
    attribution_path = config_dir / "telemetry" / "attribution.json"
    report_config_path = state_dir / "config" / "report-config.json"

    _refresh_identity_files(env, attribution_path, report_config_path)

    if not _collector_module_available():
        # Fail-closed: without the collector module the hooks would spawn a
        # failing process on every turn. Attribution/config refresh above
        # stays (harmless; retried next session start).
        logger.warning("aixcoding collector module not importable; hooks not installed")
        return

    _align_hooks(
        config_dir,
        entries=[
            _hook_entry(
                hook_id=_TURN_HOOK_ID,
                event="after_turn",
                sessions_root=sessions_root,
                state_dir=state_dir,
                report_config=report_config_path,
                attribution=attribution_path,
                scope=scope,
                final=False,
            ),
            _hook_entry(
                hook_id=_SESSION_END_HOOK_ID,
                event="session_end",
                sessions_root=sessions_root,
                state_dir=state_dir,
                report_config=report_config_path,
                attribution=attribution_path,
                scope=scope,
                final=True,
            ),
        ],
    )


def _collector_executable() -> str:
    """Prefer the GUI-subsystem interpreter (pythonw.exe) on Windows.

    The collector is spawned by the console-less detached worker, and ANY
    console creation in that context opens a visible Windows-Terminal
    window on machines whose default terminal is WT (STARTUPINFO SW_HIDE
    is ignored there; a venv python.exe launcher also re-creates a
    console one hop later even under DETACHED_PROCESS). pythonw never
    creates a console at either hop while stdio still flows through the
    inherited log-file handles. Falls back to ``sys.executable`` when
    pythonw.exe is unavailable (e.g. frozen runtime aliases).
    """
    if sys.platform == "win32":
        windowless = Path(sys.executable).with_name("pythonw.exe")
        if windowless.is_file():
            return str(windowless)
    return sys.executable


def _state_dir_for(scope: str, config_dir: Path) -> Path:
    if scope == "acp":
        # config_dir is <accountHome>/chrys(s) → account-scoped state beside it
        # (agent_studio_new rev.4d §5.2 ACP column: <accountHome>/collector-state).
        return config_dir.parent / "collector-state"
    # TUI machine-level state directory (decision D5 pending review against
    # the desktop data-root policy; user-global chrys dir is the working
    # default — single constant to switch once D5 lands).
    return config_dir / "collector-state"


def _resolve_sessions_root(config_dir: Path) -> Path:
    """Honor ``CHRYS_SESSION_ROOT_DIR`` exactly like the engine session store."""
    from chrys.foundation.config.settings import resolve_sessions_dir

    return resolve_sessions_dir(config_dir)


# ---------------------------------------------------------------------------
# Duty 1 + 2: attribution / report-config refresh
# ---------------------------------------------------------------------------


def _refresh_identity_files(
    env: Mapping[str, str],
    attribution_path: Path,
    report_config_path: Path,
) -> None:
    account_id = env.get(_ACCOUNT_ID_ENV, "")
    token = env.get(_TELEMETRY_TOKEN_ENV, "")
    url = env.get(_TELEMETRY_URL_ENV, "")

    if account_id:
        _write_json_if_changed(attribution_path, {"version": 1, "account_id": account_id})
    else:
        # ACP logged out, or TUI without the login-state bridge (D4a). Not an
        # error: the collector degrades to account_id "unknown" (P1 — collect
        # with degraded attribution rather than not collect at all).
        logger.warning(
            "%s absent or empty; attribution not refreshed (%s)",
            _ACCOUNT_ID_ENV,
            attribution_path,
        )

    _refresh_report_config(report_config_path, token=token, url=url)


def _refresh_report_config(path: Path, *, token: str, url: str) -> None:
    current: dict[str, Any] = {}
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                current = loaded
        except OSError, ValueError:
            logger.warning("unreadable report config %s; regenerating", path)

    config: dict[str, Any] = dict(current)
    config["version"] = 2
    if url:
        config["sink"] = "http"
        config["endpoint"] = url.rstrip("/") + _TELEMETRY_API_PREFIX
    elif config.get("sink") != "http":
        # Local observability sink: no credentials yet, keep collection
        # visible on disk instead of failing closed (collector schema v2).
        config["sink"] = "file"
        config.pop("endpoint", None)
    if token:
        config["token"] = token
    else:
        config.pop("token", None)

    if config == current:
        return
    _write_json_if_changed(path, config)


# ---------------------------------------------------------------------------
# Duty 3: collector module verification (fail-closed)
# ---------------------------------------------------------------------------


def _collector_module_available() -> bool:
    return importlib.util.find_spec("chrys.aixcoding.telemetry.collector") is not None


# ---------------------------------------------------------------------------
# Duty 4: hooks.yaml alignment
# ---------------------------------------------------------------------------


def _hook_entry(
    *,
    hook_id: str,
    event: str,
    sessions_root: Path,
    state_dir: Path,
    report_config: Path,
    attribution: Path,
    scope: str,
    final: bool,
) -> dict[str, Any]:
    # The collector runs as a module of this interpreter: under PyApp,
    # sys.executable is the runtime alias interpreter (verified) and
    # ``-s`` matches the engine's detached-worker isolation. On Windows
    # pythonw is preferred so the console-less spawn chain never creates
    # a (visible, WT-hosted) console (see _collector_executable).
    argv: list[str] = [
        _collector_executable(),
        "-s",
        "-m",
        "chrys.aixcoding.telemetry.collector",
        "run",
        "--session-from-env",
        _SESSION_ID_ENV_KEY,
        "--sessions-root",
        str(sessions_root),
        "--state-dir",
        str(state_dir),
        "--report-config",
        str(report_config),
        "--attribution",
        str(attribution),
        "--scope",
        scope,
        "--report-retries",
        _REPORT_RETRIES,
        "--max-runtime-ms",
        str(_MAX_RUNTIME_MS),
    ]
    if final:
        argv.append("--final")
    return {
        "id": hook_id,
        # Version fingerprint: bump to force re-alignment over stale entries.
        "description": f"AIxCoding session telemetry collector ({event}) {_ENTRY_VERSION}",
        "event": event,
        "run": {
            "type": "command",
            "argv": argv,
            # ${session_id} is expanded by the hook runner (env templates only).
            "env": {_SESSION_ID_ENV_KEY: "${session_id}"},
        },
        "execution": {
            "mode": "fire_and_forget",
            "detach": True,
            "delivery": "durable",
            "timeout_seconds": _HOOK_TIMEOUT_SECONDS,
            "on_error": "ignore",
        },
    }


def _align_hooks(config_dir: Path, *, entries: list[dict[str, Any]]) -> None:
    hooks_dir = config_dir / "hooks"
    candidates: list[tuple[str, str]] = [
        ("hooks.yaml", "yaml"),
        ("hooks.yml", "yaml"),
        ("hooks.json", "json"),
    ]
    name, fmt = "hooks.yaml", "yaml"
    for candidate_name, candidate_fmt in candidates:
        if (hooks_dir / candidate_name).is_file():
            name, fmt = candidate_name, candidate_fmt
            break
    path = hooks_dir / name

    existing: dict[str, Any] = {}
    if path.is_file():
        try:
            text = path.read_text(encoding="utf-8")
            raw = json.loads(text) if fmt == "json" else (yaml.safe_load(text) or {})
        except OSError, ValueError, yaml.YAMLError:
            # The user's file is unparsable: leave it untouched (the engine
            # already disables global hooks on such files) rather than risk
            # appending into a broken document.
            logger.warning("hooks config %s is unparsable; collector hooks not aligned", path)
            return
        if not isinstance(raw, dict):
            logger.warning("hooks config %s has an unexpected root; collector hooks not aligned", path)
            return
        existing = raw

    hooks = existing.get("hooks", [])
    if not isinstance(hooks, list) or not all(isinstance(h, dict) for h in hooks):
        logger.warning("hooks config %s has a malformed 'hooks' list; collector hooks not aligned", path)
        return

    kept = [h for h in hooks if not str(h.get("id", "")).startswith(_OWNED_ID_PREFIX)]
    new_hooks = [*kept, *entries]
    if new_hooks == hooks and "version" in existing:
        return  # Zero-write idempotency: re-aligned content equals on-disk content.

    updated = dict(existing)
    updated["version"] = existing.get("version", 1)
    updated["hooks"] = new_hooks
    try:
        _write_atomic(path, updated, fmt)
    except OSError:
        logger.warning("failed to write hooks config %s; collector hooks not aligned", path, exc_info=True)


# ---------------------------------------------------------------------------
# Atomic writes (owner-only where supported; mirrors the outbox writer)
# ---------------------------------------------------------------------------


def _write_json_if_changed(path: Path, data: dict[str, Any]) -> None:
    if path.is_file():
        try:
            if json.loads(path.read_text(encoding="utf-8")) == data:
                return
        except OSError, ValueError:
            pass  # Regenerate on unreadable/stale content.
    try:
        _write_atomic(path, data, "json")
    except OSError:
        logger.warning("failed to write %s", path, exc_info=True)


def _write_atomic(path: Path, data: dict[str, Any], fmt: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_tmp = tempfile.mkstemp(prefix=f"{path.name}.", suffix=".tmp", dir=path.parent)
    tmp = Path(raw_tmp)
    try:
        with contextlib.suppress(AttributeError, OSError):
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            if fmt == "json":
                json.dump(data, handle, indent=2)
                handle.write("\n")
            else:
                yaml.safe_dump(data, handle, default_flow_style=False, sort_keys=False, allow_unicode=True)
        os.replace(tmp, path)
        with contextlib.suppress(OSError):
            os.chmod(path, 0o600)
    except BaseException:
        with contextlib.suppress(OSError):
            os.close(fd)
        with contextlib.suppress(OSError):
            tmp.unlink(missing_ok=True)
        raise
