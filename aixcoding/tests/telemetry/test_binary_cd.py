"""Exercise the CD packaging code across the artifact transport boundary."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest
import yaml

WORKFLOW = Path(__file__).resolve().parents[3] / ".github/workflows/aixcoding-otel-business-telemetry-cd.yml"


@pytest.mark.parametrize("platform", ["linux", "macos", "windows"])
def test_resource_package_preserves_binary_and_build_facts(tmp_path, platform):
    data = yaml.load(WORKFLOW.read_text(), Loader=yaml.BaseLoader)
    steps = data["jobs"]["build-binaries"]["steps"]
    package = next((step for step in steps if step.get("id") == "resource-package"), None)
    assert package is not None, "Package on the native runner before artifact transport"
    script = package["run"].split("<<'PYCODE'\n", 1)[1].rsplit("\nPYCODE", 1)[0]
    name = "aixcoding-cli.exe" if platform == "windows" else "aixcoding-cli"
    binary = tmp_path / name
    binary.write_bytes(b"#!/bin/sh\nprintf fixture\n")
    binary.chmod(0o755)
    facts = {"host_version": "0.35.2", "adapter_version": "0.1.0a3", "host_sources_unchanged": True}
    (tmp_path / "chrys-telemetry-offline-dist.tar.gz.json").write_text(json.dumps(facts))
    (tmp_path / "telemetry-wheel").mkdir()
    (tmp_path / "telemetry-wheel/provenance.json").write_text(json.dumps({"commit": "b" * 40}))
    artifact = f"aixcoding-cli-{platform}-fixture-offline"
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env={
            **os.environ,
            "BINARY_NAME": name,
            "ARTIFACT_NAME": artifact,
            "BUILD_PLATFORM": platform,
            "BUILD_TARGET": f"fixture-{platform}",
            "HOST_COMMIT": "a" * 40,
            "GITHUB_OUTPUT": str(tmp_path / "outputs"),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assets = tmp_path / "release-assets"
    extension = ".zip" if platform == "windows" else ".tar.gz"
    archive = assets / (artifact + extension)
    # Actions normalizes loose files to 0644. The inner binary must survive it.
    archive.chmod(0o644)
    downloaded = tmp_path / "downloaded"
    downloaded.mkdir()
    if platform == "windows":
        with zipfile.ZipFile(archive) as bundle:
            assert bundle.namelist() == [name]
            bundle.extractall(downloaded)
    else:
        with tarfile.open(archive) as bundle:
            assert bundle.getnames() == [name]
            bundle.extractall(downloaded, filter="data")
        if os.name != "nt":
            assert (downloaded / name).stat().st_mode & 0o111
            probe = subprocess.run([str(downloaded / name)], capture_output=True, check=True)
            assert probe.stdout == b"fixture"
    assert (downloaded / name).read_bytes() == binary.read_bytes()
    assert (tmp_path / "package-smoke" / name).read_bytes() == binary.read_bytes()
    manifest = json.loads((assets / (artifact + "-build-manifest.json")).read_text())
    assert manifest["host_commit"] == "a" * 40
    assert manifest["adapter"]["commit"] == "b" * 40
    assert manifest["host_version"] == "0.35.2"
    assert manifest["resource_sha256"] == hashlib.sha256(archive.read_bytes()).hexdigest()
    assert manifest["binary_sha256"] == hashlib.sha256(binary.read_bytes()).hexdigest()

    # Run the real collector after simulating download of the packaged artifact.
    artifact_dir = tmp_path / "artifacts" / artifact
    shutil.copytree(assets, artifact_dir)
    for asset in artifact_dir.iterdir():
        asset.chmod(0o644)
    shutil.copytree(tmp_path / "telemetry-wheel", tmp_path / "artifacts/telemetry-wheel")
    collector = data["jobs"]["collect-telemetry-assets"]["steps"][1]["run"]
    collected = subprocess.run(
        ["bash", "-e", "-c", collector], cwd=tmp_path, capture_output=True, text=True, check=False
    )
    assert collected.returncode == 0, collected.stderr
    delivered = tmp_path / "release"
    assert (delivered / archive.name).read_bytes() == archive.read_bytes()
    assert (delivered / "telemetry-provenance.json").is_file()
    sums = (delivered / "SHA256SUMS.txt").read_text().splitlines()
    assert sums
    for line in sums:
        checksum, filename = line.split("  ", 1)
        assert hashlib.sha256((delivered / filename).read_bytes()).hexdigest() == checksum
