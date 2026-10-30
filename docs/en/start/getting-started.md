# Getting started with AIxCoding-CLI

This tutorial covers how to install AIxCoding-CLI and use agents in a project to complete a development task.

## 1. Install AIxCoding-CLI

AIxCoding-CLI provides prebuilt offline packages for macOS, Linux, and Windows. The packages include Python and runtime dependencies, so you do not need to install Python separately.

`<version>` and `<architecture>` in the commands below are placeholders; replace them with the actual values from the downloaded file names.

### macOS

Choose `aixcoding-cli-macos-aarch64-v<version>-offline.tar.gz` (Apple silicon) or `aixcoding-cli-macos-x86_64-v<version>-offline.tar.gz` (Intel) according to your processor, then run the following in the download directory:

```bash
tar xzf aixcoding-cli-macos-<architecture>-v<version>-offline.tar.gz
chmod +x ./aixcoding-cli
./aixcoding-cli install
```

### Linux

Choose `aixcoding-cli-linux-x86_64-v<version>-offline.tar.gz` or `aixcoding-cli-linux-aarch64-v<version>-offline.tar.gz` according to your processor, then run the following in the download directory:

```bash
tar xzf aixcoding-cli-linux-<architecture>-v<version>-offline.tar.gz
chmod +x ./aixcoding-cli
./aixcoding-cli install
```

The Linux x86-64 package requires glibc 2.17 or later; the ARM64 package requires glibc 2.18 or later. Distributions that only provide musl, such as Alpine Linux, are outside the scope of the prebuilt packages.

The HTTP download root is `http://22.189.54.139/aixcoding/file/aixcoding`, which maps to the server directory `/homepage/aixcoding/`. The root holds `install.sh` and `install.ps1`; `channels/cli/prod.txt` and `channels/cli/test.txt` each hold one line with the full version number, and packages live under `releases/cli/<full version>/`. No FTP credentials are needed. Linux and macOS users can run the same command; the script detects the platform automatically and creates the `aixcoding` launch command:

```bash
curl -fsSL -o install.sh 'http://22.189.54.139/aixcoding/file/aixcoding/install.sh' && bash install.sh
```

This installs the production package by default; to install the test package, run `bash install.sh --channel test`. The CD pipeline uploads the per-platform binary artifacts separately and does not package the install scripts. Manually place the two install scripts in the HTTP root and the artifact ZIP for each platform under `releases/cli/<full version>/`, then write the full version number into the matching channel file; build wheels do not need to be uploaded to the HTTP mirror. When only Linux is built, the artifacts contain only the Linux binary package. The package names for the five platforms are listed in the README installation table.


### Windows

In PowerShell, run the following command to install the current Windows x86-64 package from the production channel:

```powershell
irm 'http://22.189.54.139/aixcoding/file/aixcoding/install.ps1' | iex
```

To install the test package, first run `$env:ICODE_CHANNEL='test'` (this environment variable keeps its historical name), then the command above. The installer tries to add AIxCoding-CLI to the current user's `PATH`. After installation, open a new terminal.

### Verify the installation

```shell
aixcoding-cli --version
```

The command should print the AIxCoding-CLI version. On macOS or Linux, if the system cannot find `aixcoding-cli`, add `~/.local/bin` to `PATH` as the installer suggests; if the installer reports that `~/.local/bin/aixcoding-cli` already exists, that command starts another program—use `chrys` instead. On Windows, open a new terminal; if the installer reports that updating the user PATH failed, add `%LOCALAPPDATA%\chrys\bin` to your user `PATH` manually.


> **About launch commands**: `aixcoding-cli` is the standard launch command of this tool; `aixcoding` (created automatically by the install script) and `chrys` (a historical command name) are fully equivalent to it—any of them starts the same program. This manual uses `aixcoding-cli` throughout.

## 2. Start AIxCoding-CLI in a project

Start this tutorial in a project managed with Git or one that can be safely restored. Before letting an agent modify files, save anything not yet written to disk and commit existing changes with Git, so you can tell the agent's modifications apart from previous work and restore the previous state if needed.

In a terminal, change into the project directory you want to work on and start AIxCoding-CLI:

```shell
cd <project-directory>
aixcoding-cli
```

Replace `<project-directory>` with the actual path of your project directory. To switch directories after startup, see [Working directory](../guides/daily-use/workspaces.md).


## 3. Use agents

### Choose an agent

AIxCoding-CLI provides two main agents by default: Q&A Agent and Code Agent. Both can read a project, analyze code, and discuss designs, but they differ in focus and available tools: Q&A Agent is mainly read-only, suited to exploring a project, explaining code, and analyzing problems; Code Agent can modify files and run commands, suited to writing, reviewing, refactoring, debugging, and verifying code.

You can switch agents when no agent task is running. Type `#` in the input box; the agent list appears above the input box. Choose by clicking, or with the arrow keys and Enter. You can also click the agent name in the status bar above the input box and switch in the agent selection window.

### Use the Q&A Agent

Q&A Agent is suited to exploring a project, analyzing code, tracing implementations, and discussing designs **without modifying the project**. It answers based on project content and tries to provide traceable references.

After switching to **Q&A Agent**, type `/new` in the input box and press Enter to start a new session.

The example below assumes the current project is a to-do app and only demonstrates usage. Adjust the questions and tasks to your actual project.

```text
请分析任务列表的实现，并为增加“清除已完成任务”功能提出方案。说明需要修改哪些文件以及实现步骤。
```

Q&A Agent may search files, read file contents, or run read-only commands. Tool calls appear as cards; when the analysis finishes, it proposes an implementation plan.

Your messages and the agent's replies are rendered as Markdown. To copy the raw content of a message, click **Copy** next to the message title; selecting text with the mouse copies what is displayed.

### Use the Code Agent

Code Agent is suited to tasks that need **file modifications, command execution, and result verification**. It reads the relevant code first, then implements, debugs, or refactors the code as the task requires.

After Q&A Agent proposes a plan, you can switch to **Code Agent** in the same session. Switching agents does not clear the current session's context, so Code Agent can continue the development task based on the existing plan:

```text
请根据刚才讨论的方案实现“清除已完成任务”功能。修改代码并运行必要的测试。
```

If an approval dialog appears, review the tool call about to run—especially the command, target files, and scope of impact—and approve only what matches your intent. For the behavior of the different approval modes, see [Configure approval modes](../guides/configuration/approval.md).

When the task finishes, review the agent's final reply and browse the file changes recorded for this session with `/diff`. Then use Git or another version control tool to review the full changes in the working directory, and confirm that the feature works, the necessary tests pass, and there are no unrelated changes. Commit the changes once everything checks out.

## 4. End the session

To finish, type `/exit` or press `Ctrl+Q` to exit AIxCoding-CLI.

## 5. Next steps

You have now installed AIxCoding-CLI and learned the basics of Q&A Agent and Code Agent, and how they work together in one session to complete a development task.

To continue exploring:

- [Configure agents](../guides/configuration/agents.md) to create or modify agents and set their instructions, models, tools, and sub-agents
- [Working directory](../guides/daily-use/workspaces.md)
- [Configure approval modes](../guides/configuration/approval.md)
- Extend AIxCoding-CLI with skills and MCP
