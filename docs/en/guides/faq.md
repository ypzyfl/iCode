# FAQ

## 1. Cannot type Chinese in a Windows terminal

**Symptom** (Windows): After opening the terminal, you cannot type Chinese.

**Cause**: The terminal in use (such as PowerShell or the CMD command prompt) is too old. This is unrelated to AIxCoding-CLI.

**Solution**: Install a newer version of the terminal. After installing it, Chinese input works normally in the terminal.

## 2. "Python was not found" error

**Symptom** (Windows): After sending a message in a conversation, a red error appears at the top of the interface:

```
× 错误
hook 'security-prompt-guard' failed (exit_code=9009): Python was not
found but can be installed from the Microsoft Store:
https://go.microsoft.com/fwlink?linkID=2082640
```

**Cause**: Windows ships with a Microsoft Store Python3 placeholder (a 0 KB `python3.exe`, usually located in `%LOCALAPPDATA%\Microsoft\WindowsApps\`). When looking for `python3` in PATH, the program hits this placeholder first. It does not actually run Python; instead, it prompts you to install Python from the Microsoft Store and exits with code 9009, which makes message sending fail.

**Solution**:

1. Find where Python3 is on Windows. In a terminal (cmd or PowerShell), run:

   ```
   where python3
   ```

   The output lists every program named python3 in PATH. The one that is 0 KB and located in `%LOCALAPPDATA%\Microsoft\WindowsApps\` is the placeholder.

2. Delete the 0 KB Python3 placeholder:

   ```
   del "%LOCALAPPDATA%\Microsoft\WindowsApps\python3.exe"
   ```

   - If the file is reported as in use and cannot be deleted: find the process ID holding the file and end that process, then delete again. To find the holder, run `resmon` from "Run" to open Resource Monitor, switch to the "CPU" tab, type `python3` in the "Associated Handles" search box, right-click the process and choose "End Process" (or end it with `taskkill /PID <process-id> /F`), then run the delete command again.
   - If access is denied: run the terminal as administrator and delete again.

3. After the deletion, send a message in AIxCoding-CLI again; it now works normally.

## 3. "aixcoding-cli command not found" error

After installation, open a new terminal so that PATH takes effect. If the command still cannot be found:

- macOS / Linux: add `~/.local/bin` to `PATH` as the installer suggests;
- Windows: add `%LOCALAPPDATA%\chrys\bin` to your user `PATH`;
- you can also start the program with the equivalent commands `aixcoding` or `chrys`.
