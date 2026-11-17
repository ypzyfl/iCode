# Getting started with AIxCoding-CLI

This tutorial shows how to install AIxCoding-CLI and use agents to complete a development task in a project.

## 1. Install AIxCoding-CLI

AIxCoding-CLI provides prebuilt offline packages for macOS, Linux and Windows. Each package already bundles Python and all runtime dependencies, so you do not need to install Python separately.

In the commands below, `<version>` and `<architecture>` are placeholders. Replace them with the actual values from the filename you downloaded.

### macOS

Choose `aixcoding-cli-macos-aarch64-v<version>-offline.tar.gz` for Apple silicon or `aixcoding-cli-macos-x86_64-v<version>-offline.tar.gz` for Intel, then run the following in your download directory:

```bash
tar xzf aixcoding-cli-macos-<architecture>-v<version>-offline.tar.gz
chmod +x ./aixcoding-cli
./aixcoding-cli install
```

### Linux

Choose `aixcoding-cli-linux-x86_64-v<version>-offline.tar.gz` or `aixcoding-cli-linux-aarch64-v<version>-offline.tar.gz` for your processor, then run the following in your download directory:

```bash
tar xzf aixcoding-cli-linux-<architecture>-v<version>-offline.tar.gz
chmod +x ./aixcoding-cli
./aixcoding-cli install
```

The Linux x86-64 package requires glibc 2.17 or later, and the ARM64 package requires glibc 2.18 or later. Distributions that provide only musl, such as Alpine Linux, are not supported by the prebuilt packages.

The HTTP download root is `http://22.189.54.139/aixcoding/file/aixcoding`, which maps to the server directory `/homepage/aixcoding/`. The root holds `install.sh` and `install.ps1`; `channels/cli/prod.txt` and `channels/cli/test.txt` each hold one line with a full version number, and the packages are stored under `releases/cli/<full-version>/`. No FTP credentials are needed. macOS and Linux users can run the same command; the script detects the platform automatically and creates the `aixcoding` start command:

```bash
curl -fsSL -o install.sh 'http://22.189.54.139/aixcoding/file/aixcoding/install.sh' && bash install.sh
```

By default the production package is installed; to install a test build, run `bash install.sh --channel test`. The CD pipeline uploads each platform's binary artifact separately and does not package the install scripts. Place the two install scripts in the HTTP root manually, put each platform's artifact ZIP under `releases/cli/<full-version>/`, and write the full version number into the matching channel file; the build wheel does not need to be uploaded to the HTTP mirror. If only Linux is built, the artifacts contain only the Linux binary package. The five platform package names are listed in the README installation table.

### Windows

In PowerShell, run the following command to install the current Windows x86-64 package from the production channel:

```powershell
irm 'http://22.189.54.139/aixcoding/file/aixcoding/install.ps1' | iex
```

To install a test build, run `$env:AIXCODING_CHANNEL='test'` first, then run the command above. The installer attempts to add AIxCoding-CLI to the current user's `PATH`. Open a new terminal after installation.

### Verify the installation

```shell
aixcoding-cli --version
```

The command should print the AIxCoding-CLI version number. On macOS or Linux, if your system cannot find `aixcoding-cli`, add `~/.local/bin` to `PATH` as the installer instructs; if the installer reported that `~/.local/bin/aixcoding-cli` already exists, that command starts another program; use the `chrys` command instead. On Windows, open a new terminal; if the installer reported that updating the user PATH failed, add `%LOCALAPPDATA%\chrys\bin` to your user `PATH` manually.

> **About the start commands**: `aixcoding-cli` is the standard start command for this tool; `aixcoding` (created automatically by the install script) and `chrys` (the historical command name) are fully equivalent to it — typing any of them starts the same program. This guide consistently uses `aixcoding-cli`.

### Uninstall AIxCoding-CLI

Run:

```shell
aixcoding-cli uninstall
```

If you installed an offline package, the command lists what it will remove: the `aixcoding-cli` and `chrys` commands and the files the package unpacked. It removes them once you confirm. On Windows, it also removes AIxCoding-CLI from your user `PATH`, and the last files go a moment after the command exits. The package you downloaded stays where you saved it.

AIxCoding-CLI keeps its data in `~/.chrys` (`%APPDATA%\chrys` on Windows): your settings, API keys, model profiles, agents, skills, sessions and more. Uninstalling keeps this folder. To delete it and everything in it as well, run `aixcoding-cli uninstall --purge`; if you save sessions in another folder, the `sessions` folder there is deleted too. Add `--yes` to skip the confirmation.

## 2. Start AIxCoding-CLI in a project

