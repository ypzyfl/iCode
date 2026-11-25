# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

from __future__ import annotations

from collections.abc import Iterator

import pytest

from chrys.service.aixcoding.llm_call_interception.interceptor import set_http_policy


@pytest.fixture(autouse=True)
def empty_http_policy() -> Iterator[None]:
    set_http_policy(None)
    yield
    set_http_policy(None)
