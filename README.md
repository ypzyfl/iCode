```
   ▄   ▄▄▄▄
   ▀██████▀          █▄
 ▀▀  ██              ██
 ██  ██     ▄███▄ ▄████ ▄█▀█▄
 ██  ██     ██ ██ ██ ██ ██▄█▀
▄██  ▀█████▄▀███▀▄█▀███▄▀█▄▄▄
```

English | [简体中文](README.zh.md)

> **Work in progress.** Interfaces, file formats, and defaults still change between
> releases.

## What is iCode?

Let the screenshots speak for themselves.

> **Use a modern terminal.** iCode works best in one such as
> [Windows Terminal](https://github.com/microsoft/terminal) on Windows or
> [Ghostty](https://ghostty.org) on macOS and Linux.

### Home

The agent, model, approval mode and session at a glance, with agents (`#`), models (`$`),
commands (`/`), files (`@`) and the shell (`!`) a keystroke away from the input bar.

![iCode start screen with the Code Agent selected and an empty conversation sidebar](screenshots/homepage.png)

### Chat

Answers render as rich Markdown in the terminal, diagrams included.

![A chat answer rendering an entity diagram and a formatted bullet list](screenshots/chat.png)

### Workflows

Watch a workflow run node by node, with each agent node's model, tool calls and token spend.

![Workflow mode running the demo workflow, showing its node graph mid-run](screenshots/workflow.png)

### Agents

An agent is configuration, not code: instructions, tools, sub-agents, skills, MCP servers and
memory, all edited in one place (**F2**).

![The Agent Configuration screen editing the built-in Code Agent](screenshots/agents.png)

### Models

Model profiles from different providers side by side, switchable mid-conversation (**F4**).

![The Model Configuration screen editing a DeepSeek profile that uses the Responses API](screenshots/models.png)

### Diff

Every file the agent changed, turn by turn or all at once, in unified or split view.

![The diff viewer showing a change tree and a unified diff of a Python file](screenshots/diff.png)

### Rollback

Pick a turn, review the file changes that would be reverted, then discard the conversation
after it.

![The rollback dialog listing the file changes to revert after a chosen turn](screenshots/rollback.png)

### Trajectory

Where the time and tokens went (**F12**): model versus tools versus waiting, a per-turn
breakdown, and token and cache usage.

![The trajectory overview with time, token and parallelism breakdowns](screenshots/trajectory-overview.png)

Every model call, hook and tool call in a turn, laid out on a timeline.

![The trajectory timeline showing a turn's model cycles, hooks and tool calls](screenshots/trajectory-timeline.png)

### Shell

The shell (`!`) is a real terminal, so full-screen programs run in place with every keystroke
forwarded to them: here `htop`, inside iCode, inside iCode, inside iCode.

![Three nested iCode shells, the innermost running htop](screenshots/shell.png)

## How to run

[uv](https://github.com/astral-sh/uv) is the only prerequisite; it provisions Python 3.14
for you. From a checkout:

```bash
uv sync --extra all        # not bare `uv sync`, not `--all-extras`
./scripts/fetch_rg.sh      # downloads the vendored ripgrep; Windows: .\scripts\fetch_rg.ps1
uv run icode               # `uv run chrys` starts the same thing (`Chrys` is our code name)
```

iCode ships no model profiles, so press **F4** on first launch to add one.

## Install a packaged TUI from an internal mirror

Upload the files from the CD workflow's `icode-release-bundle` artifact to one
mirror directory. It contains `install.sh`, `latest.txt`, `SHA256SUMS.txt`, and
the packages built for the selected platforms. Replace `http://mirror.example/icode`
below with the URL of that directory. The mirror must contain the package for
the machine you are installing on; a Linux-only CD run does not produce the
macOS or Windows packages.

| Machine | Package selected from the mirror | Install command |
| --- | --- | --- |
| Linux ARM64 (aarch64) | `icode-linux-aarch64-v<version>-offline.tar.gz` | `curl -fsSL -o install.sh 'http://mirror.example/icode/install.sh' && ICODE_BASE_URL='http://mirror.example/icode' bash install.sh` |
| Linux x86-64 | `icode-linux-x86_64-v<version>-offline.tar.gz` | `curl -fsSL -o install.sh 'http://mirror.example/icode/install.sh' && ICODE_BASE_URL='http://mirror.example/icode' bash install.sh` |
| macOS Apple silicon | `icode-macos-aarch64-v<version>-offline.tar.gz` | `curl -fsSL -o install.sh 'http://mirror.example/icode/install.sh' && ICODE_BASE_URL='http://mirror.example/icode' bash install.sh` |
| macOS Intel | `icode-macos-x86_64-v<version>-offline.tar.gz` | `curl -fsSL -o install.sh 'http://mirror.example/icode/install.sh' && ICODE_BASE_URL='http://mirror.example/icode' bash install.sh` |
| Windows x86-64 | `icode-windows-x86_64-v<version>-offline.zip` | Use the PowerShell commands below; `install.sh` does not run on Windows. |

On Linux and macOS, the script reads `latest.txt`, selects the matching package,
and installs the `aixcoding` command. Downloading the script before running it
ensures a failed download stops the install. Open a new terminal, then run
`aixcoding --version` to check the installation. Linux x86-64 requires glibc
2.17 or later; Linux ARM64 requires glibc 2.18 or later.

On Windows, run this in PowerShell from the directory where you want to download
the package:

```powershell
$mirror = 'http://mirror.example/icode'
$version = (Invoke-RestMethod "$mirror/latest.txt").Trim().TrimStart('v')
$archive = "icode-windows-x86_64-v$version-offline.zip"
Invoke-WebRequest "$mirror/$archive" -OutFile $archive
Expand-Archive $archive -DestinationPath '.\icode-windows-x86_64' -Force
& '.\icode-windows-x86_64\icode.exe' install
```

Open a new PowerShell window and run `icode --version`. The current Windows
installer provides the `icode` command; the `aixcoding` alias is created by
`install.sh` on Linux and macOS.

## User guide

Press **F8** inside iCode to open the built-in user guide, a complete walkthrough of using it.
The same pages live in [`docs/`](docs/), in [English](docs/en/start/what-is-icode.md) and
[简体中文](docs/zh-Hans/start/what-is-icode.md).

## Privacy

iCode does not collect your data. It has no telemetry, analytics or crash reporting, and by
default it sends nothing, usage data included, to us or to any other third party. What iCode
itself sends goes only to destinations you configure: the model providers you add, the MCP
servers your agents use, and any hooks or OpenTelemetry export you set up. The web tools are
off by default. If you turn them on for an agent, its search queries go to the search provider
you configure, or to Exa's public search service (`mcp.exa.ai`) if you configure none, and the
pages it reads are requested directly from their websites. Shell commands, skill scripts and
workflows that you or your agents run are programs in their own right, with your network
access, so what they send is up to them. Your data is yours alone, and we respect your privacy.

## Regulatory compliance

iCode is solely a tool for orchestrating agents and workflows. It does not include or provide
any AI model; every model it uses is one you connect to it. When you integrate AI models into
iCode for a particular business or engineering use, you bear full responsibility for meeting
the compliance obligations that use carries under the EU AI Act (Regulation (EU) 2024/1689)
and any other applicable legal or regulatory framework.

## License

iCode is open source under the [Apache License 2.0](LICENSE). It also contains and bundles
third-party software, each part under its own license; [NOTICE](NOTICE) lists them with their
copyright notices and license terms.
