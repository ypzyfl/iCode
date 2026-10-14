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

The FTP root is `ftp://82.186.78.127/homepage/aixcoding-TUI`. Put `install.sh` at that root. `channels/prod.txt` and `channels/test.txt` each hold
one full version, and archives go in `releases/<full-version>/`. The CD
workflow's flat `icode-release-bundle` artifact includes the platform archives,
`install.sh`, `README.md`, `version.txt`, and a wheel. Upload only `install.sh`
to the FTP root and the matching archives to `releases/<full-version>/`.
Set `channels/prod.txt` or `channels/test.txt` manually to the full version
after the upload finishes. A Linux-only build does not include macOS or
Windows packages.
For previously uploaded packages, the installer also accepts `icode-<platform>-v<version>-offline.tar.gz` or `.zip` with a root-level `icode` executable.

Configure curl's `~/.netrc` with the FTP host, username, and password, then run
`chmod 600 ~/.netrc`. The script uses `curl --netrc` for FTP downloads; no
credentials belong in the URL or script.

| Machine | Package in the mirror | Install command |
| --- | --- | --- |
| Linux ARM64 | `aixcoding-cli-linux-aarch64-v<version>-offline.tar.gz` | `curl --netrc -fsSL 'ftp://82.186.78.127/homepage/aixcoding-TUI/install.sh' \| bash` |
| Linux x86-64 | `aixcoding-cli-linux-x86_64-v<version>-offline.tar.gz` | `curl --netrc -fsSL 'ftp://82.186.78.127/homepage/aixcoding-TUI/install.sh' \| bash` |
| macOS Apple silicon | `aixcoding-cli-macos-aarch64-v<version>-offline.tar.gz` | `curl --netrc -fsSL 'ftp://82.186.78.127/homepage/aixcoding-TUI/install.sh' \| bash` |
| macOS Intel | `aixcoding-cli-macos-x86_64-v<version>-offline.tar.gz` | `curl --netrc -fsSL 'ftp://82.186.78.127/homepage/aixcoding-TUI/install.sh' \| bash` |
| Windows x86-64 | `aixcoding-cli-windows-x86_64-v<version>-offline.zip` | Use the PowerShell commands below. |

On Linux and macOS, the script reads `channels/prod.txt` by default. For test packages,
download the script and run `bash install.sh --channel test`. To ensure a failed
script download stops the command, use
`curl --netrc -fsSL -o install.sh 'ftp://82.186.78.127/homepage/aixcoding-TUI/install.sh' && bash install.sh`.
The script selects the matching package and installs the `aixcoding` command.
Open a new terminal and run
`aixcoding --version` to verify it. Linux x86-64 requires glibc 2.17 or later;
Linux ARM64 requires glibc 2.18 or later.

On Windows, run this in PowerShell from the directory where you want to download
the package:

```powershell
$mirror = 'ftp://82.186.78.127/homepage/aixcoding-TUI'
$channel = 'prod' # change to test for test packages
$version = (curl.exe --netrc --silent --show-error --fail "$mirror/channels/$channel.txt").Trim().TrimStart('v')
$archive = "aixcoding-cli-windows-x86_64-v$version-offline.zip"
curl.exe --netrc --fail --location --output $archive "$mirror/releases/$version/$archive"
Expand-Archive $archive -DestinationPath '.\aixcoding-cli-windows-x86_64' -Force
& '.\aixcoding-cli-windows-x86_64\aixcoding-cli.exe' install
```

Open a new PowerShell window and run `aixcoding-cli --version`. The shell
`install.sh` is for Linux and macOS.

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
