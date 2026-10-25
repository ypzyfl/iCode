# (tests — asserts are pytest idiom, Chinese prose is the data)
"""Shared fixtures for diagnostics tests: logging state isolation."""

from __future__ import annotations

import logging
import sys
import threading

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


@pytest.fixture
def restore_hooks():
    """Restore interpreter/thread excepthooks around tests that install ours."""
    saved = (sys.excepthook, threading.excepthook)
    yield
    sys.excepthook, threading.excepthook = saved
