# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Focus-field tests (registration table §3.1; M4): per-field
construction and redaction — relative path / no drive letter,
512/64KB truncations — plus the HTTP-sink focus_fields_enabled gate
(implementation ahead of the D1 sign-off, remote payload excluded,
file sink observes locally)."""

from __future__ import annotations

import json
from typing import Any

from chrys.aixcoding.telemetry.collector.analysis.context import EventCommonContext, build_event_common
from chrys.aixcoding.telemetry.collector.analysis.focus_fields import (
    MAX_FUNC_ERROR_MESSAGE_CHARS,
    MAX_SNIPPET_CHARS,
    clip_snippet,
    derive_func_error_message,
    derive_mcp_uri,
    derive_save_focus_fields,
    relativize_tool_path,
)
from chrys.aixcoding.telemetry.collector.analysis.git_context import GitRepositoryInfo


def call(name: str, arguments: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "type": "function_call",
        "call_id": "c1",
        "name": name,
        "arguments": json.dumps(arguments),
        "additional_properties": {"_chrys_tool_context": context} if context is not None else {},
    }


class TestRelativizeToolPath:
    def test_relative_input_unifies_separators(self) -> None:
        assert relativize_tool_path("src\\main.py", None, None) == "src/main.py"

    def test_absolute_relativizes_against_git_root(self) -> None:
        assert relativize_tool_path("D:\\repo\\src\\main.py", "D:/repo", None) == "src/main.py"

    def test_absolute_relativizes_against_primary_cwd_without_git(self) -> None:
        assert relativize_tool_path("D:\\repo\\src\\main.py", None, "D:\\repo") == "src/main.py"

    def test_git_root_takes_precedence(self) -> None:
        assert relativize_tool_path("/home/u/work/repo/a.ts", "/home/u/work/repo", "/home/u") == "a.ts"

    def test_posix_absolute_outside_bases_never_keeps_leading_slash(self) -> None:
        relative = relativize_tool_path("/home/u/other/a.ts", "/home/u/work/repo", None)
        assert relative is not None
        assert not relative.startswith("/")
        assert ":\\" not in relative

    def test_windows_drive_outside_base_drops_drive_segment(self) -> None:
        relative = relativize_tool_path("E:\\elsewhere\\a.ts", "D:/repo", None)
        assert relative is not None
        assert not _has_drive_prefix(relative)
        assert relative == "elsewhere/a.ts"

    def test_case_insensitive_prefix_match(self) -> None:
        assert relativize_tool_path("d:\\REPO\\src\\a.ts", "D:\\Repo", None) == "src/a.ts"


def _has_drive_prefix(value: str) -> bool:
    return len(value) >= 2 and value[1] == ":"


class TestDeriveSaveFocusFields:
    def test_read_file_yields_value_and_file_name(self) -> None:
        fields = derive_save_focus_fields(call("read_file", {"path": "D:\\repo\\src\\a.ts"}), "D:/repo", None)
        assert fields["value"] == "src/a.ts"
        assert fields["fileName"] == "src/a.ts"
        for field in ("value", "fileName"):
            assert not fields[field].startswith("/")
            assert not _has_drive_prefix(fields[field])

    def test_view_image_yields_value_and_file_name(self) -> None:
        fields = derive_save_focus_fields(call("view_image", {"path": "img/logo.png"}), None, None)
        assert fields == {"value": "img/logo.png", "fileName": "img/logo.png"}

    def test_write_tools_carry_no_value_or_file_name(self) -> None:
        fields = derive_save_focus_fields(call("write_file", {"path": "src/a.ts", "content": "x"}), None, None)
        assert "value" not in fields
        assert "fileName" not in fields

    def test_skill_tool_value_prefers_context_skill_name(self) -> None:
        fields = derive_save_focus_fields(
            call("load_skill", {"skill_name": "MySkill raw"}, {"skill_name": "my-skill", "skill_revision": "1"}),
            None,
            None,
        )
        assert fields == {"value": "my-skill"}

    def test_skill_tool_value_falls_back_to_argument(self) -> None:
        fields = derive_save_focus_fields(call("read_skill_resource", {"skill_name": "my-skill"}), None, None)
        assert fields == {"value": "my-skill"}

    def test_mcp_uri_stitches_server_and_remote_name(self) -> None:
        fields = derive_save_focus_fields(
            call("fetch_page", {"url": "https://x"}, {"server_name": "docs", "remote_name": "fetch_page"}),
            None,
            None,
        )
        assert fields == {"extra": {"mcpUri": "mcp://docs/fetch_page"}}

    def test_mcp_uri_falls_back_to_normalized_name(self) -> None:
        fields = derive_save_focus_fields(
            call("prefixed_tool", {}, {"server_name": "docs", "normalized_name": "tool"}),
            None,
            None,
        )
        assert fields == {"extra": {"mcpUri": "mcp://docs/tool"}}

    def test_malformed_arguments_only_affect_focus_fields(self) -> None:
        broken = call("read_file", {})
        broken["arguments"] = '{"path": "src/a.ts'
        fields = derive_save_focus_fields(broken, None, None)
        assert fields == {}


class TestDeriveMcpUri:
    def test_missing_context_yields_none(self) -> None:
        assert derive_mcp_uri(call("fetch_page", {})) is None

    def test_missing_server_yields_none(self) -> None:
        assert derive_mcp_uri(call("fetch_page", {}, {"remote_name": "fetch_page"})) is None

    def test_missing_tool_yields_none(self) -> None:
        assert derive_mcp_uri(call("fetch_page", {}, {"server_name": "docs"})) is None


class TestDeriveFuncErrorMessage:
    def result(self, metadata: dict[str, Any] | None = None, exception: str | None = None) -> dict[str, Any]:
        result: dict[str, Any] = {
            "type": "function_result",
            "call_id": "c1",
            "result": "Error: boom",
            "additional_properties": {},
        }
        if metadata is not None:
            result["additional_properties"]["_chrys_tool_result_metadata"] = metadata
        if exception is not None:
            result["exception"] = exception
        return result

    def test_structured_message_wins(self) -> None:
        message = derive_func_error_message(self.result({"failed": True, "tool_error_message": "boom"}))
        assert message == "boom"

    def test_exception_field_is_the_fallback(self) -> None:
        assert derive_func_error_message(self.result({"failed": True}, exception="Traceback")) == "Traceback"

    def test_truncates_to_512(self) -> None:
        message = derive_func_error_message(self.result({"tool_error_message": "x" * 600}))
        assert message == "x" * MAX_FUNC_ERROR_MESSAGE_CHARS

    def test_no_error_source_yields_none(self) -> None:
        assert derive_func_error_message(self.result()) is None


class TestClipSnippet:
    def test_truncates_to_64k_chars(self) -> None:
        assert len(clip_snippet("x" * (MAX_SNIPPET_CHARS + 10))) == MAX_SNIPPET_CHARS

    def test_short_text_is_untouched(self) -> None:
        assert clip_snippet("short") == "short"


class TestGitRemoteCommonField:
    def test_git_remote_enters_event_common(self) -> None:
        git = GitRepositoryInfo(
            remote_url="https://cnb.example.com/team/proj",
            revision="rev-1",
            branch="main",
            user_name="dev",
            user_email="dev@example.com",
            owner="team",
            repo="proj",
        )
        common = build_event_common(
            EventCommonContext(
                session_id="session-1",
                attribution=None,
                product_name="proj",
                project_name="proj",
                plugin_version="0.28.0",
                primary_cwd=None,
                git=git,
            ),
            "turn_1",
        )
        assert common["gitRemote"] == "https://cnb.example.com/team/proj"

    def test_no_git_omits_git_remote(self) -> None:
        common = build_event_common(
            EventCommonContext(
                session_id="session-1",
                attribution=None,
                product_name="proj",
                project_name="proj",
                plugin_version="0.28.0",
                primary_cwd=None,
                git=None,
            ),
            "turn_1",
        )
        assert "gitRemote" not in common
