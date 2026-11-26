# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Fixtures shared by the llm_queue behavior anchors."""

from __future__ import annotations

import logging
from collections.abc import Iterator

import pytest

DETAIL_LEVEL = 5
"""Mirrors ``DETAIL_LEVEL`` in ``kernel/aixcoding/diagnostics/logging_support``."""


@pytest.fixture
def detail_records() -> Iterator[list[logging.LogRecord]]:
    """Capture the file-only ``aixcoding.detail`` subtree, which ``caplog`` cannot see.

    The subtree is non-propagating in production (ADR-0017), so a test that wants
    its records must attach to it and save/restore its state like the diagnostics
    tests do.
    """
    detail = logging.getLogger("aixcoding.detail")
    saved = (detail.handlers[:], detail.propagate, detail.level)
    records: list[logging.LogRecord] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    capture = _Capture()
    capture.setLevel(logging.NOTSET)
    logging.addLevelName(DETAIL_LEVEL, "DETAIL")
    detail.setLevel(DETAIL_LEVEL)
    detail.propagate = False
    detail.addHandler(capture)
    yield records
    detail.handlers[:] = saved[0]
    detail.propagate, detail.level = saved[1], saved[2]
