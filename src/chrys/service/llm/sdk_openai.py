# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""The ``AsyncOpenAI`` client Chrys builds for every OpenAI-SDK provider.

Importing this module loads the OpenAI SDK; the client factory imports it only
while it builds such a client.
"""

from __future__ import annotations

from typing import Any

from openai import AsyncOpenAI

from chrys.service.llm.sdk_headers import CaseFoldedDefaultHeaders
from chrys.service.llm.sdk_retry import DeterministicConnectionSleepGuard


class RetryGuardedAsyncOpenAI(DeterministicConnectionSleepGuard, CaseFoldedDefaultHeaders, AsyncOpenAI):
    """``AsyncOpenAI`` that does not retry a connection error that cannot self-heal, and sends each header name once."""

    # AIxCoding auth: tolerate a credential-free client (aixcoding/docs/batches/llm-keyless-sdk-auth)
    def _validate_headers(self, headers: Any, custom_headers: Any) -> None:
        """Let a credential-free client send its request unauthenticated on purpose.

        The stock validation refuses a bearer request whose headers carry
        neither ``Authorization`` nor an explicit omission — and that omission
        cannot be declared at construction time, because the SDK's header
        merge strips ``Omit`` values before the check runs.  A client built
        with the empty-key provider (no profile key, no env key) is by
        construction "unauthenticated on purpose": the check is skipped, and
        the request simply carries no ``Authorization`` header.
        """
        if not self.api_key and not self.admin_api_key:
            return
        super()._validate_headers(headers, custom_headers)
