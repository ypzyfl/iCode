# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Run CD's actual version, filename and asset collection scripts together."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]


def _run(script: str, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["bash", "-eo", "pipefail", "-c", script],
        cwd=cwd,
        env={**os.environ, **env},
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result


@pytest.mark.parametrize(
    ("mode", "version", "ref", "release_tag", "expected_version"),
    [
        ("update-release", "0.35.2", "main_aixcoding_cli_0.35.2", "v0.35.2", "0.35.2"),
        ("create-release", "0.36.0", "main_aixcoding_cli_0.36.0", "v0.36.0", "0.36.0"),
        ("update-release", "1.2.3", "main_aixcoding_cli_1.2.3_final", "v1.2.3", "1.2.3"),
        ("test", "0.35.2", "main_aixcoding_cli_0.35.2", "", "0.35.2-dev-e69d83a"),
        ("test", "0.35.2", "", "", "0.35.2-dev-e69d83a"),
        ("upstream-tag", "0.35.2", "v0.35.2", "v0.35.2", "0.35.2"),
    ],
)
def test_binary_versions_match_collected_release_assets(tmp_path, mode, version, ref, release_tag, expected_version):
    workflow = yaml.load((REPO_ROOT / ".github/workflows/cd.yml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    jobs = workflow["jobs"]
    steps = {step.get("name"): step for step in jobs["build-binaries"]["steps"]}
    assert steps["Determine version"]["env"]["RELEASE_TAG"] == "${{ needs.resolve-build.outputs.tag }}"
    environment_file = tmp_path / "environment"
    output_file = tmp_path / "outputs"
    wheel_name = f"icode_tui-{version}-py3-none-any.whl"
    wheel = tmp_path / "wheel"
    wheel.mkdir()
    (wheel / wheel_name).write_bytes(b"fixture wheel")
    env = {
        "GITHUB_ENV": str(environment_file),
        "GITHUB_OUTPUT": str(output_file),
        "GITHUB_REF": f"refs/tags/{ref}" if mode == "upstream-tag" else "refs/heads/version-branch",
        "GITHUB_REF_NAME": ref if mode == "upstream-tag" else "version-branch",
        "GITHUB_SHA": "e69d83ab005b342bd80054f7d1a195fa09d4fed4",
        "RELEASE_TAG": release_tag,
    }
    script = steps["Determine version"]["run"].replace("${{ inputs.ref || '' }}", ref)
    _run(script, tmp_path, env)
    actual = dict(line.split("=", 1) for line in environment_file.read_text(encoding="utf-8").splitlines())
    assert actual["PROJECT_VERSION"] == expected_version
    env.update(actual)

    artifacts = tmp_path / "artifacts"
    wheel_artifact = artifacts / "wheel"
    wheel_artifact.mkdir(parents=True)
    (wheel_artifact / wheel_name).write_bytes(b"fixture wheel")
    expected_assets = {wheel_name, "SHA256SUMS.txt"}
    for system in ("linux", "macos", "windows"):
        for arch in ("x86_64", "aarch64"):
            base = f"aixcoding-cli-{system}-{arch}"
            if system == "windows":
                base += ".exe"
            script = steps["Determine binary and artifact names"]["run"]
            script = script.replace("${{ matrix.artifact }}", base).replace("${{ matrix.installer }}", "offline")
            output_file.write_text("", encoding="utf-8")
            _run(script, tmp_path, env)
            names = dict(line.split("=", 1) for line in output_file.read_text(encoding="utf-8").splitlines())
            artifact = artifacts / names["artifact"]
            artifact.mkdir()
            (artifact / names["binary"]).write_bytes(b"fixture binary")
            extension = "zip" if system == "windows" else "tar.gz"
            expected_assets.add(f"aixcoding-cli-{system}-{arch}-v{expected_version}-offline.{extension}")

    if mode == "test":
        assert not release_tag
        assert "-dev-" in expected_version
        return

    env.update(
        RELEASE_MODE=mode,
        TAG=release_tag,
        BUILD_SHA=env["GITHUB_SHA"],
        GITHUB_SERVER_URL="https://github.com",
        GITHUB_REPOSITORY="ypzyfl/iCode",
        GITHUB_RUN_ID="44217008983",
        GITHUB_RUN_ATTEMPT="1",
    )
    collect = next(step for step in jobs["release"]["steps"] if step.get("name") == "Collect release assets")
    _run(collect["run"], tmp_path, env)
    if mode != "upstream-tag":
        expected_assets.add("BUILD_INFO.md")
    assert {path.name for path in (tmp_path / "release").iterdir()} == expected_assets
    _run("sha256sum -c SHA256SUMS.txt", tmp_path / "release", env)
