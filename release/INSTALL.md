# AIxCoding-CLI 安装指南（内网用户版）

AIxCoding-CLI 是一个运行在终端里的智能体平台（TUI）。安装包已内置 Python 和全部依赖，**无需安装 Python，全程离线可用**。

## 环境要求

| 项目 | 要求 |
|---|---|
| 系统 | Linux（x86-64 glibc ≥ 2.17，ARM64 glibc ≥ 2.18，如银河麒麟 V10）或 macOS |
| 架构 | ARM64（aarch64）或 x86_64 |
| 磁盘 | 约 500 MB（安装包 + 解压后的运行时） |

> 不支持 Alpine 等 musl 发行版；Windows 请使用对应的 zip 包手动安装。

## 安装

CD 流水线分别上传各平台二进制 Artifact，不生成包含安装脚本的 release bundle。手动将两个安装脚本和要发布的平台包放到 HTTP 下载目录；构建用 wheel 无需上传。只构建 Linux 时，产物中不会有 macOS 或 Windows 包。

```text
/homepage/aixcoding/                         # HTTP: /aixcoding/file/aixcoding/
├── install.sh
├── install.ps1
├── channels/
│   └── cli/
│       ├── prod.txt                         # 一行完整版本号
│       └── test.txt                         # 如 0.28.0-dev-9011ff5
└── releases/
    └── cli/
        └── 0.28.0-dev-9011ff5/
            └── aixcoding-cli-linux-x86_64-v0.28.0-dev-9011ff5-offline.zip
```

手动把 `install.sh` 和 `install.ps1` 放到 HTTP 根目录，并把需要的平台包放入 `releases/cli/<完整版本>/`。手动运行 CD 时，可下载对应平台的 Artifact ZIP；Linux/macOS 的 ZIP 包也可直接由 `install.sh` 安装。确认安装包上传完毕后，手动将完整版本号写入 `channels/cli/test.txt` 或 `channels/cli/prod.txt`。测试通过后发布同一构建到生产，只需更新 `channels/cli/prod.txt`，无需复制二进制。两个频道文件都只包含一行完整版本号；首次发布时分别准备。
已上传的 Linux/macOS 旧安装包若以 `icode-` 开头，保持原文件名即可；`install.sh` 会尝试该包名，并接受包内根目录的 `icode` 可执行文件。

### 方式一：从内网镜像安装

HTTP 下载地址可直接访问，无需配置 FTP 凭据。

```bash
curl -fsSL -o install.sh 'http://aicoding.s.bocsys.cn/aixcoding/file/aixcoding/install.sh' && bash install.sh
```

默认读取 `channels/cli/prod.txt`。安装测试包时运行 `bash install.sh --channel test`；在线安装会根据完整版本号和平台从 `releases/cli/` 目录下载安装包。

Windows x86-64 在 PowerShell 中使用另一条单行命令（需要先上传 `install.ps1` 和 Windows ZIP 包）：

```powershell
irm 'http://aicoding.s.bocsys.cn/aixcoding/file/aixcoding/install.ps1' | iex
```

默认读取生产频道；测试频道可先运行 `$env:ICODE_CHANNEL='test'`，再执行上述命令。安装后新开 PowerShell，运行 `aixcoding-cli --version` 验证。

安装指定版本：

```bash
curl -fsSL -o install.sh 'http://aicoding.s.bocsys.cn/aixcoding/file/aixcoding/install.sh' && bash install.sh --version v0.28.0-dev-9011ff5
```

### 方式二：离线安装（拿不到镜像时，如安全摆渡场景）

先获取对应平台的安装包（麒麟 ARM 为 `aixcoding-cli-linux-aarch64-v<版本>-offline.tar.gz` 或 `.zip`），把 `install.sh` 和安装包放在同一目录，然后执行：

```bash
bash install.sh --from ./aixcoding-cli-linux-aarch64-v<版本>-offline.tar.gz
```

如果拿到的是 ZIP 包，将命令末尾换成实际 ZIP 文件名，例如 `bash install.sh --from ./aixcoding-cli-linux-aarch64-v<版本>-offline.zip`。安装不需要摘要文件；如果发布方单独提供了安装包摘要，可选用 `--sha256 <64 位摘要>` 校验。`channels/cli/*.txt` 仅用于未指定 `--version` 的在线安装。

Linux ARM 包的根目录应有名为 `aixcoding-cli` 或 `icode` 的 Linux aarch64 可执行文件。安装后的启动命令是 `aixcoding`。包含 `.exe` 的 ZIP 是 Windows 包，不能在 Linux 上安装。

脚本按“检测平台 → 获取包 → 解压 → 二进制自检 → 安装 → 配置 PATH”输出进度。发生意外退出时，会打印失败阶段、脚本行号和退出码；安装命令本身的错误输出也会保留。

## 验证安装

新开一个终端，执行：

```bash
aixcoding --version
```

输出版本号即安装成功。之后在任意项目目录运行 `aixcoding` 即可启动 TUI 界面。

> 安装脚本会创建 `~/.local/bin/aixcoding`，指向实际安装的程序。

## 升级与卸载

- **升级**：重新执行一次安装命令即可，旧数据（会话、配置）不受影响。
- **卸载**：删除以下内容即可——
  ```bash
  rm -f ~/.local/bin/aixcoding ~/.local/bin/aixcoding-cli ~/.local/bin/chrys
  rm -rf ~/.local/share/pyapp    # 内嵌运行时（macOS 在 ~/Library/Application Support/pyapp）
  rm -rf ~/.chrys                # 配置与数据（如需彻底清除）
  ```

## 常见问题

**1. 提示 `aixcoding: command not found`**

安装器已自动把 `~/.local/bin` 写入 shell 配置，新开终端即可；当前终端可执行 `source ~/.bashrc`（或 `~/.zshrc`）立即生效。

**2. 使用 `--sha256` 后提示 `sha256 不匹配`**

多为下载不完整，重新运行安装命令即可；反复出现请联系镜像管理员。

**3. 提示 `glibc ... 低于最低要求`**

系统版本过老，需更换满足上表要求的系统，或联系管理员获取适配版本。

**4. 首次运行 `aixcoding` 等待数秒**

首次启动需解压内嵌运行时，属正常现象，之后启动是毫秒级。

**5. 提示 `Windows 安装包` 或 `包内未找到根目录下的 aixcoding-cli`**

核对安装包路径与内容：`unzip -l <包名>.zip`。Linux ARM 包的 ZIP 根目录中应有 `aixcoding-cli`，不能是 `.exe` 或嵌套目录中的可执行文件。

**6. 提示 `包内 ./aixcoding-cli --version 失败`**

错误会附带二进制输出。先用 `file <解压后的可执行文件>` 核对是否为 Linux aarch64 程序，再检查系统的 glibc 版本。此前安装过 AIxCoding-CLI 不会引发该自检错误。

---

安装或使用问题请联系内部支持渠道；镜像内容缺失请联系镜像管理员。
