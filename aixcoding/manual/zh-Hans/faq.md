# FAQ

## 1. Windows 终端无法输入中文

**问题现象**（Windows）：进入终端后无法输入中文。

**原因**：所使用的终端（如 PowerShell、CMD 命令提示符）版本过旧，与 AIxCoding-CLI 无关。

**解决办法**：安装新版本的终端。安装后进入终端即可正常输入中文。

## 2. 提示找不到 python

**问题现象**（Windows）：在对话中发送消息后，界面顶部出现红色错误：

```
× 错误
hook 'security-prompt-guard' failed (exit_code=9009): Python was not
found but can be installed from the Microsoft Store:
https://go.microsoft.com/fwlink?linkID=2082640
```

**原因**：Windows 系统自带 Microsoft Store 的 Python3 占位程序（一个 0 KB 的 `python3.exe`，通常位于 `%LOCALAPPDATA%\Microsoft\WindowsApps\`）。程序在 PATH 中查找 `python3` 时先命中了这个占位程序，它不会真正运行 Python，而是提示去 Microsoft Store 安装并以 9009 退出，导致消息发送失败。

**解决办法**：

1. 查看 Windows 系统下 Python3 的地址。在终端（cmd 或 PowerShell）执行：

   ```
   where python3
   ```

   输出会列出 PATH 中所有名为 python3 的程序，其中大小为 0 KB、位于 `%LOCALAPPDATA%\Microsoft\WindowsApps\` 的那个就是占位程序。

2. 删除 0 KB 的 Python3 占位程序：

   ```
   del "%LOCALAPPDATA%\Microsoft\WindowsApps\python3.exe"
   ```

   - 若提示文件被占用、无法删除：先查出占用该文件的进程 ID 并结束进程，再重新删除。查占用可在「运行」中执行 `resmon` 打开资源监视器，切换到「CPU」选项卡，在「关联的句柄」搜索框输入 `python3`，找到占用进程后右键「结束进程」（或执行 `taskkill /PID 进程ID /F` 结束），然后重新执行删除命令。
   - 若提示拒绝访问：以管理员身份运行终端后再执行删除。

3. 删除后在 AIxCoding-CLI 中再次发送消息，即可正常使用。

## 3. 提示找不到 aixcoding-cli 命令

安装完成后需要打开一个新终端，让 PATH 生效。如仍找不到：

- macOS / Linux：按安装器提示将 `~/.local/bin` 加入 `PATH`；
- Windows：将 `%LOCALAPPDATA%\chrys\bin` 加入用户 `PATH`；
- 也可以使用等价命令 `aixcoding` 或 `chrys` 启动。
