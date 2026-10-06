# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Revision reading: bytes → sha256 → JSON parse (TS baseline ``reader.ts``).

Candidates are tried in order; a corrupt primary degrades to the backup (the
path actually read is recorded). All candidates unreadable → ``not_found``;
readable but every parse failed → ``malformed``. The revision hash is
computed over the exact bytes read — never over a re-encoded copy.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SessionRevision:
    path: str
    hash: str
    envelope: object


@dataclass(frozen=True, slots=True)
class ReadFailureResult:
    reason: str


def read_revision(ordered_paths: tuple[str, ...] | list[str]) -> SessionRevision | ReadFailureResult:
    saw_unparsable = False
    for candidate in ordered_paths:
        path = Path(candidate)
        try:
            blob = path.read_bytes()
        except OSError:
            continue
        try:
            envelope = json.loads(blob.decode("utf-8"))
        except UnicodeDecodeError, json.JSONDecodeError:
            saw_unparsable = True
            continue
        return SessionRevision(
            path=str(path),
            hash=hashlib.sha256(blob).hexdigest(),
            envelope=envelope,
        )
    return ReadFailureResult(reason="malformed" if saw_unparsable else "not_found")
