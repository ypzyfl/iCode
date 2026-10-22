# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Install the bundled security guard hooks into the global hooks directory.

The rule pack lives beside this module (``chrys/app/guard_hooks/``) and ships
inside the wheel and the PyApp distribution, so a user never copies files by
hand.  Installation writes to the place the runtime actually reads
(:func:`chrys.foundation.platform.get_platform` -> ``config_dir / "hooks"``):

* Windows: ``%APPDATA%\\chrys\\hooks\\``
* macOS / Linux: ``~/.chrys/hooks/``

Two machine shapes are handled:

* **Fresh install** — no ``hooks.yaml`` yet: the shipped template is written
  verbatim.
* **Existing configuration** — the entries this installer owns are replaced in
  place (matched by id) and unrelated hooks, ``settings`` and comments are
  kept.  A configuration that cannot be parsed is backed up and replaced: a
  guard that silently fails to load is worse than a hand-written hook being
  reset, and the backup keeps that hook recoverable.

Every write goes through a same-directory temporary file plus ``os.replace``,
so a crash mid-install cannot leave a half-written ``hooks.yaml`` behind.
"""

from __future__ import annotations

import contextlib
import os
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import yaml

from chrys.foundation.platform import get_platform

GUARD_ASSET_DIR = Path(__file__).resolve().parent / "guard_hooks"
"""Directory holding the shipped rule pack inside a wheel / installed build."""

_SOURCE_ASSET_DIR = Path(__file__).resolve().parents[3] / "guard_hooks"
"""Repo-root rule pack; the wheel force-includes from here (see pyproject.toml).

Source checkouts have no ``chrys/app/guard_hooks/`` — :func:`resolve_asset_dir`
falls back to this directory so running from the repo installs the same rules
a released build would.
"""


def resolve_asset_dir() -> Path:
    """Return the rule-pack directory present in this tree.

    Prefers the packaged ``chrys/app/guard_hooks/``; falls back to the repo-root
    ``guard_hooks/`` when running from a source checkout (the force-include has
    not materialized a packaged copy there).
    """
    if (GUARD_ASSET_DIR / GUARD_TEMPLATE_NAME).is_file():
        return GUARD_ASSET_DIR
    return _SOURCE_ASSET_DIR


GUARD_CONFIG_NAME = "hooks.yaml"
"""Name of the hooks configuration this installer owns entries in."""

GUARD_TEMPLATE_NAME = "hooks.yaml"
"""Shipped template; its ``path:`` values already point at ``guard/``."""

GUARD_SUBDIR = "guard"
"""Scripts and the rule dictionary go here, beside ``hooks.yaml``."""

GUARD_PAYLOAD_FILES = ("_prompt_guard.py", "_tool_guard.py", "_guard_core.py", "rules.json")
"""Files a hook subprocess needs at run time.

These names match ``guard_hooks/`` at the repo root — the single source of
truth the wheel force-includes into ``chrys/app/guard_hooks/`` (see
``pyproject.toml``). Legacy installs (before 0.31.0) shipped the same scripts
without the leading underscore; :func:`_copy_payload` removes those leftovers.
"""

LEGACY_PAYLOAD_FILES = ("prompt_guard.py", "tool_guard.py", "guard_core.py")
"""Pre-0.31.0 payload names; removed from installs so stale scripts never linger."""

MANAGED_HOOK_IDS = ("security-prompt-guard", "security-tool-guard")
"""Hook ids this installer owns; re-installing replaces exactly these."""

BACKUP_SUFFIX = ".pre-guard"

_BOM = b"\xef\xbb\xbf"
_TOP_LEVEL_KEY = re.compile(r"^(?P<key>[A-Za-z_][\w-]*)\s*:(?P<rest>.*)$")
_BLOCK_SEQUENCE = re.compile(r"^(?P<indent>[ ]*)-(?P<rest>\s.*|$)")


@dataclass(frozen=True)
class GuardInstallReport:
    """What :func:`install_guard_hooks` did, for the caller's status output."""

    hooks_dir: Path
    """Directory the rule pack was written to."""

    hooks_file: Path
    """``hooks.yaml`` that now lists the guard hooks."""

    merged_into_existing: bool
    """``True`` when another configuration was merged instead of overwritten."""

    backup: Path | None
    """Backup of the previous configuration, when one was made."""

    replaced_unparsable_config: bool = False
    """``True`` when the previous configuration could not be parsed."""


def hooks_dir_for(config_dir: Path) -> Path:
    """Return ``<config_dir>/hooks`` — the directory the runtime loads hooks from."""
    return config_dir / "hooks"


