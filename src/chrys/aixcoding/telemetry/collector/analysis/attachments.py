# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Controlled mutations blob accessor (TS ``attachments.ts``; M5 plan
§1.2/§6.3; guide §14.3/§11.1).

Blobs live at ``mutations/<sha256>`` under the session directory; the
hash shape check (lowercase hex64) doubles as path-traversal rejection —
anything illegal reads as a miss (None, the caller degrades by omitting
line counts). The analysis core depends only on the injectable
synchronous interface; the file-backed implementation is built by the
orchestration layer.
"""

from __future__ import annotations

import os
import re
from typing import Protocol

_BLOB_HASH = re.compile(r"^[0-9a-f]{64}$")

# Per-blob read cap (M5 plan §6.3: over the cap is a skip, the caller
# degrades by omitting).
MAX_BLOB_BYTES = 2 * 1024 * 1024


class MutationBlobReader(Protocol):
    def read_blob_text(self, blob_hash: str) -> str | None:
        """Read blob text; None when missing/unreadable/hash illegal/over
        the size cap."""
        ...


class SessionMutationBlobReader:
    def __init__(self, session_directory: str) -> None:
        self._session_directory = session_directory

    def read_blob_text(self, blob_hash: str) -> str | None:
        if not _BLOB_HASH.fullmatch(blob_hash):
            return None
        path = os.path.join(self._session_directory, "mutations", blob_hash)
        try:
            if os.path.getsize(path) > MAX_BLOB_BYTES:
                return None
            with open(path, encoding="utf-8") as handle:
                return handle.read()
        except OSError:
            return None


class _NullBlobReader:
    def read_blob_text(self, blob_hash: str) -> str | None:
        return None


NULL_BLOB_READER: MutationBlobReader = _NullBlobReader()
"""Null accessor: with blobs unavailable the line-count columns are
omitted as a whole."""


def split_lines(text: str) -> list[str]:
    """Split text into lines: a trailing newline never produces an
    extra empty line (``"a\\n"`` is 1 line, ``"a"`` likewise, ``"a\\nb\\n"``
    is 2); empty text is 0 lines."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines
