# Build Information

Every release package carries auto-generated provenance info so you can tell which commit a binary was built from and whether it is up to date. The info is generated automatically on every build — no manual maintenance required.

## 1. Verifying your download

Compare the SHA256 of your local file against the matching entry in `SHA256SUMS.txt` on the release page:

```bash
# Linux / macOS
sha256sum aixcoding-cli

# Windows (PowerShell)
Get-FileHash .\aixcoding-cli.exe -Algorithm SHA256
```

A matching hash proves the file is byte-identical to that build.

## 2. Checking the installed version

```bash
aixcoding-cli --version
```

This prints the current version (e.g. `0.28.0`). Note that the same version number is reused across nightly builds — **an identical version does not mean identical code**. For precise provenance, rely on `BUILD_INFO.md` / hash comparison instead.

## 3. First-run cache note

On first run the binary unpacks its embedded runtime into a local cache directory (Linux: `~/.local/share/pyapp`, Windows: `%LOCALAPPDATA%\pyapp`). When overwriting an installation with a new build of the same version, if behavior does not update, delete that cache directory and run again to force a fresh unpack.