def install_guard_hooks(*, hooks_dir: Path | None = None, asset_dir: Path | None = None) -> GuardInstallReport:
    """Copy the rule pack into *hooks_dir* and merge its hook entries.

    ``hooks_dir`` defaults to the platform hooks directory; ``asset_dir`` is
    overridable for tests.  Files are copied before the configuration is
    written, so the configuration never points at scripts that are not there.
    Idempotent: re-running on an up-to-date install rewrites the same content.
    """
    source_dir = resolve_asset_dir() if asset_dir is None else asset_dir
    missing = missing_guard_assets(source_dir)
    if missing:
        raise FileNotFoundError(f"Guard hooks assets are missing from this build: {', '.join(map(str, missing))}")

    target_dir = hooks_dir_for(get_platform().config_dir) if hooks_dir is None else hooks_dir
    template_text = (source_dir / GUARD_TEMPLATE_NAME).read_text(encoding="utf-8")
    managed_entries = parse_managed_entries(template_text)

    _copy_payload(Path(source_dir), target_dir)

    hooks_file = target_dir / GUARD_CONFIG_NAME
    if not hooks_file.exists():
        _write_text_atomic(hooks_file, template_literal_text(template_text), backup=False)
        return GuardInstallReport(target_dir, hooks_file, merged_into_existing=False, backup=None)

    raw = hooks_file.read_bytes()
    had_bom = raw.startswith(_BOM)
    text = raw.decode("utf-8-sig")
    try:
        merged_text = merge_guard_entries(text, managed_entries)
    except yaml.YAMLError, ValueError:
        return _replace_unparsable(hooks_file, template_text, had_bom)
    try:
        merged_document = yaml.safe_load(merged_text)
    except yaml.YAMLError:
        return _replace_unparsable(hooks_file, template_text, had_bom)
    if not isinstance(merged_document, dict):
        return _replace_unparsable(hooks_file, template_text, had_bom)

    _write_text_atomic(hooks_file, merged_text, backup=True, had_bom=had_bom)
    return GuardInstallReport(
        target_dir,
        hooks_file,
        merged_into_existing=True,
        backup=hooks_file.with_name(f"{hooks_file.name}{BACKUP_SUFFIX}"),
    )


def template_literal_text(template_text: str) -> str:
    """Return the template exactly as a fresh install should write it."""
    return template_text.replace("\r\n", "\n").rstrip("\n") + "\n"


def parse_managed_entries(template_text: str) -> list[str]:
    """Return the template's ``hooks:`` entries as text blocks, comments included."""
    document = yaml.safe_load(template_text)
    if not isinstance(document, dict) or not isinstance(document.get("hooks"), list):
        raise ValueError(f"{GUARD_TEMPLATE_NAME} has no hooks list")
    blocks = _hook_blocks(template_text)
    template_ids = [str(entry.get("id", "")) for entry in document["hooks"] if isinstance(entry, dict)]
    if len(blocks) != len(template_ids):
        raise ValueError(f"{GUARD_TEMPLATE_NAME}: {len(template_ids)} hooks but {len(blocks)} YAML blocks")
    return blocks


def merge_guard_entries(config_text: str, managed_entries: list[str]) -> str:
    """Replace our entries in *config_text*, keeping every other entry and setting.

    Raises ``yaml.YAMLError`` when the file cannot be parsed; the caller then
    treats it as unparsable instead of writing half of it back.
    """
    document = yaml.safe_load(config_text)
    if document is None:
        document = {}
    if not isinstance(document, dict):
        raise ValueError("hooks configuration must be a mapping")
    existing_entries = document.get("hooks")
    if existing_entries is not None and not isinstance(existing_entries, list):
        raise ValueError("hooks must be a list")

    newline = "\r\n" if "\r\n" in config_text else "\n"
    kept_blocks = [block for block in _hook_blocks(config_text) if _hook_id(block) not in MANAGED_HOOK_IDS]
    rendered = "".join(block.replace("\r\n", "\n") for block in (*kept_blocks, *managed_entries))
    span = _hook_section_span(config_text)
    if span is None:
        return template_literal_text(config_text + newline + ("hooks:\n" + rendered).replace("\n", newline))
    if not rendered:
        rendered = " []\n"
    start, end = span
    body = ("hooks:\n" + rendered).replace("\n", newline)
    return template_literal_text(config_text[:start] + body + config_text[end:])


def _replace_unparsable(hooks_file: Path, template_text: str, had_bom: bool) -> GuardInstallReport:
    backup = hooks_file.with_name(f"{hooks_file.name}{BACKUP_SUFFIX}")
    shutil.copyfile(hooks_file, backup)
    _write_text_atomic(hooks_file, template_literal_text(template_text), backup=False, had_bom=had_bom)
    return GuardInstallReport(
        hooks_file.parent,
        hooks_file,
        merged_into_existing=False,
        backup=backup,
        replaced_unparsable_config=True,
    )


# ---------------------------------------------------------------------------
# YAML section surgery
# ---------------------------------------------------------------------------


def _hook_section_span(text: str) -> tuple[int, int] | None:
    """Return the character span of the top-level ``hooks:`` section."""
    offset = 0
    start: int | None = None
    for line in text.splitlines(keepends=True):
        match = _TOP_LEVEL_KEY.match(line.rstrip("\r\n"))
        if match is not None:
            if start is not None:
                return start, offset
            if match.group("key") == "hooks":
                start = offset
        offset += len(line)
    if start is None:
        return None
    return start, len(text)


