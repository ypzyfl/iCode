# What is AIxCoding-CLI?

**AIxCoding-CLI is a platform for running and building agents.**

AIxCoding-CLI lets you interact with agents in natural language to read and edit files, run shell commands, and search codebases. Complex tasks can also be delegated to sub-agents.

The main way to interact with AIxCoding-CLI is its terminal user interface (TUI), which brings conversations, task execution, and tool calls together in one place. Tool calls appear as cards so you can see what the agent is doing. Besides the TUI, AIxCoding-CLI also supports headless execution in scripts and running the TUI in a browser.

## 1. Key features

* **Flexible combinations of agents and models.** Switch agents and models with a click in the interface or a quick command, and choose different combinations for different tasks within the same session.

* **Configurable agents.** Configure an agent's instructions, model, tools, skills, MCP servers, and sub-agents through the TUI, or edit the YAML profile directly, without changing AIxCoding-CLI source code.

## 2. Using AIxCoding-CLI

AIxCoding-CLI offers several ways to work, depending on your needs:

- **TUI**: The main AIxCoding-CLI interface, suited to interactive tasks. View tool calls, handle approval requests, and switch agents within a session.
- **Headless command-line interface (CLI)**: Run non-interactive tasks with `aixcoding-cli run`, suited to one-off tasks, scripts, and automated workflows.
- **Browser interface**: Run the TUI in a browser when you need an interactive interface outside the terminal.


For first-time use, start with the TUI. An interactive session is a quick way to learn how agents, models, and tools work together.

When you are ready to start, read [Getting started with AIxCoding-CLI](./getting-started.md) for installation and your first run.
