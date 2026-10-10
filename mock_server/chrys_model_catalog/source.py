# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Catalog payload source — "file content is the response".

Borrowed from the reference mock server: whatever JSON file this points at is
returned verbatim, re-read on **every request**, so editing the file changes
the next response without a restart.

The default file is the reference server's own response body,
``config_new.json``, kept next to this package; ``--catalog`` points at another
file of the same shape. There is no built-in fallback: this mock stands in for
*that* response, and inventing data of its own is how it would start lying about
the contract it mimics.

This module imports nothing from the product: the mock stays black-box with
respect to the contract it pretends to speak (see ``mock_server/README.md``).
The contract check belongs to the tests, which feed the payload through the
client's own parser.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: The reference server's own response body (``config_new.json`` next to this
#: package): the file is re-read and returned verbatim each request.
DEFAULT_CATALOG_FILE = Path(__file__).with_name("config_new.json")


class CatalogSourceError(Exception):
    """Raised when the configured catalog file cannot be served."""


@dataclass
class CatalogSource:
    """Reads the served catalog; ``None`` means the packaged ``config_new.json``."""

    path: Path | None = None

    def load(self) -> dict[str, Any]:
        """Return the file content as a JSON object, re-reading it each call."""
        path = self.path or DEFAULT_CATALOG_FILE
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise CatalogSourceError(f"cannot read {path}: {exc}") from exc
        except ValueError as exc:
            raise CatalogSourceError(f"{path} is not valid JSON: {exc}") from exc

        if not isinstance(raw, dict):
            raise CatalogSourceError(f"{path}: JSON must be an object")
        return raw
