# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Report config / file sink / http sink tests (scenarios ported from
the TS ``http-sink.test.ts``; contract §2/§4)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from chrys.aixcoding.telemetry.collector.report.config import read_report_config
from chrys.aixcoding.telemetry.collector.report.http_sink import (
    HttpReportSink,
    HttpReportSinkOptions,
    PlannedReportRequest,
    ReportRequestPlanning,
    plan_report_requests,
)
from chrys.aixcoding.telemetry.collector.report.port import SessionTelemetryReport
from chrys.aixcoding.telemetry.collector.report.sink import FileReportSink

COMMON: dict[str, Any] = {
    "sessionId": "session-1",
    "spanId": "11111111-2222-4333-8444-555555555555",
    "productName": "demo-repo",
    "projectName": "demo-repo",
    "channelType": "desktop",
    "channelName": "aixcoding-desktop",
    "channelVersion": "0.1.0",
    "pluginVersion": "0.28.0",
    "userId": "user-1",
}

TOOL_USE_SAVED: dict[str, Any] = {
    **COMMON,
    "kind": "tool-use-saved",
    "funcType": 3,
    "funcName": "read_file",
    "funcId": "cccccccccccccccccccccccccccccccc",
    "requestId": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
    "codeStatus": 0,
}

TOOL_STATUS_UPDATED: dict[str, Any] = {
    "kind": "tool-status-updated",
    "funcId": "cccccccccccccccccccccccccccccccc",
    "codeStatus": 1,
    "originalLines": 300,
    "addedLines": 12,
    "deletedLines": 3,
}

INPUT_TRIGGERED_USE: dict[str, Any] = {
    **COMMON,
    "kind": "input-triggered-use",
    "funcType": 0,
    "funcName": "my-skill",
}

AI_CODE_SAVED: dict[str, Any] = {
    **COMMON,
    "kind": "ai-code-saved",
    "reportId": "3d4a8d7e-7148-4295-9545-a4b8d75322e4",
    "requestId": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
    "sourceType": "edit",
    "inputMethod": "agent",
    "language": "ts",
    "blocks": [{"rangeStart": 1, "rangeEnd": 12}],
}


def report_of(events: list[dict[str, Any]]) -> SessionTelemetryReport:
    return SessionTelemetryReport(
        report_id="11111111-1111-4111-8111-111111111111",
        scope="acp",
        final=False,
        analysis_version=1,
        session={"sessionId": "session-1", "kind": "chat", "turnCount": 1},
        incremental_turns=[],
        report_events=events,
    )


class TestReadReportConfig:
    def test_accepts_v2_http_sink_with_endpoint_and_token(self, tmp_path: Path) -> None:
        path = tmp_path / "report-config.json"
        path.write_text(
            json.dumps(
                {
                    "version": 2,
                    "sink": "http",
                    "endpoint": "http://127.0.0.1:4321/csas/telemetry/api/v1",
                    "token": "tok",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        result = read_report_config(str(path))
        assert result.config is not None
        assert result.config.version == 2
        assert result.config.sink == "http"

    def test_reads_legacy_v1_by_ignoring_attribution(self, tmp_path: Path) -> None:
        path = tmp_path / "report-config.json"
        path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "sink": "file",
                    "attribution": {"account_id": "old"},
                }
            )
            + "\n",
            encoding="utf-8",
        )
        result = read_report_config(str(path))
        assert result.config is not None
        assert result.config.version == 1
        assert result.config.sink == "file"

    def test_rejects_v2_still_carrying_attribution(self, tmp_path: Path) -> None:
        path = tmp_path / "report-config.json"
        path.write_text(
            json.dumps({"version": 2, "sink": "file", "attribution": {"account_id": "x"}}) + "\n",
            encoding="utf-8",
        )
        assert read_report_config(str(path)).config is None

    def test_rejects_http_without_endpoint_and_corrupted_files(self, tmp_path: Path) -> None:
        missing_endpoint = tmp_path / "no-endpoint.json"
        missing_endpoint.write_text(json.dumps({"version": 2, "sink": "http"}) + "\n", encoding="utf-8")
        assert read_report_config(str(missing_endpoint)).config is None

        assert read_report_config(str(tmp_path / "missing.json")).config is None


class TestFileReportSink:
    def test_writes_payload_with_sequence_and_omits_nulls(self, tmp_path: Path) -> None:
        sink = FileReportSink(str(tmp_path))
        event = SessionTelemetryReport(
            report_id="rep-1",
            scope="acp",
            final=False,
            analysis_version=1,
            session={"sessionId": "4201eebc-ca45-4328-8882-272f3d7c41cb", "title": None, "turnCount": 0},
            incremental_turns=[],
            report_events=[{"kind": "tool-status-updated", "funcId": "f1", "codeStatus": 0}],
        )
        assert sink.report(event).success is True
        reports = tmp_path / "reports"
        names = sorted(entry.name for entry in reports.iterdir())
        assert names == ["4201eebcca4543288882272f3d7c41cb-1.json"]
        payload = json.loads((reports / names[0]).read_text(encoding="utf-8"))
        # Nulls omitted, numeric zero kept.
        assert "title" not in payload["session"]
        assert payload["session"]["turnCount"] == 0
        assert payload["reportId"] == "rep-1"
        assert payload["reportEvents"][0]["codeStatus"] == 0
        # Second report gets the next sequence.
        assert sink.report(event).success is True
        names = sorted(entry.name for entry in reports.iterdir())
        assert names == [
            "4201eebcca4543288882272f3d7c41cb-1.json",
            "4201eebcca4543288882272f3d7c41cb-2.json",
        ]


