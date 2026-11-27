"""Pinned release manifests must be validated before integration tools are extracted."""

from __future__ import annotations

import hashlib
import io
import json
import tarfile

import pytest
from aixcoding.tools import prepare_telemetry_release as release


def fixture_release(root):
    names = {"prepare_distribution.py", "build_embedded_binary.py", "smoke_embedded_binary.py", "LICENSE", "NOTICE"}
    tools = root / "aixcoding-telemetry-tools-0.1.0a4.tar.gz"
    with tarfile.open(tools, "w:gz") as archive:
        for name in sorted(names):
            content = b"fixture\n"
            entry = tarfile.TarInfo(name)
            entry.size = len(content)
            archive.addfile(entry, io.BytesIO(content))
    wheel = root / "aixcoding_icode_instrumentation-0.1.0a4-py3-none-any.whl"
    wheel.write_bytes(b"wheel fixture")
    report = {"passed": True, "host_commit": "b" * 40}
    (root / "verification.json").write_text(json.dumps(report))
    files = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(root.iterdir())}
    manifest = {
        "schema_version": 1,
        "tool_contract_version": 1,
        "repository": "MEDADA/aixcoding-telemetry-adapter",
        "commit": "a" * 40,
        "version": "0.1.0a4",
        "tag": "v0.1.0a4",
        "host_commit": "b" * 40,
        "verification": report,
        "files": files,
    }
    (root / "release-manifest.json").write_text(json.dumps(manifest))
    digest = hashlib.sha256((root / "release-manifest.json").read_bytes()).hexdigest()
    sums = {**files, "release-manifest.json": digest}
    (root / "SHA256SUMS.txt").write_text("".join(f"{checksum}  {name}\n" for name, checksum in sorted(sums.items())))
    return digest


def test_release_tools_are_extracted_after_validating_pinned_inputs(tmp_path):
    digest = fixture_release(tmp_path)
    result = release.prepare(tmp_path, "v0.1.0a4", digest)
    assert result["commit"] == "a" * 40
    assert (tmp_path / "prepare_distribution.py").read_bytes() == b"fixture\n"
    assert json.loads((tmp_path / "provenance.json").read_text())["tag"] == "v0.1.0a4"


@pytest.mark.parametrize("corruption", ["manifest", "wheel", "tag", "checksums"])
def test_invalid_release_is_rejected_before_tool_extraction(tmp_path, corruption):
    digest = fixture_release(tmp_path)
    tag = "v0.1.0a4"
    if corruption == "manifest":
        (tmp_path / "release-manifest.json").write_text("{}")
    elif corruption == "wheel":
        (tmp_path / "aixcoding_icode_instrumentation-0.1.0a4-py3-none-any.whl").write_bytes(b"tampered")
    elif corruption == "tag":
        tag = "v0.1.0a5"
    else:
        (tmp_path / "SHA256SUMS.txt").write_text("")
    with pytest.raises(ValueError):
        release.prepare(tmp_path, tag, digest)
    assert not (tmp_path / "prepare_distribution.py").exists()
    assert not (tmp_path / "provenance.json").exists()


def test_existing_tools_are_never_overwritten(tmp_path):
    digest = fixture_release(tmp_path)
    (tmp_path / "prepare_distribution.py").write_bytes(b"existing")
    with pytest.raises(FileExistsError):
        release.prepare(tmp_path, "v0.1.0a4", digest)
    assert (tmp_path / "prepare_distribution.py").read_bytes() == b"existing"


def test_tool_archive_cannot_install_links(tmp_path):
    fixture_release(tmp_path)
    tools = tmp_path / "aixcoding-telemetry-tools-0.1.0a4.tar.gz"
    with tarfile.open(tools, "w:gz") as archive:
        for name in (
            "prepare_distribution.py",
            "build_embedded_binary.py",
            "smoke_embedded_binary.py",
            "LICENSE",
            "NOTICE",
        ):
            member = tarfile.TarInfo(name)
            member.type = tarfile.SYMTYPE
            member.linkname = "../outside"
            archive.addfile(member)
    manifest_path = tmp_path / "release-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"][tools.name] = hashlib.sha256(tools.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    sums = {**manifest["files"], "release-manifest.json": digest}
    (tmp_path / "SHA256SUMS.txt").write_text(
        "".join(f"{checksum}  {name}\n" for name, checksum in sorted(sums.items()))
    )
    with pytest.raises(ValueError, match="archive layout"):
        release.prepare(tmp_path, "v0.1.0a4", digest)
    assert not (tmp_path / "provenance.json").exists()
