# 构建信息查询

每个发布包都携带自动生成的溯源信息，可用于确认你手中的二进制构建自哪次提交、是否为最新版本。这些信息由 CI 在每次构建时自动生成并更新，无需手动维护。

## 在 GitHub Release 页面查看

进入仓库的 [Releases](https://github.com/ypzyfl/iCode/releases) 页面，每晚构建会覆盖更新同版本 Release，其中包含：

| 文件 | 内容 |
|---|---|
| `BUILD_INFO.md` | 人类可读的构建信息：构建时间、构建分支/Tag、完整与短 Commit、提交作者、触发方式、Run 链接、资产 SHA256 汇总 |
| `release.txt` | 同上信息的键值对原始格式 |
| `SHA256SUMS.txt` | 全部发布资产的 SHA256 清单 |

## 校验你下载的包

用 SHA256 比对本地文件与 Release 页 `SHA256SUMS.txt` 中的对应条目：

```bash
# Linux / macOS
sha256sum aixcoding-cli

# Windows (PowerShell)
Get-FileHash .\aixcoding-cli.exe -Algorithm SHA256
```

哈希一致即证明文件与该次构建完全同源。

## 查询已安装程序的版本

```bash
aixcoding-cli --version
```

输出当前版本号（如 `0.28.0`）。注意：同一版本号会在每晚构建中重复使用，**版本号相同不代表代码相同**，精确溯源请以上述 `BUILD_INFO.md` / 哈希比对为准。

## 首次运行缓存提示

二进制首次运行时会把内嵌运行时解包到本地缓存目录（Linux 为 `~/.local/share/pyapp`，Windows 为 `%LOCALAPPDATA%\pyapp`）。覆盖安装同版本号的新包时，如遇行为未更新，可删除该缓存目录后重新运行，强制重新解包。
