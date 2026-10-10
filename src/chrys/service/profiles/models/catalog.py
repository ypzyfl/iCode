# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Server-owned model catalog.

``~/.chrys/models/`` has exactly one owner at a time, and there is no merge
between two sources:

* **A catalog source is configured** (``CHRYS_MODEL_CATALOG_URL``, or a host
  pushing a catalog over ACP).  Every successful sync *replaces the directory
  wholesale* — files the catalog no longer contains are deleted — and the
  directory stops being user-editable.  A failed sync changes nothing.
* **No catalog source is configured.**  The directory is the user's own, as it
  has always been: editable, never touched by this module.

"Synced once" is sticky: the state file marks the directory as server-owned, so
a later failed fetch (offline start) degrades to the previous catalog instead of
silently handing write access back to the user, which the next sync would undo.

Catalog profiles carry no credentials by default: the host injects provider
environment variables, matching the desktop host's model-projection behaviour.
``api_key`` is honoured when the catalog does send one, and profile files are
then written 0o600.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx

from chrys.foundation.text.yaml_io import dump_yaml
from chrys.service.profiles.models.schema import (
    API_STYLE_CHAT_COMPLETIONS,
    VALID_API_STYLES,
    VALID_PROVIDERS,
    ModelProfile,
)

logger = logging.getLogger(__name__)

CATALOG_URL_ENV = "CHRYS_MODEL_CATALOG_URL"
#: Pre-catalog name, still honoured so an existing deployment keeps working.
LEGACY_CATALOG_URL_ENV = "CHRYS_REMOTE_MODEL_CONFIG_URL"
CATALOG_TOKEN_ENV = "CHRYS_MODEL_CATALOG_TOKEN"
#: Overrides :data:`SYNC_INTERVAL_SECONDS` for one process, in seconds — how a
#: server-side change is watched without waiting the default quarter of an hour.
SYNC_INTERVAL_ENV = "CHRYS_MODEL_CATALOG_SYNC_INTERVAL"

#: Appended to a base URL the way the reference client builds the endpoint, so
#: a deployment configures only the host part.
CATALOG_PATH = "/llm/api/v1/continue-config/dispatch"

#: The base comes from configuration first: ``model.catalog.base_url`` in
#: ``~/.chrys/settings.yaml``, or ``CHRYS_MODEL_CATALOG_BASE_URL`` — both
#: declared on the setting in :mod:`chrys.foundation.config.settings`, which is
#: the one place the name lives. With none configured, the tier named by
#: ``CHRYS_AUTH_ENVIRONMENT=local`` falls back to the loopback mock server;
#: every other tier stays unconfigured — no sync — until a base is set.
#:
#: The tier is read from auth's own variable, not a catalog-specific one: the
#: catalog, the login flow and the user-data service are one deployment, and
#: two variables for one deployment is how a session ends up logged into DEV
#: while pulling its model list from PROD. The accepted values are auth's
#: (``aixcoding.auth.types.Environment``), and so is the PROD fallback — see
#: ``tests/service/profiles/models/test_catalog_sync.py``, which fails if the
#: two ever drift apart.
ENVIRONMENT_ENV = "CHRYS_AUTH_ENVIRONMENT"

#: Catalog base per deployment tier, keyed by the very values auth defines
#: (``aixcoding.auth.types.Environment``) — see the drift test in
#: ``tests/service/profiles/models/test_catalog_sync.py``. DEV and PROD are
#: auth's own hosts (``aixcoding.auth.environments._BASE_PATHS``): one
#: deployment, one pair of tiers, under the ``/csas`` prefix the reference
#: client's ``WebConfigs.URL_MAP`` serves the web API from, since
#: :data:`CATALOG_PATH` carries the rest (``/llm/api/v1/...``) and the two must
#: not both add ``/api/v1``. LOCAL is the loopback mock, which serves the
#: catalog straight off the origin — no prefix — on the same port auth uses for
#: the tier, written as an address because ``localhost`` may resolve to a
#: address the mock is not listening on. An unset or unknown tier resolves to
#: PROD the way ``resolve_environment`` does — an unrecognised value must not
#: silently leave the user with no catalog at all.
_CATALOG_BASES: dict[str, str] = {
    "local": "http://127.0.0.1:7777",
    "dev": "http://81.89.182.150/csas",
    "prod": "http://82.187.34.98/csas",
}
DEFAULT_ENVIRONMENT = "prod"