def _hook_blocks(text: str) -> list[str]:
    """Split the ``hooks:`` section into one text block per list entry.

    Each block starts at a list-item line and runs until the next item (or the
    end of the section), so both the item's keys and its nested mappings stay
    with it.  Comment lines between a block and the next item stay attached to
    that next item, preserving the documented layout of the file.
    """
    span = _hook_section_span(text)
    if span is None:
        return []
    lines = text[span[0] : span[1]].splitlines(keepends=True)[1:]
    item_indent = next(
        (len(sequence.group("indent")) for line in lines if (sequence := _BLOCK_SEQUENCE.match(line)) is not None),
        None,
    )
    if item_indent is None:
        return []
    blocks: list[str] = []
    current: list[str] = []
    comments: list[str] = []
    for line in lines:
        sequence = _BLOCK_SEQUENCE.match(line)
        if sequence is not None and len(sequence.group("indent")) == item_indent:
            if current:
                blocks.append("".join(current))
            current = [*comments, line]
            comments = []
        elif line.strip().startswith("#") or not line.strip():
            comments.append(line)
        elif current:
            current.extend(comments)
            current.append(line)
            comments = []
    if current:
        blocks.append("".join(current))
    return blocks


def _hook_id(block: str) -> str:
    """Return the ``id:`` of one hook block, or ``""`` when it has none."""
    parsed = yaml.safe_load(block)
    if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
        return str(parsed[0].get("id", ""))
    return ""


# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------


def missing_guard_assets(asset_dir: Path | None = None) -> list[Path]:
    """Return shipped files absent from this build."""
    root = resolve_asset_dir() if asset_dir is None else asset_dir
    expected = (root / GUARD_TEMPLATE_NAME, *(root / name for name in GUARD_PAYLOAD_FILES))
    return [path for path in expected if not path.is_file()]


def _copy_payload(source_dir: Path, target_dir: Path) -> None:
    """Copy the scripts and dictionary into ``<hooks_dir>/guard/`` atomically."""
    guard_dir = target_dir / GUARD_SUBDIR
    guard_dir.mkdir(parents=True, exist_ok=True)
    for name in GUARD_PAYLOAD_FILES:
        _copy_file_atomic(source_dir / name, guard_dir / name)
    for name in LEGACY_PAYLOAD_FILES:
        with contextlib.suppress(OSError):
            (guard_dir / name).unlink(missing_ok=True)


def _copy_file_atomic(source: Path, destination: Path) -> None:
    """Copy *source* over *destination* without exposing a partial file."""
    fd, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent)
    temporary_path = Path(temporary_name)
    try:
        os.close(fd)
        shutil.copyfile(source, temporary_path)
        os.replace(temporary_path, destination)
    finally:
        with contextlib.suppress(OSError):
            temporary_path.unlink(missing_ok=True)


def _write_text_atomic(path: Path, text: str, *, backup: bool, had_bom: bool = False) -> None:
    """Write *text* (UTF-8, optional BOM) to *path* atomically, backing up first."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if backup and path.exists():
        shutil.copyfile(path, path.with_name(f"{path.name}{BACKUP_SUFFIX}"))
    payload = text.encode("utf-8")
    if had_bom:
        payload = _BOM + payload
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
        _apply_default_permissions(temporary_path)
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            with contextlib.suppress(OSError):
                temporary_path.unlink()


def _apply_default_permissions(path: Path) -> None:
    """Keep the configuration owner-only where the platform supports it."""
    if sys.platform == "win32":
        return
    with contextlib.suppress(OSError, AttributeError):
        os.chmod(path, 0o600)


def installed_guard_hooks(hooks_dir: Path | None = None) -> tuple[bool, list[str]]:
    """Return ``(config_lists_guards, missing_files)`` for a hooks directory."""
    target_dir = hooks_dir_for(get_platform().config_dir) if hooks_dir is None else hooks_dir
    hooks_file = target_dir / GUARD_CONFIG_NAME
    listed = False
    with contextlib.suppress(OSError, yaml.YAMLError):
        document = yaml.safe_load(hooks_file.read_text(encoding="utf-8-sig")) if hooks_file.is_file() else None
        if isinstance(document, dict) and isinstance(document.get("hooks"), list):
            ids = {str(entry.get("id", "")) for entry in document["hooks"] if isinstance(entry, dict)}
            listed = all(hook_id in ids for hook_id in MANAGED_HOOK_IDS)
    missing = [
        str(target_dir / GUARD_SUBDIR / name)
        for name in GUARD_PAYLOAD_FILES
        if not guard_file_present(target_dir, name)
    ]
    return listed, missing


def guard_file_present(target_dir: Path, name: str) -> bool:
    """Return whether one installed rule-pack file exists under ``guard/``."""
    return (target_dir / GUARD_SUBDIR / name).is_file()


__all__ = [
    "GUARD_ASSET_DIR",
    "GUARD_PAYLOAD_FILES",
    "GUARD_SUBDIR",
    "MANAGED_HOOK_IDS",
    "GuardInstallReport",
    "hooks_dir_for",
    "install_guard_hooks",
    "installed_guard_hooks",
    "merge_guard_entries",
    "missing_guard_assets",
    "parse_managed_entries",
    "template_literal_text",
]
