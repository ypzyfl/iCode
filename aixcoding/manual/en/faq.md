# FAQ

## 1. Cannot type Chinese in the Windows terminal

**Symptom** (Windows): Chinese input does not work in the terminal.

**Cause**: The terminal in use (e.g. an outdated PowerShell or CMD prompt) is too old. This is unrelated to AIxCoding-CLI.

**Solution**: Install an up-to-date terminal. After installing it, Chinese input works normally in the new terminal.

## 2. Error: python not found

**Symptom** (Windows): after sending a message in a conversation, a red error appears at the top of the window:

```
× 错误
hook 'security-prompt-guard' failed (exit_code=9009): Python was not
found but can be installed from the Microsoft Store:
https://go.microsoft.com/fwlink?linkID=2082640
```

**Cause**: Windows ships a Microsoft Store Python3 stub (a 0 KB `python3.exe`, usually located in `%LOCALAPPDATA%\Microsoft\WindowsApps\`). When the program looks up `python3` on the PATH it hits this stub first; instead of actually running Python it suggests installing Python from the Microsoft Store and exits with code 9009, which makes sending the message fail.

**Solution**:

1. Find the location of Python3 on Windows. In a terminal (cmd or PowerShell), run:

   ```
   where python3
   ```

   The output lists every program named `python3` on the PATH. The one that is 0 KB and located in `%LOCALAPPDATA%\Microsoft\WindowsApps\` is the stub.

2. Delete the 0 KB Python3 stub:

   ```
   del "%LOCALAPPDATA%\Microsoft\WindowsApps\python3.exe"
   ```

   - If it says the file is in use and cannot be deleted: find the process ID that holds the file, end that process, then delete again. To find it, run `resmon` from the Run dialog to open Resource Monitor, switch to the **CPU** tab, type `python3` into the search box under **Associated handles**, right-click the holding process and choose **End process** (or run `taskkill /PID <pid> /F`), then run the delete command again.
   - If it says access denied: run the terminal as administrator and delete again.

3. Send the message again in AIxCoding-CLI; it now works normally.

## 3. Error: the aixcoding-cli command is not found

After installation you must open a new terminal so that PATH changes take effect. If the command is still not found:

- macOS / Linux: add `~/.local/bin` to `PATH` as the installer suggests;
- Windows: add `%LOCALAPPDATA%\chrys\bin` to your user `PATH`;
- You can also start with the equivalent commands `aixcoding` or `chrys`.