#: Written inside the profiles directory.  The leading dot keeps it out of the
#: ``*.yaml`` / ``*.yml`` scans that build the registry.
STATE_FILENAME = ".catalog-state.json"

SOURCE_REMOTE = "remote"
SOURCE_HOST = "host"

MAX_PROFILES = 128
#: Same shape as the desktop host's profile-id rule, so ids agree across sides.
SAFE_PROFILE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

#: How often the catalog is re-fetched while a session runs. The reference
#: client polls the same endpoint on a clock
#: (`core/aixcoding/config/ConfigSyncService.ts`: immediate sync at startup,
#: then ``setInterval`` every 15 minutes), so that is the default: a
#: server-side model change reaches a long-lived session without a restart,
#: and a quarter of an hour keeps the traffic negligible.
#:
#: ``CHRYS_MODEL_CATALOG_SYNC_INTERVAL`` overrides it for one process — see
#: :func:`sync_interval_seconds`, which is what actually reads the environment.
#: The constant is the default, not the interval: binding it as a parameter
#: default would freeze the value at import, too early to see the variable.
SYNC_INTERVAL_SECONDS = 15 * 60

_DEFAULT_FETCH_TIMEOUT = 3.0


class ModelCatalogError(Exception):
    """Raised when a catalog cannot be fetched, parsed or applied."""


class ModelCatalogReadOnly(ModelCatalogError):
    """Raised when a user edit is attempted on a server-owned catalog."""


@dataclass(frozen=True)
class ModelCatalog:
    """One complete, authoritative set of model profiles."""

    items: tuple[ModelProfile, ...]
    version: str = ""
    default_profile_id: str = ""

    def profile_ids(self) -> tuple[str, ...]:
        return tuple(profile.id for profile in self.items)


@dataclass(frozen=True)
class CatalogState:
    """What the last successful sync wrote, persisted next to the profiles."""

    version: str
    source: str
    profile_ids: tuple[str, ...]
    default_profile_id: str = ""


@dataclass(frozen=True)
class CatalogSyncResult:
    """Outcome of one sync attempt."""

    replaced: bool
    version: str
    profile_ids: tuple[str, ...]
    default_profile_id: str = ""
    previous_profile_ids: tuple[str, ...] = ()

    @property
    def removed_profile_ids(self) -> tuple[str, ...]:
        return tuple(pid for pid in self.previous_profile_ids if pid not in self.profile_ids)


def catalog_directory() -> Path:
    """Return the directory a catalog replaces: ``~/.chrys/models``."""
    from chrys.foundation.platform import get_platform

    return get_platform().config_dir / "models"


def catalog_state_path() -> Path:
    return catalog_directory() / STATE_FILENAME


def catalog_base_url() -> str:
    """Return the catalog base for the current environment, or "" when there is none.

    A configured base wins: ``model.catalog.base_url`` in
    ``~/.chrys/settings.yaml`` or ``CHRYS_MODEL_CATALOG_BASE_URL``. With none
    configured the base comes from the deployment tier
    (:data:`_CATALOG_BASES`), so ``local`` reaches the loopback mock while
    ``dev`` and ``prod`` reach their own host.
    """
    from chrys.foundation.config.process_settings import process_settings

    configured = process_settings().model_catalog_base_url.strip()
    if configured:
        return configured
    tier = os.environ.get(ENVIRONMENT_ENV, "").strip().lower()
    return _CATALOG_BASES.get(tier, _CATALOG_BASES[DEFAULT_ENVIRONMENT])


