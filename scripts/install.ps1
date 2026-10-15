# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

# Install the Windows x86-64 release from the internal HTTP mirror.
param(
    [ValidateSet('prod', 'test')]
    [string]$Channel = $(if ($env:ICODE_CHANNEL) { $env:ICODE_CHANNEL } else { 'prod' }),
    [string]$Version = '',
    [string]$BaseUrl = $(if ($env:ICODE_BASE_URL) { $env:ICODE_BASE_URL } else { 'http://22.189.54.139/aixcoding/file/aixcoding' })
)

$ErrorActionPreference = 'Stop'
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
    throw 'This installer runs only on Windows.'
}
if (-not [Environment]::Is64BitOperatingSystem) {
    throw 'Only Windows x86-64 is supported by this installer.'
}

$root = $BaseUrl.TrimEnd('/')
if (-not $Version) {
    Write-Host "Reading $Channel channel"
    $Version = [string](Invoke-RestMethod -Uri "$root/channels/cli/${Channel}.txt")
}
$Version = $Version.Trim() -replace '^[vV]', ''
if ($Version -notmatch '^[0-9]+\.[0-9]+\.[0-9]+([._-][A-Za-z0-9._-]+)?$') {
    throw "Invalid release version: $Version"
}

$archive = "aixcoding-cli-windows-x86_64-v$Version-offline.zip"
$workDir = Join-Path ([IO.Path]::GetTempPath()) ("aixcoding-install-" + [guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($workDir) | Out-Null
try {
    $archivePath = Join-Path $workDir $archive
    $extractDir = Join-Path $workDir 'extract'
    Write-Host "Downloading $archive"
    Invoke-WebRequest -Uri "$root/releases/cli/$Version/$archive" -OutFile $archivePath -UseBasicParsing
    Expand-Archive -LiteralPath $archivePath -DestinationPath $extractDir
    $binary = Join-Path $extractDir 'aixcoding-cli.exe'
    if (-not (Test-Path -LiteralPath $binary -PathType Leaf)) {
        throw "Archive does not contain aixcoding-cli.exe at its root: $archive"
    }
    & $binary --version
    if ($LASTEXITCODE -ne 0) { throw "Binary self-check failed (exit $LASTEXITCODE)." }
    & $binary install
    if ($LASTEXITCODE -ne 0) { throw "Installation failed (exit $LASTEXITCODE)." }
    Write-Host 'Installation complete. Open a new PowerShell window and run aixcoding-cli.'
}
finally {
    Remove-Item -LiteralPath $workDir -Recurse -Force -ErrorAction SilentlyContinue
}