Start this tutorial in a project managed with Git or one that you can safely restore. Before asking an agent to modify files, save any unsaved content and record existing changes with a Git commit. This lets you distinguish the agent's changes and restore the previous state if needed.

In a terminal, go to the project directory and start AIxCoding-CLI:

```shell
cd <project-directory>
aixcoding-cli
```

Replace `<project-directory>` with the actual path to your project. To switch directories after startup, see [Working directory](../guides/daily-use/workspaces.md).

AIxCoding-CLI first prints `Starting AIxCoding-CLI...` and shows a loading screen while it gets ready. When the main screen appears, it keeps showing that it is loading until the agent is ready.

While an agent runs, the status bar above the input shows elapsed time, tool calls and, while text is arriving, its speed. Long runs include hours and days, for example `1d 4h 20m 50s`. Tool cards, background tasks, CLI progress, and the F12 timing dashboard also support days; compact displays keep only the largest time units.

Once the agent answers, the answer's header shows how long the whole turn took, for example `Code Agent - 2:04 AM (6m 5s)`: from when you sent your message, or clicked **Continue** or **Retry**, to the answer, including the time the agent waited for your approval or reply. A message you send while the agent works doesn't restart it. It shows the same when you reopen the session.

## 3. Use agents

### Select an agent

AIxCoding-CLI provides two main agents by default: Q&A Agent and Code Agent. Both can read the project, analyze code, and discuss approaches, but they have different roles and tools. Q&A Agent primarily provides read-only capabilities for understanding projects, explaining code, and analyzing problems. Code Agent can modify files and run commands, making it suitable for writing, reviewing, refactoring, debugging, and validating code.

You can switch agents when no agent task is running. Type `#` in the input field to display the agent list above it. Select an agent by clicking it, or use the up and down arrow keys and press Enter. You can also click the agent name in the status bar above the input field to switch agents in the agent selection dialog.

### Use Q&A Agent

Q&A Agent helps you understand a project, analyze code, trace implementations, and discuss approaches **without modifying the project**. It answers based on the project contents and aims to provide evidence you can trace back to its source.

After switching to **Q&A Agent**, type `/new` in the input field and press Enter to start a new session.

The following examples assume the current project is a to-do app and illustrate how to use the agents. Adapt the questions and tasks to your own project.

```text
Analyze the task list implementation and propose a plan for adding a "Clear completed tasks" feature. Explain which files need to change and the implementation steps.
```

Q&A Agent may search for files, read their contents, or run read-only commands. Tool calls appear as cards, grouped under one header while the agent works through them. While they run, the header shows what the agent is doing; once they are done, it says what the calls did, by kind, for example `▸ Read 3 files · searched for 2 patterns · ran 1 command`, and ends with how many failed or were interrupted, if any, which stay in view when the window is too narrow for the whole line. When the agent made a single call there and it succeeded, the header says what that call did instead, for example `▸ Read src/app.py` or `▸ Ran zsh command: Run the tests`; a path inside the folder you work in is shown relative to it. While the agent waits with `sleep`, the header shows why and counts down the time left, for example `Sleeping: Waiting for CI · 29s left`; to stop waiting, open the cards and click **Skip**. Once done, it says how long the agent slept and why, for example `▸ Slept 23s: Waiting for CI`. Click the header to show or hide the cards. After completing its analysis, the agent presents an implementation plan.

### Use Code Agent

Code Agent handles tasks that require **modifying files, running commands, and validating results**. It reads the relevant code first, then implements, debugs, or refactors it as requested.

After Q&A Agent provides an implementation plan, you can switch to **Code Agent** in the same session. Switching agents preserves the current session's context, so Code Agent can continue the development task using the existing plan:

```text
Implement the "Clear completed tasks" feature using the plan we just discussed. Modify the code and run the necessary tests.
```

If an approval dialog appears, review the tool call before approving it. Pay particular attention to the command, target files, and scope of its effects, and approve only when they match your expectations. For the behavior of each approval mode, see [Configure approval modes](../guides/configuration/approval.md).

When the task is complete, review the agent's final response and use `/diff` to browse the file changes recorded in the current session. Then use Git or another version control tool to inspect the complete working directory changes. Confirm that the feature works correctly, the necessary tests pass, and there are no unrelated changes. Once you have verified the changes, you can commit them.

### Ask about AIxCoding-CLI itself

You can ask the agent about AIxCoding-CLI in the input field, for example:

- "What features does AIxCoding-CLI offer?"
- "How do I configure an MCP server in AIxCoding-CLI?"
- "How does AIxCoding-CLI's context compaction work?"

