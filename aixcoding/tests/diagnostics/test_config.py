# (tests — asserts are pytest idiom, Chinese prose is the data)
"""Tests for chrys.kernel.aixcoding.diagnostics.config."""

from __future__ import annotations

import logging
from pathlib import Path

from chrys.kernel.aixcoding.diagnostics.config import load_config


def test_defaults_when_file_missing(tmp_path: Path):
    cfg = load_config(tmp_path)
    assert cfg.logging.level == logging.INFO
    assert cfg.logging.panel is False
    assert cfg.source is None


def test_parses_toml_values(tmp_path: Path):
    (tmp_path / "aixcoding.toml").write_text('[logging]\nlevel = "DEBUG"\npanel = true\n', encoding="utf-8")
    cfg = load_config(tmp_path)
    assert cfg.logging.level == logging.DEBUG
    assert cfg.logging.panel is True
    assert cfg.source == tmp_path / "aixcoding.toml"


def test_invalid_toml_falls_back(tmp_path: Path, capsys):
    (tmp_path / "aixcoding.toml").write_text("not [ valid toml", encoding="utf-8")
    cfg = load_config(tmp_path)
    assert cfg.logging.level == logging.INFO
    assert cfg.logging.panel is False
    assert "cannot parse" in capsys.readouterr().err


def test_bad_level_name_falls_back(tmp_path: Path):
    (tmp_path / "aixcoding.toml").write_text('[logging]\nlevel = "NOISY"\n', encoding="utf-8")
    cfg = load_config(tmp_path)
    assert cfg.logging.level == logging.INFO


def test_panel_non_bool_falls_back_to_default(tmp_path: Path):
    (tmp_path / "aixcoding.toml").write_text('[logging]\npanel = "yes"\n', encoding="utf-8")
    cfg = load_config(tmp_path)
    assert cfg.logging.panel is False  # non-bool type → fail-safe default


def test_missing_logging_section_uses_defaults(tmp_path: Path):
    (tmp_path / "aixcoding.toml").write_text("[other]\nx = 1\n", encoding="utf-8")
    cfg = load_config(tmp_path)
    assert cfg.logging.level == logging.INFO
    assert cfg.logging.panel is False
