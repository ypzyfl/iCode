"""Validate a pinned adapter release before unpacking its integration tools."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tarfile
from pathlib import Path

TOOL_MEMBERS = frozenset(
    {"prepare_distribution.py", "build_embedded_binary.py", "smoke_embedded_binary.py", "LICENSE", "NOTICE"}
)


def read_manifest(directory: Path, tag: str, expected_digest: str) -> dict:
    path = directory / "release-manifest.json"
    if re.fullmatch(r"[0-9a-f]{64}", expected_digest) is None:
        raise ValueError("manifest digest must be a full SHA256 value")
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected_digest:
        raise ValueError("release manifest digest mismatch")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest["schema_version"] != 1 or manifest["tool_contract_version"] != 1:
        raise ValueError("unsupported release contract")
    if manifest["repository"] != "MEDADA/aixcoding-telemetry-adapter":
        raise ValueError("unexpected adapter repository")
    if manifest["tag"] != tag or tag != "v" + manifest["version"]:
        raise ValueError("adapter tag differs from pinned manifest")
    if re.fullmatch(r"[0-9a-f]{40}", manifest["commit"]) is None:
        raise ValueError("adapter source commit must be immutable")
    version = manifest["version"]
    expected = {
        f"aixcoding_icode_instrumentation-{version}-py3-none-any.whl",
        f"aixcoding-telemetry-tools-{version}.tar.gz",
        "verification.json",
    }
    if set(manifest["files"]) != expected or any(Path(name).name != name for name in expected):
        raise ValueError("unexpected release asset layout")
    if manifest["verification"].get("passed") is not True:
        raise ValueError("release has no successful verification")
    return manifest


def prepare(directory: Path, tag: str, expected_digest: str) -> dict:
    manifest = read_manifest(directory, tag, expected_digest)
    sums = {**manifest["files"], "release-manifest.json": expected_digest}
    expected_sums = "".join(f"{checksum}  {name}\n" for name, checksum in sorted(sums.items()))
    if (directory / "SHA256SUMS.txt").read_text(encoding="utf-8") != expected_sums:
        raise ValueError("release checksums differ from pinned manifest")
    for name, checksum in manifest["files"].items():
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != checksum:
            raise ValueError("release asset checksum mismatch")
    if json.loads((directory / "verification.json").read_text(encoding="utf-8")) != manifest["verification"]:
        raise ValueError("release verification report differs")
    if any((directory / name).exists() for name in (*TOOL_MEMBERS, "provenance.json")):
        raise FileExistsError("integration tools must be unpacked into a fresh directory")
    with tarfile.open(directory / f"aixcoding-telemetry-tools-{manifest['version']}.tar.gz") as archive:
        members = archive.getmembers()
        if sorted(member.name for member in members) != sorted(TOOL_MEMBERS) or not all(
            member.isfile() for member in members
        ):
            raise ValueError("unexpected integration tool archive layout")
        archive.extractall(directory, filter="data")
    (directory / "provenance.json").write_bytes((directory / "release-manifest.json").read_bytes())
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--manifest-only", action="store_true")
    args = parser.parse_args()
    operation = read_manifest if args.manifest_only else prepare
    manifest = operation(args.directory, args.tag, args.manifest_sha256)
    sys.stdout.write(json.dumps({"version": manifest["version"], "commit": manifest["commit"]}) + "\n")


if __name__ == "__main__":
    main()
