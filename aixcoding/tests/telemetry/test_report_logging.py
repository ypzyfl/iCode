# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Compare diagnostics with the wire and exercise the real F6 tab."""

from __future__ import annotations

import json
import logging
from logging.handlers import BufferingHandler
from pathlib import Path

import httpx
import pytest
from textual.app import App
from textual.widgets import OptionList, TabbedContent, TextArea

from chrys.app.tui.i18n import LocaleController
from chrys.app.tui.screens.logs.screen import LogViewerScreen
from chrys.app.tui.theme import TuiVariableDefaultsMixin
from chrys.foundation.config.settings import Settings
from chrys.kernel.aixcoding.diagnostics.config import DiagnosticsConfig, LoggingConfig
from chrys.kernel.aixcoding.diagnostics.logging_support import setup_logging
from chrys.service.aixcoding.telemetry.delivery import TelemetryDelivery
from chrys.service.aixcoding.telemetry.reporters import Report


@pytest.fixture
def detail_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    loggers = [logging.getLogger(name) for name in ("aixcoding", "aixcoding.detail")]
    levels = [logger.level for logger in loggers]
    with monkeypatch.context() as patch:
        for logger in loggers:
            patch.setattr(logger, "handlers", [])
            patch.setattr(logger, "propagate", logger.propagate)
        setup_logging(DiagnosticsConfig(LoggingConfig(logging.INFO, False), None), tmp_path)
        try:
            yield tmp_path / "aixcoding-logs" / "aixcoding.detail.log"
        finally:
            for logger, level in zip(loggers, levels, strict=True):
                for handler in logger.handlers:
                    handler.close()
                logger.setLevel(level)


class _LogApp(TuiVariableDefaultsMixin, App[None]):
    locale_controller = LocaleController(Settings(locale="en"))


class _NetworkStream:
    def get_extra_info(self, name: str) -> tuple[str, int] | None:
        return ("2001:db8::10", 8443) if name == "server_addr" else None


class _ClosingStream(httpx.AsyncByteStream):
    closed = False

    async def __aiter__(self):
        yield b""

    async def aclose(self) -> None:
        self.closed = True

    def get_extra_info(self, name: str) -> tuple[str, int] | None:
        return ("127.0.0.1", 8080) if name == "server_addr" and not self.closed else None


async def test_connection_peer_survives_response_close(monkeypatch: pytest.MonkeyPatch, detail_file: Path) -> None:
    monkeypatch.setenv("AIXCODING_TELEMETRY_LOG_PAYLOAD", "1")
    stream = _ClosingStream()

    async def receive(_transport: httpx.AsyncHTTPTransport, _request: httpx.Request) -> httpx.Response:
        return httpx.Response(204, stream=stream, extensions={"network_stream": stream})

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", receive)
    delivery = TelemetryDelivery("http://telemetry.invalid:8080", token_provider=lambda: None)
    delivery.submit(Report("tool-detail/save", {"requestId": "connection"}))
    await delivery.aclose()
    assert stream.closed
    entry = json.loads(detail_file.read_text(encoding="utf-8").split("telemetry.report: ", 1)[1])
    assert (entry["peer_ip"], entry["peer_port"]) == ("127.0.0.1", 8080)


