# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Verify enterprise code reports from real file-tool runs."""

from __future__ import annotations

import asyncio
import json

import pytest

from chrys.foundation.events.types import UserMessage
from chrys.service.aixcoding.telemetry.reporters import ToolStart, code_save, tool_finished


@pytest.mark.parametrize("case", ["empty-create", "delete-only", "64-blocks", "65-blocks", "binary"])
async def test_file_boundaries_on_the_wire(tmp_path, telemetry_engine, telemetry_provider, telemetry_capture, case):
    path = tmp_path / "sample.py"
    arguments = {"path": str(path)}
    name = "edit_file"
    expected_blocks = []
    expected_counts = None
    if case == "empty-create":
        name = "write_file"
        arguments["content"] = ""
        final = b""
        expected_counts = (0, 0, 0)
    elif case == "delete-only":
        path.write_bytes(b"keep\ndrop\n")
        arguments.update(old_string="drop\n", new_string="")
        final = b"keep\n"
        expected_counts = (2, 0, 1)
    elif case == "binary":
        final = b"\x00\xff\x00\x01"
        path.write_bytes(final)
        arguments.update(old_string="old", new_string="new")
    else:
        count = int(case.split("-", 1)[0])
        path.write_bytes(b"old\nkeep\n" * count)
        arguments.update(old_string="old", new_string="new", replace_all=True)
        final = b"new\nkeep\n" * count
        expected_counts = (2 * count, count, count)
        expected_blocks = (
            [{"snippet": "new", "rangeStart": line, "rangeEnd": line} for line in range(1, 2 * count, 2)]
            if count == 64
            else [{"snippet": final.decode(), "rangeStart": 1, "rangeEnd": 130}]
        )

    telemetry_provider.call("boundary-call", name, arguments)
    engine = telemetry_engine.build()
    try:
        await engine.start(telemetry_engine.profile, workspace=telemetry_engine.workspace)
        await engine.event_bus.publish(UserMessage(text="Run the file tool."), raise_handler_errors=True)
        await asyncio.wait_for(engine.wait_for_run_task(), 10)
    finally:
        await engine.shutdown()

    assert path.read_bytes() == final
    requests = telemetry_capture.requests
    endpoints = [request.url.path.split("/api/v1/")[1] for request in requests]
    expected_endpoints = ["tool-detail/save", "tool-detail/update", "tool-detail/update"]
    assert endpoints == expected_endpoints + (["ai-code/save"] if expected_blocks else [])
    save, pending, terminal, *code = [json.loads(request.content) for request in requests]
    assert save["funcId"] == pending["funcId"] == terminal["funcId"] == "boundary-call"
    assert save["fileName"] == "sample.py"
    assert pending["codeStatus"] == 3
    fields = ("originalLines", "addedLines", "deletedLines")
    if expected_counts is None:
        assert terminal["codeStatus"] == 2 and terminal["status"] == 0
        assert "binary" in terminal["funcErrorMessage"]
        # The mutation pipeline records a decoded snapshot even for the rejected edit.
        assert tuple(terminal[key] for key in fields) == (1, 0, 0)
    else:
        assert terminal["codeStatus"] == 1 and terminal["status"] == 1
        assert tuple(terminal[key] for key in fields) == expected_counts
    if expected_blocks:
        (generated,) = code
        assert generated["blocks"] == expected_blocks
        assert generated["filepath"] == "sample.py"
        assert generated["codeStatus"] == 1
        assert generated["requestId"] == save["requestId"]


def test_raw_binary_snapshots_omit_text_line_counts_and_code() -> None:
    tool = ToolStart("session", "binary", "write_file", "filesystem.write", {"path": "sample.bin"})
    metadata = {"file_snapshot": (b"\x00before", b"\x00after"), "file_mutation_op": "modify"}
    terminal = tool_finished(tool, metadata, duration_ms=0)
    assert terminal.payload["codeStatus"] == 1
    assert not {"originalLines", "addedLines", "deletedLines"}.intersection(terminal.payload)
    assert code_save(tool, metadata, common={}) is None
