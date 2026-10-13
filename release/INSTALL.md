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

CD 流水线会生成 `icode-release-bundle` 构建产物，其中包含各平台安装包、`install.sh`、`latest.txt` 和 `SHA256SUMS.txt`。从 GitHub Actions 下载并解压后，把文件一起摆渡到 AList 的同一目录；这些文件由流水线按本次构建版本和实际包内容生成，不需要手工改版本号或摘要。上传前可在 Linux 上进入该目录执行 `sha256sum -c SHA256SUMS.txt` 检查传输是否完整。部分平台的手动构建只包含所选平台，请确认镜像所需的平台包齐全，再用这份 `latest.txt` 替换镜像中的版本指针。

### 方式一：从内网镜像安装

```bash
curl -fsSL -o install.sh 'http://<镜像地址>/install.sh' && ICODE_BASE_URL='http://<镜像地址>' bash install.sh
```

在线安装会读取镜像同一目录的 `latest.txt`，并按版本下载对应平台的安装包。

安装指定版本：

```bash
curl -fsSL -o install.sh 'http://<镜像地址>/install.sh' && ICODE_BASE_URL='http://<镜像地址>' bash install.sh --version v0.28.0
```

### 方式二：离线安装（拿不到镜像时，如安全摆渡场景）

先获取对应平台的安装包（麒麟 ARM 为 `aixcoding-cli-linux-aarch64-v<版本>-offline.tar.gz` 或 `.zip`），把 `install.sh` 和安装包放在同一目录，然后执行：

```bash
bash install.sh --from ./aixcoding-cli-linux-aarch64-v<版本>-offline.tar.gz
```

如果拿到的是 ZIP 包，将命令末尾换成实际 ZIP 文件名，例如 `bash install.sh --from ./aixcoding-cli-linux-aarch64-v<版本>-offline.zip`。无需准备 `SHA256SUMS.txt`；如果发布方提供了安装包的摘要，可选用 `--sha256 <64 位摘要>` 校验。`latest.txt` 仅用于在线安装。

Linux ARM 包的根目录应有名为 `aixcoding-cli` 的 Linux aarch64 可执行文件。安装后的启动命令是 `aixcoding`。包含 `.exe` 的 ZIP 是 Windows 包，不能在 Linux 上安装。

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