async def test_file_diagnostics_match_each_outbound_post(monkeypatch: pytest.MonkeyPatch, detail_file: Path) -> None:
    monkeypatch.setenv("AIXCODING_TELEMETRY_LOG_PAYLOAD", "1")
    requests: list[httpx.Request] = []

    def receive(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(204, extensions={"network_stream": _NetworkStream()})
        if len(requests) == 2:
            return httpx.Response(503)
        raise httpx.ConnectError("synthetic failure", request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(receive))
    delivery = TelemetryDelivery(
        "https://telemetry.invalid:8443", token_provider=lambda: "test-header-token", client=client
    )
    delivery.submit(Report("tool-detail/save?source=tui", {"requestId": "r1", "value": {"code": "样例" * 9000}}))
    delivery.submit(Report("tool-detail/update", {"funcId": "f1", "status": 0}))
    delivery.submit_code(Report("ai-code/save", {"blocks": [{"start": 1, "content": "line\n"}]}))
    root = logging.getLogger()
    root_handler = BufferingHandler(100)
    root.addHandler(root_handler)
    try:
        await delivery.aclose()
        assert not any(record.name == "aixcoding.detail.telemetry" for record in root_handler.buffer)
    finally:
        root.removeHandler(root_handler)
        root_handler.close()

    assert (delivery.sent, delivery.failed, delivery.dropped) == (1, 2, 0)
    lines = detail_file.read_text(encoding="utf-8").splitlines()
    entries = [json.loads(line.split("telemetry.report: ", 1)[1]) for line in lines]
    assert [entry["endpoint"] for entry in entries] == ["tool-detail/save", "tool-detail/update", "ai-code/save"]
    assert [entry["status_code"] for entry in entries] == [204, 503, None]
    assert [entry["peer_ip"] for entry in entries] == ["2001:db8::10", None, None]
    assert [entry["peer_port"] for entry in entries] == [8443, None, None]
    assert entries[-1]["error_type"] == "ConnectError"
    assert len(entries) == len(requests) == 3
    for entry, request in zip(entries, requests, strict=True):
        assert entry["method"] == request.method == "POST"
        assert entry["url"] == str(request.url)
        assert entry["payload"] == json.loads(request.content)
        assert entry["duration_ms"] >= 0
        assert request.headers["token"] == "test-header-token"
    assert "test-header-token" not in "\n".join(lines)
    assert not detail_file.with_name("aixcoding.log").exists()


async def test_diagnostics_are_off_by_default(monkeypatch: pytest.MonkeyPatch, detail_file: Path) -> None:
    monkeypatch.delenv("AIXCODING_TELEMETRY_LOG_PAYLOAD", raising=False)
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(204)))
    delivery = TelemetryDelivery("https://telemetry.invalid", token_provider=lambda: None, client=client)
    delivery.submit(Report("tool-detail/save", {"requestId": "off"}))
    await delivery.aclose()
    assert delivery.sent == 1
    assert not detail_file.exists()


async def test_diagnostic_sink_failure_does_not_change_delivery_result(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIXCODING_TELEMETRY_LOG_PAYLOAD", "1")

    def fail(**_record: object) -> None:
        raise OSError("synthetic diagnostic failure")

    monkeypatch.setattr("chrys.service.aixcoding.telemetry.delivery.record_report", fail)
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(204)))
    delivery = TelemetryDelivery("https://telemetry.invalid", token_provider=lambda: None, client=client)
    delivery.submit(Report("tool-detail/save", {"requestId": "delivery"}))
    await delivery.aclose()
    assert (delivery.sent, delivery.failed, delivery.dropped) == (1, 0, 0)
    assert delivery.diagnostic_failures == 1


async def test_f6_copies_full_json_from_a_report_sent_before_opening(
    monkeypatch: pytest.MonkeyPatch, detail_file: Path
) -> None:
    monkeypatch.setenv("AIXCODING_TELEMETRY_LOG_PAYLOAD", "1")
    payload = {"requestId": "full-report", "value": {"text": "[literal]" + "原始内容" * 9000}}
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(204)))
    delivery = TelemetryDelivery("https://telemetry.invalid", token_provider=lambda: None, client=client)
    delivery.submit(Report("tool-detail/save", payload))
    await delivery.aclose()

    app = _LogApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await app.push_screen(LogViewerScreen())
        await pilot.pause()
        app.screen.query_one("#lv-tabs", TabbedContent).active = "lv-tab-aixcoding"
        await pilot.pause()
        assert await pilot.click("#telemetry-report-logs")
        options = app.screen.query_one(OptionList)
        options.highlighted = 0
        options.focus()
        await pilot.press("enter")
        detail = app.screen.query_one(TextArea)
        assert json.loads(detail.text)["payload"] == payload
        assert await pilot.click("#telemetry-copy-report")
        assert app.clipboard == detail.text
