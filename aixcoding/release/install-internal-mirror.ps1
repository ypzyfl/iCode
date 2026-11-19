# Install or upgrade AIxCoding from the internal release mirror (Windows x64).
# Windows on Arm uses the x64 package through emulation; native Arm is not published.
& {
    param(
        [ValidateSet('prod', 'test')]
        [string]$Channel = $(if ($env:AIXCODING_CHANNEL) { $env:AIXCODING_CHANNEL } elseif ($env:ICODE_CHANNEL) { $env:ICODE_CHANNEL } else { 'prod' }),
        [string]$Version = '',
        [string]$BaseUrl = $(if ($env:AIXCODING_BASE_URL) { $env:AIXCODING_BASE_URL } elseif ($env:ICODE_BASE_URL) { $env:ICODE_BASE_URL } else { 'http://aicoding.s.bocsys.cn/aixcoding/file/aixcoding' }),
        [switch]$Force
    )

    $ErrorActionPreference = 'Stop'
    $ProgressPreference = 'SilentlyContinue'
    $workDir = ''
    $logFile = ''
    try {
        if ($PSBoundParameters.ContainsKey('Version') -and [string]::IsNullOrWhiteSpace($Version)) {
            throw '-Version needs a non-empty value.'
        }
        if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
            throw 'This installer runs only on Windows.'
        }
        if (-not [Environment]::Is64BitOperatingSystem) { throw 'Only 64-bit Windows is supported.' }
        if (-not $env:LOCALAPPDATA) { throw 'LOCALAPPDATA is required to locate the installation directory.' }

        $root = $BaseUrl.TrimEnd('/')
        $binDir = Join-Path $env:LOCALAPPDATA 'chrys\bin'
        $ownBinary = Join-Path $binDir 'chrys.exe'
        $externalCommands = @()
        foreach ($name in @('aixcoding', 'aixcoding-cli')) {
            $externalCommands += @(Get-Command $name -CommandType Application -All -ErrorAction SilentlyContinue |
                Where-Object { [IO.Path]::GetDirectoryName($_.Source) -ne $binDir })
        }
        if ($externalCommands -and -not (Test-Path -LiteralPath $ownBinary -PathType Leaf)) {
            throw ('Another installation provides aixcoding or aixcoding-cli. Upgrade with its original tool ' +
                '(for example, uv tool upgrade iCode-TUI), or uninstall it first. No files were replaced.')
        }
        # Never replace an unrelated executable, even in the installation directory.
        foreach ($name in @('aixcoding', 'aixcoding-cli')) {
            $alias = Join-Path $binDir "$name.exe"
            if (Test-Path -LiteralPath $alias) {
                if (-not (Test-Path -LiteralPath $ownBinary -PathType Leaf)) {
                    throw "$alias belongs to another installation. Uninstall it with its original tool first."
                }
                if ((Get-FileHash -LiteralPath $alias).Hash -ne (Get-FileHash -LiteralPath $ownBinary).Hash) {
                    throw "$alias differs from this installation. No files were replaced; resolve the command conflict first."
                }
            }
        }

        $workDir = Join-Path ([IO.Path]::GetTempPath()) ("aixcoding-install-" + [guid]::NewGuid().ToString('N'))
        [IO.Directory]::CreateDirectory($workDir) | Out-Null
        $logFile = Join-Path ([IO.Path]::GetTempPath()) ("aixcoding-install-" + [guid]::NewGuid().ToString('N') + '.log')
        [IO.File]::WriteAllText($logFile, '')

        function Invoke-PackageCommand([string]$Exe, [string]$Command) {
            $stdout = Join-Path $workDir 'stdout.txt'
            $stderr = Join-Path $workDir 'stderr.txt'
            $stdin = Join-Path $workDir 'stdin.txt'
            [IO.File]::WriteAllText($stdin, '')
            $process = Start-Process -FilePath $Exe -ArgumentList $Command -NoNewWindow -PassThru `
                -RedirectStandardOutput $stdout -RedirectStandardError $stderr -RedirectStandardInput $stdin
            $null = $process.Handle
            $process.WaitForExit()
            $output = [IO.File]::ReadAllText($stdout)
            [IO.File]::AppendAllText($logFile, $output + [IO.File]::ReadAllText($stderr))
            if ($process.ExitCode -ne 0) {
                throw "Command '$Command' failed (exit code $($process.ExitCode)). Close running AIxCoding instances and retry."
            }
            return $output.Trim()
        }
        function Set-LaunchCommands {
            foreach ($name in @('aixcoding', 'aixcoding-cli')) {
                $alias = Join-Path $binDir "$name.exe"
                # Hard links follow upgrades to chrys.exe; copy is the filesystem fallback.
                if (Test-Path -LiteralPath $alias) {
                    if ((Get-FileHash -LiteralPath $alias).Hash -eq (Get-FileHash -LiteralPath $ownBinary).Hash) { continue }
                    Remove-Item -LiteralPath $alias -Force
                }
                try {
                    New-Item -ItemType HardLink -Path $alias -Target $ownBinary -ErrorAction Stop | Out-Null
                } catch {
                    Copy-Item -LiteralPath $ownBinary -Destination $alias
                }
            }
        }
        function Complete-Install {
            Set-LaunchCommands
            foreach ($name in @('aixcoding', 'aixcoding-cli')) {
                $actual = Invoke-PackageCommand (Join-Path $binDir "$name.exe") '--version'
                if ($actual -ne $Version) { throw "$name version validation failed: expected $Version, got $actual" }
            }
            Write-Host 'Installation ready. Open a new PowerShell window and run aixcoding or aixcoding-cli.'
            foreach ($command in $externalCommands) {
                Write-Host "Another command was preserved at $($command.Source). If PATH selects it, use $binDir\aixcoding.exe or $binDir\aixcoding-cli.exe."
            }
        }

        if (-not $Version) {
            Write-Host "Checking the $Channel release..."
            try {
                $Version = [string](Invoke-RestMethod -Uri "$root/channels/cli/${Channel}.txt" -UseBasicParsing)
            } catch {
                [IO.File]::AppendAllText($logFile, $_.ToString())
                throw 'Could not read the release channel. Check the network or use -BaseUrl / AIXCODING_BASE_URL.'
            }
        }
        $Version = $Version.Trim() -replace '^[vV]', ''
        if ($Version -notmatch '^\d+\.\d+\.\d+([._-][A-Za-z0-9._-]+)?$') {
            throw "Invalid release version: $Version"
        }
        $installedVersion = ''
        if (Test-Path -LiteralPath $ownBinary -PathType Leaf) {
            try { $installedVersion = Invoke-PackageCommand $ownBinary '--version' } catch { $installedVersion = '' }
        }
        if ($installedVersion -eq $Version -and -not $Force) {
            Complete-Install
            Write-Host "AIxCoding $Version is already installed. No download needed; use -Force to reinstall."
            Remove-Item -LiteralPath $logFile -Force
            return
        }
        if (-not $installedVersion) {
            Write-Host "Installing AIxCoding $Version for the first time..."
        } elseif ($installedVersion -eq $Version) {
            Write-Host "Reinstalling AIxCoding $Version..."
        } else {
            Write-Host "Updating AIxCoding: $installedVersion -> $Version"
        }

        $archive = "aixcoding-cli-windows-x86_64-v$Version-offline.zip"
        $archivePath = Join-Path $workDir $archive
        Write-Host "Downloading $archive"
        try {
            Invoke-WebRequest -Uri "$root/releases/cli/$Version/$archive" -OutFile $archivePath -UseBasicParsing
        } catch {
            [IO.File]::AppendAllText($logFile, $_.ToString())
            throw 'Could not download the ZIP package. Check the network and release; use -BaseUrl / AIXCODING_BASE_URL if the mirror moved.'
        }
        $extractDir = Join-Path $workDir 'extract'
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        [IO.Compression.ZipFile]::ExtractToDirectory($archivePath, $extractDir)
        $binary = Join-Path $extractDir 'aixcoding-cli.exe'
        if (-not (Test-Path -LiteralPath $binary -PathType Leaf)) { throw 'ZIP does not contain aixcoding-cli.exe at its root.' }
        Write-Host 'Preparing the embedded runtime (the first run may take a moment)...'
        $actual = Invoke-PackageCommand $binary '--version'
        if ($actual -ne $Version) { throw "Package version mismatch: expected $Version, got $actual" }
        Write-Host 'Installing...'
        $null = Invoke-PackageCommand $binary 'install'
        if (-not (Test-Path -LiteralPath $ownBinary -PathType Leaf)) { throw 'Installation did not create chrys.exe.' }
        Complete-Install
        Remove-Item -LiteralPath $logFile -Force
    } catch {
        Write-Host "Installation failed: $($_.Exception.Message)"
        if ($logFile) {
            [IO.File]::AppendAllText($logFile, $_.ToString())
            Write-Host "Details: $logFile"
        }
        exit 1
    } finally {
        if ($workDir) { Remove-Item -LiteralPath $workDir -Recurse -Force -ErrorAction SilentlyContinue }
    }
} @args
