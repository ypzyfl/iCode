# 构建信息查询

每个发布包都携带自动生成的溯源信息，可用于确认你手中的二进制构建自哪次提交、是否为最新版本。这些信息由 CI 在每次构建时自动生成并更新，无需手动维护。

## 1. 校验你下载的包

校验对象是**下载的安装包文件**，不是已安装的程序。先在文件管理器或终端中进入安装包所在的下载目录，再用 SHA256 比对本地文件与发布方提供的 SHA256 清单中的对应条目。命令中的 `<platform>` 和 `<version>` 是占位符，请替换为实际文件名中的平台和版本号（平台包名见 README 安装表）：

```bash
# Linux / macOS（在下载目录执行）
sha256sum aixcoding-cli-<platform>-v<version>-offline.tar.gz

# Windows（在下载目录执行，PowerShell）
Get-FileHash .\aixcoding-cli-<platform>-v<version>-offline.zip -Algorithm SHA256
```

以校验 v0.35.2 版本的安装包为例（哈希值均为示意）：

**Windows**（PowerShell，校验 Windows x86-64 安装包）：

```powershell
cd C:\Users\<用户名>\Downloads
Get-FileHash .\aixcoding-cli-windows-x86_64-v0.35.2-offline.zip -Algorithm SHA256
```

```text
Algorithm       Hash                                                                Path
---------       ----                                                                ----
SHA256          A1B2C3D4E5F60718293A4B5C6D7E8F90A1B2C3D4E5F60718293A4B5C6D7E8F...  C:\Users\<用户名>\Downloads\aixcoding-cli-...
```

**Linux / macOS**（校验 Linux x86-64 安装包）：

```bash
cd ~/Downloads
sha256sum aixcoding-cli-linux-x86_64-v0.35.2-offline.tar.gz
```

```text
a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f  aixcoding-cli-linux-x86_64-v0.35.2-offline.tar.gz
```

命令会输出一串 64 位十六进制哈希值，将其与发布方 SHA256 清单中**同名文件的条目**比对。哈希一致即证明文件与该次构建完全同源；不一致说明文件损坏或被替换，请重新下载。

## 2. 查询已安装程序的版本

```bash
aixcoding-cli --version
```

输出当前版本号（如 `0.35.2`）。注意：同一版本号会在每晚构建中重复使用，**版本号相同不代表代码相同**，精确溯源请以哈希比对为准。

## 3. 首次运行缓存提示

二进制首次运行时会把内嵌运行时解包到本地缓存目录（Linux 为 `~/.local/share/pyapp`，Windows 为 `%LOCALAPPDATA%\pyapp`）。覆盖安装同版本号的新包时，如遇行为未更新，可删除该缓存目录后重新运行，强制重新解包。

---