The agent looks up the answer in the user guide that comes with your installed version and tells you which pages it used. If a feature described in the guide is not turned on for the current agent, the answer says so. If the agent cannot read files, it tells you that it could not check the guide.

To read the guide yourself, type `/help` or press **F8**.

### Write multi-line messages

Press **Enter** to send a message, and **Shift+Enter**, **Ctrl+Enter** or **Ctrl+J** to start a new line. Press **Ctrl+O** to write in a larger editor.

Some terminals, including macOS's built-in Terminal and some tmux setups, can't tell Shift+Enter or Ctrl+Enter apart from Enter and send the message instead. Use Ctrl+J there.

In other multi-line fields, **Enter** and **Shift+Enter** start a new line. In the Ctrl+O editor, press **Ctrl+O** or **Ctrl+Enter** to commit.

### Attach images, quote the conversation and paste long text

Paste a screenshot or an image, or drop an image file into the message box, and it shows as **[Image #1]**. To quote part of the conversation, select it with the mouse and click **Quote** when it appears; **[Quote #1]** is added where the cursor is. Long pasted text, more than 800 characters or six lines or more (fewer in a very short terminal), shows as **[Pasted text #1 +5 lines]**. Keep typing around them as usual; each message numbers each kind from 1.

Click an image or quote label for a read-only preview. A label is edited as one piece: the cursor steps over it, and Backspace or Delete removes all of it. Click a pasted-text label to edit that text in the prompt editor; it stays folded while it is still long. Press **Ctrl+O** to open the prompt editor on the full text to be sent: save without changes to keep the labels; after any change, the message box shows the full text. Press **Ctrl+Z** to undo a save that changed the message.

When you send, each label is replaced by what it stands for: the images go to the model with your message, pasted text goes back where its label was, and a quote goes on lines of its own as a block quote, so any headings, lists or code in it stay inside the quote. A quote is what someone else said, so an `@file` or `` !`command` `` in it does nothing: it is sent with a backslash in front so it stays plain text. Pasted text counts as your own words and works like typed text. Your message, and what you bring back with the Up arrow or from prompt history, shows that full text rather than the labels. After you send a message, press **Ctrl+Z** in the empty message box to get the whole message back, labels included.

### Read and copy replies

All agents' replies support Markdown, formulas and Mermaid diagrams. Formulas in your own messages are not rendered as math.

Lists and quotes can contain headings, tables, code and formulas.

Single-line math is written with `$...$` or `\(...\)`. Display formulas in `math` code blocks, `$$...$$` or `\[...\]` can show fractions, matrices and aligned equations. Ordinary text, prices and shell variables keep their Markdown formatting. Formulas that are unsupported or too wide are shown as complete, wrapped source.

For example, `$x^{n+1}$` displays as xⁿ⁺¹ and `$90^\circ$` displays as 90°.

Mermaid code blocks appear as diagrams; choose **Open full diagram** to view and scroll the full result. Some diagrams are simplified with a notice; unsupported diagrams stay as source.

When the model service returns readable thinking, a folded row above the reply shows **Thinking**. As text arrives, the row adds an estimated token count and then the recent speed, for example `Thinking (3.2k tokens · 70 tok/s)`. The figures appear in muted text and update once a second. When thinking ends, the row shows **Thought:** followed by the opening words. Click it at any time, even while the model is still writing, to unfold it and read it in full, or to fold it again (`/fold` folds or unfolds all complete thinking, tool groups and text between tool calls at once). Once the model moves on to a tool call or its reply, the thinking folds, as tool groups do; so does text the model writes before a tool call, to one line showing how it begins. Thinking has no **Copy** button, and copying replies leaves it out. To see thinking unfolded while the model writes it, turn on **Expand thinking by default** in the Settings dialog (**General** → **Display preferences**).

Mouse selection copies what is displayed, without adding newlines for screen wrapping. Use **Copy** beside the message header to copy the original Markdown and LaTeX. Reopening an older conversation uses the current rendering.

## 4. End the session

To finish using AIxCoding-CLI, type `/exit` or press `Ctrl+Q` to exit.

## 5. Next steps

You have installed AIxCoding-CLI and learned the basics of Q&A Agent and Code Agent, including how to use them together in the same session to complete a development task.

You can continue exploring:

- [Configure agents](../guides/configuration/agents.md) to create or modify agents and set their instructions, models, tools, and sub-agents
- [Working directory](../guides/daily-use/workspaces.md)
- [Configure approval modes](../guides/configuration/approval.md)
- Extend AIxCoding-CLI with Skills and MCP
