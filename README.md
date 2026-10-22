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
uv run aixcoding-cli               # `uv run chrys` starts the same thing (`Chrys` is our code name)
```

iCode ships no model profiles, so press **F4** on first launch to add one.

## Install from an internal mirror

The HTTP download root is `http://82.187.34.98/aixcoding/file/aixcoding`. Put `install.sh` and `install.ps1` at that root. `channels/cli/prod.txt` and `channels/cli/test.txt` each hold
one full version, and archives go in `releases/cli/<full-version>/`. The CD
workflow uploads each platform binary as a separate artifact; it does not bundle
the installer scripts. Place `install.sh` and `install.ps1` in the HTTP root
manually, and upload the matching binary artifact ZIPs to `releases/cli/<full-version>/`.
Set `channels/cli/prod.txt` or `channels/cli/test.txt` manually to the full version
after the upload finishes. A Linux-only build does not include macOS or
Windows packages. The build also uploads a wheel used to assemble the binaries;
it is not needed in the HTTP mirror.
For previously uploaded Linux/macOS packages, `install.sh` also accepts `icode-<platform>-v<version>-offline.tar.gz` or `.zip` with a root-level `icode` executable.

The HTTP download endpoint requires no FTP credentials. The public URL path
`/aixcoding/file/aixcoding/` maps to the server directory `/homepage/aixcoding/`.

| Machine | Package in the mirror | Install command |
| --- | --- | --- |
| Linux ARM64 | `aixcoding-cli-linux-aarch64-v<version>-offline.tar.gz` | `curl -fsSL 'http://82.187.34.98/aixcoding/file/aixcoding/install.sh' \| bash` |
| Linux x86-64 | `aixcoding-cli-linux-x86_64-v<version>-offline.tar.gz` | `curl -fsSL 'http://82.187.34.98/aixcoding/file/aixcoding/install.sh' \| bash` |
| macOS Apple silicon | `aixcoding-cli-macos-aarch64-v<version>-offline.tar.gz` | `curl -fsSL 'http://82.187.34.98/aixcoding/file/aixcoding/install.sh' \| bash` |
| macOS Intel | `aixcoding-cli-macos-x86_64-v<version>-offline.tar.gz` | `curl -fsSL 'http://82.187.34.98/aixcoding/file/aixcoding/install.sh' \| bash` |
| Windows x86-64 | `aixcoding-cli-windows-x86_64-v<version>-offline.zip` | `irm 'http://82.187.34.98/aixcoding/file/aixcoding/install.ps1' \| iex` (PowerShell) |

On Linux and macOS, the script reads `channels/cli/prod.txt` by default. For test packages,
download the script and run `bash install.sh --channel test`. To ensure a failed
script download stops the command, use
`curl -fsSL -o install.sh 'http://82.187.34.98/aixcoding/file/aixcoding/install.sh' && bash install.sh`.
The script selects the matching package and installs the `aixcoding` command.
Open a new terminal and run
`aixcoding --version` to verify it. Linux x86-64 requires glibc 2.17 or later;
Linux ARM64 requires glibc 2.18 or later.

On Windows, run the one-line command in the table in PowerShell. It installs the
current production version. For the test channel, run
`$env:ICODE_CHANNEL='test'; irm 'http://82.187.34.98/aixcoding/file/aixcoding/install.ps1' | iex`.
To inspect the script first or install a specific version, download it and run it locally:

```powershell
Invoke-WebRequest 'http://82.187.34.98/aixcoding/file/aixcoding/install.ps1' -OutFile install.ps1
.\install.ps1 -Version 0.28.0-dev-9011ff5
```

Open a new PowerShell window and run `aixcoding-cli --version`. The shell
`install.sh` is for Linux and macOS; `install.ps1` is for Windows x86-64.

## User guide

Press **F8** inside AIxCoding to open the built-in user guide, a complete walkthrough of using it.
The same pages live in [`docs/`](docs/), in [English](docs/en/start/what-is-aixcoding.md) and
[简体中文](docs/zh-Hans/start/what-is-aixcoding.md).

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