def catalog_url() -> str:
    """Return the full catalog endpoint, or "" when no source is configured.

    An explicitly configured URL still wins — that is how an existing
    deployment points somewhere specific. Otherwise the base comes from
    :func:`catalog_base_url` and :data:`CATALOG_PATH` is appended to it, which
    is how the reference client builds the endpoint from a base.
    """
    for name in (CATALOG_URL_ENV, LEGACY_CATALOG_URL_ENV):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    base = catalog_base_url()
    return f"{base.rstrip('/')}{CATALOG_PATH}" if base else ""


def read_catalog_state() -> CatalogState | None:
    """Return the persisted state of the last successful sync, if any."""
    path = catalog_state_path()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError, ValueError:
        return None
    if not isinstance(raw, dict):
        return None
    ids = raw.get("profile_ids")
    return CatalogState(
        version=str(raw.get("version", "")),
        source=str(raw.get("source", SOURCE_REMOTE)),
        profile_ids=tuple(str(item) for item in ids) if isinstance(ids, list) else (),
        default_profile_id=str(raw.get("default_profile_id", "")),
    )


def write_catalog_state(state: CatalogState) -> None:
    """Persist *state* next to the profiles it describes."""
    path = catalog_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": state.version,
        "source": state.source,
        "profile_ids": list(state.profile_ids),
        "default_profile_id": state.default_profile_id,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def is_catalog_managed() -> bool:
    """Return whether ``~/.chrys/models`` is owned by a catalog.

    True once a source is configured or a catalog has ever been applied, which
    is what makes the directory read-only.
    """
    return bool(catalog_url()) or read_catalog_state() is not None


def require_catalog_writable() -> None:
    """Reject user edits while a catalog owns the directory."""
    if is_catalog_managed():
        raise ModelCatalogReadOnly("Model profiles are managed by the server catalog and cannot be edited locally.")


def _profile_field_names() -> set[str]:
    return {field.name for field in fields(ModelProfile)}


