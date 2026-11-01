# (unit test — asserts are pytest idiom; subprocess seam mocked per test-plan)
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Behavioral tests for the fork-local verification entry (aixcoding/tools/verify.py).

Plan: aixcoding/docs/batches/local-verify/test-plan.md. The single subprocess
seam (``verify._run_process``) is monkeypatched — no real pytest full run or
chrys_test delegation happens here; live end-to-end evidence lives in the
batch's verification.md instead.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from aixcoding.tools import verify


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Scripted ``_run_process``: pops (returncode, last_line) per call, records argvs."""
    holder = SimpleNamespace(argvs=[], results=[])

    def fake_run(args: list[str]) -> tuple[int, str]:
        holder.argvs.append(list(args))
        return holder.results.pop(0)

    monkeypatch.setattr(verify, "_run_process", fake_run)
    return holder


def _custom_args() -> list[str]:
    return [sys.executable, "-m", "pytest", "aixcoding/tests", "-m", verify._EXCLUDED_MARKERS]


def _delegate_args(extra: list[str]) -> list[str]:
    return [sys.executable, verify._UPSTREAM_SELECTOR.as_posix(), *extra]


def _is_custom(args: list[str]) -> bool:
    return args == _custom_args()


def _is_delegate(args: list[str]) -> bool:
    return len(args) >= 2 and Path(args[1]).name == "chrys_test.py"


def _summary(capsys: pytest.CaptureFixture[str]) -> str:
    return capsys.readouterr().out


def test_smart_also_runs_custom_suite(fake: SimpleNamespace) -> None:
    fake.results = [(0, "5 passed in 1s"), (0, "Summary: PASSED (exit 0)")]
    assert verify.main(["--smart"]) == 0
    assert len(fake.argvs) == 2
    assert _is_custom(fake.argvs[0])
    assert _is_delegate(fake.argvs[1])


def test_smart_forwards_paths(fake: SimpleNamespace) -> None:
    fake.results = [(0, "1 passed"), (0, "Summary: PASSED (exit 0)")]
    assert verify.main(["--smart", "--paths", "a.py", "b.py"]) == 0
    assert fake.argvs[1] == _delegate_args(["--smart", "--paths", "a.py", "b.py"])


def test_upstream_smart_skips_custom(fake: SimpleNamespace) -> None:
    fake.results = [(0, "Summary: PASSED (exit 0)")]
    assert verify.main(["--upstream-smart"]) == 0
    assert len(fake.argvs) == 1
    assert _is_delegate(fake.argvs[0])
    assert fake.argvs[0] == _delegate_args(["--smart"])


def test_custom_failure_fails_smart(fake: SimpleNamespace) -> None:
    fake.results = [(1, "1 failed"), (0, "Summary: PASSED (exit 0)")]
    assert verify.main(["--smart"]) == 1


def test_custom_failure_fails_full(fake: SimpleNamespace) -> None:
    fake.results = [(1, "1 failed"), (0, "Summary: PASSED (exit 0)")]
    assert verify.main(["--full"]) == 1


def test_full_runs_both_when_custom_fails(fake: SimpleNamespace) -> None:
    """No short-circuit: the upstream suite still runs after custom fails."""
    fake.results = [(1, "1 failed"), (0, "Summary: PASSED (exit 0)")]
    assert verify.main(["--full"]) == 1
    assert _is_custom(fake.argvs[0])
    assert _is_delegate(fake.argvs[1]) and fake.argvs[1] == _delegate_args(["--full"])


def test_full_runs_both_when_upstream_fails(fake: SimpleNamespace) -> None:
    fake.results = [(0, "324 passed"), (3, "Summary: FAILED (exit 3)")]
    assert verify.main(["--full"]) == 3
    assert _is_custom(fake.argvs[0]) and _is_delegate(fake.argvs[1])


def test_both_red_reports_each_and_first_nonzero(fake: SimpleNamespace, capsys: pytest.CaptureFixture[str]) -> None:
    """Both suites red: both recorded as failed, overall = the FIRST non-zero (custom's).

    Pins the aggregate order — reversing _aggregate's loop would return upstream's
    code here while every single-red test still passes.
    """
    fake.results = [(5, "1 error"), (2, "usage: chrys_test.py ... error")]
    assert verify.main(["--full"]) == 5
    assert _is_custom(fake.argvs[0]) and _is_delegate(fake.argvs[1])
    out = _summary(capsys)
    assert out.count("failed") >= 2  # custom and upstream lines both report failed
    assert "Fork verify Summary: FAILED (exit 5)" in out


def test_summary_lists_each_suite(fake: SimpleNamespace, capsys: pytest.CaptureFixture[str]) -> None:
    fake.results = [(0, "5 passed in 1s"), (1, "Summary: FAILED (exit 1)")]
    assert verify.main(["--smart"]) == 1
    out = _summary(capsys)
    assert "Fork verify Summary: FAILED (exit 1)" in out
    assert "custom" in out and "passed" in out
    assert "upstream" in out and "failed" in out
    assert "5 passed in 1s" in out


def test_delegate_exit2_is_failed_not_skipped(fake: SimpleNamespace, capsys: pytest.CaptureFixture[str]) -> None:
    """An upstream argparse error (exit 2) counts as failed, never skipped/success."""
    fake.results = [(0, "5 passed"), (2, "usage: chrys_test.py ... error: unrecognized arguments")]
    assert verify.main(["--smart"]) == 2
    out = _summary(capsys)
    assert "upstream" in out and "failed" in out
    assert "not run" not in out


def test_custom_exit5_is_failed(fake: SimpleNamespace) -> None:
    """A zero-collection custom suite (pytest exit 5) is a failure, not a pass."""
    fake.results = [(5, "no tests ran"), (0, "Summary: PASSED (exit 0)")]
    assert verify.main(["--smart"]) == 5


def test_no_changes_still_runs_custom(fake: SimpleNamespace) -> None:
    fake.results = [(0, "324 passed, 2 skipped"), (0, "no branch or working-tree changes; no tests were run.")]
    assert verify.main(["--smart"]) == 0
    assert _is_custom(fake.argvs[0])


def test_no_changes_custom_red_fails_whole(fake: SimpleNamespace) -> None:
    """With no upstream changes the overall exit code follows the custom suite."""
    fake.results = [(1, "1 failed"), (0, "no branch or working-tree changes; no tests were run.")]
    assert verify.main(["--smart"]) == 1


def test_spawn_failure_reports_not_run(
    fake: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def boom(args: list[str]) -> tuple[int, str]:
        raise OSError("spawn failed: no such file")

    monkeypatch.setattr(verify, "_run_process", boom)
    assert verify.main(["--custom-full"]) == 2
    out = _summary(capsys)
    assert "not run" in out and "spawn failed" in out


def test_custom_full_single_suite(fake: SimpleNamespace) -> None:
    fake.results = [(0, "324 passed, 2 skipped")]
    assert verify.main(["--custom-full"]) == 0
    assert fake.argvs == [_custom_args()]


def test_upstream_full_single_suite(fake: SimpleNamespace) -> None:
    fake.results = [(0, "Summary: PASSED (exit 0)")]
    assert verify.main(["--upstream-full"]) == 0
    assert fake.argvs == [_delegate_args(["--full"])]


def test_cli_mode_mutex() -> None:
    with pytest.raises(SystemExit) as missing:
        verify.main([])
    assert missing.value.code == 2
    with pytest.raises(SystemExit) as conflicting:
        verify.main(["--smart", "--full"])
    assert conflicting.value.code == 2


def test_paths_rejected_for_full() -> None:
    with pytest.raises(SystemExit) as exc:
        verify.main(["--full", "--paths", "x.py"])
    assert exc.value.code == 2
