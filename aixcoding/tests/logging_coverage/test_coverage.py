# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

# (test fixture — asserts are pytest idiom, Chinese prose is the data)
"""Coverage tests: every customized module logs onto the aixcoding tree.

Design: aixcoding/docs/batches/logging-coverage/design.md (signed off
2026-11-19). Assertions pin the channel by logger name with spy handlers
attached to the target loggers directly (no dependence on the tree's
propagate state other tests may leave behind); the main-channel messages are
asserted verbatim, which doubles as the PII sentinel (technical detail --
URLs, exception chains -- must live on the detail volume only).
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from chrys.app.aixcoding.startup import aixcoding_startup
from chrys.app.aixcoding.update import runner as runner_module
from chrys.kernel.aixcoding.diagnostics.logging_support import DETAIL_LEVEL
from chrys.service.aixcoding.config.loader import load_config
from chrys.service.aixcoding.skill_paths import (
    cwd_aixcoding_skill_paths,
    user_aixcoding_skill_paths,
)
from chrys.service.aixcoding.update import client as client_module
from chrys.service.aixcoding.update.client import check_for_update

CHECK_FAILURE = "自动更新检查失败，本次跳过。"

_SOURCES_WITHOUT_DUNDER_NAME = (
    "src/chrys/service/aixcoding/update/client.py",
    "src/chrys/service/aixcoding/update/state.py",
    "src/chrys/app/aixcoding/update/flow.py",
    "src/chrys/app/aixcoding/update/runner.py",
)


@contextmanager
def _spy(logger_name: str) -> Iterator[list[logging.LogRecord]]:
    """Attach a capturing handler directly on the named logger."""
    logger = logging.getLogger(logger_name)
    records: list[logging.LogRecord] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    handler = _Capture()
    handler.setLevel(logging.NOTSET)
    logger.addHandler(handler)
    try:
        yield records
    finally:
        logger.removeHandler(handler)


@pytest.fixture
def detail_spy() -> Iterator[list[logging.LogRecord]]:
    """Capture every record on the file-only detail subtree (ADR-0017)."""
    detail = logging.getLogger("aixcoding.detail")
    saved_level = detail.level
    logging.addLevelName(DETAIL_LEVEL, "DETAIL")  # normally done by setup_logging
    with _spy("aixcoding.detail") as records:
        detail.setLevel(DETAIL_LEVEL)
        yield records
    detail.setLevel(saved_level)


def _warn_records(records: list[logging.LogRecord]) -> list[logging.LogRecord]:
    return [r for r in records if r.levelno >= logging.WARNING]


def _info_records(records: list[logging.LogRecord]) -> list[logging.LogRecord]:
    return [r for r in records if r.levelno == logging.INFO]


# ---------------------------------------------------------------- static


def test_no_dunder_name_loggers() -> None:
    """Acceptance 1: the four update files carry no getLogger(__name__) sites."""
    repo_root = Path(__file__).resolve().parents[3]
    for rel in _SOURCES_WITHOUT_DUNDER_NAME:
        source = (repo_root / rel).read_text(encoding="utf-8")
        assert "getLogger(__name__)" not in source, rel


# ---------------------------------------------------------------- update client


def _point_at_local(monkeypatch: pytest.MonkeyPatch, base_url: str = "http://127.0.0.1:9") -> None:
    cfg = SimpleNamespace(environment="local", update=SimpleNamespace(base_url=base_url))
    monkeypatch.setattr(client_module, "load_config", lambda: cfg)


async def _check_with_transport(monkeypatch: pytest.MonkeyPatch, transport: httpx.MockTransport) -> None:
    _point_at_local(monkeypatch)
    await check_for_update(current_version="0.35.1", transport=transport)


@pytest.mark.parametrize(
    "handler",
    [
        pytest.param(lambda request: httpx.Response(500, text="boom"), id="unexpected-status"),
        pytest.param(lambda request: (_ for _ in ()).throw(httpx.ConnectTimeout("timed out")), id="timeout"),
        pytest.param(lambda request: (_ for _ in ()).throw(httpx.ConnectError("refused")), id="network-error"),
        pytest.param(lambda request: httpx.Response(200, json={"no": "manifest"}), id="bad-manifest"),
        pytest.param(lambda request: httpx.Response(200, text="not-json-at-all"), id="unparseable-body"),
    ],
)
async def test_check_failure_branches_warn_main_volume(
    monkeypatch: pytest.MonkeyPatch, detail_spy: list[logging.LogRecord], handler: Any
) -> None:
    """Acceptance 2c: every failure branch lands the fixed public WARNING (double write).

    The verbatim message assertion doubles as the PII sentinel: the failure
    reason (URL, exception) must stay on the detail volume only.
    """
    with _spy("aixcoding.update") as public:
        await _check_with_transport(monkeypatch, httpx.MockTransport(handler))

    warnings = _warn_records(public)
    assert [r.getMessage() for r in warnings] == [CHECK_FAILURE]
    detail_messages = [r.getMessage() for r in detail_spy]
    assert CHECK_FAILURE in detail_messages, "the user-facing event double-writes onto detail"
    assert len(detail_messages) >= 2, "the technical reason is detail-only"


async def test_check_no_update_204_stays_silent(
    monkeypatch: pytest.MonkeyPatch, detail_spy: list[logging.LogRecord]
) -> None:
    """Acceptance 2d guard: 204/304 mean 'no update', not a failure -- zero records."""
    with _spy("aixcoding.update") as public:
        await _check_with_transport(monkeypatch, httpx.MockTransport(lambda request: httpx.Response(204)))

    assert _warn_records(public) == []
    assert all(CHECK_FAILURE not in r.getMessage() for r in detail_spy)


async def test_check_unbuildable_params_detail_only(
    monkeypatch: pytest.MonkeyPatch, detail_spy: list[logging.LogRecord]
) -> None:
    """An unbuildable query is 'this machine is outside the contract', not a failure."""
    _point_at_local(monkeypatch)
    with _spy("aixcoding.update") as public:
        found = await check_for_update(current_version="not-a-semver")

    assert found is None
    assert _warn_records(public) == []
    assert any("不可构造" in r.getMessage() for r in detail_spy)


# ---------------------------------------------------------------- update runner


def test_wrapper_start_failure_error_double_write(
    monkeypatch: pytest.MonkeyPatch, detail_spy: list[logging.LogRecord], tmp_path: Path
) -> None:
    """Acceptance 2a: the user chose 'update now' and nothing started -- public ERROR."""
    monkeypatch.setattr(runner_module, "build_wrapper", lambda *a, **k: ["stub-argv"])
    monkeypatch.setattr(runner_module, "spawn_wrapper", lambda argv: (_ for _ in ()).throw(OSError("nope")))
    exited: list[bool] = []

    with _spy("aixcoding.update") as public:
        started = runner_module.start_update_and_exit("s", tmp_path, exited.append)

    assert started is False and exited == []
    errors = [r for r in public if r.levelno == logging.ERROR]
    assert [r.getMessage() for r in errors] == ["自动更新启动失败：更新助手未能启动，本次不会退出程序。"]
    assert any("自动更新启动失败" in r.getMessage() for r in detail_spy)


# ---------------------------------------------------------------- skills


def _skills_config(*, user: bool = True, cwd: bool = True) -> Any:
    return SimpleNamespace(auto_load_aixcoding_user_skills=user, auto_load_aixcoding_cwd_skills=cwd)


def test_skills_success_detail_only(
    monkeypatch: pytest.MonkeyPatch, detail_spy: list[logging.LogRecord], tmp_path: Path
) -> None:
    """Acceptance 3: the registered roots are a detail trace; the main channel stays empty."""
    monkeypatch.setattr("chrys.service.aixcoding.skill_paths.user_aixcoding_dir", lambda: tmp_path / ".aixcoding")
    runtime = SimpleNamespace(cwd=str(tmp_path / "ws"))

    with _spy("aixcoding.skills") as public:
        cwd_paths = cwd_aixcoding_skill_paths(_skills_config(), runtime)
        user_paths = user_aixcoding_skill_paths(_skills_config())

    assert cwd_paths and user_paths
    assert public == [], "skills loading is a background trace -- never user-facing"
    detail_text = " ".join(r.getMessage() for r in detail_spy)
    assert "已登记 aixcoding 技能根目录（工作区）" in detail_text
    assert "已登记 aixcoding 技能根目录（用户）" in detail_text


def test_skills_exception_detail_and_reraise(
    monkeypatch: pytest.MonkeyPatch, detail_spy: list[logging.LogRecord]
) -> None:
    """Acceptance 3: the function-level failure logs detail, then re-raises unchanged
    (the upstream adapter's swallow semantics must not move)."""
    monkeypatch.setattr(
        "chrys.service.aixcoding.skill_paths.user_aixcoding_dir",
        lambda: (_ for _ in ()).throw(RuntimeError("platform gone")),
    )

    with pytest.raises(RuntimeError, match="platform gone"):
        user_aixcoding_skill_paths(_skills_config())

    assert any("读取 aixcoding 技能根目录（用户）失败" in r.getMessage() for r in detail_spy)


def test_skills_team_filenotfound_silent(
    monkeypatch: pytest.MonkeyPatch, detail_spy: list[logging.LogRecord], tmp_path: Path
) -> None:
    """A missing team-skills container is the common case -- not an event."""
    monkeypatch.setattr("chrys.service.aixcoding.skill_paths.user_aixcoding_dir", lambda: tmp_path / ".aixcoding")
    (tmp_path / ".aixcoding").mkdir()
    # skills/ and market-skills/ need not exist either: only the paths are registered.

    user_aixcoding_skill_paths(_skills_config())

    assert not any("枚举失败" in r.getMessage() for r in detail_spy)


def test_skills_team_permission_error_logged_detail(
    monkeypatch: pytest.MonkeyPatch, detail_spy: list[logging.LogRecord], tmp_path: Path
) -> None:
    """PR #141 review C2: a readable-but-denied container logs the detail trace."""
    monkeypatch.setattr("chrys.service.aixcoding.skill_paths.user_aixcoding_dir", lambda: tmp_path / ".aixcoding")
    (tmp_path / ".aixcoding").mkdir()
    (tmp_path / ".aixcoding" / "team-skills").mkdir()

    def _denied(container: object) -> object:
        raise PermissionError(f"[Errno 13] Permission denied: '{tmp_path}'")

    monkeypatch.setattr("chrys.service.aixcoding.skill_paths.os.scandir", _denied)

    user_aixcoding_skill_paths(_skills_config())

    assert any("团队技能目录枚举失败" in r.getMessage() for r in detail_spy)


# ---------------------------------------------------------------- guard install


def _asset_dir() -> Path:
    from chrys.kernel.aixcoding.guard.guard_install import resolve_asset_dir

    return resolve_asset_dir()


def test_guard_fresh_install_and_merge_detail_only(detail_spy: list[logging.LogRecord], tmp_path: Path) -> None:
    """Acceptance 4: the guard's own state (install/update/idempotence) is detail-only."""
    from chrys.kernel.aixcoding.guard.guard_install import install_guard_hooks

    hooks_dir = tmp_path / "hooks"
    with _spy("aixcoding.guard") as public:
        install_guard_hooks(hooks_dir=hooks_dir, asset_dir=_asset_dir())  # fresh
        install_guard_hooks(hooks_dir=hooks_dir, asset_dir=_asset_dir())  # idempotent re-run

    assert public == [], "the guard's own state never reaches the main channel"
    detail_text = " ".join(r.getMessage() for r in detail_spy)
    assert "首次安装安全护栏" in detail_text
    assert "安全护栏已就绪" in detail_text


def test_guard_unparsable_reset_warns_main_volume(detail_spy: list[logging.LogRecord], tmp_path: Path) -> None:
    """Acceptance 4 exception: overwriting a user-authored hooks file is a public WARNING."""
    from chrys.kernel.aixcoding.guard.guard_install import install_guard_hooks

    hooks_dir = tmp_path / "hooks"
    hooks_dir.mkdir()
    (hooks_dir / "hooks.yaml").write_text(":\n  not [ valid yaml", encoding="utf-8")

    with _spy("aixcoding.guard") as public:
        install_guard_hooks(hooks_dir=hooks_dir, asset_dir=_asset_dir())

    warnings = _warn_records(public)
    assert len(warnings) == 1
    message = warnings[0].getMessage()
    assert "检测到无法解析的 hooks 配置" in message
    assert "hooks.yaml.pre-guard" in message, "the public warning names the backup for self-service recovery"
    assert not _looks_like_path(message), "the public message carries no absolute path / username (review F1)"
    backup_file = hooks_dir / "hooks.yaml.pre-guard"
    assert backup_file.is_file()
    detail_text = " ".join(r.getMessage() for r in detail_spy)
    assert "检测到无法解析的 hooks 配置" in detail_text, "double write"
    assert str(backup_file) in detail_text, "the absolute backup path stays detail-only"


def _looks_like_path(message: str) -> bool:
    """Heuristic PII sentinel: drive letters, /Users/, /home/ (review F1)."""
    import re

    return bool(re.search(r"[A-Za-z]:[\\/]|/Users/|/home/", message))


def test_main_channel_pii_sentinel(
    monkeypatch: pytest.MonkeyPatch, detail_spy: list[logging.LogRecord], tmp_path: Path
) -> None:
    """Acceptance 7: variable fields must not leak paths/usernames into the main volume."""
    from chrys.kernel.aixcoding.guard.guard_install import install_guard_hooks

    hooks_dir = tmp_path / "hooks"
    hooks_dir.mkdir()
    (hooks_dir / "hooks.yaml").write_text(":\n  not [ valid yaml", encoding="utf-8")

    (tmp_path / "aixcoding.toml").write_text('environment = "staging"\n', encoding="utf-8")
    load_config.cache_clear()

    public_messages: list[str] = []
    with _spy("aixcoding.guard") as guard_public, _spy("aixcoding.config") as config_public:
        install_guard_hooks(hooks_dir=hooks_dir, asset_dir=_asset_dir())
        load_config(config_dir=tmp_path)
        public_messages.extend(r.getMessage() for r in _warn_records(guard_public))
        public_messages.extend(r.getMessage() for r in _warn_records(config_public))

    assert len(public_messages) == 2
    assert all(not _looks_like_path(m) for m in public_messages)
    assert all("环境配置无效" in m or "hooks" in m for m in public_messages), "both events fired"


def test_guard_missing_assets_detail_only(detail_spy: list[logging.LogRecord], tmp_path: Path) -> None:
    """A broken build ships no rule pack: detail trace + the existing raise contract."""
    from chrys.kernel.aixcoding.guard.guard_install import install_guard_hooks

    empty_assets = tmp_path / "assets"
    empty_assets.mkdir()
    with _spy("aixcoding.guard") as public, pytest.raises(FileNotFoundError):
        install_guard_hooks(hooks_dir=tmp_path / "hooks", asset_dir=empty_assets)

    assert public == []
    assert any("资源缺失" in r.getMessage() for r in detail_spy)


# ---------------------------------------------------------------- config loader


@pytest.fixture(autouse=True)
def _fresh_config_cache() -> Iterator[None]:
    load_config.cache_clear()
    yield
    load_config.cache_clear()


@pytest.fixture(autouse=True)
def _clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AIXCODING_ENVIRONMENT", raising=False)


_CONFIG_CASES = {
    "environment-non-string": "environment = 123",
    "environment-invalid-value": 'environment = "staging"',
    "model-catalog-section": 'model_catalog = "not-a-table"',
    "model-catalog-base-url": "[model_catalog]\nbase_url = 123",
    "model-catalog-auto-sync": '[model_catalog]\nauto_sync = "yes"',
    "update-section": "update = 7",
    "update-base-url": "[update]\nbase_url = []",
    "cannot-parse": "this is [ not valid toml",
}


@pytest.mark.parametrize("body", _CONFIG_CASES.values(), ids=_CONFIG_CASES.keys())
def test_config_warn_triple_channel(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    detail_spy: list[logging.LogRecord],
    tmp_path: Path,
    body: str,
) -> None:
    """Acceptance 6: every _warn call site keeps stderr and double-writes (Chinese)."""
    (tmp_path / "aixcoding.toml").write_text(body, encoding="utf-8")

    with _spy("aixcoding.config") as public:
        load_config(config_dir=tmp_path)

    warnings = _warn_records(public)
    assert len(warnings) == 1, "exactly one Chinese warning per call site"
    message = warnings[0].getMessage()
    assert message and any(ord(ch) > 0x2E7F for ch in message), "the main channel speaks Chinese"
    assert any(r.getMessage() == message for r in detail_spy), "same message double-writes onto detail"
    assert "aixcoding.config:" in capsys.readouterr().err, "stderr stays the early-channel"


def test_config_dir_unavailable_triple_channel(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    detail_spy: list[logging.LogRecord],
) -> None:
    """The ninth call site: the platform config_dir itself is unavailable."""
    import chrys.foundation.platform as platform_module

    monkeypatch.setattr(platform_module, "get_platform", lambda: (_ for _ in ()).throw(RuntimeError("no platform")))

    with _spy("aixcoding.config") as public:
        load_config()

    assert [r.getMessage() for r in _warn_records(public)] == ["无法确定配置目录，改用 ~/.chrys。"]
    assert any(r.getMessage() == "无法确定配置目录，改用 ~/.chrys。" for r in detail_spy)
    assert "aixcoding.config:" in capsys.readouterr().err


def test_config_oserror_message_carries_no_path(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    detail_spy: list[logging.LogRecord],
    tmp_path: Path,
) -> None:
    """PR #141 review C1: an OSError's path-bearing str never reaches the channels."""

    def _denied(*_args: object, **_kwargs: object) -> str:
        raise PermissionError(f"[Errno 13] Permission denied: '{tmp_path}\\aixcoding.toml'")

    monkeypatch.setattr(Path, "read_text", _denied)

    with _spy("aixcoding.config") as public:
        load_config(config_dir=tmp_path)

    warnings = _warn_records(public)
    assert [r.getMessage() for r in warnings] == [
        "\u914d\u7f6e\u6587\u4ef6\u65e0\u6cd5\u8bfb\u53d6\uff0c\u5df2\u56de\u9000\u5168\u90e8\u9ed8\u8ba4\u3002"
    ]
    assert all(
        not _looks_like_path(r.getMessage())
        for r in detail_spy
        if "\u914d\u7f6e\u6587\u4ef6\u65e0\u6cd5\u8bfb\u53d6" in r.getMessage()
    )
    assert "\u914d\u7f6e\u6587\u4ef6\u65e0\u6cd5\u8bfb\u53d6" in capsys.readouterr().err


# ---------------------------------------------------------------- startup


def test_startup_task_failure_triple_channel(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    detail_spy: list[logging.LogRecord],
) -> None:
    """Acceptance 6: a failed startup task keeps stderr and double-writes (Chinese).

    PR #141 review C1: the exception carries a path-bearing str -- the channels
    must show the exception NAME only, with the traceback detail-only.
    """

    def _boom() -> None:
        raise PermissionError("[Errno 13] Permission denied: 'C:\\Users\\victim\\chrys\\aixcoding-logs'")

    import chrys.app.aixcoding.startup as startup_module

    monkeypatch.setattr(startup_module, "_TASKS", (_boom,))

    with _spy("aixcoding.startup") as public:
        aixcoding_startup()

    warnings = _warn_records(public)
    assert len(warnings) == 1
    message = warnings[0].getMessage()
    assert "启动任务 _boom 失败（PermissionError）" in message
    assert not _looks_like_path(message), "the exception name only -- never its path-bearing str"
    detail_records = [r for r in detail_spy if "启动任务 _boom 失败" in r.getMessage()]
    assert detail_records and all(not _looks_like_path(r.getMessage()) for r in detail_records)
    assert all(r.exc_info for r in detail_records), "the full traceback rides detail's exc_info"
    assert "aixcoding.startup:" in capsys.readouterr().err
