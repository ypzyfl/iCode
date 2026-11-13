# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""View complete telemetry POST records from the AIxCoding log tab."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from rich.text import Text
from textual import on
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, OptionList, TextArea
from textual.widgets.option_list import Option

from chrys.app.tui.clipboard import copy_text_to_clipboards
from chrys.app.tui.screens.dialogs.base import BaseDialog
from chrys.kernel.aixcoding.diagnostics.telemetry_reports import recent_report_logs, report_logging_enabled

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from chrys.kernel.aixcoding.diagnostics.telemetry_reports import ReportLog


class TelemetryLogButton(Button):
    def __init__(self) -> None:
        super().__init__("Telemetry reports", id="telemetry-report-logs", compact=True)
        self.display = report_logging_enabled()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.app.push_screen(_TelemetryLogDialog())


class _TelemetryLogDialog(BaseDialog[None]):
    BINDINGS: ClassVar[list] = [("escape", "dismiss", "Close")]
    DEFAULT_CSS = """
    _TelemetryLogDialog {
        align: center middle;
    }
    _TelemetryLogDialog > Vertical {
        width: 90%;
        height: 90%;
        border: round $primary;
        background: $surface;
    }
    _TelemetryLogDialog OptionList {
        height: 1fr;
    }
    _TelemetryLogDialog TextArea {
        height: 3fr;
    }
    _TelemetryLogDialog Horizontal {
        height: auto;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._records: tuple[ReportLog, ...] = ()

    def compose(self) -> ComposeResult:
        with Vertical() as pane:
            pane.border_title = "Telemetry reports"
            yield OptionList()
            yield TextArea(read_only=True)
            with Horizontal():
                yield Button("Copy report", id="telemetry-copy-report", disabled=True, compact=True)
                yield Button("Close", id="telemetry-close-reports", compact=True)

    def on_mount(self) -> None:
        self._refresh_reports()
        self.set_interval(1, self._refresh_reports)

    def _refresh_reports(self) -> None:
        records = recent_report_logs()
        options = self.query_one(OptionList)
        if records == self._records and options.option_count:
            return
        selected = options.highlighted_option
        self._records = records
        options.clear_options()
        if not records:
            options.add_option(Option("No telemetry reports yet", disabled=True))
            return
        options.add_options(Option(Text(record.summary), id=str(record.sequence)) for record in records)
        options.highlighted = next(
            (
                index
                for index, record in enumerate(records)
                if selected is not None and str(record.sequence) == selected.id
            ),
            0,
        )

    @on(OptionList.OptionSelected)
    def _show_report(self, event: OptionList.OptionSelected) -> None:
        record = next((record for record in self._records if str(record.sequence) == event.option_id), None)
        if record is not None:
            self.query_one(TextArea).load_text(record.pretty_json())
            self.query_one("#telemetry-copy-report", Button).disabled = False

    @on(Button.Pressed, "#telemetry-copy-report")
    def _copy_report(self) -> None:
        copy_text_to_clipboards(self.app, self.query_one(TextArea).text)

    @on(Button.Pressed, "#telemetry-close-reports")
    def _close(self) -> None:
        self.dismiss()
