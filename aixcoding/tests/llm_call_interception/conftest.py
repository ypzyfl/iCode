# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

from __future__ import annotations

from collections.abc import Iterator
from inspect import unwrap

import pytest

from chrys.service.aixcoding.llm_call_interception.interceptor import set_http_policy
from chrys.service.llm import clients

# AIxCoding test isolation: registering a policy installs the process-wide factory wrapper,
# so every test starts and ends with the unwrapped upstream factory.
_UNWRAPPED_FACTORY = unwrap(clients._build_profile_http_client)


@pytest.fixture(autouse=True)
def clean_http_interception() -> Iterator[None]:
    set_http_policy(None)
    clients._build_profile_http_client = _UNWRAPPED_FACTORY
    yield
    set_http_policy(None)
    clients._build_profile_http_client = _UNWRAPPED_FACTORY