def _coerce_version(catalog: ModelCatalog) -> str:
    """Fingerprint the whole item set so a version-less payload still has one.

    Every serialized field is hashed, not just the ids: the catalog owns the
    directory wholesale, so a change to *any* field — display name, base url,
    context length — is a change the files have to be rewritten for. Hashing
    the ids alone would call such a payload "unchanged" and leave the previous
    values on disk.

    What is hashed is exactly what :func:`_write_profile` puts in each YAML, so
    the fingerprint changes if and only if the directory's content would.

    Order participates: ``items`` is a tuple hashed in its own order, so
    reordering otherwise identical models counts as a change (the rewrite that
    follows is a no-op in content, not a wrong result).
    """
    payload = json.dumps(
        [_profile_to_dict(profile) for profile in catalog.items],
        separators=(",", ":"),
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ── Server payload translation ───────────────────────────────────────────
# The server speaks its own client's shape: a ``models`` array of ``title`` /
# ``model`` / ``apiBase`` / ``contextLength``, with no id and no wire fields
# (docs/model-catalog-sync-details.md §1.1). It is not ours to change, so the
# translation lives here: what the payload cannot carry is filled in from the
# one assumption that makes it derivable — every served model is reached
# through OpenRouter.

CONTINUE_PROVIDER = "openai"
CONTINUE_API_STYLE = API_STYLE_CHAT_COMPLETIONS
CONTINUE_BASE_URL = "https://openrouter.ai/api/v1"


def derive_profile_id(model: str) -> str:
    """Slug one served model name into a usable profile id (§1.1).

    Pure by construction: the same ``model`` must always yield the same id, or
    the user's selection and every agent binding would break on each sync.
    """
    slug = re.sub(r"[^a-z0-9._-]+", "-", model.strip().lower())
    return slug.strip("-")


def _unique_profile_id(base: str, taken: set[str]) -> str:
    """Disambiguate two served models that slug to the same id."""
    if base not in taken:
        return base
    suffix = 2
    while f"{base}-{suffix}" in taken:
        suffix += 1
    return f"{base}-{suffix}"


def _positive_int(value: object) -> int:
    """One payload number, or 0 when it is absent or not a positive integer."""
    if not isinstance(value, int | float | str):
        return 0
    try:
        number = int(value)
    except ValueError:
        return 0
    return max(0, number)


def translate_models_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Translate the server's ``models`` payload into iCode-native items.

    Returns the shape :func:`parse_catalog` already accepts, so validation
    stays the single gate — translation adds no second path to it.
    """
    entries = payload.get("models")
    if not isinstance(entries, list):
        raise ModelCatalogError(f"Server catalog 'models' must be a list, got {type(entries).__name__!r}")

    items: list[dict[str, Any]] = []
    taken: set[str] = set()
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise ModelCatalogError(f"Catalog item {index} must be a JSON object, got {type(entry).__name__!r}")
        model = str(entry.get("model") or "").strip()
        if not model:
            raise ModelCatalogError(f"Catalog item {index} has no 'model' to derive a profile id from")
        profile_id = _unique_profile_id(derive_profile_id(model), taken)
        taken.add(profile_id)
        item: dict[str, Any] = {
            "id": profile_id,
            # The real payload's title carries leading whitespace.
            "name": str(entry.get("title") or model).strip(),
            "provider": CONTINUE_PROVIDER,
            "api_style": CONTINUE_API_STYLE,
            "model_id": model,
            # ``apiBase`` is optional and often simply absent; the served
            # models are reached through OpenRouter either way.
            "base_url": str(entry.get("apiBase") or "").strip() or CONTINUE_BASE_URL,
            # No ``api_key`` on purpose: the catalog is not a credential
            # channel, and a key in the profile file would be one more place
            # for it to leak. The key is resolved at send time from the host's
            # environment instead (service/llm/clients.py).
        }
        context_length = _positive_int(entry.get("contextLength"))
        if context_length:
            item["max_context_tokens"] = context_length
        items.append(item)

    # The server's shape carries no version and no default: the caller
    # fingerprints the id list, and a cold start takes the first entry.
    return {"items": items, "version": "", "default_profile_id": items[0]["id"] if items else ""}


def parse_catalog(payload: object) -> ModelCatalog:
    """Validate one catalog payload and build a :class:`ModelCatalog`.

    Accepts a bare JSON array of profiles, an object with ``items``, or the
    server's own ``models`` shape, which is translated first. Unknown keys are
    dropped so the payload can evolve without breaking older clients.
    """
    items_raw: object
    version = ""
    default_profile_id = ""

    if isinstance(payload, dict):
        if "models" in payload and "items" not in payload:
            payload = translate_models_payload(payload)
        items_raw = payload.get("items")
        version = str(payload.get("version", "") or "")
        default_profile_id = str(payload.get("default_profile_id", "") or "")
    else:
        items_raw = payload

    if not isinstance(items_raw, list):
        raise ModelCatalogError(
            f"Model catalog must be a list or an object with 'items', got {type(items_raw).__name__!r}"
        )
    if not items_raw:
        raise ModelCatalogError("Model catalog is empty; refusing to replace the model list with nothing.")
    if len(items_raw) > MAX_PROFILES:
        raise ModelCatalogError(f"Model catalog exceeds the {MAX_PROFILES} profile limit.")

    allowed = _profile_field_names()
    profiles: list[ModelProfile] = []
    seen: set[str] = set()
    for index, item in enumerate(items_raw, start=1):
        if not isinstance(item, dict):
            raise ModelCatalogError(f"Catalog item {index} must be a JSON object, got {type(item).__name__!r}")
        filtered = {key: value for key, value in item.items() if key in allowed}
        try:
            profile = ModelProfile(**filtered)  # type: ignore[arg-type]
        except (TypeError, ValueError) as exc:
            raise ModelCatalogError(f"Catalog item {index} is invalid: {exc}") from exc
        if not SAFE_PROFILE_ID.match(profile.id):
            raise ModelCatalogError(f"Catalog item {index} has an unusable profile id: {profile.id!r}")
        if profile.provider not in VALID_PROVIDERS:
            raise ModelCatalogError(f"Catalog item {index} has an unsupported provider: {profile.provider!r}")
        if profile.api_style not in VALID_API_STYLES:
            raise ModelCatalogError(f"Catalog item {index} has an unsupported api_style: {profile.api_style!r}")
        if profile.id in seen:
            raise ModelCatalogError(f"Catalog item {index} repeats profile id {profile.id!r}")
        seen.add(profile.id)
        profiles.append(profile)

    catalog = ModelCatalog(items=tuple(profiles), version=version, default_profile_id=default_profile_id)
    if not catalog.version:
        catalog = ModelCatalog(
            items=catalog.items,
            version=_coerce_version(catalog),
            default_profile_id=catalog.default_profile_id,
        )
    return catalog


def _catalog_token() -> str:
    """The credential to send with a catalog request, or "" when there is none.

    The catalog is an authenticated endpoint: the token the login flow stored
    is the one it expects. The environment still wins, so a deployment that
    issues its own credential (or a test) is not forced through a login.

    Reading it performs no network I/O — a stale token is the server's to
    reject, not ours to refresh here — but a session that cannot be read at
    all yields "", which the caller turns into a cancelled sync rather than an
    unauthenticated request answered with a 401.
    """
    env_token = os.environ.get(CATALOG_TOKEN_ENV, "").strip()
    if env_token:
        return env_token
    try:
        from aixcoding.auth import get_login_session

        stored = get_login_session().stored_token
    except Exception:
        logger.warning("Could not read the login session for the model catalog request.", exc_info=True)
        return ""
    return (stored or "").strip()


def has_catalog_credential() -> bool:
    """Whether a catalog request could be authenticated right now.

    The poll is only worth a thread once this is true: without a credential
    every attempt is refused before a request is made, so an unauthenticated
    session would spin one for nothing. The caller starts the poll when this
    flips — on login — rather than when the process starts.
    """
    return bool(_catalog_token())


def _catalog_user_id() -> str:
    """The logged-in user for the ``userId`` parameter, or "" when unknown.

    The remote catalog is served per user and answers an empty id with the
    public default (``ConfigSyncService.fetchRemoteModelConfig``), so unlike
    the credential an absent id does not cancel the sync — it asks for the
    default list instead.
    """
    try:
        from aixcoding.auth import get_login_session

        stored = get_login_session().stored_user_id
    except Exception:
        logger.warning("Could not read the login session user for the model catalog request.", exc_info=True)
        return ""
    return (stored or "").strip()


#: Query parameters the reference client hard-codes on every catalog request
#: (``ConfigSyncService.fetchRemoteModelConfig``): the dispatch endpoint
#: answers one global config scope, as JSON. ``userId`` is not among them —
#: it is appended per login by :func:`_catalog_endpoint`.
_CATALOG_FIXED_QUERY: tuple[tuple[str, str], ...] = (
    ("scopeType", "global"),
    ("scopeValue", "config"),
    ("format", "json"),
)


def _catalog_endpoint(endpoint: str, user_id: str) -> str:
    """Return *endpoint* carrying the fixed scope/format parameters and ``userId=``.

    The reference client concatenates ``&userId=`` onto a URL that already
    ends in a query; parsing instead keeps this right for a bare endpoint too,
    which is what a configured base produces. The scope/format parameters are
    part of the wire contract, so they are always sent — replacing any a
    configured URL happened to carry — while an existing ``userId`` is replaced
    rather than duplicated.
    """
    parts = urlsplit(endpoint)
    fixed = {name for name, _value in _CATALOG_FIXED_QUERY}
    query = [
        (name, value)
        for name, value in parse_qsl(parts.query, keep_blank_values=True)
        if name != "userId" and name not in fixed
    ]
    query.extend(_CATALOG_FIXED_QUERY)
    query.append(("userId", user_id))
    return urlunsplit(parts._replace(query=urlencode(query)))


async def fetch_catalog(url: str | None = None, *, timeout: float = _DEFAULT_FETCH_TIMEOUT) -> ModelCatalog:
    """Fetch and validate a catalog.

    Args:
        url: Endpoint.  Defaults to :func:`catalog_url`.
        timeout: HTTP timeout in seconds; deliberately short on the startup path.

    Raises:
        ModelCatalogError: when no source is configured, when no credential is
            available (there is no unauthenticated catalog request), or on
            transport, HTTP, decoding or validation failures.
    """
    endpoint = (url or catalog_url()).strip()
    if not endpoint:
        raise ModelCatalogError("No model catalog source is configured.")

    token = _catalog_token()
    if not token:
        raise ModelCatalogError(
            f"No model catalog credential: log in, or set {CATALOG_TOKEN_ENV}. "
            "The sync is skipped and the previous model list is kept."
        )

    headers: dict[str, str] = {"Accept": "application/json", "token": token}
    endpoint = _catalog_endpoint(endpoint, _catalog_user_id())

    started = time.monotonic()
    logger.info("Model catalog request: GET %s (timeout %.0fs).", endpoint, timeout)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(endpoint, headers=headers)
            response.raise_for_status()
            payload: Any = response.json()
    except httpx.HTTPStatusError as exc:
        logger.warning("Model catalog request rejected by %s: HTTP %d.", endpoint, exc.response.status_code)
        raise ModelCatalogError(f"Model catalog request failed: {exc}") from exc
    except httpx.HTTPError as exc:
        logger.warning("Model catalog request to %s failed before a response: %s", endpoint, exc)
        raise ModelCatalogError(f"Model catalog request failed: {exc}") from exc
    except ValueError as exc:
        logger.warning("Model catalog response from %s is not valid JSON: %s", endpoint, exc)
        raise ModelCatalogError(f"Model catalog response is not valid JSON: {exc}") from exc

    catalog = parse_catalog(payload)
    logger.info(
        "Model catalog response: HTTP %d, %d model(s), version %.12s, in %.2fs.",
        response.status_code,
        len(catalog.items),
        catalog.version,
        time.monotonic() - started,
    )
    return catalog


def _clear_directory(directory: Path) -> int:
    """Delete every profile file in *directory*.  Returns the count removed."""
    removed = 0
    for pattern in ("*.yaml", "*.yml"):
        for path in sorted(directory.glob(pattern)):
            path.unlink()
            removed += 1
    return removed


def _write_profile(directory: Path, profile: ModelProfile) -> Path:
    path = directory / f"{profile.id}.yaml"
    path.write_text(dump_yaml(_profile_to_dict(profile)), encoding="utf-8")
    if profile.api_key:
        # Credentials were supplied by the catalog: keep them off group/other.
        path.chmod(0o600)
    return path


def _profile_to_dict(profile: ModelProfile) -> dict[str, Any]:
    from chrys.service.profiles.models.serializer import profile_to_dict

    return profile_to_dict(profile)


def apply_catalog(catalog: ModelCatalog, *, source: str = SOURCE_REMOTE) -> CatalogSyncResult:
    """Replace the whole model directory with *catalog*.

    The catalog is authoritative: every existing profile file is removed first,
    then the catalog's profiles are written.  Nothing is merged and nothing
    outside the catalog survives into the registry.

    Raises:
        ModelCatalogError: if the catalog is unusable or the directory cannot
            be written.  The directory is only cleared after validation, so a
            failure here leaves the previous catalog in place.
    """
    if not catalog.items:
        raise ModelCatalogError("Cannot apply an empty model catalog.")

    directory = catalog_directory()
    directory.mkdir(parents=True, exist_ok=True)

    previous_state = read_catalog_state()
    previous_ids = previous_state.profile_ids if previous_state else ()
    _clear_directory(directory)
    for profile in catalog.items:
        _write_profile(directory, profile)

    write_catalog_state(
        CatalogState(
            version=catalog.version,
            source=source,
            profile_ids=catalog.profile_ids(),
            default_profile_id=catalog.default_profile_id,
        )
    )

    result = CatalogSyncResult(
        replaced=True,
        version=catalog.version,
        profile_ids=catalog.profile_ids(),
        default_profile_id=catalog.default_profile_id,
        previous_profile_ids=previous_ids,
    )
    logger.info(
        "Model catalog %s applied: %d profile(s) from %s.",
        catalog.version,
        len(catalog.items),
        source,
    )
    return result


async def sync_catalog(
    *,
    url: str | None = None,
    timeout: float = _DEFAULT_FETCH_TIMEOUT,
    source: str = SOURCE_REMOTE,
) -> CatalogSyncResult | None:
    """Fetch and apply the catalog in one step.

    Returns ``None`` when no source is configured (the directory stays the
    user's own).  Propagates :class:`ModelCatalogError` on failure so the
    caller decides between a silent startup fallback and a reported refresh;
    the directory is untouched in that case.
    """
    if not (url or catalog_url()):
        return None
    catalog = await fetch_catalog(url, timeout=timeout)
    return apply_catalog(catalog, source=source)


def sync_catalog_blocking(*, timeout: float = _DEFAULT_FETCH_TIMEOUT) -> CatalogSyncResult | None:
    """Run one sync from the startup path, where no event loop exists yet.

    Returns ``None`` when no source is configured.  Failures are logged and
    swallowed: the directory keeps the previous catalog, so an offline start
    still has models.  A running loop means this was called from async code
    that should have awaited :func:`sync_catalog` instead; starting a nested
    loop there would be wrong, so the sync is skipped.
    """
    if not catalog_url():
        return None
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        pass
    else:
        logger.warning("sync_catalog_blocking called with a running loop; await sync_catalog instead.")
        return None
    try:
        return asyncio.run(sync_catalog(timeout=timeout))
    except ModelCatalogError as exc:
        logger.warning("Could not sync the model catalog, keeping the previous list: %s", exc)
        return None


def sync_interval_seconds() -> float:
    """Return the poll interval: the environment's, else :data:`SYNC_INTERVAL_SECONDS`.

    Read at call time, not at import: the variable exists so one process can be
    started with a shorter interval than the default — watching a server-side
    change land without waiting the quarter of an hour.

    Anything unparseable or non-positive falls back to the default and is
    logged: a typo must neither stop the poll (zero) nor turn it into a hot
    loop (negative).
    """
    raw = os.environ.get(SYNC_INTERVAL_ENV, "").strip()
    if not raw:
        return float(SYNC_INTERVAL_SECONDS)
    try:
        value = float(raw)
    except ValueError:
        logger.warning("%s=%r is not a number; using %.0fs.", SYNC_INTERVAL_ENV, raw, SYNC_INTERVAL_SECONDS)
        return float(SYNC_INTERVAL_SECONDS)
    if value <= 0:
        logger.warning("%s=%r is not positive; using %.0fs.", SYNC_INTERVAL_ENV, raw, SYNC_INTERVAL_SECONDS)
        return float(SYNC_INTERVAL_SECONDS)
    return value


class CatalogSyncHandle:
    """Controls a running :func:`start_periodic_sync` loop.

    Returned instead of a bare stop event so a caller that is already polling
    can ask for an extra sync without starting a second thread: a login
    changes whose catalog is served and that must land now rather than at the
    next tick, while two threads would both rewrite the model directory and
    race the registry they refresh. Waking the existing thread keeps every
    sync serial, on the one thread that already owns the loop.

    ``set()`` stays available so callers written against the event it replaces
    keep working; it means stop.
    """

    def __init__(self) -> None:
        self._cv = threading.Condition()
        self._stopped = False
        self._pending = False

    def stop(self) -> None:
        """End the loop; the thread wakes at once instead of at the next tick."""
        with self._cv:
            self._stopped = True
            self._cv.notify_all()

    def set(self) -> None:
        """Stop, under the :class:`threading.Event` spelling this replaces."""
        self.stop()

    def sync_now(self) -> None:
        """Run one sync as soon as the loop can, then resume the interval."""
        with self._cv:
            if self._stopped:
                return
            self._pending = True
            self._cv.notify_all()

    def _wait(self, interval: float) -> bool:
        """Wait for the interval, a :meth:`sync_now`, or a stop.

        Returns ``False`` when the loop must end, ``True`` when it owes a sync
        — either the interval elapsed or one was requested.
        """
        with self._cv:
            if self._stopped:
                return False
            if not self._pending:
                self._cv.wait(interval)
                if self._stopped:
                    return False
            self._pending = False
        return True


def start_periodic_sync(
    *,
    interval: float | None = None,
    immediate: bool = False,
    timeout: float = _DEFAULT_FETCH_TIMEOUT,
    on_applied: Callable[[CatalogSyncResult], None] | None = None,
) -> CatalogSyncHandle | None:
    """Re-sync the catalog every *interval* seconds on a daemon thread.

    *interval* defaults to :func:`sync_interval_seconds` — the environment's
    override, else the 15-minute default — and is resolved when the loop starts
    rather than when this module is imported. *immediate* runs one sync before
    the first sleep, for the caller that starts the loop mid-session (a login)
    and cannot wait a whole interval for the list to appear.

    Returns ``None`` when there is nothing to poll: no catalog source, or no
    credential — a request without one is refused before it is sent, so the
    loop would do nothing but log. Call :func:`has_catalog_credential` to tell
    the two apart, and start the loop again when a login supplies the token.

    Otherwise the thread sleeps first: the bootstrap already ran the
    "immediately" sync, so a fresh start does not fetch twice.

    A failed sync is inert by design and reports the way the startup one does
    (:func:`sync_catalog_blocking` logs and keeps the previous list); a profile
    the catalog just deleted simply resolves to nothing on the next turn, which
    is the same failure the user would see after a restart. *on_applied* runs on
    the sync thread, so it must be thread-safe; an exception from it must not
    kill the loop.

    Returns :class:`CatalogSyncHandle`, whose ``sync_now()`` pulls one catalog
    ahead of the clock — a login changes whose models are served — and whose
    ``stop()`` ends the loop; or ``None`` when there is nothing to poll.
    """
    if not catalog_url():
        logger.info("Model catalog sync not started: no catalog source is configured.")
        return None
    if not has_catalog_credential():
        logger.info("Model catalog sync not started: no credential yet — it starts on login.")
        return None

    interval = sync_interval_seconds() if interval is None else interval
    logger.info(
        "Model catalog sync started: every %.0fs%s.",
        interval,
        ", with one now" if immediate else "",
    )
    handle = CatalogSyncHandle()

    def _sync_once() -> None:
        result = sync_catalog_blocking(timeout=timeout)
        if result is None or on_applied is None:
            return
        try:
            on_applied(result)
        except Exception:
            logger.exception("Model catalog sync callback failed; the next sync still runs.")

    def _run() -> None:
        if immediate:
            _sync_once()
        while handle._wait(interval):
            _sync_once()
        logger.info("Model catalog sync stopped.")

    threading.Thread(target=_run, name="chrys-model-catalog-sync", daemon=True).start()
    return handle
