# (tests — asserts are pytest idiom, Chinese prose is the data)
"""Shared fixtures for diagnostics tests: logging state isolation."""

from __future__ import annotations

import logging

import pytest

AIX = "aixcoding"


@pytest.fixture
def aix_logger_state():
    """Isolate the global ``aixcoding`` logger between tests."""
    logger = logging.getLogger(AIX)
    saved = (logger.handlers[:], logger.propagate, logger.level)
    logger.handlers.clear()
    yield logger
    logger.handlers[:] = saved[0]
    logger.propagate, logger.level = saved[1], saved[2]
