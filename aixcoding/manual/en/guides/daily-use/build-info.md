# Build Information Query

Every release package carries automatically generated provenance information, so you can confirm which commit the binary in your hands was built from and whether it is the latest version. This information is generated and updated automatically by CI on every build and requires no manual maintenance.

## 1. Verify the package you downloaded

The verification target is the **downloaded installer file**, not the installed program. First enter the download directory containing the installer in a file manager or terminal, then compare the local file against the corresponding entry in the publisher's SHA256 manifest using SHA256. `<platform>` and `<version>` in the commands are placeholders; replace them with the platform and version from the actual file name (see the README install table for package names):

```bash
# Linux / macOS (run in the download directory)
sha256sum aixcoding-cli-<platform>-v<version>-offline.tar.gz

# Windows (run in the download directory, PowerShell)
Get-FileHash .\aixcoding-cli-<platform>-v<version>-offline.zip -Algorithm SHA256
```

As an example of verifying the v0.35.2 installer (hash values are illustrative):

**Windows** (PowerShell, verifying the Windows x86-64 installer):

```powershell
cd C:\Users\<username>\Downloads
Get-FileHash .\aixcoding-cli-windows-x86_64-v0.35.2-offline.zip -Algorithm SHA256
```

```text
Algorithm       Hash                                                                Path
---------       ----                                                                ----
SHA256          A1B2C3D4E5F60718293A4B5C6D7E8F90A1B2C3D4E5F60718293A4B5C6D7E8F...  C:\Users\<username>\Downloads\aixcoding-cli-...
```

**Linux / macOS** (verifying the Linux x86-64 installer):

```bash
cd ~/Downloads
sha256sum aixcoding-cli-linux-x86_64-v0.35.2-offline.tar.gz
```

```text
a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f  aixcoding-cli-linux-x86_64-v0.35.2-offline.tar.gz
```

The command outputs a 64-character hexadecimal hash. Compare it with the entry for the **file of the same name** in the publisher's SHA256 manifest. A matching hash proves the file comes from exactly that build; a mismatch means the file is corrupted or was replaced — download it again.

## 2. Query the installed program's version

```bash
aixcoding-cli --version
```

This prints the current version number (e.g. `0.35.2`). Note that the same version number is reused for nightly builds, so **an identical version number does not mean identical code** — use hash comparison for precise provenance.

## 3. First-run cache notice

The first time the binary runs it unpacks its embedded runtime into a local cache directory (`~/.local/share/pyapp` on Linux, `%LOCALAPPDATA%\pyapp` on Windows). When installing a new package with the same version number over an existing one, if behavior does not change, delete that cache directory and run again to force a fresh unpack.

---