class TestPlanReportRequests:
    def test_maps_each_event_kind_to_its_endpoint_in_order(self) -> None:
        requests = plan_report_requests([TOOL_USE_SAVED, TOOL_STATUS_UPDATED, AI_CODE_SAVED])
        assert [request.path for request in requests] == [
            "tool-detail/save",
            "tool-detail/update",
            "ai-code/save",
        ]
        save_body = requests[0].body
        assert save_body["productName"] == "demo-repo"
        assert save_body["funcType"] == 3
        assert save_body["funcName"] == "read_file"
        assert save_body["funcId"] == "cccccccccccccccccccccccccccccccc"
        assert save_body["requestId"] == "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
        assert save_body["codeStatus"] == 0
        assert save_body["channelType"] == "desktop"
        # The discriminator field never reaches the wire.
        assert "kind" not in save_body
        assert requests[1].body == {
            "funcId": "cccccccccccccccccccccccccccccccc",
            "codeStatus": 1,
            "originalLines": 300,
            "addedLines": 12,
            "deletedLines": 3,
        }
        assert requests[2].body["reportId"] == "3d4a8d7e-7148-4295-9545-a4b8d75322e4"
        assert requests[2].body["sourceType"] == "edit"
        assert requests[2].body["blocks"] == [{"rangeStart": 1, "rangeEnd": 12}]

    def test_aggregates_consecutive_input_triggered_use_into_batch(self) -> None:
        requests = plan_report_requests([INPUT_TRIGGERED_USE, INPUT_TRIGGERED_USE])
        assert len(requests) == 1
        assert requests[0].path == "tool-detail/batch-save"
        batch = requests[0].body
        assert isinstance(batch, list)
        assert all(item["funcType"] == 0 and item["funcName"] == "my-skill" for item in batch)
        assert all("kind" not in item for item in batch)

    def test_returns_no_requests_for_empty_events(self) -> None:
        assert plan_report_requests([]) == []

    def test_attaches_version_headers_to_saves_only_with_planning(self) -> None:
        content_hash = "a" * 64
        planning = ReportRequestPlanning(
            analysis_version=3,
            content_hash_by_span_id={COMMON["spanId"]: content_hash},
        )
        requests = plan_report_requests(
            [TOOL_USE_SAVED, TOOL_STATUS_UPDATED, INPUT_TRIGGERED_USE, AI_CODE_SAVED],
            planning,
        )
        expected_headers = {
            "X-Turn-Content-Hash": content_hash,
            "X-Analysis-Version": "3",
        }
        # save and ai-code/save carry the version headers; update and
        # batch-save do not.
        assert requests[0].headers == expected_headers
        assert requests[3].headers == expected_headers
        assert requests[1].headers is None
        assert requests[2].headers is None
        # No planning input → no headers (backward compatible).
        assert plan_report_requests([TOOL_USE_SAVED])[0].headers is None
        # spanId outside the map (the turn is not in the increment): no
        # guessing, headers omitted.
        unknown_span = {**TOOL_USE_SAVED, "spanId": "99999999-9999-4999-8999-999999999999"}
        assert plan_report_requests([unknown_span], planning)[0].headers is None


class _StubBackend:
    """httpx.MockTransport-backed stub backend (records requests,
    scripted responses)."""

    def __init__(self, status: int = 200, body: dict[str, Any] | None = None) -> None:
        self.requests: list[dict[str, Any]] = []
        self.status = status
        self.body = body if body is not None else {"success": True, "message": "ok", "code": 200, "result": None}

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(
            {
                "path": request.url.path.replace("/csas/telemetry/api/v1/", ""),
                "token": request.headers.get("token"),
                "body": json.loads(request.content.decode("utf-8")),
            }
        )
        return httpx.Response(self.status, json=self.body)


def _sink(stub: _StubBackend, token: str | None = None) -> HttpReportSink:
    return HttpReportSink(
        HttpReportSinkOptions(
            endpoint="http://127.0.0.1:4321/csas/telemetry/api/v1",
            token=token,
            client=httpx.Client(transport=httpx.MockTransport(stub.handler)),
        )
    )


class TestHttpReportSink:
    def test_sends_events_to_four_endpoints_in_order_with_token(self) -> None:
        stub = _StubBackend()
        result = _sink(stub, token="token-1").report(
            report_of([INPUT_TRIGGERED_USE, TOOL_USE_SAVED, TOOL_STATUS_UPDATED, AI_CODE_SAVED])
        )
        assert result.success is True
        assert [request["path"] for request in stub.requests] == [
            "tool-detail/batch-save",
            "tool-detail/save",
            "tool-detail/update",
            "ai-code/save",
        ]
        assert all(request["token"] == "token-1" for request in stub.requests)

    def test_sends_nothing_when_no_report_events(self) -> None:
        stub = _StubBackend()
        result = _sink(stub).report(report_of([]))
        assert result.success is True
        assert stub.requests == []

    def test_fails_retryable_on_http_503_and_stops_subsequent(self) -> None:
        stub = _StubBackend(status=503, body={"error": "unavailable"})
        result = _sink(stub).report(report_of([TOOL_USE_SAVED, TOOL_STATUS_UPDATED]))
        assert result.success is False
        assert result.retryable is True
        assert len(stub.requests) == 1

    def test_fails_non_retryable_on_business_rejection(self) -> None:
        stub = _StubBackend(status=200, body={"success": False, "message": "rejected", "code": 500, "result": None})
        result = _sink(stub).report(report_of([TOOL_USE_SAVED]))
        assert result.success is False
        assert result.retryable is False

    def test_planned_request_shape(self) -> None:
        request = PlannedReportRequest(path="tool-detail/save", body={"a": 1})
        assert request.headers is None
