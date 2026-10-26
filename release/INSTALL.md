# AIxCoding-CLI 用户安装手册

安装包已内置 Python 和依赖，无需另装 Python。请选择与系统、CPU 架构对应的安装包；离线包可在无网络环境下安装，模型服务仍需按实际环境配置。

| 系统 | 支持平台 |
|---|---|
| Linux（含银河麒麟） | x86_64：glibc ≥ 2.17；ARM64（aarch64）：glibc ≥ 2.18；不支持 Alpine 等 musl 系统 |
| macOS | Apple 芯片（ARM64）或 Intel（x86_64） |
| Windows | x86_64 |

## 1. 通过内网脚本安装（推荐）

需能访问内网下载地址，且镜像已提供对应平台的安装包。默认安装生产版本。

### Linux / macOS

在终端执行：

```bash
curl -fsSL http://aicoding.s.bocsys.cn/aixcoding/file/aixcoding/install.sh | bash
```

安装完成后，**新开终端**，验证并启动：

```bash
aixcoding --version
aixcoding
```

### Windows

在 PowerShell 中执行：

```powershell
irm http://aicoding.s.bocsys.cn/aixcoding/file/aixcoding/install.ps1 | iex
```

安装完成后，**新开 PowerShell**，验证并启动：

```powershell
aixcoding-cli --version
aixcoding-cli
```

如需测试版本：Linux / macOS 将安装命令末尾的 `| bash` 换成 `| bash -s -- --channel test`；Windows 先运行 `$env:ICODE_CHANNEL='test'`，再执行安装命令。

Windows 在同一 PowerShell 窗口切回生产版本前，先运行 `Remove-Item Env:ICODE_CHANNEL`。

## 2. 离线安装

从发布方获取对应平台的安装包。包名中的 `linux`、`macos`、`windows` 表示系统，`aarch64` 或 `x86_64` 表示 CPU 架构，以实际提供的包名为准。

### Linux / macOS

将 `install.sh` 和安装包放在同一目录，在该目录打开终端执行（将文件名换成实际包名）：

```bash
bash install.sh --from ./aixcoding-cli-linux-aarch64-v<版本>-offline.zip
```

也支持 `.tar.gz` 包。完成后新开终端，运行 `aixcoding`。

### Windows

解压 Windows ZIP 安装包，在解压目录打开 PowerShell，执行：

```powershell
.\aixcoding-cli.exe install
```

完成后新开 PowerShell，运行 `aixcoding-cli`。

## 3. 解压后直接启动（不安装命令）

解压对应平台的安装包，**在解压目录打开终端或 PowerShell**，运行以下命令。建议从终端启动，便于查看提示和错误。

### Linux / macOS

```bash
chmod +x ./aixcoding-cli
./aixcoding-cli
```

macOS 若提示文件被隔离，确认安装包来源可信后执行，再重新启动：

```bash
xattr -d com.apple.quarantine ./aixcoding-cli
```

### Windows

```powershell
.\aixcoding-cli.exe
```

程序运行在终端中；双击 `.exe` 可能打开终端窗口，但出错退出后不便查看信息，推荐使用上述命令。

> 旧版包内的可执行文件可能叫 `icode`，请将上述命令中的 `aixcoding-cli` 换成 `icode`（Windows 为 `icode.exe`）。直接启动仍会在本机准备内嵌运行时，首次启动可能需要等待数秒。

## 4. 升级与常见问题

- **升级**：重新执行对应平台的安装命令，会话和配置保留。
- **提示找不到命令**：先新开终端；Linux / macOS 也可直接运行 `~/.local/bin/aixcoding`。
- **无法下载**：确认已连接内网；镜像缺少安装包时联系发布方，或使用离线安装。
- **无法运行可执行文件**：核对系统与 CPU 架构；Linux 还需满足上表的 glibc 要求，不能使用 Windows 的 `.exe` 包。
