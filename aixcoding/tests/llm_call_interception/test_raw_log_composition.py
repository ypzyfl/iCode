# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

from __future__ import annotations

import json

import httpx
import pytest
from aixcoding.tests.llm_call_interception.support import ChunkStream, profile

from chrys.service.aixcoding.llm_call_interception import HttpChange
from chrys.service.aixcoding.llm_call_interception.installer import install_http_interception
from chrys.service.aixcoding.llm_call_interception.interceptor import set_http_policy
from chrys.service.llm import clients


class Mutation:
    async def before_request(self, context, headers, body):
        updated = dict(headers)
        updated["X-Policy"] = "request-modified"
        return HttpChange(headers=updated, body=b"request-modified")

    async def before_response_body(self, context, status_code, headers, body):
        return HttpChange(body=b"response-modified")


@pytest.mark.parametrize("buffered", [True, False])
async def test_raw_log_sees_mutated_request_and_original_response(
    monkeypatch: pytest.MonkeyPatch, tmp_path, buffered: bool
) -> None:
    original = clients._build_profile_http_client
    monkeypatch.setattr(clients, "_build_profile_http_client", original)
    install_http_interception()
    set_http_policy(Mutation())
    log_path = tmp_path / "raw.jsonl"

    async def handle(request: httpx.Request) -> httpx.Response:
        assert await request.aread() == b"request-modified"
        if buffered:
            return httpx.Response(200, content=b"response-original")
        return httpx.Response(200, stream=ChunkStream([b"response-orig", b"inal"]))

    http = clients._build_profile_http_client(
        profile(),
        httpx.Timeout(5),
        raw_http_log_path=log_path,
        transport=httpx.MockTransport(handle),
    )
    try:
        response = await http.post("http://llm.test", content=b"request-original")
        assert response.content == b"response-modified"
    finally:
        await http.aclose()

    records = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert [record["event"] for record in records] == ["request", "response"]
    assert ["x-policy", "request-modified"] in records[0]["request"]["headers"]
    assert records[0]["request"]["body"]["text"] == "request-modified"
    assert records[1]["response"]["body"]["text"] == "response-original"
