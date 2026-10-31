# 考古扫描报告（candidate custom points）

- 扫描目标：`D:\Coding\aixcoding\aixcoding-cli\aixcoding-cli__0.28.0_final`
- 上游侧标记命中：932（注释标记 24 / 非注释命中 908）
- 定制资产文件数：57（aixcoding/ + src/chrys/aixcoding/）

## 上游侧命中（甄别分类；非注释命中多为品牌字符串，需人工判定归属）

| 类型 | 文件:行 | 内容 | 归属模块 |
| --- | --- | --- | --- |
| 非注释命中 | AGENTS.md:3 | Chrys is a Python 3.14+ agent platform: Textual TUI, headless CLI and ACP server. Users see it as **AIxCoding** / `aixcoding-cli` (`foundation/branding.py`; `msg()` fallbacks write `{app}`, bound with `app=APP_DISPLAY_NAME`); the package, the `chrys` command, `~/.chrys`, `CHRYS_*`, wire/header names and data keys keep `chrys`. `pyproject.toml` is the source of truth for version and deps. Paths are under `src/chrys/` unless they start with `tests/`, `scripts/`, `docs/`, `locales/`, `.github/` or name a root file; a bare file name continues the directory named just before it. | — |
| 非注释命中 | AGENTS.md:114 | - **User guide** (F8 or `/help`; `app/tui/screens/guides/`): reads `docs/index.yaml` + `docs/<locale>/` at runtime; the wheel bundles `docs/` via `force-include` (CI checks it); `CHRYS_DOCS_ROOT` overrides. A page must be listed in `index.yaml`; say AIxCoding/`aixcoding-cli` (internal names stay); `#anchors` are GitHub heading slugs. | — |
| 非注释命中 | README.md:147 | Press **F8** inside AIxCoding to open the built-in user guide, a complete walkthrough of using it. | — |
| 非注释命中 | README.zh.md:127 | 在 AIxCoding 中按 **F8** 即可打开内置的用户指南，其中完整介绍了 AIxCoding 的使用方法。相同的内容也位于 [`docs/`](docs/) 目录，提供 [English](docs/en/start/what-is-aixcoding.md) 和 [简体中文](docs/zh-Hans/start/what-is-aixcoding.md) 两个版本。 | — |
| 非注释命中 | docs/en/guides/configuration/agents.md:3 | AIxCoding uses agent profiles to define an agent's name, instructions, model, available tools, sub-agents, and other settings. This guide explains how to create, clone, edit, reset, switch, and delete agent profiles in the terminal user interface (TUI), and how to configure models and sub-agents for an agent. | — |
| 非注释命中 | docs/en/guides/configuration/agents.md:57 | Use cloning to create a new profile based on an existing agent. Cloning creates an independent copy without changing the original profile. When you clone a built-in agent, AIxCoding creates a custom agent copy that you can edit independently. | — |
| 非注释命中 | docs/en/guides/configuration/agents.md:61 | 3. AIxCoding copies the agent's configuration, generates unique values for its name and display name, and selects the new copy. | — |
| 非注释命中 | docs/en/guides/configuration/agents.md:78 | - You cannot change **Name** or **Agent Type** for the built-in agents included with AIxCoding, such as Code Agent and Q&A Agent. Other settings can be adjusted as needed. | — |
| 非注释命中 | docs/en/guides/configuration/agents.md:84 | Deleting a custom agent also removes its configuration stored on your machine. This cannot be undone in AIxCoding. Built-in agents cannot be deleted. | — |
| 非注释命中 | docs/en/guides/configuration/agents.md:97 | If you delete the agent currently in use, AIxCoding automatically switches to another available main agent when you close the configuration window. | — |
| 非注释命中 | docs/en/guides/configuration/agents.md:101 | The built-in agents included with AIxCoding cannot be deleted. | — |
| 非注释命中 | docs/en/guides/configuration/agents.md:103 | When you edit and save a built-in agent, AIxCoding creates a user profile file with the same name, such as `Code.yaml`, in the [user agent profile directory](../../reference/agent-profile.md#user-agent-profile-directory). This file stores both your changes and the other settings in effect at that time. For example, if you only add an MCP server, the saved profile contains that server and retains the current values of the other settings. | — |
| 非注释命中 | docs/en/guides/configuration/agents.md:105 | At startup, AIxCoding gives precedence to the user profile file with the same name, instead of merging user and built-in settings field by field. As a result, after an AIxCoding upgrade, updates to built-in defaults such as agent instructions are not automatically applied to that agent. | — |
| 非注释命中 | docs/en/guides/configuration/agents.md:142 | The Code Agent and Q&A Agent included with AIxCoding can serve as main agents. Explore and General are sub-agents only. External ACP agents are also sub-agents only. To configure them, see [Configure external ACP agents](../extensions/external-acp-agents.md). | — |
| 非注释命中 | docs/en/guides/configuration/agents.md:178 | After switching, AIxCoding immediately uses the selected agent for subsequent requests. The current agent is grayed out in the list, with a hollow circle before its name. The list shows only profiles that can serve as main agents. | — |
| 非注释命中 | docs/en/guides/configuration/approval.md:3 | When an agent makes a tool call, such as running a Shell command or writing a file, AIxCoding may require approval first. This guide explains how to choose an approval mode and handle approval requests in the terminal user interface (TUI), as well as how approval settings differ across ways of running AIxCoding. | — |
| 非注释命中 | docs/en/guides/configuration/approval.md:7 | The approval mode determines how AIxCoding handles tool calls that require approval. Which calls require approval depends on both the `approval` policy in the agent profile and AIxCoding's safety rules. See the [approval field in the agent profile reference](../../reference/agent-profile.md#approval). | — |
| 非注释命中 | docs/en/guides/configuration/approval.md:17 | **Approval judge model**: In automatic mode, AIxCoding calls the approval judge model and sends it the current time, the workspace directories, all user prompts of the current turn and the latest of them, and the tool name, tool kind, and arguments. By default, the approval judge uses the current session's model. To change it, press **F10** to open **Settings**, select the **Models & Agents** tab, and change **Approval judge model** in the **Model roles** section. | — |
| 非注释命中 | docs/en/guides/configuration/approval.md:44 | - In automatic mode, the dialog initially shows **Evaluating**. If the model judges the call safe, the dialog closes automatically. If the model judges it suspicious, the title changes to **Flagged by Auto-Review** and the dialog shows the reason and waits for a person to decide. You can also approve or decline directly while evaluation is in progress. If the approval judge model is unavailable or evaluation fails, AIxCoding keeps the dialog open for a person to decide instead of approving the tool call automatically. | — |
| 非注释命中 | docs/en/guides/configuration/approval.md:69 | - In manual mode, the **Approval Required** dialog opens. After approval, AIxCoding version is displayed. | — |
| 非注释命中 | docs/en/guides/configuration/approval.md:71 | - In bypass mode, the command runs and displays AIxCoding version without an approval dialog. | — |
| 非注释命中 | docs/en/guides/configuration/approval.md:73 | ## Approval modes in other ways of running AIxCoding | — |
| 非注释命中 | docs/en/guides/configuration/approval.md:75 | Other ways of running AIxCoding use the following approval modes and switching methods: | — |
| 非注释命中 | docs/en/guides/configuration/approval.md:78 | - **AIxCoding ACP server**: Defaults to manual mode. Use `aixcoding-cli acp --approval manual\|auto\|bypass` to set the initial mode. ACP clients that support this capability can also switch the current session's mode. | — |
| 非注释命中 | docs/en/guides/configuration/compaction.md:3 | When a long conversation approaches the model's context window, AIxCoding automatically compacts earlier content to make room for subsequent requests. This guide explains how to configure the Last Words supplement and output limit for agents of the "Built-in" type. External ACP agents manage their own context. | — |
| 非注释命中 | docs/en/guides/configuration/compaction.md:9 | AIxCoding automatically calculates when to start compaction based on the maximum context window, maximum output tokens, and a safety margin for the current model profile. Set the maximum context window and maximum output tokens in the [model profile](./models.md) according to the model's capabilities and your task requirements. The "Compaction" tab does not provide a separate setting for when compaction starts. | — |
| 非注释命中 | docs/en/guides/configuration/compaction.md:11 | When the context is nearly full, AIxCoding also lowers the output limit of the next request so that its input and output fit in the context window, leaving a small margin for error in its token estimate. | — |
| 非注释命中 | docs/en/guides/configuration/compaction.md:13 | During compaction, AIxCoding first summarizes older tool results and, if needed, removes older tool calls together with their results. If it still needs to free up space, it replaces completed turns in the current context with a compaction summary. If these steps are still insufficient, AIxCoding generates Last Words for the current task to preserve the information needed to continue, then removes the current turn's tool calls, tool results, and intermediate content from the context supplied to the model, keeping the user's messages. | — |
| 非注释命中 | docs/en/guides/configuration/memory.md:7 | **Memory is added to the system prompt when the main agent loads.** AIxCoding reads the memory files configured for the current main agent and provides their content to the agent as reference material. Memory content uses part of the model's context window and is sent to the model service with requests. Avoid including sensitive information such as secret keys or access tokens in memory. | — |
| 非注释命中 | docs/en/guides/configuration/memory.md:11 | **Memory is suited to stable, reusable information.** AIxCoding only loads memory files with the `.md` or `.txt` extension. Memory should contain information that can be reused across tasks, such as project conventions, background material, and frequently needed information. Keep it brief, clear, and up to date; instructions for a temporary task are better included directly in the current request. | — |
| 非注释命中 | docs/en/guides/configuration/memory.md:13 | **The default agents already use AGENTS.md as memory.** The main agents included with AIxCoding, such as Code Agent, load `AGENTS.md` from the working directory. To add general project instructions, start by maintaining this file. If it is not needed, remove its entry from the "Memory" tab. | — |
| 非注释命中 | docs/en/guides/configuration/memory.md:28 | AIxCoding first loads the `.md` and `.txt` files directly in the folder, then scans subfolders one level at a time. For each configured folder, it scans at most two levels of subfolders and loads at most 100 files. If an important file may fall outside these limits, add it separately in the "Files" section. | — |
| 非注释命中 | docs/en/guides/configuration/memory.md:32 | If the same file is both added individually and discovered in a folder, it is loaded only once. The combined content from all memory sources is limited to 35,000 tokens. Individually added files load first, then folders. Once a file would exceed the limit, that file and all remaining files are skipped, and AIxCoding displays a warning. | — |
| 非注释命中 | docs/en/guides/configuration/memory.md:34 | After switching working directories or changing the current agent profile, AIxCoding reloads memory using the new paths. | — |
| 非注释命中 | docs/en/guides/configuration/memory.md:36 | AIxCoding does not monitor loaded memory files for changes. After editing a file directly on disk, reload the main agent for the changes to take effect. For example, restart AIxCoding, switch working directories, modify and save the current agent profile, or switch to another main agent and then switch back. | — |
| 非注释命中 | docs/en/guides/configuration/models.md:46 | Replace `PROVIDER_API_KEY` with the name of the environment variable that holds the key. Make sure the variable is set before starting AIxCoding. Environment variable names can contain only letters, numbers, and underscores, and cannot start with a number. | — |
| 非注释命中 | docs/en/guides/configuration/models.md:54 | 3. AIxCoding creates and selects a copy containing all fields from the original profile, and generates a unique name for it. | — |
| 非注释命中 | docs/en/guides/configuration/models.md:70 | Deleting a profile removes its local model profile file and **cannot be undone in AIxCoding**. Once you are sure you no longer need the profile: | — |
| 非注释命中 | docs/en/guides/configuration/models.md:77 | AIxCoding keeps at least one model profile, so "Delete" is unavailable when only one remains. If you delete the profile currently in use, AIxCoding automatically switches to another selectable profile after you close the configuration window. | — |
| 非注释命中 | docs/en/guides/configuration/models.md:108 | AIxCoding should respond with a greeting. If the model service returns an error, first check the model ID, base URL, API key, and other model profile settings. | — |
| 非注释命中 | docs/en/guides/configuration/models.md:112 | - **The error message contains `The Chat Completions client supports only n=1`**: With the Chat Completions style, AIxCoding processes only one response per request and does not support multiple candidate responses, so the `n` parameter must be omitted or set to the integer `1`. Remove the value or set it to `1` in the profile's "Chat Options", including when it was set indirectly through `extra_body`. | — |
| 非注释命中 | docs/en/guides/configuration/models.md:115 | ### If AIxCoding can't reach the model service | — |
| 非注释命中 | docs/en/guides/configuration/models.md:117 | When AIxCoding can tell why a model request failed, it says so in plain words, with the original error text below it; a paused sub-agent's card shows both as well. While AIxCoding retries, the retry notice shows only the plain-words message. If the device running AIxCoding doesn't seem to have a network connection, AIxCoding says so as well; check that first. | — |
| 非注释命中 | docs/en/guides/configuration/settings.md:1 | # Configure AIxCoding-CLI settings | — |
| 非注释命中 | docs/en/guides/configuration/settings.md:3 | AIxCoding settings control the interface appearance, default agent, sessions, tools, notifications, and some security options. This guide explains how to configure these basics in the terminal user interface (TUI) and check when changes take effect. | — |
| 非注释命中 | docs/en/guides/configuration/settings.md:5 | To edit `settings.yaml` directly or configure settings through environment variables, see the [AIxCoding settings file reference](../../reference/settings.md) for file locations, settings keys, and source precedence. | — |
| 非注释命中 | docs/en/guides/configuration/settings.md:43 | \| A message showing how many changes apply after restart \| Changes are saved, but you must quit and restart AIxCoding for them to take effect \| | — |
| 非注释命中 | docs/en/guides/configuration/settings.md:56 | \| UI Language \| Changes only AIxCoding interface text, not conversation content, the model's output language, or existing records. You can also switch the interface language with `/language`. \| Immediately \| | — |
| 非注释命中 | docs/en/guides/configuration/settings.md:62 | \| Save prompt history \| Saves submitted input across sessions for reuse. When no other dialog covers the main screen, press **Ctrl+R** to open the prompt history list above the input field. Click an entry, or select it with the up and down arrow keys and press **Enter**, to copy the prompt into the input field. The history file, `prompt_history.jsonl`, is stored in `~/.chrys/` on macOS and Linux, or `%APPDATA%\chrys\` on Windows. Turning this setting off does not delete the file; AIxCoding stops reading it, and **Ctrl+R** shows "No results". Re-enable the setting and restart AIxCoding to read the file's entries again. To clear the history, delete the history file; deletion cannot be undone. \| After restart \| | — |
| 非注释命中 | docs/en/guides/configuration/settings.md:94 | \| Default approval mode \| Sets the default approval mode for the next AIxCoding launch; it does not affect the current session. Only `manual` and `auto` are offered; to bypass approval in the current session, use `/approval bypass`. For switching the current session's mode and the differences between modes, see [Configure approval modes](./approval.md). \| Saved immediately; applies at the next launch \| | — |
| 非注释命中 | docs/en/guides/configuration/settings.md:101 | \| Load project hooks \| Controls whether AIxCoding loads hooks from `.chrys/hooks` in the current working directory; it does not affect user-level hooks. To create and validate hooks, see [Configure and write hooks](../extensions/hooks.md). For the complete configuration fields, see the [Hooks configuration reference](../../reference/hooks.md). \| On close \| | — |
| 非注释命中 | docs/en/guides/configuration/settings.md:107 | \| Capture raw HTTP traffic \| Records model requests and responses for troubleshooting. **Logs may contain API keys, complete prompts, and model responses in plain text.** Enable this only while troubleshooting and protect the log files. When finished, turn it off promptly and restart AIxCoding. The log file, `llm_raw_http.jsonl`, is stored in the current session folder; see [Find the session ID and storage location](../daily-use/sessions.md#find-the-session-id-and-storage-location). \| After restart \| | — |
| 非注释命中 | docs/en/guides/configuration/settings.md:113 | \| OpenTelemetry export \| Enables telemetry to record traces, logs, and metrics. When disabled, the other two settings do not cause AIxCoding to save or send telemetry. \| After restart \| | — |
| 非注释命中 | docs/en/guides/configuration/settings.md:125 | \| Auto-generate session titles \| Makes additional model requests to generate titles based on the conversation. **Once you set a session title manually, AIxCoding stops updating that session's title automatically.** To set or clear a manual title, see [Change a session title](../daily-use/sessions.md#change-the-session-title). \| On close \| | — |
| 非注释命中 | docs/en/guides/configuration/settings.md:131 | \| Session storage root \| Determines where AIxCoding saves sessions. Leave blank to use the default location; sessions are stored in the root's `sessions` subdirectory. "In use" shows the `sessions` directory used by the current launch. After changing the root, restart AIxCoding to use the new location; until then, sessions continue to be saved in the directory shown under "In use". **After restart, new sessions are saved in the new directory, but existing session files are not moved automatically.** To continue using existing sessions at the new location, see [Migrate session storage](../daily-use/sessions.md#migrate-session-storage). \| After restart \| | — |
| 非注释命中 | docs/en/guides/configuration/settings.md:137 | \| Rollback snapshots to keep \| Sets the maximum number of rollback snapshots kept per session. AIxCoding creates a snapshot before it starts processing each newly submitted prompt; older snapshots are deleted automatically when the limit is exceeded. Snapshots are stored in the session folder's `snapshots` subdirectory. Keeping more snapshots lets `/rollback` return to more earlier session states, but uses more disk space. \| On close \| | — |
| 非注释命中 | docs/en/guides/configuration/settings.md:169 | \| Ask-user timeout (seconds) \| Sets how long AIxCoding waits for an answer. When left blank, it uses the default value shown in the TUI. If no answer arrives before the timeout, AIxCoding returns a timeout result to the agent. Set to `0` to wait until an answer arrives or the task is interrupted. When using an ACP client such as an IDE plugin, `ask_user` has no server-side time limit by default; to set one, use `--ask-user-timeout` when starting the ACP server. \| On close \| | — |
| 非注释命中 | docs/en/guides/configuration/settings.md:181 | \| Workspace change notices \| When processing a newly submitted prompt, AIxCoding gives the agent a summary of working directory file changes since the previous prompt was submitted. This includes changes made by the current session's agent and its sub-agents, as well as changes made manually, by other programs, or by other AIxCoding sessions. \| On close \| | — |
| 非注释命中 | docs/en/guides/configuration/settings.md:196 | \| Suppress while AIxCoding is focused \| Prevents desktop popups and sounds while AIxCoding is in the foreground. \| Immediately \| | — |
| 非注释命中 | docs/en/guides/configuration/themes.md:61 | Select a user theme at the top of the editor and click “Delete”. Check the theme name in the confirmation dialog, then click “Delete” again. Deleting the currently applied theme switches AIxCoding to the default theme, `chrys`. | — |
| 非注释命中 | docs/en/guides/configuration/tools.md:3 | Built-in tools let agents access files, search content, execute shell commands, and use other AIxCoding features. This guide explains how to enable or disable built-in tool kinds for an agent in the terminal user interface (TUI). | — |
| 非注释命中 | docs/en/guides/configuration/tools.md:34 | Web search is off in every agent shipped with AIxCoding, and it is separate from File search, which only searches local files. Web fetch is a separate switch. With no search provider configured, queries go to Exa's public search service. Before you turn it on, see [Configure web tools](./web-tools.md) for where requests go, approval, and network limits. | — |
| 非注释命中 | docs/en/guides/configuration/tools.md:40 | By default, questions appear in an ask-user dialog. If the dialog obscures conversation content you need to review, click **Answer Inline** to show the current question in the conversation instead; this applies only to the current question. If you want future questions to appear in the conversation by default, enable **Show questions in the chat** in [Configure AIxCoding settings](./settings.md). | — |
| 非注释命中 | docs/en/guides/configuration/tools.md:44 | The wait time for an answer is controlled by the **Ask-user timeout (seconds)** setting in [Configure AIxCoding settings](./settings.md). | — |
| 非注释命中 | docs/en/guides/configuration/tools.md:58 | For filesystem, search, and Shell tools, relative paths are resolved against the current [working directory](../daily-use/workspaces.md), and shell commands run in the current working directory by default. Switching working directories changes the base for these relative paths and the default working directory for commands. The working directory is the default location for operations; it does not restrict tools to paths within it. Whether an operation can run also depends on its tool arguments, whether approval is granted when required, and the permissions of the system user running AIxCoding. | — |
| 非注释命中 | docs/en/guides/configuration/web-tools.md:5 | **Web tools are off by default.** No agent shipped with AIxCoding (Code, QA, Explore, or General) includes them, so AIxCoding sends no search queries and fetches no pages until you enable the tools for an agent. | — |
| 非注释命中 | docs/en/guides/configuration/web-tools.md:22 | Web tools belong to each agent separately. A sub-agent such as General gets them only if its own profile includes them. To add them to a built-in agent, edit and save it in the TUI; AIxCoding then saves your own copy of that agent (see [Override built-in agents](../../reference/agent-profile.md#override-built-in-agents)). | — |
| 非注释命中 | docs/en/guides/configuration/web-tools.md:40 | With `web_search` turned on and no provider configured, the default mode `auto` sends your search queries to **Exa's public, anonymous search endpoint at `https://mcp.exa.ai/mcp`**. Exa is a third-party search service. No API key or account is needed. AIxCoding sends only what the agent searches for and how many results it wants, not your files or the conversation itself; the agent writes the queries, so they can include details from your task. The service has free-tier rate limits and can be unavailable. To send queries somewhere else, [choose a search provider](#choose-a-search-provider); to stop searching, set the mode to `off`. | — |
| 非注释命中 | docs/en/guides/configuration/web-tools.md:68 | If the combination is invalid, such as `auto` with a `providers` map but no `fallback_chain`, the agent starts without its web tools and AIxCoding shows a warning with the reason (see [When web tools do not appear](#when-web-tools-do-not-appear)). An unknown mode or a malformed provider entry makes the whole profile invalid instead. | — |
| 非注释命中 | docs/en/guides/configuration/web-tools.md:117 | AIxCoding reads the key from the environment that started AIxCoding or from your user `.env` file (macOS / Linux: `~/.chrys/.env`; Windows: `%APPDATA%\chrys\.env`). A variable set in the starting environment takes precedence, even when it is empty. A `.env` file in the working directory cannot provide web credentials. The user `.env` file is read each time the agent is built, so after changing it, save the agent again or restart AIxCoding. Only the keys of the providers the agent actually uses are read. | — |
| 非注释命中 | docs/en/guides/configuration/web-tools.md:121 | In `auto` mode, AIxCoding tries the providers in `fallback_chain` in order and returns the first answer, including an empty one. It moves on to the next provider when: | — |
| 非注释命中 | docs/en/guides/configuration/web-tools.md:130 | For keyed and custom providers, an HTTP 4xx error usually means a configuration problem, such as a wrong key, so the chain stops and the agent receives the error with its status, for example `Error: http_4xx (HTTP 403)`. Errors caused by the request itself, such as an empty query, also stop the chain. There is no hidden fallback: AIxCoding tries only the providers you list. | — |
| 非注释命中 | docs/en/guides/configuration/web-tools.md:210 | - **Public addresses only**: before connecting, AIxCoding resolves the host name and refuses private, loopback, link-local, and other non-public addresses unless the origin is in `private_origins`. AIxCoding then connects to the address it checked, while keeping the original host name for the request and TLS certificate checks. With **Web proxy DNS** set to `remote`, the proxy resolves the name instead; see [Use a fake-IP proxy](#use-a-fake-ip-proxy). | — |
| 非注释命中 | docs/en/guides/configuration/web-tools.md:213 | - **Proxy**: web tools ignore proxy variables such as `HTTP_PROXY` and `HTTPS_PROXY`. To use a proxy, set **Web proxy URL** (`tools.web_egress.proxy_url`) to an `http://` or `https://` proxy address without credentials or a path. It applies only to web tools. With **Web proxy DNS** at its default `local`, AIxCoding reaches a site through the proxy at its IPv4 addresses only, so a site that has only IPv6 addresses fails with `proxy_ipv6_unsupported`. With `remote`, the proxy resolves the name and may reach such a site over IPv6. In either mode, a URL that names an IPv6 address directly, such as `https://[2001:db8::1]/`, cannot go through the proxy. Certificate settings from the environment, such as `SSL_CERT_FILE`, are still honored. | — |
| 非注释命中 | docs/en/guides/configuration/web-tools.md:232 | With `remote`, AIxCoding sends the host name to the proxy, and the proxy decides which address it finally connects to. Blocking private and other non-public destinations for a name is then the proxy's job, not AIxCoding's. AIxCoding still applies every other rule: HTTPS only, the origin lists, redirect checks, and TLS certificate checks against the host name. It also still refuses URLs that name a non-public address directly, such as `https://127.0.0.1` or `https://localhost`, unless the origin is in `private_origins`. An IPv6 address written in a URL still cannot go through a proxy and fails with `proxy_ipv6_unsupported`. | — |
| 非注释命中 | docs/en/guides/configuration/web-tools.md:234 | AIxCoding never switches to `remote` on its own. Adding the fake-IP range to `private_origins` is not a substitute: the lists hold single origins, and exempting the range would also let names that resolve to your own network through. | — |
| 非注释命中 | docs/en/guides/configuration/web-tools.md:238 | The agent can limit a search to `allowed_domains` or exclude `blocked_domains`, but not both at once. A domain also covers its subdomains. AIxCoding always checks the results itself, and how much the provider helps depends on the provider: | — |
| 非注释命中 | docs/en/guides/configuration/web-tools.md:241 | - Exa's public endpoint cannot filter, so AIxCoding asks it for more results and keeps only the matching ones. | — |
| 非注释命中 | docs/en/guides/configuration/web-tools.md:266 | - AIxCoding does not run JavaScript, does not read `robots.txt`, and does not summarize pages. Use `denied_origins` to keep `web_fetch` away from specific origins. Each entry matches exactly one origin: it does not cover subdomains or the `www.` variant, so list each one you mean. | — |
| 非注释命中 | docs/en/guides/configuration/web-tools.md:268 | Search results and page text come from outside sources. AIxCoding marks them as untrusted data for the agent; check the source links before relying on important claims. | — |
| 非注释命中 | docs/en/guides/configuration/web-tools.md:272 | Some model services can run web search themselves. When a model profile declares such a tool in its `chat_options`, for example `{"tools": [{"type": "web_search"}]}`, the provider's tool takes over that name. If the agent also includes the matching AIxCoding tool, the local tool is turned off for that run and AIxCoding shows a notice once. This works per name: a provider-run `web_search` leaves a local `web_fetch` in place. | — |
| 非注释命中 | docs/en/guides/configuration/web-tools.md:274 | Provider-run search happens on the model provider's side, so AIxCoding's approval rules and network settings do not apply to it. To use AIxCoding's own tools instead, remove the declaration from the model's `chat_options`. | — |
| 非注释命中 | docs/en/guides/configuration/web-tools.md:278 | If AIxCoding cannot set up an agent's web tools, for example because a key variable is missing or a custom endpoint is not granted, the agent still starts without them and AIxCoding shows a warning that names the agent and the reason. Fix the configuration, then save the agent again or restart AIxCoding. | — |
| 非注释命中 | docs/en/guides/daily-use/sessions.md:3 | A session contains conversation history and related data, such as rollback snapshots and diagnostic logs. AIxCoding saves sessions automatically so you can resume a conversation or look up past tasks later. This guide explains how to switch, name, find, resume, and delete sessions in the terminal user interface (TUI), and how to migrate existing sessions when changing their storage location. | — |
| 非注释命中 | docs/en/guides/daily-use/sessions.md:22 | After you set a title manually, the new title appears in the session list and on the main screen, and AIxCoding stops updating that session's title automatically. If [automatic session titles](../configuration/settings.md#sessions) are enabled, clearing the "Session Title" dialog and saving restores the existing automatic title and lets AIxCoding continue updating it automatically during subsequent tasks. | — |
| 非注释命中 | docs/en/guides/daily-use/sessions.md:30 | - **Filter by where a session was last used**: The "TUI", "CLI", and "ACP" checkboxes above the search field show sessions last used in the TUI, in [`aixcoding-cli run`](../running/aixcoding-run.md), or in an editor or other client connected through [`aixcoding-cli acp`](../running/aixcoding-acp.md). Only "TUI" is checked at first. Sessions from earlier AIxCoding versions count as TUI. AIxCoding remembers your choice until you quit it. Hover over a session to see where it was last used. | — |
| 非注释命中 | docs/en/guides/daily-use/sessions.md:34 | - **Resume a session**: Select a session and click "Resume". You can also double-click it, or select it with the up and down arrow keys and press Enter. AIxCoding closes the current conversation view, loads the selected session, and switches the working directory to the session's saved primary working directory; the current session remains saved in the list. Before resuming, check the working directory that will be restored in the list's "Directory" column. | — |
| 非注释命中 | docs/en/guides/daily-use/sessions.md:36 | When you resume a long conversation, AIxCoding shows its most recent part first so you can continue right away; earlier messages keep loading above it for a few seconds. | — |
| 非注释命中 | docs/en/guides/daily-use/sessions.md:44 | Deleting the current session also starts a new session, like `/clear`. A session open in another AIxCoding instance cannot be deleted; close that instance first. | — |
| 非注释命中 | docs/en/guides/daily-use/sessions.md:58 | Before starting, finish the current task and close other AIxCoding instances, then follow these steps: | — |
| 非注释命中 | docs/en/guides/daily-use/sessions.md:67 | \| already present \| The destination already contains the same session ID, so it was skipped. AIxCoding does not compare or update the destination contents. \| If you cannot confirm which version is at the destination, use an empty destination directory and migrate again, or keep the source data. \| | — |
| 非注释命中 | docs/en/guides/daily-use/sessions.md:68 | \| active \| The session is open in an AIxCoding instance, so it was skipped. \| Close other instances and retry. If it is the current session, close settings and run `/new`; do not send a message in the new session, then migrate again. \| | — |
| 非注释命中 | docs/en/guides/daily-use/sessions.md:73 | 5. Close all AIxCoding instances and restart, then press **F1** to open the "Chat Sessions" window and confirm that important sessions appear and can be resumed. | — |
| 非注释命中 | docs/en/guides/daily-use/sessions.md:75 | Migration keeps the original data in the source directory; it is not deleted automatically. After confirming that migration is complete, if you need to free up space, close AIxCoding and archive or delete the old `sessions` directory shown under "From" in the migration window. Manual deletion cannot be undone. | — |
| 非注释命中 | docs/en/guides/daily-use/workspaces.md:3 | The working directory is the default directory AIxCoding uses for file operations and command execution. Before asking the agent to modify files, save any unsaved content to disk and record existing changes with a Git commit. This makes it easier to distinguish the agent's changes and restore the previous state if needed. | — |
| 非注释命中 | docs/en/guides/daily-use/workspaces.md:7 | In a terminal, enter the project directory and start AIxCoding: | — |
| 非注释命中 | docs/en/guides/daily-use/workspaces.md:14 | AIxCoding uses the directory it was started in as the working directory. | — |
| 非注释命中 | docs/en/guides/daily-use/workspaces.md:32 | `<project-directory>` can be an absolute path or a path relative to the current working directory. If the target does not exist or is not a directory, AIxCoding displays an error and keeps the current working directory. | — |
| 非注释命中 | docs/en/guides/daily-use/workspaces.md:36 | When switching working directories, AIxCoding reloads the current agent and loads memory and skills from the new working directory. For configuration details, see [Configure memory](../configuration/memory.md) and [Install and use skills](../extensions/skills.md). | — |
| 非注释命中 | docs/en/guides/extensions/external-acp-agents.md:5 | **External ACP agents can be used as sub-agents or workflow nodes, but not as the main chat agent**. Each time an external ACP agent is called, AIxCoding starts an external agent process for that invocation and communicates with it over ACP. The external agent handles the task and tool calls; approval requests, execution status, progress updates, and the final result are passed over the ACP connection. When the invocation ends, AIxCoding closes the connection and terminates the process. | — |
| 非注释命中 | docs/en/guides/extensions/external-acp-agents.md:11 | - Is installed on the device running AIxCoding. | — |
| 非注释命中 | docs/en/guides/extensions/external-acp-agents.md:16 | You do not need to start the ACP server in advance. When testing the connection or calling the sub-agent, AIxCoding automatically starts the external agent process using the configuration and establishes an ACP connection over stdio. | — |
| 非注释命中 | docs/en/guides/extensions/external-acp-agents.md:32 | 3. Change "Agent Type" to "External ACP". AIxCoding automatically enables "Sub-Agent only". | — |
| 非注释命中 | docs/en/guides/extensions/external-acp-agents.md:34 | 5. Add any environment variables required for authentication. The external agent does not inherit AIxCoding's environment, so add them here; see [Use environment variables](#use-environment-variables). | — |
| 非注释命中 | docs/en/guides/extensions/external-acp-agents.md:51 | When testing a connection, AIxCoding starts a temporary external agent process and checks whether it can establish an ACP session, without sending a task. After a successful connection, the report shows sections for identity, capabilities, modes, models, configuration options, and authentication methods, listing the information provided by the external agent. Information the agent does not provide may appear as "Not advertised.", "The agent did not report its identity.", or a blank entry. This does not indicate a connection failure. | — |
| 非注释命中 | docs/en/guides/extensions/external-acp-agents.md:53 | When the test ends, AIxCoding closes the temporary process. | — |
| 非注释命中 | docs/en/guides/extensions/external-acp-agents.md:62 | ### Example: Configure AIxCoding as an external ACP agent | — |
| 非注释命中 | docs/en/guides/extensions/external-acp-agents.md:64 | AIxCoding itself can also provide an ACP server over stdio. Use the following configuration: | — |
| 非注释命中 | docs/en/guides/extensions/external-acp-agents.md:75 | This command starts AIxCoding ACP server, offering the `Code` agent by default and using `manual` approval mode. For more configuration and usage instructions for AIxCoding ACP server, see [Use AIxCoding ACP server](../running/aixcoding-acp.md). | — |
| 非注释命中 | docs/en/guides/extensions/external-acp-agents.md:79 | The external agent does not inherit the environment AIxCoding runs in. It starts with only a basic set of variables — `HOME`, `LOGNAME`, `PATH`, `SHELL`, `TERM`, and `USER` on macOS and Linux; `APPDATA`, `HOMEDRIVE`, `HOMEPATH`, `LOCALAPPDATA`, `PATH`, `PATHEXT`, `PROCESSOR_ARCHITECTURE`, `SYSTEMDRIVE`, `SYSTEMROOT`, `TEMP`, `USERNAME`, and `USERPROFILE` on Windows — plus the environment variables set in the agent profile. Add anything else the agent needs, such as API keys or proxy settings like `HTTPS_PROXY`, as environment variables in the profile. | — |
| 非注释命中 | docs/en/guides/extensions/external-acp-agents.md:81 | In the executable, arguments, environment variable values, and working directory, you can use `{{ENV_VAR}}` to reference environment variables in the environment where AIxCoding runs. This lets you reuse existing configuration values without entering fixed values or sensitive information directly in the agent profile. Environment variable names can contain only letters, digits, and underscores, and cannot start with a digit. | — |
| 非注释命中 | docs/en/guides/extensions/external-acp-agents.md:89 | AIxCoding resolves these references when you save the profile, when you test the connection, and each time it starts the external agent. If a referenced variable does not exist or has an empty value, the profile cannot be saved, and the connection test or invocation fails. | — |
| 非注释命中 | docs/en/guides/extensions/external-acp-agents.md:93 | When "Working Directory" is blank, the external agent uses the current AIxCoding session's working directory. | — |
| 非注释命中 | docs/en/guides/extensions/external-acp-agents.md:107 | All of these settings can be left blank. When they are blank, AIxCoding uses the external agent's defaults. Test the connection again after changing the configuration. | — |
| 非注释命中 | docs/en/guides/extensions/external-acp-agents.md:111 | "Model ID" is applied on a best-effort basis. If the external agent does not list the specified model, or answers the switch with an unsupported-method or invalid-parameters error, AIxCoding continues using the external agent's default model. Any other error while switching the model fails the connection. | — |
| 非注释命中 | docs/en/guides/extensions/external-acp-agents.md:120 | "Handshake Timeout (seconds)" limits how long AIxCoding waits to start the process, complete ACP initialization, and open a session. "Idle Timeout (seconds; 0 disables)" limits how long AIxCoding waits without receiving any activity during an invocation. Set it to `0` to allow an unlimited idle wait. The **Test** button does not use "Handshake Timeout (seconds)": it always waits at most 15 seconds, so an agent that starts more slowly can fail the test yet still work when invoked. | — |
| 非注释命中 | docs/en/guides/extensions/hooks.md:15 | The following steps create a project hook in the working directory of the current AIxCoding session. It applies only to this working directory and appends the turn status to `hook-events.log` in that directory after each turn ends. | — |
| 非注释命中 | docs/en/guides/extensions/hooks.md:50 | AIxCoding provides the event's JSON input file through the `CHRYS_HOOK_PAYLOAD_FILE` environment variable. The input for `after_turn` includes `turn` and `status`, which contain the turn number and ending status. By default, the script runs in the current AIxCoding session's working directory, so `hook-events.log` is also written there. | — |
| 非注释命中 | docs/en/guides/extensions/hooks.md:54 | Switch sessions or restart AIxCoding to apply the configuration on disk. | — |
| 非注释命中 | docs/en/guides/extensions/hooks.md:85 | This configuration matches only `filesystem.write` tool calls that have a `path` argument whose path ends in `.env`. Blocking hooks finish before AIxCoding continues processing the call. | — |
| 非注释命中 | docs/en/guides/extensions/hooks.md:105 | After switching sessions or restarting AIxCoding, create a dedicated test file, `hook-demo/.env`, with known content such as `HOOK_TEST=unchanged`. Ask the agent to attempt one modification using only `write_file` or `edit_file`, then stop after rejection without using the shell or another method. Check that the tool call is rejected before execution and displays the reason provided by the script. Then confirm that the file content is unchanged. You can delete `hook-demo/.env` after verification. | — |
| 非注释命中 | docs/en/guides/extensions/hooks.md:140 | Switch sessions or restart AIxCoding to apply the configuration. The system reminder takes effect only after the blocking hook finishes successfully. AIxCoding wraps the reminder in `<system-reminder>` tags and sends it to the model along with the user's submitted message. The reminder does not appear in the TUI conversation and is not saved in session data. | — |
| 非注释命中 | docs/en/guides/extensions/hooks.md:142 | To confirm that a `user_prompt_submit` hook is working, or to inspect the actual system reminder sent to the model, check the raw HTTP log of model requests. This log contains unredacted API keys and full conversation content, so enable it only temporarily for troubleshooting. In the TUI, press **F10**, go to **Security** > **Diagnostics**, enable **Capture raw HTTP traffic**, and restart AIxCoding. Submit a message using the Code agent, then search for the reminder text "After modifying Python files" in `llm_raw_http.jsonl` in the current session directory. For its location, see [Find the session ID and storage location](../daily-use/sessions.md#find-the-session-id-and-storage-location). After verification, disable raw HTTP traffic capture and restart AIxCoding again. | — |
| 非注释命中 | docs/en/guides/extensions/hooks.md:152 | \| Check, reject, or modify an operation before it continues \| `blocking` \| AIxCoding waits for the hook to finish; some events apply the action decision from the result file \| | — |
| 非注释命中 | docs/en/guides/extensions/hooks.md:153 | \| Continue the current operation immediately, but let AIxCoding wait for a limited time when the current turn or session ends \| `async` \| AIxCoding continues immediately, then waits for the hook to finish at applicable events, within the wait limit \| | — |
| 非注释命中 | docs/en/guides/extensions/hooks.md:154 | \| Send ordinary notifications or record information in a task that can be interrupted by exit \| `fire_and_forget` \| AIxCoding continues immediately and does not wait when the current turn or session ends; this is the default mode \| | — |
| 非注释命中 | docs/en/guides/extensions/hooks.md:156 | An asynchronous hook (`async`) does not delay the event that triggered it or the current operation. When the current turn or session ends, if an applicable asynchronous hook is still running, AIxCoding waits for it to finish before ending the turn or session. AIxCoding does not wait for asynchronous hooks triggered by `user_interrupt`. The wait limit at session end is configurable in [Global settings](../../reference/hooks.md#global-settings). To retry unfinished tasks after AIxCoding exits, also configure `delivery: durable`. | — |
| 非注释命中 | docs/en/guides/extensions/mcp.md:3 | Model Context Protocol (MCP) servers can provide AIxCoding agents with external tools, prompt templates, and usage instructions. This guide explains how to connect HTTP or STDIO MCP servers in the terminal user interface (TUI), configure which tools are available, and control whether prompt templates are loaded and server instructions are included in the model context. | — |
| 非注释命中 | docs/en/guides/extensions/mcp.md:18 | HTTP header values and STDIO environment variable values can both use `{{ENV_VAR}}` to reference environment variables set before starting AIxCoding. Variable names can contain only letters, digits, and underscores, and cannot start with a digit. | — |
| 非注释命中 | docs/en/guides/extensions/mcp.md:26 | 3. If the server requires authentication, add names and values under "Headers". Use `{{ENV_VAR}}` to reference environment variables set before starting AIxCoding, for example: | — |
| 非注释命中 | docs/en/guides/extensions/mcp.md:34 | 5. Keeping TLS certificate verification enabled is recommended. To connect to a self-signed server you have confirmed is trustworthy, you can enable "Skip TLS verification". When enabled, AIxCoding does not verify the HTTPS server certificate and cannot confirm that it is connecting to the intended server. | — |
| 非注释命中 | docs/en/guides/extensions/mcp.md:40 | 3. Add any environment variables the process needs. Enter values directly or use `{{ENV_VAR}}` to reference environment variables set before starting AIxCoding. | — |
| 非注释命中 | docs/en/guides/extensions/mcp.md:77 | 2. **Test the server connection**: Click "Test" at the bottom right of the server configuration card. AIxCoding attempts to connect and displays the server's identity, advertised capabilities, and usage instructions in a connection report, along with the tools and prompt templates available under the current configuration. | — |
| 非注释命中 | docs/en/guides/extensions/mcp.md:83 | - For STDIO servers, first inspect the executable, working directory, process exit code, and tail of standard error shown in the connection error. Then check the command, arguments, and environment variables, and confirm that the command can start in the indicated working directory. AIxCoding shows only a limited amount of standard error output. For complete logs, enable logging as described in the server's documentation. Remove sensitive information such as tokens and credentials before sharing diagnostics. | — |
| 非注释命中 | docs/en/guides/extensions/skills.md:9 | \| Location \| When to use it \| How AIxCoding loads it \| | — |
| 非注释命中 | docs/en/guides/extensions/skills.md:11 | \| AIxCoding user skills directory \| Make skills available to all agents of the "Built-in" type in AIxCoding \| Always loaded automatically \| | — |
| 非注释命中 | docs/en/guides/extensions/skills.md:12 | \| AIxCoding shared user directory (`~/.aixcoding/skills`) \| Share skills between the AIxCoding CLI and AIxCoding desktop clients \| Loaded automatically by default; can be disabled per agent \| | — |
| 非注释命中 | docs/en/guides/extensions/skills.md:13 | \| Agent Skills shared directory \| Share skills between AIxCoding and other tools that support Agent Skills \| Loaded automatically by default; can be disabled per agent \| | — |
| 非注释命中 | docs/en/guides/extensions/skills.md:14 | \| `<working-directory>/.aixcoding/skills` \| AIxCoding-specific skills for the current working directory \| Loaded automatically by default; can be disabled per agent \| | — |
| 非注释命中 | docs/en/guides/extensions/skills.md:18 | Here, `<working-directory>` is the current working directory. When you switch working directories, AIxCoding reloads the skills from the new working directory. | — |
| 非注释命中 | docs/en/guides/extensions/skills.md:24 | \| AIxCoding user skills directory \| `~/.chrys/skills` \| `%APPDATA%\chrys\skills` \| | — |
| 非注释命中 | docs/en/guides/extensions/skills.md:25 | \| AIxCoding shared user directory \| `~/.aixcoding/skills` \| `%USERPROFILE%\.aixcoding\skills` \| | — |
| 非注释命中 | docs/en/guides/extensions/skills.md:28 | When multiple directories contain skills with the same name, the AIxCoding-specific directories take precedence over the corresponding Agent Skills directories: `~/.aixcoding/skills` wins over `~/.agents/skills`, and `<working-directory>/.aixcoding/skills` wins over `<working-directory>/.agents/skills`. | — |
| 非注释命中 | docs/en/guides/extensions/skills.md:32 | AIxCoding searches for `SKILL.md` files in configured skills directories and up to two levels of subdirectories. Once it finds a `SKILL.md`, it recognizes the containing directory as a skill directory and stops searching for nested skills within it. | — |
| 非注释命中 | docs/en/guides/extensions/skills.md:36 | The AIxCoding user skills directory is always loaded automatically. The Agent Skills shared directory and the current working directory's skills directory are also loaded automatically by default. If a source has been disabled in the agent's configuration, enable it again. For a custom directory, add it to the corresponding agent's configuration. | — |
| 非注释命中 | docs/en/guides/extensions/skills.md:57 | > **Note**: Skill scripts run as local processes without sandbox isolation. Before installing a third-party skill, inspect its `SKILL.md`, scripts, and other related files, and install skills only from trusted sources. AIxCoding runs skill scripts through the `run_skill_script` tool. Whether this tool requires confirmation depends on the agent's approval rules and the [current approval mode](../configuration/approval.md). | — |
| 非注释命中 | docs/en/guides/extensions/skills.md:61 | After you save the agent's configuration and return to the session, AIxCoding reloads its skills. If you add skill directories or change their files directly on disk, AIxCoding does not monitor those changes in real time. The next time you send a message, AIxCoding rescans the current agent's enabled skills directories before processing the message. | — |
| 非注释命中 | docs/en/guides/extensions/skills.md:88 | If the skill name matches a built-in AIxCoding slash command, you cannot invoke it explicitly with `/skill-name`. In that case, name the skill directly in your message, for example: | — |
| 非注释命中 | docs/en/guides/extensions/skills.md:98 | Skills loaded from the [installation locations](#skill-installation-locations) listed earlier are directory-based skills, each containing a `SKILL.md`. AIxCoding also supports inline skills defined directly in an agent profile. These do not require a skill directory or `SKILL.md`. | — |
| 非注释命中 | docs/en/guides/extensions/skills.md:100 | If multiple skills have the same name, AIxCoding loads only the one with the highest priority. Priority, from highest to lowest, is: | — |
| 非注释命中 | docs/en/guides/extensions/skills.md:103 | 2. The AIxCoding user skills directory. | — |
| 非注释命中 | docs/en/guides/extensions/skills.md:114 | Each skill uses its own directory with a `SKILL.md` at the directory root. The following is a minimal skill that AIxCoding can load: | — |
| 非注释命中 | docs/en/guides/extensions/skills.md:131 | `SKILL.md` must use UTF-8 encoding. It starts with a YAML configuration block enclosed by `---`, also called frontmatter, followed by instructions for the agent. The frontmatter should be a valid YAML mapping; if it is not valid YAML, AIxCoding tries to read it line by line and logs a warning. AIxCoding validates the file as follows: | — |
| 非注释命中 | docs/en/guides/extensions/skills.md:139 | \| `license`, `allowed-tools` \| Optional; AIxCoding reads their values without further validation \| | — |
| 非注释命中 | docs/en/guides/extensions/skills.md:140 | \| `metadata` \| Optional; must be a YAML mapping, otherwise AIxCoding does not retain this field \| | — |
| 非注释命中 | docs/en/guides/extensions/skills.md:141 | \| Body \| AIxCoding imposes no additional length or structure restrictions \| | — |
| 非注释命中 | docs/en/guides/extensions/skills.md:143 | Use valid YAML for the frontmatter to ensure that the skill loads reliably. AIxCoding does not load a skill if its frontmatter, `name`, or `description` is missing, or if field values fail the validation rules above. | — |
| 非注释命中 | docs/en/guides/extensions/skills.md:149 | * `allowed-tools`: Declares tools that may be approved in advance under the Agent Skills specification. This field is still experimental. AIxCoding currently only reads and retains its value; it does not automatically grant tool permissions based on it. | — |
| 非注释命中 | docs/en/guides/extensions/skills.md:151 | AIxCoding skill directories and the `SKILL.md` format follow the common Agent Skills specification. For details on these fields and the complete skill specification, see the [official Agent Skills specification](https://agentskills.io/specification). | — |
| 非注释命中 | docs/en/guides/extensions/skills.md:170 | AIxCoding recognizes text files as skill resources only if they have one of these extensions: `.md`, `.txt`, `.rst`, `.html`, `.htm`, `.xml`, `.svg`, `.json`, `.jsonl`, `.yaml`, `.yml`, `.toml`, `.csv`, `.tsv`, `.ini`, `.cfg`, `.css`. | — |
| 非注释命中 | docs/en/guides/extensions/skills.md:175 | * AIxCoding reads only files at the skill directory root and in its immediate subdirectories. For example, it discovers `guide.md` and `references/guide.md`, but ignores `references/api/guide.md`. | — |
| 非注释命中 | docs/en/guides/extensions/skills.md:176 | * Within a skill directory, AIxCoding skips files and directories accessed through symbolic links or Windows directory junctions. Both point to other locations on disk. To use their contents, place the actual files in the skill directory. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-acp.md:1 | # Use AIxCoding ACP server | — |
| 非注释命中 | docs/en/guides/running/aixcoding-acp.md:3 | Editors and development tools that support the Agent Client Protocol (ACP) can connect to AIxCoding to use AIxCoding agents in the client. The ACP client provides the interface, while AIxCoding communicates with it over standard input and output (stdio), runs agents, executes tools, and saves sessions. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-acp.md:5 | Before you begin, install AIxCoding and configure at least one model. For preparation steps, see [Getting started with AIxCoding](../../start/getting-started.md) and [Configure models](../configuration/models.md). | — |
| 非注释命中 | docs/en/guides/running/aixcoding-acp.md:7 | ## Connect to AIxCoding | — |
| 非注释命中 | docs/en/guides/running/aixcoding-acp.md:26 | 1. Start or connect to AIxCoding in the client. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-acp.md:28 | 3. Confirm that the client displays a reply from AIxCoding. A reply means the connection is configured successfully. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-acp.md:43 | When creating or restoring a session, the client can pass the project's working directory to AIxCoding. The directory supplied by the client must be an existing absolute path. If the client does not provide a working directory, AIxCoding uses the directory specified by `--workdir <project-directory>`. If both are provided, the client's working directory takes precedence. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-acp.md:45 | AIxCoding checks `--workdir` at startup. The specified directory must exist even if the client will later provide a working directory; otherwise, AIxCoding cannot start. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-acp.md:47 | Session data is saved in AIxCoding's session storage directory, rather than the working directory. To find the actual location, see [Find the session ID and storage location](../daily-use/sessions.md#find-the-session-id-and-storage-location). AIxCoding records the working directory when a session is created. Listing sessions through an ACP client shows only sessions that match the current working directory. AIxCoding refuses to restore a session if the working directory does not match. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-acp.md:53 | AIxCoding sends agent replies and tool call status to the client. When the client cancels a task, AIxCoding interrupts the current task. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-acp.md:55 | When a desktop client supplies its identity and an explicit selected Agent (`agent-studio.dev/selected-agent` with `schemaVersion: 1`, `agentMarketSkillId`, and `agentName`) in ACP prompt metadata, AIxCoding reports one Agent-use telemetry record as it prepares that prompt's first model request, before reporting its subsequent tool calls. The record uses `funcType=1001`, puts the selected Agent name in `funcName`, and uses the desktop kernel source from `agent-studio.dev/function-name` for `agentName`, matching tool-call records (`funcType=3`). It includes the model request and session IDs so it can be joined with other telemetry from that prompt. No Agent-use record is sent for a prompt without a model request or an explicit selection. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-acp.md:59 | If the client supports session management, a closed session can still be restored in the same working directory. Deleting a session removes the session record saved by AIxCoding, and the session can no longer be restored in AIxCoding. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-acp.md:61 | To use the question feature through an ACP client, the client must support AIxCoding's `_chrys/request_input` extension request (shown as `chrys/request_input` in ACP SDKs that add the underscore prefix automatically). AIxCoding uses this request to send the agent's questions to the client and receive the user's answers; a client that does not support it cannot complete tasks that require user answers. Use `--ask-user-timeout` to limit how long AIxCoding waits for an answer. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-acp.md:63 | If the client supports switching approval modes or models, it can change the corresponding settings for the current session. These switches, like the initial mode set with `--approval`, are not written to AIxCoding's local configuration. If the client uses AIxCoding's extension requests to change settings or agent and model profiles, however, those changes are written to AIxCoding's local configuration. The next time the ACP server starts, the initial approval mode still comes only from `--approval`; other initial settings are determined by the local configuration and the startup arguments for that launch. Model profiles and available agents remain managed through AIxCoding's local configuration. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-run.md:11 | - Install AIxCoding-CLI and configure at least one working model. See [Getting started with AIxCoding-CLI](../../start/getting-started.md) and [Configure models](../configuration/models.md). | — |
| 非注释命中 | docs/en/guides/running/aixcoding-run.md:29 | While the task runs, AIxCoding-CLI shows its progress. When the task finishes, it shows a summary line and then the agent's final response. For example: | — |
| 非注释命中 | docs/en/guides/running/aixcoding-run.md:43 | See [Read the progress](#read-the-progress) for what each line means. Control characters in the response that could change your terminal are shown as `�`; when you redirect the output to a file or another program, or add `--json`, the response is kept exactly as written. If the task fails, the error message is written to standard error (`stderr`), and the command exits with a nonzero status. When AIxCoding-CLI can tell why a model request failed, the message says so, and a `detail:` line below it shows the original error text. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-run.md:101 | `--task` does not require a particular file extension. AIxCoding-CLI reads the file's contents and uses them as the prompt for this task. The task file path can be absolute or relative. For a relative path, AIxCoding-CLI looks for the file in the directory specified by `--workdir`, or in the directory where you run the command if `--workdir` is omitted. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-run.md:141 | {"session_id": "8de5057d-58ff-477e-9158-2f1b8d8e9fc0", "result": "Hello! I'm AIxCoding, a read-only Q&A assistant for this codebase. I can help you with questions about the code, architecture, APIs, conventions, and how things work — with file and line references so you can jump straight to the source.\n\nWhat would you like to know?", "duration": 9.018} | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:1 | # Run AIxCoding in a browser | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:3 | `aixcoding-cli serve` displays AIxCoding terminal user interface (TUI) in a browser, where you can chat, approve tool calls, and change configuration. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:7 | This guide calls the device running the browser the “local device” and the machine running AIxCoding service the “server.” The server can be the local device or a remote server accessed over a network. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:9 | Before you begin, [install AIxCoding](../../start/getting-started.md#1-install-aixcoding-cli) on the server. The browser provides the interface; AIxCoding uses the server's configuration and reads and modifies files and runs commands with the permissions of the system user who started the service. All these operations take place on the server. All visitors share its configuration, files, and sessions; they do not receive separate accounts. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:17 | \| Run and access AIxCoding locally \| [Start AIxCoding locally](#start-aixcoding-cli-locally) \| | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:18 | \| Access AIxCoding on a remote server over SSH \| [Access remote AIxCoding from your local device](#access-remote-aixcoding-cli-from-your-local-device) \| | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:19 | \| Access AIxCoding through a fixed HTTPS domain \| [Access AIxCoding through a fixed HTTPS domain](#access-aixcoding-cli-through-a-fixed-https-domain) \| | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:21 | ## Start AIxCoding locally | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:33 | The service is running when the terminal displays `Serving AIxCoding TUI on ...` and an access URL. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:39 | The AIxCoding interface should appear after login, using any existing model configuration on the server. Once a model is configured, send “Hello” and check that you receive a reply. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:43 | ### 3. Finish using AIxCoding | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:45 | Keep the service terminal running while you use AIxCoding. Once your tasks are finished, press `Ctrl+C` in that terminal to stop the service. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:47 | Each time you open a page and establish a connection, the server starts a separate AIxCoding instance. Conversation history is saved on the server. After reopening the page, you can [restore a saved session](../daily-use/sessions.md#resume-an-existing-session). | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:51 | ## Access remote AIxCoding from your local device | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:53 | If you can already log in to the remote server over SSH, you can create an SSH tunnel to forward your local browser's connection to remote AIxCoding over an encrypted channel, without configuring a domain. The following steps require two terminal windows on your local device. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:55 | ### 1. Log in to the remote server and start AIxCoding in the first terminal | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:63 | After login, commands in this terminal run on the remote server. Change to the remote working directory, then start AIxCoding: | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:83 | ### 3. Open AIxCoding in your local browser | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:85 | Visit `http://localhost:7777` and enter AIxCoding browser login password you set in step 1. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:87 | When the browser connects to your local `localhost:7777`, the SSH tunnel forwards the connection to remote AIxCoding. Keep `localhost` in the browser URL for this example; do not replace it with the remote IP address. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:89 | When your tasks are finished, press `Ctrl+C` in the first terminal to stop AIxCoding and in the second terminal to close the SSH tunnel. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:91 | ## Access AIxCoding through a fixed HTTPS domain | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:93 | To access AIxCoding at a fixed address such as `https://aixcoding-cli.example.com`, deploy a reverse proxy. The browser establishes an encrypted connection to the proxy, which forwards requests to AIxCoding. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:95 | This section assumes an existing HTTPS proxy. Configure the domain and certificate on the proxy; AIxCoding itself does not serve HTTPS. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:97 | ### 1. Start AIxCoding | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:99 | The following example requires the proxy and AIxCoding to run on the same server. In a terminal on the server, change to your working directory, replace `aixcoding-cli.example.com` with your actual domain, and run: | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:105 | Set a browser login password and keep the terminal running. This command makes AIxCoding accept connections only from the same server. The browser accesses the address specified by `--public-url` through the proxy. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:112 | - Preserve the original `Host` header from browser requests so AIxCoding can check the access domain. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:115 | By default, AIxCoding counts incorrect passwords by proxy address, so multiple visitors may share a failure count. If the proxy is trusted and correctly rewrites `X-Forwarded-For` (the client address request header), add `--auth-trust-forwarded-for` to AIxCoding startup command to count failures by the visitor address supplied by the proxy instead. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:119 | Replace `aixcoding-cli.example.com` with your actual domain and open the corresponding HTTPS address in your local browser, such as `https://aixcoding-cli.example.com`. Do not add AIxCoding port `:7777`. The browser should display AIxCoding login page without a certificate warning. After login, send a message and confirm that you receive a reply. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:121 | The connection from the browser to the proxy is encrypted; the proxy still connects to AIxCoding over HTTP within the server. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:125 | If the proxy runs on another server or in a separate container, it may not be able to reach AIxCoding at `127.0.0.1`. After adjusting the listening address, use firewall or container network rules to restrict access to the backend port to trusted proxies, preventing direct connections that bypass the HTTPS proxy. Setting an HTTPS `--public-url` does not encrypt the HTTP connection from the proxy to AIxCoding. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:135 | Change to your working directory and start AIxCoding with the password file: | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:145 | On the server, set an environment variable for the process that starts AIxCoding, such as `CHRYS_SERVE_PASSWORD`, to a nonempty login password. Then run: | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:153 | ## Access AIxCoding directly through a LAN IP address | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:163 | `--host 0.0.0.0` allows other devices to connect to AIxCoding. `--allow-insecure-auth` explicitly allows plain text password login over the network. Without this option, AIxCoding refuses to start in this example. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:171 | Confirm that AIxCoding is installed on the server and that its installation directory is on `PATH`. If you just installed it, reopen the terminal and run this command to verify: | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:189 | Change the first port after `-L` to an available local port, keeping the last port set to the port remote AIxCoding is listening on. For example, if remote AIxCoding uses `7777` and local port `8888` is available, run this on your local device: | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:195 | Replace `<user>` and `<server>` with the SSH username and server address. Also restart AIxCoding on the remote server with the new browser access URL: | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:205 | First confirm that AIxCoding service is still running, then check that the browser URL matches your access method: use `localhost` for the local or SSH examples, the configured domain for HTTPS, or the server IP for a direct LAN connection. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:215 | Check that AIxCoding is still running, that the proxy's forwarding address and port match AIxCoding's listening configuration, and that the proxy can reach that address. Consult the proxy logs for the specific cause. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:219 | Use the domain or IP address and port displayed when AIxCoding starts. When accessing through a proxy, check that it preserves the original `Host` header. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:223 | Check that the browser URL matches the address specified by `--public-url`, including the scheme (`http` or `https`), domain, and port. AIxCoding rejects connections with a mismatched origin. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:227 | If the message is `Invalid login token`, reopen the login page and enter the password again. If it is `Invalid login origin`, check that the browser URL matches the access URL configured for AIxCoding. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:231 | The client address is locked out. First confirm that no tasks are running in other pages, then press `Ctrl+C` in AIxCoding terminal and restart the service. If multiple visitors using a proxy are locked out at once, check the conditions in the HTTPS section to determine whether enabling `--auth-trust-forwarded-for` is appropriate. | — |
| 非注释命中 | docs/en/guides/running/aixcoding-serve.md:235 | When the page reconnects, the server starts a new AIxCoding instance. Follow the steps for restoring a saved session to restore conversation history, but interrupted tasks do not resume automatically. | — |
| 非注释命中 | docs/en/guides/running/workflows.md:44 | A workflow session can save multiple runs. Click the “Run 1”, “Run 2”, and subsequent run tabs above “Workflow”, “Info”, and the other tabs to browse each run. After quitting and reopening AIxCoding, first switch to “Workflow” through the app mode selector in the upper left. Press `F1` or click `f1 Sessions` at the bottom of the interface, then select a workflow session to view its historical inputs, outputs, and node records. | — |
| 非注释命中 | docs/en/guides/running/workflows.md:83 | Finally, `wf.build()` validates and builds the workflow. **The file must assign the result to a module-level variable named `workflow` so AIxCoding can load it.** | — |
| 非注释命中 | docs/en/guides/running/workflows.md:85 | You do not need to restart AIxCoding after saving the file. Click “New Session” to open the workflow picker and select `greeting`. | — |
| 非注释命中 | docs/en/guides/running/workflows.md:93 | By default, workflows use the Python interpreter running AIxCoding. If a workflow needs third-party libraries, use inline script metadata to specify your own Python interpreter or virtual environment. Install dependencies yourself; AIxCoding does not install them automatically. See [Workflow reference: Execution environment](../../reference/workflows.md#execution-environment) for configuration details. The Python examples in this tutorial use only the standard library and need no additional environment setup. | — |
| 非注释命中 | docs/en/guides/running/workflows.md:139 | - When a node returns a string, AIxCoding places it in `WorkflowValue.text` and sets `data` to `None`. Here, `describe()` only needs to output a description, so it returns a string. | — |
| 非注释命中 | docs/en/guides/running/workflows.md:192 | ### Use an AIxCoding-CLI agent | — |
| 非注释命中 | docs/en/guides/running/workflows.md:256 | For a regular AIxCoding agent, `instructions_suffix` is appended to the profile's existing `instructions` as part of the system prompt. The upstream `text` remains the user message. | — |
| 非注释命中 | docs/en/reference/agent-profile.md:16 | AIxCoding loads only non-hidden files with the `.yaml` or `.yml` extension in this directory. Other files are ignored. Invalid profiles do not prevent other profiles from loading, but are skipped with a warning in the startup log. | — |
| 非注释命中 | docs/en/reference/agent-profile.md:18 | AIxCoding loads these files at startup. After manually adding, editing, or deleting a profile, restart AIxCoding for the change to take effect. | — |
| 非注释命中 | docs/en/reference/agent-profile.md:24 | When loading user profiles, AIxCoding normalizes the files based on their contents: | — |
| 非注释命中 | docs/en/reference/agent-profile.md:26 | - If the filename is not `<name>.yaml`, AIxCoding renames it to `<name>.yaml`. This also changes the `.yml` extension to `.yaml`. | — |
| 非注释命中 | docs/en/reference/agent-profile.md:27 | - If the profile has no `id`, AIxCoding assigns a stable ID and rewrites the entire file. The rewrite does not preserve existing comments, field order, or formatting, and it removes unrecognized keys and fields set to their default values (except `approval`, which is always written). | — |
| 非注释命中 | docs/en/reference/agent-profile.md:28 | - If `sub_agents.agents` references a built-in agent that has been removed from AIxCoding, AIxCoding deletes those entries and rewrites the file in the same way. The references are kept if you have your own profile with that name, and the change waits while any profile file in the directory fails to load. | — |
| 非注释命中 | docs/en/reference/agent-profile.md:29 | - If another profile already occupies the target filename, the profile is not loaded. Where possible, AIxCoding renames the conflicting file with a `.conflict` marker. | — |
| 非注释命中 | docs/en/reference/agent-profile.md:33 | If a conflict occurs, inspect `<name>.yaml` and the file marked with `.conflict`, and keep the profile you need. To retain both, turn one file into a separate profile: change its `name`, remove its existing `id`, and restore the `.yaml` extension. AIxCoding assigns the profile a new ID after a restart. | — |
| 非注释命中 | docs/en/reference/agent-profile.md:35 | Filesystem restrictions may prevent AIxCoding from adding the `.conflict` marker. In that case, the conflicting file retains its original name but is still not loaded. | — |
| 非注释命中 | docs/en/reference/agent-profile.md:39 | The original profiles for built-in agents are included with AIxCoding installation. When you edit and save a built-in agent through the TUI, AIxCoding creates a profile with the same name in the [user agent profile directory](#user-agent-profile-directory). For example, editing and saving the built-in agent named `Code` creates `Code.yaml`. | — |
| 非注释命中 | docs/en/reference/agent-profile.md:41 | The built-in agent names are `Code`, `QA`, `Explore`, and `General`. A profile manually created in the user agent profile directory with any of these `name` values also overrides the corresponding built-in agent. An override replaces the entire built-in profile; it does not inherit or merge any other fields from it. Delete the corresponding user profile and restart AIxCoding to restore the built-in profile. | — |
| 非注释命中 | docs/en/reference/agent-profile.md:60 | This example omits `id`. AIxCoding assigns a stable ID and writes it back to the file when it first loads the profile. | — |
| 非注释命中 | docs/en/reference/agent-profile.md:75 | \| `id` \| String \| Assigned automatically \| Stable identifier. If omitted or empty, AIxCoding automatically assigns a 12-character hexadecimal ID: it reuses the built-in agent's ID when the names match, or generates a new ID otherwise. You can also specify a unique ID manually; quote an ID made only of digits, such as `id: "123"`, because an unquoted one is read as a number and the profile fails to load. When copying and modifying an existing profile to create a new one, remove the `id` field so AIxCoding can assign a new ID. \| | — |
| 非注释命中 | docs/en/reference/agent-profile.md:102 | If `profile_id` is omitted, empty, or not found among the loaded model profiles, the main agent uses the model profile currently active in the session, and a sub-agent inherits the model profile actually used by its parent. AIxCoding also logs a warning when the ID cannot be found. | — |
| 非注释命中 | docs/en/reference/agent-profile.md:155 | Both `env` and `headers` are key-value mappings: enter the variable or header name on the left and its value on the right. You can specify values directly or use `{{ENV_VAR}}` to reference an environment variable set before starting AIxCoding. If a variable referenced in `env` is missing or empty, the server connection fails. For `headers`, variables are resolved and this rule applies only when `resolve_header_templates` is `true`. | — |
| 非注释命中 | docs/en/reference/agent-profile.md:184 | When loading on demand is enabled, AIxCoding also adds control tools for listing, loading, and unloading MCP tools. Their naming rules are described in [MCP tool names](./tool-kinds-and-names.md#mcp-tool-names). In this case, `tool_name_prefix` cannot exceed 49 characters. | — |
| 非注释命中 | docs/en/reference/agent-profile.md:190 | `shell_filter` applies only to tools in the `shell` kind. If this field is omitted or set to `unrestricted`, AIxCoding does not filter shell commands. | — |
| 非注释命中 | docs/en/reference/agent-profile.md:192 | Shell tool calls go through [approval](#approval) first. Once approved, `shell_filter` checks the actual command. The command runs only after both checks pass. If the filter blocks a command, AIxCoding returns a tool error indicating that the command was blocked, without starting a shell process. | — |
| 非注释命中 | docs/en/reference/agent-profile.md:214 | Only the names in this table enable presets. Unrecognized presets do not take effect: the scalar form performs no shell filtering; for the object form, AIxCoding attempts to use the custom rules in the same object. If `commands` is empty, no shell filtering occurs in that case either. | — |
| 非注释命中 | docs/en/reference/agent-profile.md:237 | In custom rules, use executable names in `commands`, such as `[git, rg]`. Names are case-sensitive; when using an absolute path, specify the full path. For commands joined by `\|`, `&&`, `\|\|`, `;`, or similar operators, AIxCoding checks each segment separately. Execution is allowed only if every command name satisfies the rules. The example above allows `rg foo .`; it blocks `rg foo . \| less` because `less`, on the right side of the pipe, is not in the allowlist. | — |
| 非注释命中 | docs/en/reference/agent-profile.md:268 | An out-of-range number or a malformed `providers` entry also causes the profile to be skipped. A combination that does not fit the mode, such as a `provider` mode without `provider` or a selected provider missing from `providers`, instead leaves the agent without its web tools, and AIxCoding shows a warning with the reason. | — |
| 非注释命中 | docs/en/reference/agent-profile.md:316 | If `approval` is not configured, AIxCoding uses these defaults: | — |
| 非注释命中 | docs/en/reference/agent-profile.md:338 | 1. AIxCoding determines the initial approval level from `default` and `overrides`. | — |
| 非注释命中 | docs/en/reference/agent-profile.md:339 | 2. AIxCoding adjusts the result using safety rules: | — |
| 非注释命中 | docs/en/reference/agent-profile.md:357 | When multiple rules match a tool call, AIxCoding selects one in this order of precedence: | — |
| 非注释命中 | docs/en/reference/agent-profile.md:380 | If `overrides` is omitted, AIxCoding uses the default overrides: `shell: require`, `filesystem.write: require`, and `todo: skip`. Explicitly setting `overrides: {}` clears these defaults, so tools that match no other rule use `default`. | — |
| 非注释命中 | docs/en/reference/agent-profile.md:412 | \| `paths` \| List of strings \| `[]` \| Additional skill search roots. AIxCoding searches each directory and up to two levels of subdirectories for `SKILL.md`. Once found, it does not search inside that skill directory. Relative paths are resolved against the current [working directory](../guides/daily-use/workspaces.md). AIxCoding expands a leading `~` to the current user's home directory. \| | — |
| 非注释命中 | docs/en/reference/agent-profile.md:418 | \| `auto_load_aixcoding_user_skills` \| Boolean \| `true` \| Whether to load the AIxCoding shared user skills directory (`~/.aixcoding/skills`, shared with the AIxCoding desktop clients). \| | — |
| 非注释命中 | docs/en/reference/agent-profile.md:421 | The AIxCoding user skills directory is always loaded. The other automatically loaded directories are on by default; each can be disabled with its corresponding `auto_load_*` field. For user-level directory paths, see [Skill installation locations](../guides/extensions/skills.md#skill-installation-locations). | — |
| 非注释命中 | docs/en/reference/agent-profile.md:423 | When multiple sources contain skills with the same name, precedence from highest to lowest is: earlier directories in `paths`, AIxCoding user skills directory, the AIxCoding shared user directory (`~/.aixcoding/skills`), the user-level shared Agent Skills directory, `.aixcoding/skills` in the current working directory, `.agents/skills` in the current working directory, and earlier definitions in `inline`. If one search root contains multiple skills with the same name, discovery order is unspecified. Keep only one to ensure that the intended version loads. | — |
| 非注释命中 | docs/en/reference/agent-profile.md:466 | `compaction` configures the continuation information (Last Words) that AIxCoding generates when compacting the current task. These settings do not affect compaction summaries of earlier tool results or completed conversation turns. | — |
| 非注释命中 | docs/en/reference/agent-profile.md:478 | \| `last_words_template` \| String \| Empty \| Additional instructions appended to AIxCoding's fixed Last Words requirements, emphasizing information to preserve from the current task. Does not replace the fixed format. \| | — |
| 非注释命中 | docs/en/reference/agent-profile.md:482 | `last_words_max_output_tokens` limits output, while `phase4_side_call_token_budget` limits cumulative input. The latter is mainly intended for strict control of additional model usage and can usually be left at its default. If the budget is insufficient, AIxCoding preserves the current task's content. If the context is still too large, the task may be unable to continue. | — |
| 非注释命中 | docs/en/reference/agent-profile.md:484 | `compaction` does not provide a setting for the compaction trigger threshold. AIxCoding automatically determines when to compact based on the current model's context window, maximum output tokens, and safety margin. | — |
| 非注释命中 | docs/en/reference/agent-profile.md:509 | The **Agent Configuration** window in the TUI checks the concurrency values and the `tool_name` format when saving; AIxCoding does not check them when loading a YAML file you edited by hand. A concurrency value of `0` or less makes every call to the affected sub-agents fail. | — |
| 非注释命中 | docs/en/reference/agent-profile.md:539 | \| `env` \| String-valued object \| `{}` \| Environment variables passed to the process. Names must follow environment variable naming rules and be unique ignoring case. `CHRYS_ACP_SUBAGENT_DEPTH` is reserved for AIxCoding. \| | — |
| 非注释命中 | docs/en/reference/agent-profile.md:540 | \| `cwd` \| String \| Empty \| The external agent's working directory. If empty, uses the current AIxCoding session's working directory. Relative paths are resolved against that session directory. \| | — |
| 非注释命中 | docs/en/reference/agent-profile.md:541 | \| `allow_external_cwd` \| Boolean \| `false` \| Whether to allow the external agent to run outside the current session's working directory and its subdirectories. Defaults to `false`: a `cwd` outside the allowed directory scope causes an error and prevents startup; AIxCoding does not fall back to the default directory. This option only controls startup directory validation, not the external agent's file access permissions. \| | — |
| 非注释命中 | docs/en/reference/agent-profile.md:550 | **Directory scope for `allow_external_cwd`**: If an ACP client creates AIxCoding session and supplies additional working directories, the external agent can run in those directories and their subdirectories even when `allow_external_cwd` is `false`. | — |
| 非注释命中 | docs/en/reference/agent-profile.md:552 | `command`, `args`, values in `env`, and `cwd` can use `{{ENV_VAR}}` to reference environment variables from AIxCoding process. Missing or empty variables cause startup to fail. For connection tests, working directory security boundaries, and how configuration options are applied, see [Configure external ACP agents](../guides/extensions/external-acp-agents.md). | — |
| 非注释命中 | docs/en/reference/hooks.md:3 | Hooks let AIxCoding automatically run local scripts or commands at specified points. Use this page to look up the complete configuration fields, defaults, event data, and execution rules. If you are using hooks for the first time, start with [Configure and write hooks](../guides/extensions/hooks.md) to create and verify a hook using runnable examples. | — |
| 非注释命中 | docs/en/reference/hooks.md:17 | \| Turn \| `turn` \| AIxCoding's handling of a user request, from when processing begins until the agent stops generating content and calling tools. A user interruption or run failure also ends the current turn; additional messages submitted during a run still belong to the current turn. \| | — |
| 非注释命中 | docs/en/reference/hooks.md:19 | \| Blocking hook \| `execution.mode: blocking` \| AIxCoding waits for the hook to finish before continuing; some events apply the decision returned by the hook. \| | — |
| 非注释命中 | docs/en/reference/hooks.md:20 | \| Async hook \| `execution.mode: async` \| AIxCoding immediately continues the current operation, but usually waits for the hook to finish before the current turn or session ends. \| | — |
| 非注释命中 | docs/en/reference/hooks.md:21 | \| Fire-and-forget hook \| `execution.mode: fire_and_forget` \| AIxCoding immediately continues and does not wait for the hook at the end of the current turn or session. This is the default mode. \| | — |
| 非注释命中 | docs/en/reference/hooks.md:22 | \| Detached execution \| `execution.detach: true` \| Allows a fire-and-forget hook that has already started to keep running after AIxCoding exits. \| | — |
| 非注释命中 | docs/en/reference/hooks.md:23 | \| Durable delivery \| `execution.delivery: durable` \| Records unfinished non-blocking hook tasks so AIxCoding can retry them later. The same task may run more than once, so scripts must be safe to run repeatedly. \| | — |
| 非注释命中 | docs/en/reference/hooks.md:24 | \| Input file \| `CHRYS_HOOK_PAYLOAD_FILE` \| A JSON file that AIxCoding generates for the event, containing event and context data. \| | — |
| 非注释命中 | docs/en/reference/hooks.md:25 | \| Result file \| `CHRYS_HOOK_RESULT` \| A JSON file to which the hook writes a decision or additional information. Only eligible blocking hooks can use it to change AIxCoding's behavior. \| | — |
| 非注释命中 | docs/en/reference/hooks.md:29 | AIxCoding can load one hook configuration file from each of the global configuration directory and the current working directory: | — |
| 非注释命中 | docs/en/reference/hooks.md:36 | Either location can use `hooks.yml` or `hooks.json` instead. If a directory contains multiple candidates, AIxCoding loads only the first one, in the order `hooks.yaml`, `hooks.yml`, `hooks.json`. | — |
| 非注释命中 | docs/en/reference/hooks.md:38 | `<working-directory>` is the session's working directory. For project configuration, AIxCoding checks only `<working-directory>/.chrys/hooks/`; it does not search parent or child directories of the working directory. | — |
| 非注释命中 | docs/en/reference/hooks.md:44 | Editing a hook configuration file on disk does not take effect immediately. After editing, switch sessions or restart AIxCoding to reload the configuration. Changes to hook scripts alone do not require a reload; the next time the hook is triggered, it uses the new script content. | — |
| 非注释命中 | docs/en/reference/hooks.md:58 | Both `version` and `settings` can be omitted; AIxCoding then uses the defaults listed in the table. | — |
| 非注释命中 | docs/en/reference/hooks.md:70 | \| `outbox_retry_age_seconds` \| Number (>= `0`) \| `60.0` \| Used only for durable delivery hooks. After starting, AIxCoding retries hook tasks that were not recorded as complete because of a previous exit or crash. This setting specifies the minimum delay in seconds before a retry, measured from the task's last execution start, or from its creation if it has never run. \| | — |
| 非注释命中 | docs/en/reference/hooks.md:84 | \| `execution` \| Object \| See [Execution behavior](#execution-behavior) \| Whether AIxCoding waits for the hook, its time limit, and how failures are handled. \| | — |
| 非注释命中 | docs/en/reference/hooks.md:101 | \| `session_start` \| After the agent is ready. Triggered when AIxCoding starts, a session is created, or the current session is rolled back to its beginning; not triggered by switching agents or models. \| None \| | — |
| 非注释命中 | docs/en/reference/hooks.md:102 | \| `session_restored` \| After a saved session is restored. When a session is restored immediately after starting AIxCoding, both `session_start` and `session_restored` may be triggered. \| `restored_session_id`: ID of the saved session restored this time \| | — |
| 非注释命中 | docs/en/reference/hooks.md:103 | \| `session_end` \| When the current session ends: exiting AIxCoding, switching sessions, starting a new session, deleting or clearing the current session, or rolling it back to its beginning. \| None \| | — |
| 非注释命中 | docs/en/reference/hooks.md:131 | Approval events notify or record when tool approval is waiting for a human decision. They cover only tool approvals handled by AIxCoding, not approvals forwarded by external ACP agents. For payload details, see [Approval event fields](#approval-event-fields). | — |
| 非注释命中 | docs/en/reference/hooks.md:136 | \| `approval_resolved` \| After a human approves or rejects the request, before AIxCoding continues processing the decision. Not triggered if the wait is interrupted; does not mean the tool has executed or succeeded. \| Same as `approval_requested`, plus `approved` \| | — |
| 非注释命中 | docs/en/reference/hooks.md:138 | In automatic approval mode (`auto`), AIxCoding completes the automatic review first and triggers approval events only if a human decision is still needed. Neither event is triggered if automatic review approves the request, approval is bypassed, or a decision is already available before the wait begins. | — |
| 非注释命中 | docs/en/reference/hooks.md:185 | ### When AIxCoding waits for async hooks | — |
| 非注释命中 | docs/en/reference/hooks.md:187 | Async hooks run immediately when triggered, and the current operation continues. If a hook has not finished, AIxCoding waits at the following points: | — |
| 非注释命中 | docs/en/reference/hooks.md:190 | - When the current session ends, it waits for async hooks triggered by session events. Because `session_end` is triggered during session shutdown, AIxCoding starts waiting for it immediately. | — |
| 非注释命中 | docs/en/reference/hooks.md:234 | - Use YAML single-quoted strings for regular expressions where possible; backslashes must be escaped inside double quotes. If a regular expression is invalid, AIxCoding logs a warning and the condition does not match. | — |
| 非注释命中 | docs/en/reference/hooks.md:242 | \| `script` \| Run an existing script, with AIxCoding choosing the runtime based on the file extension. \| `path` \| | — |
| 非注释命中 | docs/en/reference/hooks.md:265 | AIxCoding selects the runtime based on the file extension: | — |
| 非注释命中 | docs/en/reference/hooks.md:271 | \| `.sh`, `.bash`, `.zsh` \| `bash` or `sh`; on Windows, AIxCoding also looks for Git Bash \| | — |
| 非注释命中 | docs/en/reference/hooks.md:278 | For `.py` files, AIxCoding first searches the user's `PATH` for `uv`, `python3`, and `python`, in that order. If it finds `uv`, it runs the script with `uv run`; if it finds Python, it uses that interpreter directly. If none are found, it uses `uv` or Python from AIxCoding's bundled runtime. | — |
| 非注释命中 | docs/en/reference/hooks.md:280 | Before running other script types, install the corresponding runtime from the table and ensure AIxCoding can find it through `PATH`. | — |
| 非注释命中 | docs/en/reference/hooks.md:292 | AIxCoding does not interpret arguments through a shell, so redirection, pipes, variable expansion, and command substitution do not take effect. | — |
| 非注释命中 | docs/en/reference/hooks.md:317 | On macOS and Linux, AIxCoding uses the shell specified by the `$SHELL` environment variable, or `/bin/sh` if it is unset. On Windows, it uses Command Prompt (CMD). Syntax support may differ between shells. | — |
| 非注释命中 | docs/en/reference/hooks.md:327 | \| `env` \| Object mapping strings to strings \| `{}` \| Environment variables added to the hook process; values override those passed by AIxCoding when names match. \| | — |
| 非注释命中 | docs/en/reference/hooks.md:348 | \| Relative `cwd` \| The AIxCoding process's current working directory, which may differ from the session working directory \| | — |
| 非注释命中 | docs/en/reference/hooks.md:350 | When setting `cwd`, use an absolute path or the `${workspace_cwd}` or `${chrys_home}` template. For example, `${chrys_home}/hooks` specifies the `hooks` directory under AIxCoding configuration directory. The target directory must exist. | — |
| 非注释命中 | docs/en/reference/hooks.md:357 | \| `${chrys_home}` \| The AIxCoding configuration directory, usually `~/.chrys` or `%APPDATA%\chrys` \| | — |
| 非注释命中 | docs/en/reference/hooks.md:361 | AIxCoding performs literal replacement of these templates wherever they appear in `env` values and `cwd`. Other variables or expressions, such as `~`, `$VAR`, `${VAR}`, and `${VAR:-default}`, are not expanded by AIxCoding. | — |
| 非注释命中 | docs/en/reference/hooks.md:365 | `execution` controls whether AIxCoding waits for a hook, whether the hook can keep running after AIxCoding exits, whether unfinished tasks are retried, and how timeouts and failures are handled. All fields can be omitted. The defaults suit most notification and logging scripts: the current operation does not wait for the hook, the hook runs for at most 30 seconds, and a warning is logged if it fails. | — |
| 非注释命中 | docs/en/reference/hooks.md:376 | \| `async` \| The current operation continues immediately; see [When AIxCoding waits for async hooks](#when-aixcoding-cli-waits-for-async-hooks) for later waits \| Notifications and logging that should not delay the current operation but need to finish before the turn or current session ends \| No \| | — |
| 非注释命中 | docs/en/reference/hooks.md:377 | \| `fire_and_forget` (default) \| The current operation continues immediately; AIxCoding does not wait at the end of the turn or current session \| Notifications and logging that may be interrupted by AIxCoding exiting before they finish \| No \| | — |
| 非注释命中 | docs/en/reference/hooks.md:386 | `on_error` determines how AIxCoding continues when a hook cannot start, times out, or returns a nonzero exit code: | — |
| 非注释命中 | docs/en/reference/hooks.md:394 | When a blocking hook fails, AIxCoding ignores the decision returned by the script and applies only `on_error`. | — |
| 非注释命中 | docs/en/reference/hooks.md:407 | `detach` is a boolean that defaults to `false`. Set it to `true` if a hook that has already started needs to keep running after AIxCoding exits. It is available only with `mode: fire_and_forget`. | — |
| 非注释命中 | docs/en/reference/hooks.md:413 | `delivery` controls whether AIxCoding retries unfinished tasks on a later startup: | — |
| 非注释命中 | docs/en/reference/hooks.md:418 | \| `durable` \| Records pending tasks and retries eligible unfinished tasks when AIxCoding starts. Available only for `async` and `fire_and_forget`. \| | — |
| 非注释命中 | docs/en/reference/hooks.md:424 | `detach` keeps an already-started process running after AIxCoding exits, while `delivery` lets AIxCoding resume unfinished tasks on a later startup. Both can be set together. For example: | — |
| 非注释命中 | docs/en/reference/hooks.md:446 | AIxCoding provides both an input file and a result file every time a hook runs. Both files are deleted after the hook finishes; do not save their paths for later use. | — |
| 非注释命中 | docs/en/reference/hooks.md:551 | AIxCoding applies decisions only when a blocking hook successfully returns exit code `0`, and only for the events and conditions listed below. Result files from async and fire-and-forget hooks do not change AIxCoding's behavior. If a hook cannot start, times out, or returns a nonzero exit code, its result file is ignored and `on_error` from the [failure handling configuration](#setting-time-limits-and-failure-handling) applies. | — |
| 非注释命中 | docs/en/reference/hooks.md:566 | - If the JSON is invalid, the top-level value is not an object, or the file exceeds 1 MiB, AIxCoding logs a warning and ignores the result, treating it as no decision. | — |
| 非注释命中 | docs/en/reference/hooks.md:575 | When both project and global configuration are loaded, execution mode determines the phase in which a hook runs, and configuration source determines the order within each phase. For a single event, AIxCoding processes hooks in two phases: | — |
| 非注释命中 | docs/en/reference/hooks.md:578 | 2. If no hook rejects the operation, AIxCoding starts matching async and fire-and-forget hooks: first in project configuration order, then in global configuration order. These non-blocking hooks may run concurrently, so they may finish in a different order from the one in which they started. | — |
| 非注释命中 | docs/en/reference/hooks.md:594 | Project and global configurations may define the same `id`. Both hooks are retained, and AIxCoding logs a duplicate-name warning. | — |
| 非注释命中 | docs/en/reference/hooks.md:602 | If either configuration file is invalid, AIxCoding displays a warning and disables all hooks defined in that file; a valid configuration file in the other location still takes effect. No warning is issued when a configuration file is not found. | — |
| 非注释命中 | docs/en/reference/opentelemetry.md:3 | AIxCoding can use OpenTelemetry to record the following telemetry data during agent runs: | — |
| 非注释命中 | docs/en/reference/opentelemetry.md:9 | A collector is a service that receives telemetry data. AIxCoding sends data to a collector using the OpenTelemetry Protocol (OTLP). On this page, an “endpoint” is the address where the collector receives telemetry data. | — |
| 非注释命中 | docs/en/reference/opentelemetry.md:11 | This page covers AIxCoding OpenTelemetry configuration, local storage and export of telemetry data, and connections to OTLP collectors. | — |
| 非注释命中 | docs/en/reference/opentelemetry.md:17 | OpenTelemetry is disabled by default. Enable it under [Settings → Security → Telemetry](../guides/configuration/settings.md#telemetry) in the terminal user interface (TUI), or use the following environment variables. **All settings on this page take effect after restarting AIxCoding.** | — |
| 非注释命中 | docs/en/reference/opentelemetry.md:32 | When `CHRYS_OTEL` or “OpenTelemetry export” in the TUI is disabled, AIxCoding neither saves nor sends telemetry data, even if an endpoint or sensitive data option is configured. | — |
| 非注释命中 | docs/en/reference/opentelemetry.md:48 | After you configure any collector endpoint and restart AIxCoding, AIxCoding stops saving telemetry data locally. Failed remote exports do not fall back to local storage, so the affected data may be lost. | — |
| 非注释命中 | docs/en/reference/opentelemetry.md:91 | AIxCoding sends data over OTLP/gRPC and uses the configured endpoint addresses directly. Leave `OTEL_EXPORTER_OTLP_PROTOCOL` unset or set it to `grpc`. AIxCoding installations do not include the OTLP HTTP exporter: with `http/protobuf` (or `http`), OpenTelemetry setup fails and AIxCoding records no telemetry at all, not even locally; any other value exports nothing. | — |
| 非注释命中 | docs/en/reference/opentelemetry.md:112 | Replace `<token>` with the token provided by the collector, and set it before starting AIxCoding. | — |
| 非注释命中 | docs/en/reference/opentelemetry.md:132 | The default service name (`service.name`) is `chrys`, and the service version is the currently installed AIxCoding version. Use the service name to find data in the collector or its connected observability platform. | — |
| 非注释命中 | docs/en/reference/opentelemetry.md:134 | If AIxCoding instances running in multiple locations send data to the same collector, use service names and resource attributes to distinguish their sources. Resource attributes are labels attached to telemetry data, such as the runtime environment and instance name. | — |
| 非注释命中 | docs/en/reference/opentelemetry.md:136 | For example, when running an AIxCoding instance in a test environment, set the following in Bash or Zsh: | — |
| 非注释命中 | docs/en/reference/opentelemetry.md:143 | After you start AIxCoding in the same terminal, exported data carries the following identifiers, which you can use to filter it in the observability platform: | — |
| 非注释命中 | docs/en/reference/opentelemetry.md:149 | \| `service.instance.id` \| `test-01` \| Instance name, used to distinguish multiple AIxCoding instances in the same environment \| | — |
| 非注释命中 | docs/en/reference/opentelemetry.md:157 | When a metrics endpoint is configured (including one inherited from the base endpoint), AIxCoding attempts to export the following metrics every 5 seconds: | — |
| 非注释命中 | docs/en/reference/opentelemetry.md:165 | AIxCoding automatically adds the `gen_ai.token.type` label to token usage. When querying `gen_ai.client.token.usage` in the observability platform: | — |
| 非注释命中 | docs/en/reference/opentelemetry.md:175 | 1. OpenTelemetry is enabled, and AIxCoding was restarted after the configuration changed. | — |
| 非注释命中 | docs/en/reference/settings.md:1 | # AIxCoding-CLI settings file reference | — |
| 非注释命中 | docs/en/reference/settings.md:3 | `settings.yaml` stores AIxCoding interface preferences, the default agent, and session and tool settings. This page lists common settings by purpose and explains file locations and format, how to write values, precedence when multiple sources are present, and which settings project files can override. | — |
| 非注释命中 | docs/en/reference/settings.md:5 | For steps to change settings in the terminal user interface (TUI) and when those changes take effect, see [Configure AIxCoding settings](../guides/configuration/settings.md). | — |
| 非注释命中 | docs/en/reference/settings.md:14 | AIxCoding looks for `.chrys/settings.yaml` only in the current session's working directory. It does not search parent directories or subdirectories. | — |
| 非注释命中 | docs/en/reference/settings.md:24 | After editing the settings file manually, save it and restart AIxCoding for the changes to take effect. | — |
| 非注释命中 | docs/en/reference/settings.md:67 | If you manually set the default approval mode to `bypass` in YAML or an environment variable, approval is bypassed the next time AIxCoding starts with that default. When you switch to `bypass` with `/approval` in the TUI, AIxCoding saves `auto` as the default mode; the TUI Settings dialog does not offer `bypass`. | — |
| 非注释命中 | docs/en/reference/settings.md:69 | Hooks are external commands that AIxCoding runs on specific events. Project hooks and project settings are controlled separately: disabling `project.config_enabled` does not disable project hooks. For authoring and configuration, see [Configure and write hooks](../guides/extensions/hooks.md). | — |
| 非注释命中 | docs/en/reference/settings.md:81 | Changing the session storage root does not automatically move existing sessions. If the specified directory is unavailable, AIxCoding reports it and falls back to the default location. For migration steps, see [Move session storage](../guides/daily-use/sessions.md#migrate-session-storage). | — |
| 非注释命中 | docs/en/reference/settings.md:94 | \| `mutations.coordination.enabled` \| `CHRYS_MUTATION_COORDINATION` \| `true` \| Boolean; help distinguish file changes made by different AIxCoding sessions sharing a working directory \| | — |
| 非注释命中 | docs/en/reference/settings.md:142 | \| `notifications.suppress_when_focused` \| Suppress notifications while AIxCoding has focus \| | — |
| 非注释命中 | docs/en/reference/settings.md:148 | To send a notification, the master switch, the corresponding event switch, and at least one delivery method must be enabled, and notifications must not be suppressed because AIxCoding has focus. Turning off the master switch does not clear the other choices. | — |
| 非注释命中 | docs/en/reference/settings.md:152 | **Raw HTTP logs may contain plaintext API keys, full prompts, and model responses.** Enable this only after confirming where the data will go and who can access it. After troubleshooting, turn off diagnostic options you no longer need and restart AIxCoding. | — |
| 非注释命中 | docs/en/reference/settings.md:176 | At startup, AIxCoding attempts to migrate AIxCoding settings from the legacy user `.env` file into the user `settings.yaml` and remove the migrated lines. During the merge, existing keys in `settings.yaml` take precedence and are not overwritten. Settings that have not yet been migrated continue to apply at priority 3 in the table. If migration fails, AIxCoding reports it and retries on the next startup. Environment variables such as model service API keys remain in `.env`. | — |
| 非注释命中 | docs/en/reference/settings.md:178 | AIxCoding settings in the working directory's `.env` file do not take effect. Write project settings in `.chrys/settings.yaml`. | — |
| 非注释命中 | docs/en/reference/settings.md:227 | AIxCoding reports and ignores disallowed project keys, values that exceed override restrictions, and unknown keys, while continuing to apply other valid settings. | — |
| 非注释命中 | docs/en/reference/settings.md:236 | \| `aixcoding-cli serve` \| Hosts the TUI in a browser; configuration files and environment variables come from the machine running AIxCoding service \| | — |
| 非注释命中 | docs/en/reference/settings.md:240 | 1. Confirm that the settings file is in the correct location and that you have saved it and restarted AIxCoding. | — |
| 非注释命中 | docs/en/reference/settings.md:243 | 4. Check the messages AIxCoding reports at startup. For how invalid values and unknown keys are handled, see [Value syntax and invalid values](#value-syntax-and-invalid-values); for directory-related messages, check [File locations and format](#file-locations-and-format). | — |
| 非注释命中 | docs/en/reference/themes.md:3 | AIxCoding supports theme files for customizing the appearance of the terminal user interface (TUI). This page describes the file format, common color fields, and loading rules. To edit and save themes through the interface, see [Customize themes](../guides/configuration/themes.md). | — |
| 非注释命中 | docs/en/reference/themes.md:14 | Theme files must use UTF-8 encoding and have a `.yaml` or `.yml` extension. Place them directly in this directory; AIxCoding does not read theme files in subdirectories. | — |
| 非注释命中 | docs/en/reference/themes.md:22 | When a `.yaml` file and a `.yml` file have the same theme name, AIxCoding prefers `.yaml`. If the `.yaml` file is invalid, AIxCoding still tries the `.yml` file. Only one theme is kept per name. | — |
| 非注释命中 | docs/en/reference/themes.md:24 | After adding or editing a theme file, restart AIxCoding to load it, then press **F9** and select the corresponding theme from the theme list to apply it. | — |
| 非注释命中 | docs/en/reference/themes.md:52 | `primary` is the only required field. All other fields are optional. AIxCoding fills in omitted colors automatically; see [Default Color Rules](#default-color-rules). | — |
| 非注释命中 | docs/en/reference/themes.md:147 | If AIxCoding finds malformed YAML, a missing `primary` field, unknown top-level fields, or invalid field values while loading, it displays a warning and skips the file. Use the warning to check the corresponding file, correct it, and restart AIxCoding to load it again. Other valid themes remain available. | — |
| 非注释命中 | docs/en/reference/themes.md:149 | If a theme loads successfully but a `variables` value cannot be used in the corresponding interface style when applied, AIxCoding displays a warning and falls back to the default `chrys` theme. This fallback does not overwrite the saved theme selection. Correct the file, then restart AIxCoding to try again. | — |
| 非注释命中 | docs/en/reference/tool-kinds-and-names.md:3 | AIxCoding uses tool kinds (`tool_kind`) to group tools with similar purposes or sources, and tool names (`tool_name`) to identify individual tools. A kind can contain multiple tools. For example, `filesystem.write` includes `write_file` and `edit_file`. | — |
| 非注释命中 | docs/en/reference/tool-kinds-and-names.md:28 | Tool availability also depends on the current agent, model capabilities, and how AIxCoding is run. For example, `view_image` is only provided to models that support image input, and the headless CLI mode `aixcoding-cli run` does not provide `ask_user`. | — |
| 非注释命中 | docs/en/reference/tool-kinds-and-names.md:30 | `web_search` and `web_fetch` are not enabled in any agent shipped with AIxCoding. When an agent includes them, either tool is left out while its mode is `off` or if the model's provider runs a web tool of the same name. See [Configure web tools](../guides/configuration/web-tools.md). | — |
| 非注释命中 | docs/en/reference/tool-kinds-and-names.md:34 | The main tool in the `shell` kind uses the name of the current shell, such as `zsh`, `bash`, `pwsh`, `powershell`, or `cmd`. On Windows, when Git Bash is detected, AIxCoding also provides a `git_bash` tool alongside the main shell tool. The actual names depend on the operating system and the shells detected by AIxCoding. | — |
| 非注释命中 | docs/en/reference/tool-kinds-and-names.md:46 | The `mcp` kind includes tools provided by MCP servers. AIxCoding first replaces any characters in a tool name other than English letters, digits, underscores, and hyphens with hyphens. If `tool_name_prefix` is not set, this processed name is used directly. | — |
| 非注释命中 | docs/en/reference/tool-kinds-and-names.md:48 | When `tool_name_prefix` is set, AIxCoding also removes leading underscores and hyphens from the processed name, then combines it as `<prefix>_<tool_name>`. If removing these characters leaves an empty name, only the prefix is used. For example, if a server provides `search` or `_search` and the prefix is `github`, the final name is `github_search` in both cases. | — |
| 非注释命中 | docs/en/reference/tool-kinds-and-names.md:52 | When on-demand loading is enabled, AIxCoding also provides three control tools: | — |
| 非注释命中 | docs/en/reference/tui-slash-commands.md:29 | The following table lists the built-in slash commands in AIxCoding. | — |
| 非注释命中 | docs/en/reference/tui-slash-commands.md:41 | \| `/exit` \| `/quit` \| Exit AIxCoding and return to the terminal. \| — \| | — |
| 非注释命中 | docs/en/reference/tui-slash-commands.md:46 | \| `/login` \| — \| Open the AIxCoding device-code login dialog. The dialog shows a user code and opens the verification page in your browser automatically; confirm the grant there to finish logging in. The credential is stored with OS-level encryption and validated silently on the next start. The header shows the login state to the right of the approval-mode badge: a green ● with the account name when signed in, a gray ● "Not logged in" badge otherwise. \| — \| | — |
| 非注释命中 | docs/en/reference/tui-slash-commands.md:47 | \| `/logout` \| — \| Clear the stored AIxCoding credential for the current environment and log out. Running this while already logged out is safe: the command reports the state and does nothing. The header login badge turns gray immediately after logout. \| — \| | — |
| 非注释命中 | docs/en/reference/tui-slash-commands.md:54 | \| `/rollback`<br>`/rollback <N>`<br>`/rollback to <N>` \| — \| Roll back the conversation while keeping current file changes, or roll back the conversation and restore the file changes that AIxCoding can recover. Rollback cannot be undone. \| No argument: open the rollback picker, with the most recent available target selected by default. The file restoration option in the lower-left corner of the "Rollback" dialog (its label includes the file count) controls whether file changes are also restored.<br>`N`: immediately discard the most recent `N` turns; must be a positive integer. A turn starts with a user submission and ends when that agent run finishes.<br>`to N`: keep turns 1 through `N` and discard later turns. `N` must be a nonnegative integer; `0` returns to the start of the session.<br>Both `/rollback N` and `/rollback to N` run immediately and restore the file changes from the discarded turns that AIxCoding can recover. \| | — |
| 非注释命中 | docs/en/reference/tui-slash-commands.md:60 | \| `/settings [tab]` \| — \| Open the settings dialog. See [Configure AIxCoding settings](../guides/configuration/settings.md#settings-dialog). \| `tab`: open a specific tab directly. Available values are `general`, `models`, `security`, `sessions`, `tools`, and `notifications`. With no argument, press **Space** or **Enter** to show available tabs. \| | — |
| 非注释命中 | docs/en/reference/tui-slash-commands.md:62 | \| `/help` \| — \| Open the "AIxCoding User Guide" dialog, which shows this documentation. You can also press **F8** or click `f8 Help` in the footer. \| — \| | — |
| 非注释命中 | docs/en/reference/tui-slash-commands.md:63 | \| `/man [command]` \| — \| Show AIxCoding command help. \| No argument: press **Space** or **Enter** to show commands with help available.<br>`command`: a command name or alias. Show the specified command's name, usage, description, aliases, and options. \| | — |
| 非注释命中 | docs/en/reference/tui-slash-commands.md:67 | Skills loaded at runtime can be invoked using `/skill-name`. When you submit a skill command, AIxCoding asks the agent to use that skill for the current turn's task. | — |
| 非注释命中 | docs/en/reference/tui-slash-commands.md:76 | Skill commands are not built-in AIxCoding commands. If a skill has the same name as a built-in command, the built-in command takes precedence. | — |
| 非注释命中 | docs/en/reference/workflows.md:38 | \| 2 \| Under AIxCoding configuration directory: `%APPDATA%\chrys\workflows\` on Windows; `~/.chrys/workflows/` on Linux and macOS \| `global` \| | — |
| 非注释命中 | docs/en/reference/workflows.md:39 | \| 3 \| Built-in examples shipped with AIxCoding \| `builtin` \| | — |
| 非注释命中 | docs/en/reference/workflows.md:54 | The confirmation is saved, so later runs can omit `--trust`. Confirmation is required again if the entry file's source, the built workflow definition, or environment information changes, including the selected interpreter's path, version, platform, or the workflow SDK supplied by AIxCoding. This check does not cover changes to installed dependencies or inspect every imported Python file. | — |
| 非注释命中 | docs/en/reference/workflows.md:194 | `fn` must return a string or a `WorkflowValue`. AIxCoding converts a returned string to `WorkflowValue(text=returned_string, data=None)`. | — |
| 非注释命中 | docs/en/reference/workflows.md:218 | \| `model` \| Optional AIxCoding model profile ID or name, listed by `aixcoding-cli models`; when omitted, the model selection rules below apply \| | — |
| 非注释命中 | docs/en/reference/workflows.md:237 | `model` is matched against AIxCoding model profiles in this order: | — |
| 非注释命中 | docs/en/reference/workflows.md:245 | Regular AIxCoding agents select a model in this priority order: | — |
| 非注释命中 | docs/en/reference/workflows.md:249 | 3. The workflow's default model. In the TUI, select it under “Run Settings”. In the CLI, loading an existing workflow session with `aixcoding-cli workflow run <workflow-id> --session <session-id>` retains that session's saved model selection. If no workflow default has been selected, the [default model configured in AIxCoding](settings.md#agents-models-and-requests) is used. | — |
| 非注释命中 | docs/en/reference/workflows.md:257 | The node returns a `WorkflowValue` with the agent's response text in `text` and `None` in `data`. Regular AIxCoding agents prefer the final response text. If the final response has no text, the text emitted during this execution is concatenated in order as the node output, which may include commentary around tool calls. | — |
| 非注释命中 | docs/en/reference/workflows.md:261 | Regular AIxCoding agent nodes support profile settings as follows (✓ supported, ✗ unsupported). For field formats and configuration rules, see the [Agent profile reference](agent-profile.md). | — |
| 非注释命中 | docs/en/reference/workflows.md:285 | - An explicit `model` takes an AIxCoding model profile ID or name. AIxCoding uses only its `model_id` to request a remote model switch over ACP; the profile's other fields do not apply. If the remote agent does not list the model, or rejects the switch because the method is unsupported or the parameters are invalid, execution continues with the remote default model. | — |
| 非注释命中 | docs/en/reference/workflows.md:288 | - The external agent executes its own tools. Only operations for which it sends ACP permission requests enter AIxCoding's approval process. | — |
| 非注释命中 | docs/en/reference/workflows.md:381 | A built workflow returned by `WorkflowBuilder.build()`. Assign it to the workflow file's top-level `workflow` variable for AIxCoding to load and run. | — |
| 非注释命中 | docs/en/reference/workflows.md:607 | \| An external ACP agent node loses its connection, stops responding, reports an error, or reaches its `timeout` \| `Retry.max_attempts` has not been reached. AIxCoding cannot tell which errors an external agent reports are permanent, so it retries them all. It does not retry an agent that cannot be started, one that still cannot be reached after the attempt retried the connection several times, a rejected configuration, or an answer the agent refuses, cuts short or leaves empty \| | — |
| 非注释命中 | docs/en/reference/workflows.md:610 | If retrying could make the model provider run one of its own tools a second time, such as an MCP server or shell the provider runs, the node is not retried automatically. Provider-run search and code execution are safe to repeat and don't stop retries; neither do AIxCoding's own file, Shell or MCP tools. | — |
| 非注释命中 | docs/en/reference/workflows.md:626 | By default, workflows use the Python interpreter running AIxCoding. You can instead specify an existing virtual environment or Python executable in the workflow file. Python 3.9 and later are supported. | — |
| 非注释命中 | docs/en/reference/workflows.md:637 | Keep the `#` prefixes and `# ///` markers: AIxCoding reads the configuration from these comments. `[tool.chrys]` is the AIxCoding-specific configuration section. Relative `python` paths are resolved against the directory containing the workflow file. | — |
| 非注释命中 | docs/en/reference/workflows.md:639 | `python` can also point directly to a Python executable, such as `"/opt/homebrew/bin/python3.12"`. AIxCoding does not search `PATH` for commands. For an environment created with uv, point to its `.venv`. | — |
| 非注释命中 | docs/en/reference/workflows.md:641 | AIxCoding does not install dependencies automatically. Install the workflow's third-party packages in the selected environment beforehand. AIxCoding supplies `chrys.workflows` at runtime, so it needs no separate installation. | — |
| 非注释命中 | docs/en/reference/workflows.md:647 | \| `requires-python` \| Optional Python version constraint string, such as `">=3.10,<3.13"`. AIxCoding checks the selected interpreter against it and refuses to load if it does not match; it does not find or install another version automatically. Only comma-separated `~=`, `==`, `!=`, `<=`, `>=`, `<`, and `>` clauses with numeric release versions are supported: `.*` works only with `==` and `!=`, and `~=` needs at least two version components. Any other clause also refuses loading \| | — |
| 非注释命中 | docs/en/reference/workflows.md:648 | \| `dependencies` \| Optional array of dependency strings. A nonempty array requires `[tool.chrys] python`, otherwise loading is refused even if the default environment already has those packages. With a user-supplied interpreter, AIxCoding neither installs these dependencies nor verifies that installed versions match the declaration \| | — |
| 非注释命中 | docs/en/reference/workflows.md:675 | Run Settings also offers a default model selector when the workflow contains AIxCoding agent nodes. | — |
| 非注释命中 | docs/en/reference/workflows.md:723 | \| `session_restored` \| When a session loaded from saved records starts its first new run in the current AIxCoding process, before `workflow_run_start` \| `restored_session_id`: ID of the restored session \| | — |
| 非注释命中 | docs/en/reference/workflows.md:724 | \| `session_end` \| When a session that has started a run in the current AIxCoding process is deleted, AIxCoding closes normally, or the CLI run command ends normally \| None \| | — |
| 非注释命中 | docs/en/reference/workflows.md:728 | Within each AIxCoding process, a session triggers `session_start` or `session_restored` only on its first run. Each accepted run triggers one `workflow_run_start` and one `workflow_run_end`; node retries do not trigger them again. End events are not guaranteed if the process crashes or is forcibly terminated. | — |
| 非注释命中 | docs/en/reference/workflows.md:732 | `workflow_run_start` and `workflow_run_end` are for notifications and recording. If a hook is configured as blocking, AIxCoding waits for it to finish but does not use its returned action to prevent the run or grant tool permissions. `action: block` is ignored, and `on_error: block` is treated as a warning on hook failure. | — |
| 非注释命中 | docs/en/start/getting-started.md:1 | # Getting started with AIxCoding-CLI | — |
| 非注释命中 | docs/en/start/getting-started.md:3 | This tutorial shows how to install AIxCoding-CLI, configure a model, and use agents to complete a development task in a project. | — |
| 非注释命中 | docs/en/start/getting-started.md:5 | ## 1. Install AIxCoding-CLI | — |
| 非注释命中 | docs/en/start/getting-started.md:7 | AIxCoding-CLI provides prebuilt offline installation packages for macOS, Linux, and Windows. The packages include Python and runtime dependencies, so you do not need to install Python separately. | — |
| 非注释命中 | docs/en/start/getting-started.md:50 | For the test channel, set `$env:ICODE_CHANNEL='test'` before running the command. The installer attempts to add AIxCoding-CLI to the current user's `PATH`. Open a new terminal after installation. | — |
| 非注释命中 | docs/en/start/getting-started.md:58 | The command should print AIxCoding-CLI version number. If your system cannot find `aixcoding-cli` on macOS or Linux, add `~/.local/bin` to `PATH` as the installer instructs. If the installer reported that `~/.local/bin/aixcoding-cli` already exists, that command starts another program; use `chrys` instead. On Windows, open a new terminal; if the installer reported that updating the user PATH failed, add `%LOCALAPPDATA%\chrys\bin` to your user `PATH` manually. | — |
| 非注释命中 | docs/en/start/getting-started.md:60 | ## 2. Start AIxCoding-CLI in a project | — |
| 非注释命中 | docs/en/start/getting-started.md:64 | In a terminal, go to the project directory and start AIxCoding-CLI: | — |
| 非注释命中 | docs/en/start/getting-started.md:95 | AIxCoding-CLI should reply with a greeting. If the model service returns an error, check the model profile again, including the model ID, base URL, and API key. | — |
| 非注释命中 | docs/en/start/getting-started.md:101 | AIxCoding-CLI provides two main agents by default: Q&A Agent and Code Agent. Both can read the project, analyze code, and discuss approaches, but they have different roles and tools. Q&A Agent primarily provides read-only capabilities for understanding projects, explaining code, and analyzing problems. Code Agent can modify files and run commands, making it suitable for writing, reviewing, refactoring, debugging, and validating code. | — |
| 非注释命中 | docs/en/start/getting-started.md:137 | To finish using AIxCoding-CLI, type `/exit` or press `Ctrl+Q` to exit. | — |
| 非注释命中 | docs/en/start/getting-started.md:141 | You have installed AIxCoding-CLI, configured a model, and learned the basics of Q&A Agent and Code Agent, including how to use them together in the same session to complete a development task. | — |
| 非注释命中 | docs/en/start/getting-started.md:149 | - Extend AIxCoding-CLI with [Skills](../guides/extensions/skills.md) and [MCP](../guides/extensions/mcp.md) | — |
| 非注释命中 | docs/en/start/what-is-aixcoding.md:1 | # What is AIxCoding? | — |
| 非注释命中 | docs/en/start/what-is-aixcoding.md:3 | **AIxCoding is a platform for running and building agents.** | — |
| 非注释命中 | docs/en/start/what-is-aixcoding.md:5 | AIxCoding lets you interact with agents in natural language to read and edit files, run shell commands, search codebases, and perform other tasks. Complex tasks can also be delegated to sub-agents. | — |
| 非注释命中 | docs/en/start/what-is-aixcoding.md:7 | The main way to interact with AIxCoding is through its terminal user interface (TUI), which brings conversations, task execution, and tool calls together in one place. Tool calls appear as cards so you can see what the agent is doing. AIxCoding also supports headless execution in scripts, integration with editors through the Agent Client Protocol (ACP), and running the TUI in a browser. | — |
| 非注释命中 | docs/en/start/what-is-aixcoding.md:13 | * **Configurable agents.** Configure an agent's instructions, model, tools, skills, MCP servers, and sub-agents through the TUI, or edit its YAML profile directly, without changing AIxCoding source code. | — |
| 非注释命中 | docs/en/start/what-is-aixcoding.md:19 | Agents and models are independent in AIxCoding, so you can combine them to suit different tasks. AIxCoding includes built-in agents but does not include model profiles or API credentials. Before first use, create a model profile and connect it to a model service. | — |
| 非注释命中 | docs/en/start/what-is-aixcoding.md:21 | AIxCoding currently supports model providers including Anthropic, OpenAI, DeepSeek, and GLM. You can also connect to other model services, including locally hosted models, through OpenAI API-compatible endpoints. | — |
| 非注释命中 | docs/en/start/what-is-aixcoding.md:23 | ## Using AIxCoding | — |
| 非注释命中 | docs/en/start/what-is-aixcoding.md:25 | AIxCoding offers several ways to work, depending on your needs: | — |
| 非注释命中 | docs/en/start/what-is-aixcoding.md:27 | - **TUI**: The main AIxCoding interface, suited to interactive tasks. View tool calls, handle approval requests, and switch agents and model profiles within a session. | — |
| 非注释命中 | docs/en/start/what-is-aixcoding.md:30 | - **ACP server**: Use AIxCoding as an agent backend for [editors or other development tools that support ACP](../guides/running/aixcoding-acp.md). | — |
| 非注释命中 | docs/en/start/what-is-aixcoding.md:34 | When you are ready to start, read [Getting started with AIxCoding](getting-started.md) for installation, model configuration, and your first run. | — |
| 非注释命中 | docs/index.yaml:33 | zh-Hans: 运行 AIxCoding-CLI | — |
| 非注释命中 | docs/index.yaml:34 | en: Running AIxCoding-CLI | — |
| 非注释命中 | docs/index.yaml:46 | zh-Hans: 配置 AIxCoding-CLI | — |
| 非注释命中 | docs/index.yaml:47 | en: AIxCoding-CLI Configuration | — |
| 非注释命中 | docs/index.yaml:69 | zh-Hans: 扩展 AIxCoding-CLI | — |
| 非注释命中 | docs/index.yaml:70 | en: AIxCoding-CLI Extensions | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/agents.md:3 | AIxCoding 使用智能体配置定义智能体的名称、提示词、模型、可调用工具和子智能体等。本指南介绍如何在终端用户界面（Terminal User Interface，TUI）中创建、克隆、修改、重置、切换和删除智能体配置，以及如何为智能体设置模型和子智能体。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/agents.md:57 | 需要基于现有智能体创建新的配置时，可以使用克隆功能。克隆会生成一个独立副本，不会修改原智能体配置。克隆内置智能体时，AIxCoding 会创建对应的自定义智能体副本，后续可以独立修改。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/agents.md:61 | 3. AIxCoding 会复制原智能体的配置，自动生成不重复的智能体名称和显示名称，并选中生成的副本。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/agents.md:67 | - 点击“克隆”后，AIxCoding 会创建一个用于当前配置界面编辑的临时副本，只有点击“保存”后，该配置才会正式创建并保留。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/agents.md:78 | - AIxCoding 默认提供的内置智能体（如 Code Agent、Q&A Agent）的“名称”和“智能体类型”不可修改，其他配置可以按需调整。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/agents.md:84 | 删除自定义智能体后，保存在本机的相关配置也会被移除，且无法在 AIxCoding 中撤销。内置智能体不能删除。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/agents.md:97 | 如果删除的是当前正在使用的智能体，关闭配置窗口后，AIxCoding 会自动切换到其他可用的主智能体。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/agents.md:101 | AIxCoding 默认提供的内置智能体不支持删除。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/agents.md:103 | 修改内置智能体并保存后，AIxCoding 会在[用户智能体配置目录](../../reference/agent-profile.md#用户智能体配置目录)中生成同名的用户配置文件，例如 `Code.yaml`。该文件会保存修改内容以及当时生效的其他设置。例如，只新增一个 MCP 服务器时，保存后的配置既包含这个 MCP 服务器，也保留其他设置当时的值。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/agents.md:105 | 启动时，AIxCoding 会优先使用同名的用户配置文件，而不会将用户配置与内置配置逐项合并。因此，升级 AIxCoding 后，新版本对内置智能体提示词等默认设置的更新不会自动应用到该智能体。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/agents.md:142 | AIxCoding 默认提供的 Code Agent 和 Q&A Agent 可以作为主智能体，Explore 和 General 仅用作子智能体。外部 ACP 智能体也仅用作子智能体，配置方法请参阅[配置外部 ACP 智能体](../extensions/external-acp-agents.md)。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/agents.md:178 | 切换后，AIxCoding 会立即使用所选智能体处理后续请求。当前使用的智能体在列表中以灰色显示，名称前带有空心圆圈。列表仅显示可以作为主智能体使用的配置。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/approval.md:3 | 智能体执行工具调用（例如运行 Shell 命令、写入文件）时，AIxCoding 可能要求先经过审批。本指南介绍如何在终端用户界面（Terminal User Interface，TUI）中选择审批模式、处理审批请求，以及不同运行方式下的审批设置。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/approval.md:7 | 审批模式决定 AIxCoding 如何处理需要审批的工具调用。具体哪些调用需要审批，由智能体配置文件中的 `approval` 审批策略和 AIxCoding 的安全规则共同决定，详见[智能体配置文件参考中的 approval 字段](../../reference/agent-profile.md#approval)。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/approval.md:34 | 未更改默认设置时，首次启动 TUI 默认使用“手动”审批模式。切换当前审批模式时，AIxCoding 也会更新下次启动的默认模式：选择“手动”或“自动”会将所选模式保存为默认值；选择“绕过”只对当前运行生效，为避免重启后继续绕过审批保护，此时下次启动的默认模式会保存为“自动”。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/approval.md:44 | - 自动模式下，对话框先显示“正在评估”。模型判定安全后，对话框自动关闭；模型判定可疑时，标题变为“自动审查已标记”并展示理由，等待人工决定。评估期间也可以直接批准或拒绝。如果审批裁判模型不可用或评估失败，AIxCoding 不会自动批准工具调用，而是保留审批对话框，等待人工决定。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/approval.md:69 | - 手动模式下，弹出“工具审批”对话框；批准后显示 AIxCoding 版本。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/approval.md:71 | - 绕过模式下，不显示审批对话框，直接运行命令并显示 AIxCoding 版本。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/approval.md:78 | - **AIxCoding ACP 服务**：默认手动，可用 `aixcoding-cli acp --approval manual\|auto\|bypass` 指定初始模式；支持该能力的 ACP 客户端也可以切换当前会话的模式。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/compaction.md:3 | 长对话接近模型的上下文窗口时，AIxCoding 会自动压缩较早的内容，为后续请求留出空间。本指南介绍如何配置“内置”类型智能体的 Last Words 补充内容和输出上限。外部 ACP 智能体自行管理上下文。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/compaction.md:9 | AIxCoding 根据当前模型配置中的最大上下文窗口、最大输出词元数和安全余量自动计算何时开始压缩。请根据模型能力和任务需要，在[模型配置](./models.md)中设置最大上下文窗口和最大输出词元数。“压缩”标签页不能单独设置触发时机。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/compaction.md:11 | 上下文接近占满时，AIxCoding 还会降低下一次请求的输出上限，使输入和输出都能容纳在上下文窗口内，并为词元数估算误差留出少量余量。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/compaction.md:13 | 压缩时，AIxCoding 会先将较早的工具结果替换为摘要，必要时再移除较早的工具调用及其结果；如果仍需释放空间，则在当前上下文中用压缩摘要代替已经完成的对话轮次。如果这些处理仍然不够，AIxCoding 会为当前任务生成 Last Words，保留继续完成任务所需的信息，再从提供给模型的上下文中移除本轮的工具调用、工具结果和中间内容，只保留用户消息。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/memory.md:7 | **记忆会在主智能体加载时加入系统提示词。** AIxCoding 会读取当前主智能体配置的记忆文件，并将内容作为参考资料提供给智能体。记忆内容会占用模型的上下文窗口，并随请求发送给模型服务。因此，建议避免在记忆中包含密钥、访问令牌等敏感信息。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/memory.md:11 | **记忆适合保存稳定且通用的信息。** AIxCoding 只加载扩展名为 `.md` 或 `.txt` 的记忆文件。适合放入记忆的内容应当能够在多个任务中重复使用，例如项目约定、背景资料和常用信息。内容应简短、明确并保持更新；临时任务要求更适合直接写在当前请求中。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/memory.md:13 | **默认智能体已配置 AGENTS.md 作为记忆。** AIxCoding 默认提供的主智能体（如 Code Agent）会加载工作目录中的 `AGENTS.md`。需要为项目补充通用说明时，可以优先维护该文件；如不需要，可在“记忆”标签页中删除该条目。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/memory.md:28 | AIxCoding 会先加载该目录直属的 `.md` 和 `.txt` 文件，再逐层扫描子目录。对于每个配置的文件夹，最多扫描两层子目录，最多加载 100 个文件。若某个重要文件可能不在扫描范围内，可将其单独添加到“文件”区域。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/memory.md:32 | 同一实际文件同时被单独添加和从文件夹中发现时，只会加载一次。多个记忆来源的合计内容上限为 35,000 词元。AIxCoding 先加载单独添加的文件，再加载文件夹；一旦某个文件会使内容超过上限，该文件及其后的所有文件都会被跳过，AIxCoding 会显示警告。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/memory.md:34 | 切换工作目录或修改当前智能体配置后，AIxCoding 会根据新路径重新加载记忆。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/memory.md:36 | AIxCoding 不会实时监控已经加载的记忆文件。直接在磁盘上修改文件内容后，需要重新加载主智能体才能使修改生效，例如重新启动 AIxCoding、切换工作目录、修改并保存当前智能体配置，或切换到其他主智能体后再切回。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/models.md:31 | - 点击“新建”时，AIxCoding 会立即创建并保存一项空白配置。后续填写或修改的内容需要点击“保存”才会生效；直接关闭窗口不会删除已经创建的空白配置。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/models.md:46 | 将 `PROVIDER_API_KEY` 替换为存放密钥的环境变量名；启动 AIxCoding 前应确保该环境变量已经设置。环境变量名只能包含字母、数字和下划线，且不能以数字开头。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/models.md:54 | 3. AIxCoding 会创建并选中一个包含原配置全部字段的副本，并为副本生成不重复的名称。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/models.md:70 | 删除操作会移除保存在本机的模型配置文件，且**无法在 AIxCoding 中撤销**。确认不再需要该配置后： | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/models.md:77 | AIxCoding 至少保留一项模型配置，因此只剩一项时无法点击“删除”。如果删除了正在使用的配置，关闭配置窗口后，AIxCoding 会自动切换到其他可选配置。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/models.md:108 | AIxCoding 应正常返回问候回复。若模型服务返回错误，先核对模型 ID、服务地址、API 密钥等模型配置。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/models.md:112 | - **报错信息包含 `The Chat Completions client supports only n=1`**：使用 Chat Completions 样式时，AIxCoding 每次请求只处理一条回复，不支持多候选回复，`n` 参数应省略或设为整数 `1`。在模型配置的“Chat 选项（额外请求字段）”中把该值删除或改为 `1`，包括经 `extra_body` 间接设置的情况。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/models.md:117 | AIxCoding 能判断模型请求失败的原因时，会用通俗的话说明原因，并在下方附上原始错误信息；暂停的子智能体卡片上也是如此。AIxCoding 自动重试时，重试提示只显示这句说明。如果运行 AIxCoding 的设备看起来没有网络连接，AIxCoding 也会一并提示，此时请先检查网络。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/settings.md:1 | # 配置 AIxCoding-CLI 设置 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/settings.md:3 | AIxCoding 设置控制界面外观、默认智能体、会话、工具、通知和部分安全选项。本指南介绍如何在终端用户界面（Terminal User Interface，TUI）中完成这些基础配置，并确认修改何时生效。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/settings.md:5 | 如需直接编辑 `settings.yaml` 或通过环境变量配置，请参阅[AIxCoding 设置文件参考](../../reference/settings.md)，了解文件位置、设置键和来源优先级。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/settings.md:43 | \| 提示有多少项修改需重启后生效 \| 修改已经保存，但必须退出并重新启动 AIxCoding 后才会生效 \| | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/settings.md:56 | \| 界面显示语言 \| 只改变 AIxCoding 界面文案，不改变会话内容、模型输出语言或已有记录。也可输入 `/language` 切换界面显示语言。\| 立即 \| | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/settings.md:62 | \| 保存提示词历史 \| 跨会话保存提交过的输入，供后续复用。主界面未被其他窗口覆盖时，按 **Ctrl+R** 会在输入栏上方打开历史提示词列表；鼠标单击记录，或用上下键选中记录后按回车，会将该提示词复制到输入栏。提示词历史记录文件 `prompt_history.jsonl` 保存在：macOS 和 Linux 的 `~/.chrys/`，或 Windows 的 `%APPDATA%\chrys\`。关闭此设置不会删除该历史记录文件，只是不再读取，按 **Ctrl+R** 将显示“无结果”；重新启用并重启 AIxCoding 后，仍可读取该历史记录文件中的记录。若要清理历史，请删除该历史记录文件；删除后无法恢复。 \| 重启后 \| | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/settings.md:94 | \| 默认审批模式 \| 设置下次启动 AIxCoding 时默认使用的审批模式，不影响当前会话。窗口中只提供 `manual` 和 `auto`；如需在当前会话中绕过审批，请使用 `/approval bypass`。当前会话的模式切换及各模式区别请参阅[配置审批模式](./approval.md)。 \| 设置立即保存，下次启动生效 \| | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/settings.md:107 | \| 捕获原始 HTTP 流量 \| 记录模型请求和响应，以便排查问题。**日志可能以明文包含 API 密钥、完整提示词和模型回复**，因此建议仅在排查时开启，并妥善保管日志文件；排查完成后，应及时关闭该设置并重启 AIxCoding。日志文件 `llm_raw_http.jsonl` 保存在当前会话文件夹中；查找该文件夹的方法请参阅[查找会话 ID 和会话保存位置](../daily-use/sessions.md#查找会话-id-和会话保存位置)。 \| 重启后 \| | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/settings.md:113 | \| OpenTelemetry 导出 \| 启用遥测，记录追踪、日志和指标。关闭时，另外两项不会使 AIxCoding 保存或发送遥测数据。 \| 重启后 \| | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/settings.md:125 | \| 自动生成会话标题 \| 开启后，AIxCoding 会发起额外的模型请求以根据对话内容智能生成标题。**手动设置会话标题后，AIxCoding 不再自动更新该会话的标题。** 有关设置或清除手动标题，请参阅[修改会话标题](../daily-use/sessions.md#修改会话标题)。 \| 关闭窗口后 \| | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/settings.md:131 | \| 会话存储根目录 \| 决定 AIxCoding 保存会话的位置，留空时使用默认位置；会话实际保存在该目录的 `sessions` 子目录。“使用中”显示本次启动正在使用的 `sessions` 目录。修改根目录后，需要重启 AIxCoding 才会使用新位置；重启前，会话仍保存在“使用中”所示目录。**重启后，新会话会保存到新目录，但旧会话文件不会自动迁移。** 若要在新位置继续使用已有会话，请参阅[迁移会话存储位置](../daily-use/sessions.md#迁移会话存储位置)。 \| 重启后 \| | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/settings.md:137 | \| 保留的回滚快照数 \| 决定每个会话最多保留多少份回滚快照。AIxCoding 每次开始处理一条新提交的提示词前，都会创建一份快照；超过保留数量后，较早的快照会被自动删除。快照保存在对应会话文件夹的 `snapshots` 子目录中。保留的快照越多，使用 `/rollback` 时可返回的较早会话状态越多，但占用的磁盘空间也越多。 \| 关闭窗口后 \| | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/settings.md:169 | \| 询问用户超时（秒） \| 决定 AIxCoding 等待回答的时间。留空时使用 TUI 界面显示的默认值。超过设定时间仍未收到回答时，AIxCoding 会把超时结果返回给智能体；设为 `0` 时会一直等待，直到收到回答或任务中断。通过 IDE 插件等 ACP 客户端使用时，`ask_user` 默认不设置服务端等待时限；如需限制等待时间，请在启动 ACP 服务时使用 `--ask-user-timeout`。 \| 关闭窗口后 \| | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/settings.md:181 | \| 工作区变更通知 \| 开始处理一条新提交的提示词时，AIxCoding 会向智能体提供自上一次提交提示词以来的工作目录文件变更摘要。其中既包括当前会话中智能体及其子智能体的改动，也包括由人工、其他程序或其他 AIxCoding 会话造成的改动。 \| 关闭窗口后 \| | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/settings.md:196 | \| AIxCoding 获得焦点时暂停通知 \| AIxCoding 位于前台时不发送桌面弹窗或声音。                                                        \| 立即 \| | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/themes.md:61 | 在编辑器顶部选择用户主题，点击“删除”，核对确认窗口中的主题名称后再次点击“删除”。删除当前已应用的主题后，AIxCoding 会切换到默认主题 `chrys`。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/tools.md:3 | 内置工具为智能体提供访问文件、搜索内容、执行 Shell 命令以及使用其他 AIxCoding 功能的能力。本指南介绍如何在终端用户界面（Terminal User Interface，TUI）中为智能体启用或停用内置工具类别。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/tools.md:34 | AIxCoding 自带的智能体都没有启用网络搜索；它与只搜索本地文件的“文件搜索”不同。“网页读取”是单独的开关。未配置搜索提供方时，搜索请求会发往 Exa 的公开搜索服务。启用前，请参阅[配置网络工具](./web-tools.md)，了解请求的去向、审批和网络限制。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/tools.md:40 | 默认情况下，问题显示在弹出窗口中。如果弹窗遮挡了需要查看的会话内容，可以点击“在对话中回答”，将当前提问切换为在对话中显示；此操作仅对当前提问生效。如果希望后续提问默认在对话中显示，请在[配置 AIxCoding 设置](./settings.md)中开启“在对话中显示提问”。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/tools.md:44 | 等待回答的时间由[配置 AIxCoding 设置](./settings.md)中的“询问用户超时（秒）”设置控制。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/tools.md:58 | 对于文件系统、搜索和 Shell 工具，相对路径会以当前[工作目录](../daily-use/workspaces.md)为基准，Shell 命令也默认在当前工作目录中运行。切换工作目录后，这些相对路径和命令的默认工作目录会随之改变。工作目录是默认操作位置，并不表示工具只能访问工作目录内的路径；操作能否执行还取决于工具参数、需要审批时是否获得批准，以及运行 AIxCoding 的系统用户权限。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/web-tools.md:5 | **网络工具默认关闭。** AIxCoding 自带的智能体（Code、QA、Explore 和 General）都不包含网络工具；在你为某个智能体启用之前，AIxCoding 不会发送任何搜索请求，也不会读取任何网页。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/web-tools.md:22 | 网络工具按智能体分别配置。子智能体（例如 General）只有在自己的配置中包含网络工具时才能使用。如需为内置智能体添加网络工具，在 TUI 中编辑并保存该智能体，AIxCoding 会为其保存一份你自己的配置（参阅[覆盖内置智能体](../../reference/agent-profile.md#覆盖内置智能体)）。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/web-tools.md:40 | 启用 `web_search` 且未配置搜索提供方时，默认的 `auto` 模式会将搜索请求发送到 **Exa 的公开匿名搜索端点 `https://mcp.exa.ai/mcp`**。Exa 是第三方搜索服务，无需 API 密钥或账号。AIxCoding 只发送智能体要搜索的内容和所需结果数量，不会发送你的文件或对话本身；但搜索词由智能体撰写，可能包含任务中的细节。该服务有免费额度的速率限制，也可能无法访问。如需将搜索请求发往其他服务，参阅[选择搜索提供方](#选择搜索提供方)；如需停止搜索，将模式设为 `off`。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/web-tools.md:68 | 如果组合无效，例如 `auto` 模式配置了 `providers` 却没有 `fallback_chain`，智能体仍会启动，但不包含网络工具，AIxCoding 会显示一条写明原因的警告（参阅[网络工具没有出现时](#网络工具没有出现时)）。未知的模式或格式错误的提供方条目则会使整个配置文件无效。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/web-tools.md:117 | AIxCoding 从启动 AIxCoding 时的环境变量或用户 `.env` 文件（macOS / Linux：`~/.chrys/.env`；Windows：`%APPDATA%\chrys\.env`）读取密钥。启动环境中已设置的变量优先，即使其值为空。工作目录中的 `.env` 文件不能提供网络工具凭据。用户 `.env` 文件在每次构建智能体时读取，修改后需重新保存智能体或重启 AIxCoding。AIxCoding 只读取智能体实际使用的提供方所需的密钥。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/web-tools.md:121 | `auto` 模式下，AIxCoding 按 `fallback_chain` 的顺序尝试各提供方，并返回第一个得到的结果，空结果也算。出现以下情况时，AIxCoding 会改用下一个提供方： | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/web-tools.md:130 | 对于需要密钥的提供方和自定义提供方，HTTP 4xx 错误通常说明配置有误（例如密钥错误），因此回退链会停止，智能体收到带状态码的错误，例如 `Error: http_4xx (HTTP 403)`。由请求本身引起的错误（例如搜索词为空）也会停止回退链。AIxCoding 不会暗中回退：只尝试你列出的提供方。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/web-tools.md:210 | - **仅限公网地址**：连接前，AIxCoding 解析主机名，并拒绝私有、回环、链路本地等非公网地址，除非来源列在 `private_origins` 中。随后 AIxCoding 连接已检查过的地址，同时在请求和 TLS 证书校验中保留原始主机名。“网络代理 DNS”设为 `remote` 时改由代理解析主机名，参阅[使用 fake-IP 代理](#使用-fake-ip-代理)。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/web-tools.md:213 | - **代理**：网络工具忽略 `HTTP_PROXY`、`HTTPS_PROXY` 等代理变量。如需使用代理，将“网络代理地址”（`tools.web_egress.proxy_url`）设为 `http://` 或 `https://` 代理地址，不含凭据和路径。该代理只用于网络工具。“网络代理 DNS”为默认的 `local` 时，AIxCoding 经代理只连接网站的 IPv4 地址，因此只有 IPv6 地址的网站会返回 `proxy_ipv6_unsupported` 错误。设为 `remote` 时由代理解析主机名，代理可以通过 IPv6 访问这类网站。无论哪种模式，直接写出 IPv6 地址的 URL（例如 `https://[2001:db8::1]/`）都无法通过代理访问。环境中的证书设置（例如 `SSL_CERT_FILE`）仍然有效。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/web-tools.md:232 | 设为 `remote` 后，AIxCoding 把主机名交给代理，最终连接哪个地址由代理决定。对主机名拦截私有地址和其他非公网目标因此成为代理的职责，而不再由 AIxCoding 负责。其他规则仍然有效：仅限 HTTPS、来源列表、重定向检查，以及按主机名进行的 TLS 证书校验。直接写成非公网地址的 URL（例如 `https://127.0.0.1` 或 `https://localhost`）仍会被拒绝，除非来源列在 `private_origins` 中。URL 中直接写出的 IPv6 地址仍然无法通过代理访问，会返回 `proxy_ipv6_unsupported` 错误。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/web-tools.md:234 | AIxCoding 不会自行切换到 `remote`。把 fake-IP 地址段加入 `private_origins` 也不能替代这一设置：列表只接受单个来源，而放行整个地址段还会让解析到你自己网络的主机名一并通过。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/web-tools.md:238 | 智能体可以用 `allowed_domains` 限定搜索范围，或用 `blocked_domains` 排除域名，但两者不能同时使用。域名同时涵盖其子域名。AIxCoding 始终自行检查结果，提供方能提供多少帮助则因提供方而异： | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/web-tools.md:241 | - Exa 公开端点不支持筛选，因此 AIxCoding 向其请求更多结果，只保留匹配的结果。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/web-tools.md:261 | - 同站重定向（协议和端口相同，仅多或少 `www.` 前缀）最多跟随 2 次，每次都按网络规则检查。重定向到其他网站时，AIxCoding 会把新 URL 报告给智能体，由智能体显式读取。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/web-tools.md:266 | - AIxCoding 不执行 JavaScript，不读取 `robots.txt`，也不对页面做摘要。可以用 `denied_origins` 阻止 `web_fetch` 访问特定来源。每个条目只精确匹配一个来源，不包括子域名或 `www.` 变体，需要的每一个都要单独列出。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/web-tools.md:268 | 搜索结果和页面文本来自外部来源，AIxCoding 会向智能体标明它们是不可信的数据；使用重要信息前，应核对来源链接。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/web-tools.md:272 | 部分模型服务可以自行运行网络搜索。模型配置在 `chat_options` 中声明此类工具时（例如 `{"tools": [{"type": "web_search"}]}`），提供方的工具会占用该名称。如果智能体也包含对应的 AIxCoding 工具，本地工具会在该次运行中停用，AIxCoding 会显示一次提示。该规则按名称生效：由提供方运行的 `web_search` 不影响本地的 `web_fetch`。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/web-tools.md:274 | 由提供方运行的搜索在模型提供方一侧执行，因此不受 AIxCoding 审批规则和网络设置约束。如需改用 AIxCoding 自己的工具，请从模型的 `chat_options` 中删除该声明。 | — |
| 非注释命中 | docs/zh-Hans/guides/configuration/web-tools.md:278 | 如果 AIxCoding 无法为某个智能体准备网络工具（例如缺少密钥变量，或自定义端点未授权），该智能体仍会启动，只是不包含网络工具，AIxCoding 会显示一条警告，写明智能体名称和原因。修正配置后，重新保存智能体或重启 AIxCoding。 | — |
| 非注释命中 | docs/zh-Hans/guides/daily-use/sessions.md:3 | 会话包含对话历史及相关数据，例如回滚快照、诊断日志等。AIxCoding 会自动保存会话，以便稍后恢复对话或查询历史任务。本指南介绍如何在终端用户界面（Terminal User Interface，TUI）中切换、命名、查找、恢复和删除会话，以及更换存储位置时如何迁移已有会话。 | — |
| 非注释命中 | docs/zh-Hans/guides/daily-use/sessions.md:22 | 手动设置标题后，新标题会显示在会话列表和主界面中，AIxCoding 将不再自动更新该会话的标题。若已开启[自动生成会话标题](../configuration/settings.md#会话)，清空“会话标题”窗口中的内容并保存后，AIxCoding 会恢复已有的自动标题，并在后续任务中继续自动更新。 | — |
| 非注释命中 | docs/zh-Hans/guides/daily-use/sessions.md:30 | - **按最后使用位置筛选**：搜索框上方的“TUI”“CLI”“ACP”复选框分别对应最后在 TUI 中、通过 [`aixcoding-cli run`](../running/aixcoding-run.md)，或在通过 [`aixcoding-cli acp`](../running/aixcoding-acp.md) 连接的编辑器等客户端中使用的会话。默认只勾选“TUI”。旧版本 AIxCoding 保存的会话按 TUI 处理。所做选择在退出 AIxCoding 前一直保留。将鼠标悬停在会话上，可查看它最后在哪里使用。 | — |
| 非注释命中 | docs/zh-Hans/guides/daily-use/sessions.md:34 | - **恢复会话**：选择目标会话后点击“恢复”；也可以双击目标会话，或使用上下方向键选择后按回车。AIxCoding 会关闭当前对话视图，加载所选会话，并将工作目录切换到该会话保存时的主工作目录；当前会话仍会保存在列表中。恢复前可通过列表中的“目录”列核对将要恢复的工作目录。 | — |
| 非注释命中 | docs/zh-Hans/guides/daily-use/sessions.md:36 | 恢复较长的对话时，AIxCoding 会先显示最近的内容，可立即继续操作；更早的消息会在随后几秒内陆续加载到上方。 | — |
| 非注释命中 | docs/zh-Hans/guides/daily-use/sessions.md:44 | 删除当前会话时，AIxCoding 会同时开始新会话，与 `/clear` 类似。其他 AIxCoding 实例正在使用的会话无法删除，请先关闭该实例。 | — |
| 非注释命中 | docs/zh-Hans/guides/daily-use/sessions.md:58 | 开始前，结束当前任务并关闭其他 AIxCoding 实例，然后执行以下操作： | — |
| 非注释命中 | docs/zh-Hans/guides/daily-use/sessions.md:67 | \| 已存在 \| 目标中已有同一会话 ID，因此跳过。AIxCoding 不会比较或更新目标内容。 \| 无法确认目标版本时，建议更换空的目标目录重新迁移，或保留源数据。 \| | — |
| 非注释命中 | docs/zh-Hans/guides/daily-use/sessions.md:68 | \| 使用中 \| 会话正在某个 AIxCoding 实例中打开，因此跳过。 \| 关闭其他实例后重试。若是当前会话，关闭设置窗口并执行 `/new`；不要在新会话中发送消息，然后再次迁移。 \| | — |
| 非注释命中 | docs/zh-Hans/guides/daily-use/sessions.md:73 | 5. 关闭所有 AIxCoding 实例并重新启动，再按 **F1** 打开“聊天会话”窗口，确认重要会话已经出现并可以恢复。 | — |
| 非注释命中 | docs/zh-Hans/guides/daily-use/sessions.md:75 | 迁移完成后，源目录会保留原数据，不会自动删除。确认迁移完整后，如需释放空间，关闭 AIxCoding，再归档或删除迁移窗口中“从”所显示的旧 `sessions` 目录。手工删除无法撤销。 | — |
| 非注释命中 | docs/zh-Hans/guides/daily-use/workspaces.md:3 | 工作目录是 AIxCoding 执行文件操作和命令时使用的默认目录。在让智能体修改文件前，建议先保存尚未写入磁盘的内容，并使用 Git commit 记录已有变更，以便区分智能体所做的修改，并在需要时恢复到修改前的状态。 | — |
| 非注释命中 | docs/zh-Hans/guides/daily-use/workspaces.md:7 | 在终端中进入项目目录并启动 AIxCoding： | — |
| 非注释命中 | docs/zh-Hans/guides/daily-use/workspaces.md:14 | AIxCoding 会将启动时所在的目录作为工作目录。 | — |
| 非注释命中 | docs/zh-Hans/guides/daily-use/workspaces.md:32 | `<project-directory>` 可以是绝对路径，也可以是相对于当前工作目录的路径。如果目标不存在或不是目录，AIxCoding 会提示错误并保留当前工作目录。 | — |
| 非注释命中 | docs/zh-Hans/guides/daily-use/workspaces.md:36 | 切换工作目录时，AIxCoding 会重新加载当前智能体，并加载新工作目录中的记忆和技能。具体配置方式参阅[配置记忆](../configuration/memory.md)和[安装和使用技能](../extensions/skills.md)。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/external-acp-agents.md:5 | **外部 ACP 智能体可以作为子智能体或工作流节点使用，不能作为聊天主智能体**。每次调用外部 ACP 智能体时，AIxCoding 都会为本次调用启动外部智能体进程，并通过 ACP 与其通信。任务处理和工具调用由外部智能体负责，审批请求、执行状态、进度更新和最终结果通过 ACP 连接传递。调用结束后，AIxCoding 会关闭连接并终止该进程。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/external-acp-agents.md:11 | - 已安装在运行 AIxCoding 的设备上； | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/external-acp-agents.md:16 | 无需提前启动 ACP 服务。测试连接或调用子智能体时，AIxCoding 会根据配置自动启动外部智能体进程，并通过 stdio 建立 ACP 连接。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/external-acp-agents.md:32 | 3. 将“智能体类型”改为“外部 ACP”。AIxCoding 会自动将其设置为“仅用作子智能体”。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/external-acp-agents.md:34 | 5. 按需添加认证所需的环境变量。外部智能体不会继承 AIxCoding 的环境变量，需要在此添加，详见[使用环境变量](#使用环境变量)。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/external-acp-agents.md:51 | 测试连接时，AIxCoding 会启动一个临时外部智能体进程，检查能否建立 ACP 会话，但不会发送任务。连接成功后，报告会显示身份、能力、模式、模型、配置选项和认证方式等栏目，并列出外部智能体提供的信息；未提供的信息可能显示“未声明。”“智能体未报告其身份信息。”或留空，这不表示连接失败。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/external-acp-agents.md:53 | 测试结束后，AIxCoding 会关闭该临时进程。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/external-acp-agents.md:62 | ### 示例：将 AIxCoding 配置为外部 ACP 智能体 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/external-acp-agents.md:64 | AIxCoding 自身也可以通过 stdio 提供 ACP 服务。可以使用以下配置： | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/external-acp-agents.md:75 | 该命令会启动 AIxCoding ACP 服务，默认提供 `Code` 智能体，并使用 `manual` 审批模式。有关 AIxCoding ACP 服务的更多配置和使用说明，请参阅[使用 AIxCoding ACP 服务](../running/aixcoding-acp.md)。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/external-acp-agents.md:79 | 外部智能体不会继承 AIxCoding 运行环境中的环境变量。它启动时只带有一组基本变量（macOS 和 Linux 上为 `HOME`、`LOGNAME`、`PATH`、`SHELL`、`TERM` 和 `USER`；Windows 上为 `APPDATA`、`HOMEDRIVE`、`HOMEPATH`、`LOCALAPPDATA`、`PATH`、`PATHEXT`、`PROCESSOR_ARCHITECTURE`、`SYSTEMDRIVE`、`SYSTEMROOT`、`TEMP`、`USERNAME` 和 `USERPROFILE`），以及智能体配置中设置的环境变量。智能体所需的其他变量，例如 API 密钥或 `HTTPS_PROXY` 等代理设置，请在配置中作为环境变量添加。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/external-acp-agents.md:81 | 在可执行文件、参数、环境变量值和工作目录中，可以使用 `{{ENV_VAR}}` 引用 AIxCoding 运行环境中的环境变量，从而复用已有配置值，避免在智能体配置中直接填写固定值或敏感信息。环境变量名只能包含字母、数字和下划线，且不能以数字开头。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/external-acp-agents.md:89 | 保存配置、测试连接以及每次启动外部智能体时，AIxCoding 都会解析引用的环境变量。若对应环境变量不存在或值为空，配置将无法保存，测试连接或调用也会失败。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/external-acp-agents.md:93 | “工作目录”留空时，外部智能体使用 AIxCoding 当前会话的工作目录。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/external-acp-agents.md:107 | 以上配置项均可留空。留空时，AIxCoding 将使用外部智能体的默认配置。修改配置后，请重新测试连接。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/external-acp-agents.md:111 | “模型 ID”按尽力方式应用。如果外部智能体未列出指定模型，或以“不支持的方法”或“参数无效”错误拒绝切换，AIxCoding 会继续使用外部智能体的默认模型；切换模型时出现其他错误则连接失败。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/hooks.md:15 | 下面将在 AIxCoding 当前会话的工作目录中创建一个项目钩子。它只对当前工作目录生效，并会在每一轮结束后将轮次状态追加到该目录下的 `hook-events.log`。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/hooks.md:50 | AIxCoding 通过 `CHRYS_HOOK_PAYLOAD_FILE` 环境变量提供本次事件的 JSON 输入文件。`after_turn` 事件的输入包含 `turn` 和 `status`，分别表示轮次编号和结束状态。脚本默认在 AIxCoding 当前会话的工作目录中运行，所以 `hook-events.log` 也会写到工作目录。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/hooks.md:54 | 切换会话或重启 AIxCoding，使磁盘上的配置生效。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/hooks.md:85 | 这段配置只匹配具有 `path` 参数，并且路径以 `.env` 结尾的 `filesystem.write` 工具调用。阻塞式钩子会在 AIxCoding 继续处理调用前完成。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/hooks.md:105 | 切换会话或重启 AIxCoding 后，先创建一个专门用于验证的 `hook-demo/.env`，写入已知内容，例如 `HOOK_TEST=unchanged`。然后要求智能体仅使用 `write_file` 或 `edit_file` 尝试修改一次，被拒绝后停止，不使用 Shell 或其他方式。检查该工具调用是否在执行前被拒绝，并显示脚本提供的原因；再确认文件内容保持不变。验证后可以删除 `hook-demo/.env`。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/hooks.md:140 | 切换会话或重启 AIxCoding，使配置生效。系统提醒只有在阻塞式钩子成功结束后才会生效。AIxCoding 会用 `<system-reminder>` 标签包住提醒内容，随用户提交的消息一起发送给模型。这段提醒不会显示在 TUI 对话中，也不会写入会话数据。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/hooks.md:142 | 如需确认 `user_prompt_submit` 钩子是否生效，或查看系统提醒发送给模型时的实际内容，可以检查模型请求的原始 HTTP 日志。该日志包含未脱敏的 API 密钥和完整对话内容，应仅在排查问题时临时启用。在 TUI 中按 **F10**，进入“安全”-“诊断”，开启“捕获原始 HTTP 流量”，然后重启 AIxCoding。使用 Code 智能体提交一条消息后，在当前会话目录的 `llm_raw_http.jsonl` 中搜索提醒正文“修改 Python 文件后”。当前会话目录的位置参阅[查找会话 ID 和会话保存位置](../daily-use/sessions.md#查找会话-id-和会话保存位置)。验证完成后，应关闭原始 HTTP 流量捕获并再次重启 AIxCoding。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/hooks.md:152 | \| 在操作继续前检查、拒绝或修改操作 \| `blocking` \| AIxCoding 等待钩子结束；部分事件会采用结果文件中的操作决定 \| | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/hooks.md:153 | \| 不阻塞当前操作，但希望 AIxCoding 在当前轮或会话结束时等待一段时间 \| `async` \| AIxCoding 立即继续，之后在适用的事件和等待上限内等待钩子完成 \| | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/hooks.md:154 | \| 普通通知或允许被退出打断的记录任务 \| `fire_and_forget` \| AIxCoding 立即继续，结束当前轮或会话时也不等待；这是默认模式 \| | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/hooks.md:156 | 异步钩子（`async`）不会延迟触发它的事件或当前操作。当前轮或会话结束时，如果相应的异步钩子仍在运行，AIxCoding 会等待它完成后再结束当前轮或会话。`user_interrupt` 触发的异步钩子不会被等待。会话结束时的等待上限可在[全局设置](../../reference/hooks.md#全局设置)中配置。需要在 AIxCoding 退出后重试未完成的任务时，还应配置 `delivery: durable`。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/mcp.md:3 | 模型上下文协议（Model Context Protocol，MCP）服务器可以为 AIxCoding 智能体提供外部工具、提示词模板和使用说明。本指南介绍如何在终端用户界面（Terminal User Interface，TUI）中连接 HTTP 或 STDIO MCP 服务器、配置可调用的工具，以及控制是否加载提示词模板、是否将服务器使用说明加入模型上下文。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/mcp.md:18 | HTTP 请求头值和 STDIO 环境变量值都可以使用 `{{ENV_VAR}}` 引用启动 AIxCoding 前已经设置的环境变量。环境变量名只能包含字母、数字和下划线，且不能以数字开头。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/mcp.md:26 | 3. 如果服务器需要认证，在“请求头”中添加名称和值。可以用 `{{ENV_VAR}}` 引用启动 AIxCoding 前已经设置的环境变量，例如： | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/mcp.md:34 | 5. 建议保持 TLS 证书验证开启。如果需要连接已确认可信的自签名服务器，可以启用“跳过 TLS 验证”。启用后，AIxCoding 不会验证 HTTPS 服务器证书，无法确认连接的是预期服务器。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/mcp.md:40 | 3. 按需添加该进程需要的环境变量。变量值可以直接填写，也可以用 `{{ENV_VAR}}` 引用启动 AIxCoding 前已经设置的环境变量。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/mcp.md:77 | 2. **测试服务器连接**：点击服务器配置卡片右下角的“测试”。AIxCoding 会尝试连接服务器，并在连接报告中显示服务器身份、声明的能力和使用说明，以及当前配置下可用的工具和提示词模板。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/mcp.md:83 | - STDIO 服务器应先查看连接错误中显示的可执行文件、工作目录、进程退出码和标准错误输出末尾，再核对命令、参数和环境变量，并确认命令能在所示工作目录中启动。AIxCoding 只显示有限长度的标准错误输出；需要完整日志时，请按照服务器文档启用日志记录。分享诊断信息前，请移除令牌、凭据等敏感信息。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/skills.md:9 | \| 位置 \| 适合情况                                 \| AIxCoding 中的加载方式 \| | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/skills.md:11 | \| AIxCoding 用户技能目录 \| 希望 AIxCoding 中所有“内置”类型的智能体都能使用           \| 始终自动加载 \| | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/skills.md:12 | \| AIxCoding 共享用户目录（`~/.aixcoding/skills`） \| 在 AIxCoding CLI 与 AIxCoding 桌面端之间共享技能     \| 默认自动加载，可针对智能体关闭 \| | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/skills.md:13 | \| Agent Skills 共享目录 \| 希望在 AIxCoding 与其他支持 Agent Skills 的工具之间共享 \| 默认自动加载，可针对智能体关闭 \| | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/skills.md:14 | \| `<working-directory>/.aixcoding/skills` \| 只希望在当前工作目录中使用的 AIxCoding 专属技能           \| 默认自动加载，可针对智能体关闭 \| | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/skills.md:18 | 其中，`<working-directory>` 表示当前工作目录。切换工作目录后，AIxCoding 会重新加载新工作目录中的技能。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/skills.md:24 | \| AIxCoding 用户技能目录 \| `~/.chrys/skills` \| `%APPDATA%\chrys\skills` \| | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/skills.md:25 | \| AIxCoding 共享用户目录 \| `~/.aixcoding/skills` \| `%USERPROFILE%\.aixcoding\skills` \| | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/skills.md:28 | 多个目录中出现同名技能时，AIxCoding 专属目录优先于对应的 Agent Skills 目录：`~/.aixcoding/skills` 优先于 `~/.agents/skills`，`<working-directory>/.aixcoding/skills` 优先于 `<working-directory>/.agents/skills`。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/skills.md:32 | AIxCoding 会在已配置的技能目录及其最多两层子目录中查找 `SKILL.md` 文件。找到 `SKILL.md` 后，将所在目录识别为一个技能目录，不再继续查找其中嵌套的技能。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/skills.md:36 | AIxCoding 用户技能目录始终自动加载。Agent Skills 共享目录和当前工作目录中的技能目录默认也会自动加载；若曾在智能体配置中关闭对应来源，需要重新启用。使用自定义目录时，需要将目录添加到相应智能体的配置中。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/skills.md:57 | > **注意**：技能脚本会作为本地进程运行，不受安全沙箱隔离。安装第三方技能前，请检查 `SKILL.md`、脚本及其他相关文件，仅安装来自可信来源的技能。AIxCoding 通过 `run_skill_script` 工具运行技能脚本；该工具是否需要确认，取决于智能体审批规则和[当前审批模式](../configuration/approval.md)。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/skills.md:61 | 保存智能体配置并返回会话后，AIxCoding 会重新加载技能。如果直接在磁盘上添加技能目录或修改其中的文件，AIxCoding 不会实时监控这些变化。下一次发送消息时，AIxCoding 会先重新扫描当前智能体已启用的技能目录，再处理该消息。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/skills.md:88 | 如果技能名称与 AIxCoding 的内置斜杠命令相同，则无法使用 `/skill-name` 显式调用该技能。此时，可以在消息中直接指定技能名称，例如： | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/skills.md:98 | 从前文列出的[技能安装位置](#技能安装位置)加载的技能都属于目录技能，每个技能都包含 `SKILL.md`。AIxCoding 还支持直接在智能体配置文件中定义内嵌技能，这类技能不需要技能目录或 `SKILL.md`。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/skills.md:100 | 如果发现多个同名技能，AIxCoding 只会加载优先级最高的一个。优先级从高到低依次为： | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/skills.md:103 | 2. AIxCoding 用户技能目录； | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/skills.md:131 | `SKILL.md` 需要使用 UTF-8 编码。文件开头是由 `---` 包围的 YAML 配置区，也称为 frontmatter；之后是提供给智能体的操作说明。frontmatter 应写成有效的 YAML 键值对象；若不是有效的 YAML，AIxCoding 会尝试逐行读取并记录警告。AIxCoding 按以下规则校验文件内容： | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/skills.md:139 | \| `license`、`allowed-tools` \| 可选；AIxCoding 读取字段值，但不额外校验其内容 \| | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/skills.md:140 | \| `metadata` \| 可选；必须是 YAML 对象，否则 AIxCoding 不会保留该字段 \| | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/skills.md:141 | \| 正文 \| AIxCoding 不额外限制长度或结构 \| | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/skills.md:143 | 为了确保技能能够稳定加载，请使用有效的 YAML 编写 frontmatter。缺少 frontmatter、`name` 或 `description`，或者字段值未通过上述校验时，AIxCoding 不会加载该技能。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/skills.md:149 | * `allowed-tools`：按照 Agent Skills 规范声明可预先批准运行的工具。该字段仍处于实验阶段；AIxCoding 当前只读取并保留字段值，不会据此自动授予工具权限。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/skills.md:151 | AIxCoding 的技能目录和 `SKILL.md` 格式遵循 Agent Skills 通用规范。上述字段的详细写法和技能的完整规范参阅 [Agent Skills 官方规范](https://agentskills.io/specification)。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/skills.md:170 | AIxCoding 只会将以下扩展名的文本文件识别为技能资源：`.md`、`.txt`、`.rst`、`.html`、`.htm`、`.xml`、`.svg`、`.json`、`.jsonl`、`.yaml`、`.yml`、`.toml`、`.csv`、`.tsv`、`.ini`、`.cfg`、`.css`。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/skills.md:175 | * AIxCoding 只读取技能目录根层和直接子目录中的文件。例如，`guide.md` 和 `references/guide.md` 会被发现，`references/api/guide.md` 则会被忽略。 | — |
| 非注释命中 | docs/zh-Hans/guides/extensions/skills.md:176 | * AIxCoding 会跳过技能目录内部通过符号链接或 Windows 目录联接访问的文件和目录。这两类链接都指向磁盘中的其他位置；如需使用其中的内容，请将实际文件放入技能目录。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-acp.md:1 | # 使用 AIxCoding ACP 服务 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-acp.md:3 | 支持智能体客户端协议（Agent Client Protocol，ACP）的编辑器或开发工具，可以连接 AIxCoding，在客户端中使用 AIxCoding 智能体。ACP 客户端提供交互界面，AIxCoding 通过标准输入输出（stdio）与客户端通信，负责运行智能体、执行工具并保存会话。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-acp.md:5 | 开始前，请先安装 AIxCoding，并至少配置一个模型。有关准备步骤，参阅[开始使用 AIxCoding](../../start/getting-started.md)和[配置模型](../configuration/models.md)。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-acp.md:7 | ## 连接 AIxCoding | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-acp.md:26 | 1. 在客户端启动或连接 AIxCoding。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-acp.md:28 | 3. 确认客户端显示 AIxCoding 的回复。出现回复即表示连接配置成功。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-acp.md:43 | 客户端在创建或恢复会话时，可以将项目的工作目录交给 AIxCoding。客户端提供的工作目录必须是已存在的绝对路径。客户端未提供工作目录时，AIxCoding 使用 `--workdir <project-directory>` 指定的目录；两者同时存在时，以客户端提供的工作目录为准。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-acp.md:45 | AIxCoding 会在启动时检查 `--workdir`。即使客户端随后会提供工作目录，该选项指定的目录也必须存在，否则 AIxCoding 无法启动。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-acp.md:47 | 会话数据不会写入工作目录，而是保存在 AIxCoding 的会话存储目录中；有关实际保存位置，参阅[查找会话 ID 和会话保存位置](../daily-use/sessions.md#查找会话-id-和会话保存位置)。AIxCoding 会记录会话创建时的工作目录。通过 ACP 客户端列出会话时，只会显示与当前工作目录匹配的会话；恢复会话时，如果工作目录不匹配，AIxCoding 会拒绝恢复。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-acp.md:53 | AIxCoding 会将智能体回复和工具调用状态发送给客户端。客户端取消任务时，AIxCoding 会中断当前任务。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-acp.md:55 | 桌面端在 ACP prompt 元数据中提供客户端身份，并通过 `agent-studio.dev/selected-agent`（`schemaVersion: 1`、`agentMarketSkillId`、`agentName`）明确传入所选智能体时，AIxCoding 会在准备该消息的首个模型请求时、后续工具调用上报前，发送一条智能体使用记录。该记录使用 `funcType=1001`，`funcName` 为所选智能体名称，`agentName` 为 `agent-studio.dev/function-name` 传入的桌面端内核来源，与工具调用记录（`funcType=3`）一致。记录携带模型请求 ID 和会话 ID，以便与本轮其他埋点关联。未产生模型请求或未明确选择智能体的消息不会上报智能体使用记录。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-acp.md:59 | 如果客户端支持管理会话，关闭会话后仍可以在同一工作目录中恢复；删除会话会移除 AIxCoding 保存的会话记录，之后无法在 AIxCoding 中恢复。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-acp.md:61 | 如果要在 ACP 客户端中使用提问功能，客户端需要支持 AIxCoding 的 `_chrys/request_input` 扩展请求（在会自动添加下划线前缀的 ACP SDK 中显示为 `chrys/request_input`）。AIxCoding 通过此请求向客户端发送智能体的问题，并接收用户回答；不支持该请求的客户端无法完成需要用户回答的任务。等待回答的时间可以通过 `--ask-user-timeout` 限制。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-acp.md:63 | 客户端支持审批模式或模型切换时，可以更改当前会话的相应设置。这些切换与通过 `--approval` 设置的初始模式一样，都不会写入 AIxCoding 的本地配置；但如果客户端使用 AIxCoding 的扩展请求修改设置、智能体配置或模型配置，这些更改会写入 AIxCoding 的本地配置。下次启动 ACP 服务时，初始审批模式仍只由 `--approval` 决定，其他初始设置按本地配置和当次启动参数确定。模型配置和可用智能体仍由 AIxCoding 的本地配置管理。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-run.md:1 | # 使用 AIxCoding-CLI 执行无界面任务 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-run.md:11 | - 已安装 AIxCoding-CLI，并至少配置一个可用模型。请参阅[开始使用 AIxCoding-CLI](../../start/getting-started.md)和[配置模型](../configuration/models.md)。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-run.md:29 | 任务运行期间，AIxCoding-CLI 会显示运行进度；任务完成后，先显示一行汇总，再显示智能体的最终回复。例如： | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-run.md:43 | 各行的含义请参阅[查看运行进度](#查看运行进度)。回复中可能改动终端显示的控制字符会显示为 `�`；将输出重定向到文件或其他程序，或添加 `--json` 时，回复保持原样。若任务失败，错误信息写入标准错误（`stderr`），命令以非零状态退出。AIxCoding-CLI 能判断模型请求失败的原因时，错误信息会说明原因，下方的 `detail:` 行显示原始错误信息。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-run.md:101 | `--task` 不要求特定文件后缀。AIxCoding-CLI 会读取该文件内容，并将其作为本次任务的提示词。任务文件路径可以是绝对路径，也可以是相对路径；使用相对路径时，AIxCoding-CLI 会在 `--workdir` 指定的目录中查找该文件，未指定 `--workdir` 时，则在运行命令时所在的目录中查找。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-run.md:141 | {"session_id": "8de5057d-58ff-477e-9158-2f1b8d8e9fc0", "result": "Hello! I'm AIxCoding, a read-only Q&A assistant for this codebase. I can help you with questions about the code, architecture, APIs, conventions, and how things work — with file and line references so you can jump straight to the source.\n\nWhat would you like to know?", "duration": 9.018} | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:1 | # 在浏览器中运行 AIxCoding | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:3 | `aixcoding-cli serve` 在浏览器中显示 AIxCoding 的终端用户界面（Terminal User Interface，TUI），支持对话、审批工具调用和修改配置。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:7 | 本文将运行浏览器的设备称为“本机”，将运行 AIxCoding 服务的机器称为“服务端”。服务端可以是本机，也可以是通过网络访问的远程服务器。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:9 | 开始前，服务端应已[安装 AIxCoding](../../start/getting-started.md#1-安装-aixcoding-cli)。浏览器提供操作界面，AIxCoding 则使用服务端的配置，以启动服务的系统用户权限读取、修改文件和执行命令。这些操作均发生在服务端，所有访问者共享服务端的配置、文件和会话，不会获得独立账户。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:17 | \| 本机运行和访问 \| [在本机启动 AIxCoding](#在本机启动-aixcoding-cli) \| | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:18 | \| 通过 SSH 访问远程服务器上的 AIxCoding \| [从本机访问远程 AIxCoding](#从本机访问远程-aixcoding-cli) \| | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:21 | ## 在本机启动 AIxCoding | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:33 | 终端显示 `Serving AIxCoding TUI on ...` 和访问地址后，表示服务已启动。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:39 | 登录后应显示 AIxCoding 界面，服务端已有的模型配置会继续使用。确认模型已配置后，发送“你好”，检查是否能收到回复。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:47 | 每次打开页面并建立连接，服务端都会启动一个独立的 AIxCoding 实例。对话记录保存在服务端，重新打开页面后，可[恢复已保存的会话](../daily-use/sessions.md#恢复已有会话)。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:51 | ## 从本机访问远程 AIxCoding | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:53 | 如果已能通过 SSH 登录远程服务器，可以建立 SSH 隧道，将本机浏览器的连接通过加密通道转发到远程 AIxCoding，无需配置域名。以下步骤需要在本机打开两个终端窗口。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:55 | ### 1. 在第一个终端中登录远程服务器并启动 AIxCoding | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:63 | 登录后，在该终端中执行的命令会运行在远程服务器上。进入远程工作目录，然后启动 AIxCoding： | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:85 | 访问 `http://localhost:7777`，输入第一步设置的 AIxCoding 浏览器登录密码。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:87 | 浏览器访问本机的 `localhost:7777` 后，SSH 隧道会将连接转发到远程 AIxCoding。因此，本例中的浏览器地址应保持为 `localhost`，不能改为远程 IP。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:89 | 任务结束后，在第一个终端按 `Ctrl+C` 停止 AIxCoding，在第二个终端按 `Ctrl+C` 关闭 SSH 隧道。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:93 | 通过 `https://aixcoding-cli.example.com` 等固定地址访问时，需部署反向代理：浏览器与代理建立加密连接，代理再将请求转发至 AIxCoding。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:95 | 本节适用于已有 HTTPS 代理的环境。域名和证书需要在代理侧配置，AIxCoding 本身不提供 HTTPS 服务。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:97 | ### 1. 启动 AIxCoding | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:99 | 以下示例要求代理与 AIxCoding 运行在同一台服务器上。在服务器终端中进入工作目录，将 `aixcoding-cli.example.com` 替换为实际域名，然后运行： | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:105 | 设置浏览器登录密码，并保持终端运行。此命令让 AIxCoding 只接受同一台服务器上的连接，浏览器则通过代理访问 `--public-url` 指定的地址。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:112 | - 保留浏览器请求中的原始 `Host` 头，使 AIxCoding 能核对访问域名。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:115 | 默认情况下，AIxCoding 按代理地址累计密码错误次数，多个访问者可能共享失败计数。若代理可信且会正确重写 `X-Forwarded-For`（客户端地址请求头），可在 AIxCoding 启动命令中添加 `--auth-trust-forwarded-for`，改为按代理提供的访问者地址计数。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:119 | 将 `aixcoding-cli.example.com` 替换为实际域名，在本机浏览器中打开对应的 HTTPS 地址，例如 `https://aixcoding-cli.example.com`，无需添加 AIxCoding 的端口 `:7777`。浏览器应显示 AIxCoding 登录页面，且没有证书警告。登录后发送一条消息，确认能收到回复。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:121 | 浏览器到代理的连接已加密；代理到 AIxCoding 仍使用服务器内部的 HTTP 连接。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:125 | 代理位于其他服务器或独立容器中时，`127.0.0.1` 可能无法连接 AIxCoding。调整监听地址后，应通过防火墙或容器网络规则限制后端端口仅供可信代理访问，避免绕过 HTTPS 代理直接连接。设置 HTTPS `--public-url` 不会加密代理到 AIxCoding 的 HTTP 连接。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:145 | 在服务端为 AIxCoding 启动进程设置环境变量，例如 `CHRYS_SERVE_PASSWORD`，并将变量值设为非空的登录密码。然后运行： | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:163 | `--host 0.0.0.0` 允许其他设备连接 AIxCoding。`--allow-insecure-auth` 显式允许通过网络进行明文密码登录；本例未指定该选项时，AIxCoding 会拒绝启动。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:171 | 确认服务端已安装 AIxCoding，且安装目录已加入 `PATH`。若刚完成安装，重新打开终端后运行以下命令验证： | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:189 | 将 `-L` 后的第一个端口改为本机空闲端口，最后一个端口保持为远程 AIxCoding 的监听端口。例如，远程 AIxCoding 使用 `7777`，且本机的 `8888` 端口空闲时，可在本机运行： | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:195 | 将 `<user>` 和 `<server>` 替换为 SSH 用户名和服务器地址。同时在远程服务器上重新启动 AIxCoding，指定新的浏览器访问地址： | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:205 | 先确认 AIxCoding 服务仍在运行，再核对浏览器地址是否与所用方式一致：按本机或 SSH 示例访问时使用 `localhost`，通过 HTTPS 访问时使用配置的域名，通过局域网直连时使用服务端 IP。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:215 | 检查 AIxCoding 是否仍在运行、代理转发的地址和端口是否与 AIxCoding 的监听配置一致，以及代理是否能连接该地址；具体原因可查看代理日志。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:219 | 使用 AIxCoding 启动时显示的域名或 IP 及端口访问。经代理访问时，检查代理是否保留了原始 `Host` 头。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:223 | 核对浏览器地址是否与 `--public-url` 指定的地址一致，包括协议（`http` 或 `https`）、域名和端口。AIxCoding 会拒绝来源地址不匹配的连接。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:227 | 若提示 `Invalid login token`，重新打开登录页面后输入密码；若提示 `Invalid login origin`，核对浏览器地址是否与 AIxCoding 配置的访问地址一致。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:231 | 该客户端地址已锁定。先确认其他页面没有正在执行的任务，再在 AIxCoding 终端按 `Ctrl+C` 并重新启动。多个代理访问者同时被锁定时，按 HTTPS 章节中的条件检查是否适合启用 `--auth-trust-forwarded-for`。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/aixcoding-serve.md:235 | 页面重新连接后，服务端会启动新的 AIxCoding 实例。可按“恢复已保存的会话”中的步骤恢复对话记录，但中断的任务不会自动继续。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/workflows.md:44 | 同一工作流会话可以保存多次运行。在“工作流”“信息”等页签上方，点击“运行 1”“运行 2”等运行页签，可切换查看各次记录。退出并重新打开 AIxCoding 后，先通过左上角的应用模式选择器切换到“工作流”。按 `F1` 或点击界面底部的 `f1 会话`，在会话列表中选择工作流会话，可查看历史输入、输出和节点记录。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/workflows.md:83 | 最后，`wf.build()` 检查并生成工作流。**文件必须将生成的对象赋给模块顶层的 `workflow` 变量，供 AIxCoding 加载。** | — |
| 非注释命中 | docs/zh-Hans/guides/running/workflows.md:85 | 保存文件后无需重启 AIxCoding。点击“新建会话”，打开工作流选择器，选择 `greeting`。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/workflows.md:93 | 默认使用运行 AIxCoding 的 Python 解释器。工作流需要第三方库时，可以通过文件内的脚本元数据指定自备 Python 解释器或虚拟环境；依赖需自行安装，AIxCoding 不会自动安装。配置方式见[工作流参考：执行环境](../../reference/workflows.md#执行环境)。本教程的 Python 示例仅使用标准库，无需额外准备环境。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/workflows.md:139 | - 返回字符串时，AIxCoding 将字符串放入 `WorkflowValue.text`，并将 `data` 设为 `None`。本例中的 `describe()` 只需要输出说明，因此返回字符串。 | — |
| 非注释命中 | docs/zh-Hans/guides/running/workflows.md:192 | ### 使用 AIxCoding-CLI 智能体 | — |
| 非注释命中 | docs/zh-Hans/guides/running/workflows.md:256 | 对普通 AIxCoding 智能体，`instructions_suffix` 追加在配置原有的 `instructions` 后，作为系统提示词的一部分；上游传入的 `text` 仍作为用户消息。 | — |
| 非注释命中 | docs/zh-Hans/reference/agent-profile.md:16 | AIxCoding 只加载目录中扩展名为 `.yaml` 或 `.yml` 的非隐藏文件，其他文件会被忽略。无效配置不会阻止其他配置加载，但会被跳过，并在启动日志中记录警告。 | — |
| 非注释命中 | docs/zh-Hans/reference/agent-profile.md:18 | AIxCoding 在启动时加载这些文件。手工新增、修改或删除配置文件后，更改会在下次启动 AIxCoding 时生效。 | — |
| 非注释命中 | docs/zh-Hans/reference/agent-profile.md:24 | 加载用户配置时，AIxCoding 会根据配置内容规范化文件： | — |
| 非注释命中 | docs/zh-Hans/reference/agent-profile.md:26 | - 文件名不是 `<name>.yaml` 时，AIxCoding 会将其重命名为 `<name>.yaml`。这也会将 `.yml` 扩展名改为 `.yaml`。 | — |
| 非注释命中 | docs/zh-Hans/reference/agent-profile.md:27 | - 配置缺少 `id` 时，AIxCoding 会分配稳定 ID，并重写整个文件。重写后不会保留原有注释、字段顺序和格式，还会移除无法识别的键和取默认值的字段（`approval` 除外，它始终会写入）。 | — |
| 非注释命中 | docs/zh-Hans/reference/agent-profile.md:28 | - `sub_agents.agents` 引用了已从 AIxCoding 中移除的内置智能体时，AIxCoding 会删除这些条目，并以同样方式重写文件。如果你有同名的自有配置，则保留这些引用；目录中有配置文件加载失败时，此项修改会推迟。 | — |
| 非注释命中 | docs/zh-Hans/reference/agent-profile.md:29 | - 目标文件名已被其他配置占用时，该配置不会加载。AIxCoding 会尽可能将冲突文件重命名为带 `.conflict` 标记的文件。 | — |
| 非注释命中 | docs/zh-Hans/reference/agent-profile.md:33 | 发生冲突时，检查 `<name>.yaml` 和带 `.conflict` 标记的文件，并保留需要的配置。如需同时保留两者，将其中一个文件改为新的独立配置：修改 `name`，删除原有的 `id`，并将文件扩展名恢复为 `.yaml`。重启后，AIxCoding 会为该配置分配新 ID。 | — |
| 非注释命中 | docs/zh-Hans/reference/agent-profile.md:35 | 受文件系统限制时，AIxCoding 可能无法添加 `.conflict` 标记。此时冲突文件会保留原名，但仍不会加载。 | — |
| 非注释命中 | docs/zh-Hans/reference/agent-profile.md:39 | 内置智能体的原始配置随 AIxCoding 安装。通过 TUI 修改并保存内置智能体后，AIxCoding 会在[用户智能体配置目录](#用户智能体配置目录)中生成同名配置文件。例如，修改并保存名称为 `Code` 的内置智能体后会生成 `Code.yaml`。 | — |
| 非注释命中 | docs/zh-Hans/reference/agent-profile.md:41 | 内置智能体的 `name` 包括 `Code`、`QA`、`Explore` 和 `General`。在用户智能体配置目录下手工创建的配置文件使用上述任一 `name` 时，也会覆盖对应的内置智能体。覆盖配置会完整替代内置配置，不会继承或合并内置配置中的其他字段。删除对应的用户配置文件并重启 AIxCoding，即可恢复使用内置配置。 | — |
| 非注释命中 | docs/zh-Hans/reference/agent-profile.md:60 | 示例省略了 `id`。AIxCoding 首次加载配置时会分配稳定 ID 并回写文件。 | — |
| 非注释命中 | docs/zh-Hans/reference/agent-profile.md:75 | \| `id` \| 字符串 \| 自动分配 \| 稳定标识符。省略或留空时，AIxCoding 会自动分配一个 12 位十六进制 ID：与内置智能体同名时沿用其 ID，否则生成新的 ID。也可以手动填写唯一 ID；纯数字 ID 需要加引号，例如 `id: "123"`，否则会被读取为数字，导致配置加载失败。复制已有配置文件并在其基础上修改以创建新的配置时，建议删除 `id` 字段，由 AIxCoding 自动分配新的 ID。 \| | — |
| 非注释命中 | docs/zh-Hans/reference/agent-profile.md:102 | 省略 `profile_id`、将其留空，或者填写的 ID 在已加载的模型配置中找不到时，主智能体使用会话中当前生效的模型配置，子智能体继承父智能体实际使用的模型配置。ID 找不到时，AIxCoding 还会记录警告。 | — |
| 非注释命中 | docs/zh-Hans/reference/agent-profile.md:155 | `env` 和 `headers` 都是键值映射：左侧填写变量名或请求头名称，右侧填写对应的值。值可以直接填写，也可以用 `{{ENV_VAR}}` 引用启动 AIxCoding 前已设置的环境变量。`env` 中引用的变量缺失或为空时，服务器连接失败；`headers` 仅在 `resolve_header_templates` 为 `true` 时解析变量并应用这一规则。 | — |
| 非注释命中 | docs/zh-Hans/reference/agent-profile.md:184 | 启用按需加载时，AIxCoding 还会添加用于查看、加载和卸载 MCP 工具的控制工具，名称规则见 [MCP 工具名称](./tool-kinds-and-names.md#mcp-工具名称)。此时，`tool_name_prefix` 不能超过 49 个字符。 | — |
| 非注释命中 | docs/zh-Hans/reference/agent-profile.md:190 | `shell_filter` 只对 `shell` 类别中的工具生效。省略此字段或设置为 `unrestricted` 时，AIxCoding 不过滤 Shell 命令。 | — |
| 非注释命中 | docs/zh-Hans/reference/agent-profile.md:192 | Shell 工具调用先经过[审批](#approval)，放行后再由 `shell_filter` 检查具体命令；两项检查都通过后，命令才会执行。若命令被过滤器阻止，AIxCoding 不会启动 Shell 进程，而是返回“命令被阻止”的工具错误。 | — |
| 非注释命中 | docs/zh-Hans/reference/agent-profile.md:214 | 只有上表中的名称会启用预设。无法识别的预设不会生效：使用标量写法时不进行 Shell 过滤；使用对象写法时，AIxCoding 会尝试使用同一对象中的自定义规则，若 `commands` 为空，同样不进行 Shell 过滤。 | — |
| 非注释命中 | docs/zh-Hans/reference/agent-profile.md:237 | 在自定义规则中，`commands` 填写可执行文件名，例如 `[git, rg]`。名称区分大小写；使用绝对路径时需要填写完整路径。对于由 `\|`、`&&`、`\|\|` 或 `;` 等连接的多个命令，AIxCoding 会分别检查每一段，所有命令名都符合规则后才会执行。以上示例允许 `rg foo .`；`rg foo . \| less` 会被阻止，因为管道右侧的 `less` 不在允许名单中。 | — |
| 非注释命中 | docs/zh-Hans/reference/agent-profile.md:268 | 数值超出范围或 `providers` 条目格式错误时，同样会导致该配置被跳过。与模式不符的组合（例如 `provider` 模式未设置 `provider`，或选用了 `providers` 中不存在的提供方）则会让智能体不包含网络工具，AIxCoding 会显示一条写明原因的警告。 | — |
| 非注释命中 | docs/zh-Hans/reference/agent-profile.md:316 | 未配置 `approval` 时，AIxCoding 使用以下默认配置： | — |
| 非注释命中 | docs/zh-Hans/reference/agent-profile.md:338 | 1. AIxCoding 根据 `default` 和 `overrides` 确定初始审批级别。 | — |
| 非注释命中 | docs/zh-Hans/reference/agent-profile.md:339 | 2. AIxCoding 根据安全规则调整结果： | — |
| 非注释命中 | docs/zh-Hans/reference/agent-profile.md:380 | 省略 `overrides` 时，AIxCoding 使用默认覆盖项 `shell: require`、`filesystem.write: require` 和 `todo: skip`。显式设置 `overrides: {}` 会清空这些默认覆盖项，未匹配其他规则的工具均使用 `default`。 | — |
| 非注释命中 | docs/zh-Hans/reference/agent-profile.md:412 | \| `paths` \| 字符串列表 \| `[]` \| 额外的技能搜索根目录。AIxCoding 在每个目录及其最多两层子目录中查找 `SKILL.md`；找到后不再搜索该技能目录的内部。相对路径按当前[工作目录](../guides/daily-use/workspaces.md)解析；路径开头的 `~` 由 AIxCoding 展开为当前用户主目录。 \| | — |
| 非注释命中 | docs/zh-Hans/reference/agent-profile.md:418 | \| `auto_load_aixcoding_user_skills` \| 布尔值 \| `true` \| 是否加载 AIxCoding 共享用户技能目录（`~/.aixcoding/skills`，与 AIxCoding 桌面端共享）。 \| | — |
| 非注释命中 | docs/zh-Hans/reference/agent-profile.md:421 | AIxCoding 用户技能目录始终加载；其余自动加载目录默认开启，可分别通过对应的 `auto_load_*` 字段关闭。用户级技能目录路径见[技能安装位置](../guides/extensions/skills.md#技能安装位置)。 | — |
| 非注释命中 | docs/zh-Hans/reference/agent-profile.md:423 | 多个来源出现同名技能时，优先级从高到低为：`paths` 中靠前的目录、AIxCoding 用户技能目录、AIxCoding 共享用户目录（`~/.aixcoding/skills`）、Agent Skills 用户级共享目录、当前工作目录的 `.aixcoding/skills`、当前工作目录的 `.agents/skills`、`inline` 中靠前的定义。同一个搜索根目录中存在多个同名技能时，发现顺序不确定；为确保加载指定版本，请只保留其中一个。 | — |
| 非注释命中 | docs/zh-Hans/reference/agent-profile.md:466 | `compaction` 用于配置 AIxCoding 压缩当前任务时生成的续接信息（Last Words）；这些设置不影响较早工具结果或已完成对话轮次的压缩摘要。 | — |
| 非注释命中 | docs/zh-Hans/reference/agent-profile.md:478 | \| `last_words_template` \| 字符串 \| 空 \| 附加到 AIxCoding 固定 Last Words 要求后的补充说明，用于强调当前任务中需要保留的信息，不会替换固定格式。 \| | — |
| 非注释命中 | docs/zh-Hans/reference/agent-profile.md:482 | `last_words_max_output_tokens` 限制输出，`phase4_side_call_token_budget` 限制累计输入。后者主要用于严格控制额外模型用量，通常保留默认值。预算不足时，AIxCoding 会保留当前任务内容；如果上下文仍然过大，本次任务可能无法继续。 | — |
| 非注释命中 | docs/zh-Hans/reference/agent-profile.md:484 | `compaction` 不提供压缩触发阈值设置；AIxCoding 会根据当前模型的上下文窗口、最大输出词元数和安全余量自动确定何时压缩。 | — |
| 非注释命中 | docs/zh-Hans/reference/agent-profile.md:539 | \| `env` \| 字符串对象 \| `{}` \| 传给进程的环境变量。名称须符合环境变量命名规则，忽略大小写后不得重复；`CHRYS_ACP_SUBAGENT_DEPTH` 保留给 AIxCoding。 \| | — |
| 非注释命中 | docs/zh-Hans/reference/agent-profile.md:540 | \| `cwd` \| 字符串 \| 空 \| 外部智能体的工作目录；留空时使用 AIxCoding 当前会话的工作目录，相对路径也以该会话目录为基准解析。 \| | — |
| 非注释命中 | docs/zh-Hans/reference/agent-profile.md:550 | **`allow_external_cwd` 的目录范围**：如果 AIxCoding 会话由 ACP 客户端创建，且客户端提供了附加工作目录，那么即使 `allow_external_cwd` 为 `false`，外部智能体也可以在这些目录及其子目录中运行。 | — |
| 非注释命中 | docs/zh-Hans/reference/agent-profile.md:552 | `command`、`args`、`env` 的值和 `cwd` 可以使用 `{{ENV_VAR}}` 引用 AIxCoding 进程的环境变量。缺失或为空的变量会导致启动失败。连接测试、工作目录安全边界和配置项应用方式参阅[配置外部 ACP 智能体](../guides/extensions/external-acp-agents.md)。 | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:3 | 钩子（Hooks）让 AIxCoding 在指定时机自动运行本地脚本或命令。本页用于查询完整配置字段、默认值、事件数据和执行规则。第一次使用 Hooks 时，建议先阅读[配置和编写 Hooks](../guides/extensions/hooks.md)，通过可运行的示例创建和验证钩子。 | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:17 | \| 一轮 \| `turn` \| AIxCoding 对一次用户请求的处理过程，从开始处理请求，到智能体停止生成内容和调用工具为止。用户中断或运行失败也会结束当前轮；运行期间提交的补充消息仍属于当前轮。 \| | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:19 | \| 阻塞式钩子 \| `execution.mode: blocking` \| AIxCoding 等待钩子结束后再继续；部分事件会采用钩子返回的操作决定。 \| | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:20 | \| 异步钩子 \| `execution.mode: async` \| AIxCoding 立即继续当前操作，但通常会在当前轮或会话结束前等待钩子完成。 \| | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:21 | \| 即发即弃钩子 \| `execution.mode: fire_and_forget` \| AIxCoding 立即继续，在当前轮或会话结束时也不等待钩子；这是默认模式。 \| | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:22 | \| 分离运行 \| `execution.detach: true` \| 让已经启动的即发即弃钩子在 AIxCoding 退出后继续运行。 \| | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:23 | \| 持久投递 \| `execution.delivery: durable` \| 记录未完成的非阻塞钩子任务，以便 AIxCoding 以后重试；同一任务可能重复运行，脚本应能安全地重复执行。 \| | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:24 | \| 输入文件 \| `CHRYS_HOOK_PAYLOAD_FILE` \| AIxCoding 为本次事件生成的 JSON 文件，包含事件和上下文数据。 \| | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:25 | \| 结果文件 \| `CHRYS_HOOK_RESULT` \| 钩子写入操作决定或补充信息的 JSON 文件。只有符合条件的阻塞式钩子能借此改变 AIxCoding 的行为。 \| | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:29 | AIxCoding 可以分别从全局配置目录和当前工作目录加载一个钩子配置文件： | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:36 | 两处都可以改用 `hooks.yml` 或 `hooks.json`。同一目录存在多个候选文件时，AIxCoding 按 `hooks.yaml`、`hooks.yml`、`hooks.json` 的顺序只加载第一个。 | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:38 | `<working-directory>` 是会话的工作目录。对于项目配置，AIxCoding 只检查 `<working-directory>/.chrys/hooks/`，不会在工作目录的父目录或子目录中查找。 | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:44 | 在磁盘上编辑钩子配置文件不会实时生效。修改后，需要切换会话或重启 AIxCoding，让 AIxCoding 重新加载配置。仅修改钩子脚本则不需要重新加载；脚本会在下次触发钩子时使用新内容。 | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:58 | `version` 和 `settings` 均可省略；省略时，AIxCoding 使用表中列出的默认值。 | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:70 | \| `outbox_retry_age_seconds` \| 数值（>= `0`） \| `60.0` \| 仅用于持久投递钩子。AIxCoding 启动后，会重试因上次退出或崩溃而未记录为完成的钩子任务。此设置指定重试前至少等待的秒数，从任务上次开始执行时算起；任务从未执行过时，则从创建时算起。 \| | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:84 | \| `execution` \| 对象 \| 见[执行方式](#执行方式) \| AIxCoding 是否等待钩子、运行时限和失败处理方式。 \| | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:101 | \| `session_start` \| 智能体准备就绪后。启动 AIxCoding、新建会话或将当前会话回滚到开始处时会触发；切换智能体或模型不会触发。 \| 无 \| | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:102 | \| `session_restored` \| 已保存的会话恢复后。启动 AIxCoding 后立即恢复会话时，`session_start` 和 `session_restored` 都可能触发。 \| `restored_session_id`：本次恢复的已保存会话 ID \| | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:103 | \| `session_end` \| 当前会话结束时：退出 AIxCoding、切换会话、新建会话、删除或清空当前会话，或将当前会话回滚到开始处。 \| 无 \| | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:131 | 审批事件用于通知或记录工具审批的人工等待状态，仅覆盖 AIxCoding 处理的工具审批，不覆盖外部 ACP 智能体转发的审批。字段格式见[审批事件字段](#审批事件字段)。 | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:136 | \| `approval_resolved` \| 人工同意或拒绝审批后，AIxCoding 继续处理审批结果前；等待被中断时不触发，不表示工具已经执行或执行成功。 \| 与 `approval_requested` 相同，另有 `approved` \| | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:138 | 在自动审批模式（`auto`）下，AIxCoding 先完成自动审查，仅在仍需人工决定时触发审批事件。自动审查直接通过、审批被绕过，或进入等待前已经获得审批决定时，均不触发。 | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:187 | 异步钩子触发后立即运行，当前操作会继续执行。如果钩子尚未完成，AIxCoding 会在以下时机等待： | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:234 | - 正则表达式建议使用 YAML 单引号字符串；使用双引号时，反斜杠需要转义。正则表达式无效时，AIxCoding 会记录警告，该条件不会匹配。 | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:242 | \| `script` \| 运行已有脚本，并由 AIxCoding 根据文件扩展名选择运行程序。 \| `path` \| | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:265 | AIxCoding 根据文件扩展名选择运行程序： | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:278 | 对于 `.py` 文件，AIxCoding 会先在用户的 `PATH` 中依次查找 `uv`、`python3` 和 `python`。找到 `uv` 时，通过 `uv run` 运行脚本；找到 Python 时，直接使用该解释器。如果都未找到，则使用 AIxCoding 自带运行环境中的 `uv` 或 Python。 | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:280 | 运行其他类型的脚本前，需安装表中对应的运行程序，并确保 AIxCoding 可以通过 `PATH` 找到该程序。 | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:292 | AIxCoding 不会通过 Shell 解释参数，因此重定向、管道、变量展开和命令替换不会生效。 | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:317 | 在 macOS 和 Linux 上，AIxCoding 使用环境变量 `$SHELL` 指定的 Shell；未设置时使用 `/bin/sh`。在 Windows 上使用命令提示符（CMD）。不同 Shell 支持的语法可能不同。 | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:327 | \| `env` \| 字符串到字符串的对象 \| `{}` \| 添加到钩子进程的环境变量；名称相同时，覆盖 AIxCoding 传递的值。 \| | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:348 | \| `cwd` 使用相对路径 \| AIxCoding 进程的当前工作目录，可能与会话工作目录不同 \| | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:350 | 设置 `cwd` 时，应使用绝对路径或 `${workspace_cwd}`、`${chrys_home}` 模板，例如用 `${chrys_home}/hooks` 指定 AIxCoding 配置目录下的 `hooks` 目录；目标目录必须存在。 | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:357 | \| `${chrys_home}` \| AIxCoding 配置目录；通常为 `~/.chrys` 或 `%APPDATA%\chrys` \| | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:361 | AIxCoding 会按字面量替换 `env` 值和 `cwd` 中出现的上述模板。其他变量或表达式（如 `~`、`$VAR`、`${VAR}` 和 `${VAR:-default}`）不会由 AIxCoding 展开。 | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:365 | `execution` 控制 AIxCoding 是否等待钩子、钩子能否在 AIxCoding 退出后继续运行、未完成的任务是否重试，以及超时和失败的处理方式。所有字段都可以省略。多数通知和记录脚本使用默认值即可：当前操作不等待钩子，钩子最多运行 30 秒，失败时记录警告。 | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:377 | \| `fire_and_forget`（默认） \| 当前操作立即继续；本轮或当前会话结束时不等待钩子 \| 允许尚未完成的通知和记录被 AIxCoding 退出打断 \| 否 \| | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:386 | `on_error` 决定钩子无法启动、运行超时或返回非零退出码时，AIxCoding 如何继续： | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:394 | 阻塞式钩子失败时，AIxCoding 不采用脚本返回的操作决定，只应用 `on_error`。 | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:407 | `detach` 是布尔值，默认为 `false`。需要已启动的钩子在 AIxCoding 退出后继续运行时，可以设为 `true`，但只能用于 `mode: fire_and_forget`。 | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:413 | `delivery` 控制 AIxCoding 是否在以后启动时重试未完成的任务： | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:418 | \| `durable` \| 记录待完成的任务，在 AIxCoding 启动时重试符合条件的未完成任务。仅适用于 `async` 和 `fire_and_forget`。 \| | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:424 | `detach` 让已启动的进程在 AIxCoding 退出后继续运行，`delivery` 让 AIxCoding 在以后启动时恢复未完成的任务，两者可以同时设置。例如： | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:446 | 每次运行钩子时，AIxCoding 都会提供输入文件和结果文件。两个文件会在钩子结束后删除，不应保存其路径供以后使用。 | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:551 | 只有阻塞式钩子成功返回退出码 `0` 时，AIxCoding 才会按下表所列的事件和条件采用操作决定。异步和即发即弃钩子的结果文件不会改变 AIxCoding 行为。钩子无法启动、运行超时或返回非零退出码时，结果文件会被忽略，并按[失败处理配置](#设置运行时限和失败处理)中的 `on_error` 处理。 | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:566 | - JSON 无效、顶层不是对象或文件超过 1 MiB 时，AIxCoding 会记录警告并忽略结果，按无决定处理。 | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:575 | 同时加载项目配置和全局配置时，执行模式决定钩子在哪个阶段运行，配置来源决定每个阶段内的顺序。对于同一次事件，AIxCoding 按以下两个阶段处理钩子： | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:578 | 2. 如果没有钩子拒绝操作，AIxCoding 再启动匹配的异步和即发即弃钩子：先按项目配置中的定义顺序启动，再按全局配置中的定义顺序启动。这些非阻塞钩子可能并发运行，因此完成顺序不一定与启动顺序相同。 | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:594 | 项目配置和全局配置可以定义相同的 `id`。两个钩子都会保留，AIxCoding 同时会记录重名警告。 | — |
| 非注释命中 | docs/zh-Hans/reference/hooks.md:602 | 任一配置文件无效时，AIxCoding 会显示警告，并停用该文件定义的所有钩子；另一处有效配置文件仍然生效。未找到配置文件不会产生警告。 | — |
| 非注释命中 | docs/zh-Hans/reference/opentelemetry.md:3 | AIxCoding 可通过 OpenTelemetry 记录智能体运行过程中产生的以下遥测数据： | — |
| 非注释命中 | docs/zh-Hans/reference/opentelemetry.md:9 | 收集器是接收遥测数据的服务。AIxCoding 使用 OpenTelemetry Protocol（OTLP）向收集器发送数据。下文中的“端点”指收集器接收遥测数据的地址。 | — |
| 非注释命中 | docs/zh-Hans/reference/opentelemetry.md:11 | 本页介绍 AIxCoding 的 OpenTelemetry 配置、遥测数据的保存与导出方式，以及连接 OTLP 收集器的方法。 | — |
| 非注释命中 | docs/zh-Hans/reference/opentelemetry.md:17 | OpenTelemetry 默认关闭。可在终端用户界面（Terminal User Interface，TUI）的[设置 → 安全 → 遥测](../guides/configuration/settings.md#遥测)中启用，也可使用以下环境变量。**本页配置均在重启 AIxCoding 后生效。** | — |
| 非注释命中 | docs/zh-Hans/reference/opentelemetry.md:32 | 关闭 `CHRYS_OTEL` 或 TUI 中的“OpenTelemetry 导出”后，即使已配置端点或敏感数据选项，AIxCoding 也不会保存或发送遥测数据。 | — |
| 非注释命中 | docs/zh-Hans/reference/opentelemetry.md:48 | 配置任一收集器端点并重启 AIxCoding 后，AIxCoding 将停止在本地保存遥测数据。远端导出失败时不会回退到本地保存，因此相关数据可能丢失。 | — |
| 非注释命中 | docs/zh-Hans/reference/opentelemetry.md:91 | AIxCoding 通过 OTLP/gRPC 发送数据，直接使用配置的端点地址。`OTEL_EXPORTER_OTLP_PROTOCOL` 应保持未设置或设为 `grpc`。AIxCoding 安装包不包含 OTLP HTTP 导出器：设为 `http/protobuf`（或 `http`）时，OpenTelemetry 初始化失败，AIxCoding 不会记录任何遥测数据，也不会保存到本地；设为其他值时不会导出任何数据。 | — |
| 非注释命中 | docs/zh-Hans/reference/opentelemetry.md:112 | 将 `<token>` 替换为收集器提供的令牌，并在启动 AIxCoding 前设置。 | — |
| 非注释命中 | docs/zh-Hans/reference/opentelemetry.md:132 | 默认服务名（`service.name`）为 `chrys`，服务版本为当前安装的 AIxCoding 版本。可在收集器或其连接的观测平台中按服务名查找数据。 | — |
| 非注释命中 | docs/zh-Hans/reference/opentelemetry.md:134 | 如果多处运行的 AIxCoding 向同一个收集器发送数据，可以用服务名和资源属性区分数据来源。资源属性是附在遥测数据上的标签，例如运行环境和实例名称。 | — |
| 非注释命中 | docs/zh-Hans/reference/opentelemetry.md:136 | 例如，在测试环境中运行一个 AIxCoding 实例，可在 Bash 或 Zsh 中设置： | — |
| 非注释命中 | docs/zh-Hans/reference/opentelemetry.md:143 | 在同一终端启动 AIxCoding 后，导出的数据会带上以下标识，可在观测平台中据此筛选： | — |
| 非注释命中 | docs/zh-Hans/reference/opentelemetry.md:149 | \| `service.instance.id` \| `test-01` \| 实例名称，用于区分同一环境中的多个 AIxCoding 实例 \| | — |
| 非注释命中 | docs/zh-Hans/reference/opentelemetry.md:157 | 配置指标端点后（也可继承基础端点），AIxCoding 每 5 秒尝试导出以下指标： | — |
| 非注释命中 | docs/zh-Hans/reference/opentelemetry.md:165 | AIxCoding 会为 Token 用量自动添加 `gen_ai.token.type` 标签。在观测平台查询 `gen_ai.client.token.usage` 时： | — |
| 非注释命中 | docs/zh-Hans/reference/opentelemetry.md:175 | 1. 是否已启用 OpenTelemetry，并在修改配置后重启 AIxCoding。 | — |
| 非注释命中 | docs/zh-Hans/reference/settings.md:1 | # AIxCoding-CLI 设置文件参考 | — |
| 非注释命中 | docs/zh-Hans/reference/settings.md:3 | `settings.yaml` 保存 AIxCoding 的界面偏好、默认智能体、会话和工具设置。本文按用途列出常用设置键，并说明文件位置与格式、值的写法、多个来源并存时的优先级，以及项目文件可以覆盖的范围。 | — |
| 非注释命中 | docs/zh-Hans/reference/settings.md:5 | 在终端用户界面（Terminal User Interface，TUI）中修改设置的步骤和生效时间，见[配置 AIxCoding 设置](../guides/configuration/settings.md)。 | — |
| 非注释命中 | docs/zh-Hans/reference/settings.md:14 | AIxCoding 仅在当前会话的工作目录下查找 `.chrys/settings.yaml`，不向父目录或子目录查找。 | — |
| 非注释命中 | docs/zh-Hans/reference/settings.md:24 | 手动编辑设置文件后，保存并重新启动 AIxCoding 使修改生效。 | — |
| 非注释命中 | docs/zh-Hans/reference/settings.md:67 | 手动在 YAML 或环境变量中将默认审批模式设为 `bypass`，下次按此默认值启动时就会跳过审批。在 TUI 中通过 `/approval` 切换到 `bypass` 时，AIxCoding 会将默认模式保存为 `auto`；TUI 设置窗口不提供 `bypass`。 | — |
| 非注释命中 | docs/zh-Hans/reference/settings.md:69 | Hooks 是 AIxCoding 在特定事件时运行的外部命令。项目 Hooks 与项目设置分别控制；关闭 `project.config_enabled` 不会关闭项目 Hooks。编写与配置见[配置和编写 Hooks](../guides/extensions/hooks.md)。 | — |
| 非注释命中 | docs/zh-Hans/reference/settings.md:94 | \| `mutations.coordination.enabled` \| `CHRYS_MUTATION_COORDINATION` \| `true` \| 布尔值；协助区分共享工作目录的不同 AIxCoding 会话造成的文件改动 \| | — |
| 非注释命中 | docs/zh-Hans/reference/settings.md:142 | \| `notifications.suppress_when_focused` \| AIxCoding 获得焦点时暂停通知 \| | — |
| 非注释命中 | docs/zh-Hans/reference/settings.md:152 | **原始 HTTP 日志可能包含明文 API 密钥、完整提示词和模型回复。** 仅在明确数据去向和访问权限后启用，排查结束后关闭不再需要的诊断选项并重启 AIxCoding。 | — |
| 非注释命中 | docs/zh-Hans/reference/settings.md:176 | 启动时，AIxCoding 会尝试将旧版用户 `.env` 中的 AIxCoding 设置迁入用户 `settings.yaml`，并清理已迁移的设置行。合并时 `settings.yaml` 中已有的同名键优先保留，不会被覆盖；尚未完成迁移的设置行仍按上表第 3 级来源生效。迁移失败时会提示，并在下次启动时重试。模型服务的 API 密钥等环境变量保留在 `.env` 中。 | — |
| 非注释命中 | docs/zh-Hans/reference/settings.md:178 | 工作目录 `.env` 中的 AIxCoding 设置不生效。项目设置应写入 `.chrys/settings.yaml`。 | — |
| 非注释命中 | docs/zh-Hans/reference/settings.md:227 | AIxCoding 会提示并忽略项目中不允许的键、超出覆盖限制的值和未知键，继续应用其他有效设置。 | — |
| 非注释命中 | docs/zh-Hans/reference/settings.md:236 | \| `aixcoding-cli serve` \| 在浏览器中承载 TUI；配置文件和环境变量来自运行 AIxCoding 服务的机器 \| | — |
| 非注释命中 | docs/zh-Hans/reference/settings.md:240 | 1. 确认设置文件的位置正确，保存后已重新启动 AIxCoding。 | — |
| 非注释命中 | docs/zh-Hans/reference/settings.md:243 | 4. 查看 AIxCoding 启动时报告的消息：无效值或未知键的处理规则见[值的写法与无效值](#值的写法与无效值)；目录相关提示对照[文件位置与格式](#文件位置与格式)检查。 | — |
| 非注释命中 | docs/zh-Hans/reference/themes.md:3 | AIxCoding 支持通过主题文件自定义终端用户界面（Terminal User Interface，TUI）的外观。本页介绍主题文件的格式、常用配色字段和加载规则。通过界面修改并保存主题，请参阅[自定义主题](../guides/configuration/themes.md)。 | — |
| 非注释命中 | docs/zh-Hans/reference/themes.md:14 | 主题文件使用 UTF-8 编码，扩展名必须为 `.yaml` 或 `.yml`，直接存放在上述目录中。AIxCoding 不读取子目录中的主题文件。 | — |
| 非注释命中 | docs/zh-Hans/reference/themes.md:24 | 新增或修改主题文件后，重启 AIxCoding 加载，再按 **F9** 在主题列表中选择对应主题即可应用。 | — |
| 非注释命中 | docs/zh-Hans/reference/themes.md:52 | `primary` 是唯一必填字段，其余字段均可按需设置。未指定的颜色由 AIxCoding 自动补齐，具体规则见[默认配色规则](#默认配色规则)。 | — |
| 非注释命中 | docs/zh-Hans/reference/themes.md:147 | 加载时发现 YAML 格式错误、缺少 `primary`、未知顶层字段或无效字段值时，AIxCoding 会显示警告并跳过该文件。根据警告检查对应文件，修正后重启加载；其他有效主题仍可使用。 | — |
| 非注释命中 | docs/zh-Hans/reference/themes.md:149 | 主题通过加载后，如果应用时发现 `variables` 值无法用于对应的界面样式，AIxCoding 会显示警告并回退到默认主题 `chrys`。回退不会覆盖已保存的主题选择，修正文件后可重启重试。 | — |
| 非注释命中 | docs/zh-Hans/reference/tool-kinds-and-names.md:3 | AIxCoding 使用工具类别（`tool_kind`）对用途或来源相近的工具进行分组，使用工具名称（`tool_name`）标识具体工具。同一类别可以包含多个工具，例如 `filesystem.write` 类别包含 `write_file` 和 `edit_file`。 | — |
| 非注释命中 | docs/zh-Hans/reference/tool-kinds-and-names.md:30 | AIxCoding 自带的智能体都没有启用 `web_search` 和 `web_fetch`。智能体包含这两个工具时，如果某个工具的模式为 `off`，或模型提供方运行同名的网络工具，对应的本地工具不会提供。参阅[配置网络工具](../guides/configuration/web-tools.md)。 | — |
| 非注释命中 | docs/zh-Hans/reference/tool-kinds-and-names.md:34 | `shell` 类别中的主要工具使用当前 Shell 的名称，例如 `zsh`、`bash`、`pwsh`、`powershell` 或 `cmd`。在 Windows 上检测到 Git Bash 时，AIxCoding 还会在主要 Shell 工具之外提供 `git_bash` 工具。实际名称取决于操作系统和 AIxCoding 检测到的 Shell。 | — |
| 非注释命中 | docs/zh-Hans/reference/tool-kinds-and-names.md:46 | `mcp` 类别包含 MCP 服务器提供的工具。AIxCoding 会先将工具名称中除英文字母、数字、下划线和连字符以外的字符替换为连字符。未设置 `tool_name_prefix` 时，直接使用处理后的名称。 | — |
| 非注释命中 | docs/zh-Hans/reference/tool-kinds-and-names.md:48 | 设置 `tool_name_prefix` 后，AIxCoding 还会移除处理后名称开头的下划线和连字符，再按 `<前缀>_<工具名称>` 拼接；名称被移除为空时，只使用前缀。例如，服务器提供 `search` 或 `_search`，前缀为 `github` 时，最终名称均为 `github_search`。 | — |
| 非注释命中 | docs/zh-Hans/reference/tool-kinds-and-names.md:52 | 启用按需加载时，AIxCoding 还会提供三个控制工具： | — |
| 非注释命中 | docs/zh-Hans/reference/tui-slash-commands.md:29 | 下表列出 AIxCoding 的内置斜杠命令。 | — |
| 非注释命中 | docs/zh-Hans/reference/tui-slash-commands.md:41 | \| `/exit` \| `/quit` \| 退出 AIxCoding 并返回终端。 \| — \| | — |
| 非注释命中 | docs/zh-Hans/reference/tui-slash-commands.md:46 | \| `/login` \| — \| 打开 AIxCoding 设备码登录对话框。对话框会显示用户码，并自动在浏览器中打开验证页面，在页面上确认授权即可完成登录。凭据以操作系统级加密存储，下次启动时静默校验。顶栏在审批模式徽章右侧展示登录状态：已登录显示绿色 ● 与账号名，未登录显示灰色 ●「未登录」徽章。 \| — \| | — |
| 非注释命中 | docs/zh-Hans/reference/tui-slash-commands.md:47 | \| `/logout` \| — \| 清除当前环境存储的 AIxCoding 凭据并退出登录。未登录时执行该命令是安全的：仅提示当前状态，不做任何操作。退出后顶栏登录徽章立即变灰。 \| — \| | — |
| 非注释命中 | docs/zh-Hans/reference/tui-slash-commands.md:54 | \| `/rollback`<br>`/rollback <N>`<br>`/rollback to <N>` \| — \| 回滚分为两种：仅回滚对话并保留当前文件变更；同时回滚对话，并恢复 AIxCoding 能够恢复的文件变更。回滚结果无法撤销。 \| 省略参数：打开回滚选择器，默认选择最近的可回滚目标。通过“回滚”窗口左下角的文件还原选项（名称中会显示文件数量），可以决定是否同时恢复文件变更。<br>`N`：立即丢弃最近 `N` 轮，必须是正整数。从一次用户提交开始，到该次智能体运行结束为一轮。<br>`to N`：保留第 1 轮至第 `N` 轮并丢弃之后的轮次；`N` 必须是非负整数，`0` 表示回到会话开始处。<br>`/rollback N` 和 `/rollback to N` 都会立即执行，并恢复被丢弃轮次中 AIxCoding 能够恢复的文件变更。 \| | — |
| 非注释命中 | docs/zh-Hans/reference/tui-slash-commands.md:60 | \| `/settings [tab]` \| — \| 打开设置窗口。详见[配置 AIxCoding 设置](../guides/configuration/settings.md#设置窗口)。 \| `tab`：直接打开指定标签页。可用值为 `general`、`models`、`security`、`sessions`、`tools` 和 `notifications`。省略参数时，按空格键或 **Enter** 显示可用标签页。 \| | — |
| 非注释命中 | docs/zh-Hans/reference/tui-slash-commands.md:62 | \| `/help` \| — \| 打开“AIxCoding 用户指南”窗口，查看本文档。也可以按 **F8** 或点击底栏的 `f8 帮助`。 \| — \| | — |
| 非注释命中 | docs/zh-Hans/reference/tui-slash-commands.md:63 | \| `/man [command]` \| — \| 显示 AIxCoding 命令说明。 \| 省略参数：按空格键或 **Enter** 显示可查看的命令。<br>`command`：命令名称或别名；显示指定命令的名称、用法、说明、别名和选项。 \| | — |
| 非注释命中 | docs/zh-Hans/reference/tui-slash-commands.md:67 | 运行时加载的技能可以通过 `/skill-name` 形式调用。提交技能命令后，AIxCoding 会要求智能体在本轮任务中使用指定技能。 | — |
| 非注释命中 | docs/zh-Hans/reference/tui-slash-commands.md:76 | 技能命令不属于 AIxCoding 的内置命令。如果技能名称与内置命令相同，内置命令优先。 | — |
| 非注释命中 | docs/zh-Hans/reference/workflows.md:38 | \| 2 \| AIxCoding 配置目录下：Windows 为 `%APPDATA%\chrys\workflows\`；Linux、macOS 为 `~/.chrys/workflows/` \| `global` \| | — |
| 非注释命中 | docs/zh-Hans/reference/workflows.md:39 | \| 3 \| 随 AIxCoding 提供的内置示例 \| `builtin` \| | — |
| 非注释命中 | docs/zh-Hans/reference/workflows.md:54 | 确认会被保存，后续运行可省略 `--trust`。入口文件源码、构建出的工作流定义，或所选解释器的路径、版本、平台及 AIxCoding 提供的工作流 SDK 等环境信息发生变化后，需要重新确认。该检查不覆盖已安装依赖包的变化，也不逐一检查导入的其他 Python 文件。 | — |
| 非注释命中 | docs/zh-Hans/reference/workflows.md:194 | `fn` 必须返回字符串或 `WorkflowValue`。返回字符串时，AIxCoding 将其转换为 `WorkflowValue(text=返回的字符串, data=None)`。 | — |
| 非注释命中 | docs/zh-Hans/reference/workflows.md:218 | \| `model` \| 可选，传入 AIxCoding 模型配置的 ID 或名称，可通过 `aixcoding-cli models` 查看；省略时按下文的模型选择规则确定 \| | — |
| 非注释命中 | docs/zh-Hans/reference/workflows.md:237 | `model` 按以下顺序匹配 AIxCoding 模型配置： | — |
| 非注释命中 | docs/zh-Hans/reference/workflows.md:245 | 普通 AIxCoding 智能体按以下优先级选择模型： | — |
| 非注释命中 | docs/zh-Hans/reference/workflows.md:249 | 3. 工作流默认模型。TUI 可在“运行设置”中选择；CLI 通过 `aixcoding-cli workflow run <工作流ID> --session <会话ID>` 加载已有工作流会话时，沿用该会话保存的模型选择。未单独选择工作流默认模型时，使用 [AIxCoding 配置的默认模型](settings.md#智能体模型与请求)。 | — |
| 非注释命中 | docs/zh-Hans/reference/workflows.md:257 | 节点输出为 `WorkflowValue`，`text` 为智能体的回复文本，`data` 为 `None`。普通 AIxCoding 智能体优先使用最终回复文本；最终回复无文本时，将本次执行过程中输出的文本按顺序拼接，作为节点输出，其中可能包含工具调用前后的过程说明。 | — |
| 非注释命中 | docs/zh-Hans/reference/workflows.md:261 | 普通 AIxCoding 智能体节点对配置项的支持如下（✓ 支持，✗ 不支持），字段格式和配置规则见[智能体配置文件参考](agent-profile.md)。 | — |
| 非注释命中 | docs/zh-Hans/reference/workflows.md:285 | - 显式指定 `model` 时，填写 AIxCoding 模型配置的 ID 或名称。AIxCoding 仅使用其中的 `model_id`，通过 ACP 请求切换远端模型；该配置的其他字段不生效。模型未被远端列出，或切换请求因方法不支持、参数无效而被拒绝时，继续使用远端默认模型。 | — |
| 非注释命中 | docs/zh-Hans/reference/workflows.md:288 | - 工具执行由外部智能体负责。只有外部智能体通过 ACP 发起权限请求的操作，才会进入 AIxCoding 的审批流程。 | — |
| 非注释命中 | docs/zh-Hans/reference/workflows.md:381 | `WorkflowBuilder.build()` 返回的已构建工作流。将其赋给工作流文件顶层的 `workflow` 变量，供 AIxCoding 加载和运行。 | — |
| 非注释命中 | docs/zh-Hans/reference/workflows.md:607 | \| 外部 ACP 智能体节点连接中断、长时间无响应、报错或达到 `timeout` 上限 \| 尚未达到 `Retry.max_attempts`。AIxCoding 无法判断外部智能体报告的哪些错误无法恢复，因此都会重试；但智能体无法启动、本次尝试内多次重试连接后仍连不上、配置被拒绝，以及智能体拒绝回答、提前停止或回答为空时不重试 \| | — |
| 非注释命中 | docs/zh-Hans/reference/workflows.md:610 | 若重试可能让模型服务商再次运行它自己那边的工具（如服务商运行的 MCP 服务器或 Shell），则不自动重试节点。服务商运行的搜索和代码执行可以安全重复，不影响重试；AIxCoding 自己的文件、Shell 和 MCP 工具也不影响。 | — |
| 非注释命中 | docs/zh-Hans/reference/workflows.md:626 | 工作流默认使用运行 AIxCoding 的 Python 解释器，也可在工作流文件中指定已有的虚拟环境或 Python 可执行文件，支持 Python 3.9 及以上版本。 | — |
| 非注释命中 | docs/zh-Hans/reference/workflows.md:637 | 保留示例中的 `#` 前缀和 `# ///` 标记，AIxCoding 会读取这段注释中的配置。`[tool.chrys]` 是 AIxCoding 专用配置区，`python` 的相对路径以工作流文件所在目录为基准。 | — |
| 非注释命中 | docs/zh-Hans/reference/workflows.md:639 | `python` 也可直接填写 Python 可执行文件的路径，如 `"/opt/homebrew/bin/python3.12"`。AIxCoding 不会通过 `PATH` 查找命令。使用 uv 创建的环境时，指向其 `.venv`。 | — |
| 非注释命中 | docs/zh-Hans/reference/workflows.md:641 | AIxCoding 不会自动安装依赖，请提前在所选环境中安装工作流所需的第三方包。`chrys.workflows` 由 AIxCoding 在运行时提供，无需另外安装。 | — |
| 非注释命中 | docs/zh-Hans/reference/workflows.md:647 | \| `requires-python` \| 可选的 Python 版本约束字符串，例如 `">=3.10,<3.13"`。AIxCoding 检查所选解释器是否满足约束，不满足时拒绝加载；不会自动寻找或安装其他版本。仅支持以逗号分隔、由 `~=`、`==`、`!=`、`<=`、`>=`、`<`、`>` 与纯数字发布版本组成的子句：`.*` 只能与 `==`、`!=` 搭配，`~=` 至少需要两段版本号。其他写法同样会拒绝加载 \| | — |
| 非注释命中 | docs/zh-Hans/reference/workflows.md:648 | \| `dependencies` \| 可选的依赖字符串数组。非空时必须同时指定 `[tool.chrys] python`，否则拒绝加载，即使默认环境已经安装这些包。指定自备解释器后，AIxCoding 不安装这些依赖，也不校验已安装版本是否符合声明 \| | — |
| 非注释命中 | docs/zh-Hans/reference/workflows.md:675 | 包含 AIxCoding 智能体节点时，运行设置还提供默认模型选择。 | — |
| 非注释命中 | docs/zh-Hans/reference/workflows.md:723 | \| `session_restored` \| 从保存记录加载的会话，在本次启动 AIxCoding 后首次开始新运行时，在 `workflow_run_start` 之前 \| `restored_session_id`：恢复的会话 ID \| | — |
| 非注释命中 | docs/zh-Hans/reference/workflows.md:724 | \| `session_end` \| 本次启动 AIxCoding 后已开始过运行的会话被删除、AIxCoding 正常关闭或 CLI 运行命令正常结束时 \| 无 \| | — |
| 非注释命中 | docs/zh-Hans/reference/workflows.md:728 | 每次启动 AIxCoding 后，同一会话仅在首次运行时触发 `session_start` 或 `session_restored`；每次被接受的运行各触发一次 `workflow_run_start` 和 `workflow_run_end`，节点重试不会重复触发。进程崩溃或被强制终止时，无法保证触发结束事件。 | — |
| 非注释命中 | docs/zh-Hans/reference/workflows.md:732 | `workflow_run_start` 和 `workflow_run_end` 用于通知和记录。配置为阻塞式钩子时，AIxCoding 会等待钩子结束，但不会采用其返回的操作决定来阻止运行或授予工具权限；`action: block` 会被忽略，钩子失败时的 `on_error: block` 按警告处理。 | — |
| 非注释命中 | docs/zh-Hans/start/getting-started.md:1 | # 开始使用 AIxCoding-CLI | — |
| 非注释命中 | docs/zh-Hans/start/getting-started.md:3 | 本教程介绍如何安装 AIxCoding-CLI、配置模型，并在项目中使用智能体完成一次开发任务。 | — |
| 非注释命中 | docs/zh-Hans/start/getting-started.md:5 | ## 1. 安装 AIxCoding-CLI | — |
| 非注释命中 | docs/zh-Hans/start/getting-started.md:7 | AIxCoding-CLI 为 macOS、Linux 和 Windows 提供预构建的离线安装包。安装包已包含 Python 和运行依赖，无需另行安装 Python。 | — |
| 非注释命中 | docs/zh-Hans/start/getting-started.md:50 | 安装测试包时，先执行 `$env:ICODE_CHANNEL='test'`，再运行上述命令。安装器会尝试将 AIxCoding-CLI 加入当前用户的 `PATH`。安装完成后，请打开一个新终端。 | — |
| 非注释命中 | docs/zh-Hans/start/getting-started.md:58 | 命令应输出 AIxCoding-CLI 的版本号。在 macOS 或 Linux 上，如果系统找不到 `aixcoding-cli`，请按安装器的提示将 `~/.local/bin` 加入 `PATH`；如果安装器提示 `~/.local/bin/aixcoding-cli` 已存在，该命令会启动其他程序，请改用 `chrys` 命令。在 Windows 上请打开新的终端；如果安装器提示更新用户 PATH 失败，请手动将 `%LOCALAPPDATA%\chrys\bin` 加入用户 `PATH`。 | — |
| 非注释命中 | docs/zh-Hans/start/getting-started.md:60 | ## 2. 在项目中启动 AIxCoding-CLI | — |
| 非注释命中 | docs/zh-Hans/start/getting-started.md:64 | 在终端中进入要处理的项目目录并启动 AIxCoding-CLI： | — |
| 非注释命中 | docs/zh-Hans/start/getting-started.md:95 | AIxCoding-CLI 应正常返回问候回复。若模型服务返回错误，请重新检查模型 ID、服务地址、API 密钥等模型配置。 | — |
| 非注释命中 | docs/zh-Hans/start/getting-started.md:101 | AIxCoding-CLI 默认提供两个主智能体：Q&A Agent（问答智能体）和 Code Agent（代码智能体）。两者都可以阅读项目、分析代码和讨论方案，但定位和可用工具不同：Q&A Agent 主要提供只读能力，适合了解项目、解释代码和分析问题；Code Agent 则可以修改文件、运行命令，适合编写、审查、重构、调试和验证代码。 | — |
| 非注释命中 | docs/zh-Hans/start/getting-started.md:137 | 若要结束本次使用，输入 `/exit` 或按 `Ctrl+Q` 退出 AIxCoding-CLI。 | — |
| 非注释命中 | docs/zh-Hans/start/getting-started.md:141 | 至此，已经完成 AIxCoding-CLI 的安装和模型配置，并了解了 Q&A Agent 和 Code Agent 的基本使用方式，以及如何在同一会话中配合完成开发任务。 | — |
| 非注释命中 | docs/zh-Hans/start/getting-started.md:149 | - 通过 [Skills](../guides/extensions/skills.md) 和 [MCP](../guides/extensions/mcp.md) 扩展 AIxCoding-CLI | — |
| 非注释命中 | docs/zh-Hans/start/what-is-aixcoding.md:1 | # 什么是 AIxCoding | — |
| 非注释命中 | docs/zh-Hans/start/what-is-aixcoding.md:3 | **AIxCoding 是一个用于运行和构建智能体（Agent）的平台。** | — |
| 非注释命中 | docs/zh-Hans/start/what-is-aixcoding.md:5 | AIxCoding 支持通过自然语言与智能体交互，完成文件阅读与修改、Shell 命令执行、代码库搜索等任务，也可以将复杂任务委派给子智能体。 | — |
| 非注释命中 | docs/zh-Hans/start/what-is-aixcoding.md:7 | AIxCoding 的主要交互方式是终端用户界面（Terminal User Interface，TUI），用于集中呈现对话、任务执行和工具调用过程。工具调用会以卡片形式展示，便于了解智能体正在执行的操作。除 TUI 外，AIxCoding 还支持在脚本中以无界面模式运行，通过智能体客户端协议（Agent Client Protocol，ACP）接入编辑器，或在浏览器中运行 TUI。 | — |
| 非注释命中 | docs/zh-Hans/start/what-is-aixcoding.md:11 | * **灵活组合智能体和模型。** AIxCoding 可通过界面点击或快捷命令快速切换智能体和模型，并在同一个会话中根据任务选择不同的组合。 | — |
| 非注释命中 | docs/zh-Hans/start/what-is-aixcoding.md:13 | * **智能体可按需配置。** 可以通过 TUI 配置智能体的指令、模型、工具、技能、MCP 服务器和子智能体，也可以直接编辑 YAML 配置文件，无需修改 AIxCoding 源代码。 | — |
| 非注释命中 | docs/zh-Hans/start/what-is-aixcoding.md:19 | 在 AIxCoding 中，智能体与模型彼此独立，可以根据不同任务灵活组合。AIxCoding 提供内置智能体，但不提供模型配置或 API 凭据。首次使用前，需要创建模型配置并连接相应的模型服务。 | — |
| 非注释命中 | docs/zh-Hans/start/what-is-aixcoding.md:21 | AIxCoding 目前支持 Anthropic、OpenAI、DeepSeek 和 GLM 等模型提供商，也可以通过 OpenAI API 兼容端点连接其他模型服务，包括本地部署的模型。 | — |
| 非注释命中 | docs/zh-Hans/start/what-is-aixcoding.md:23 | ## 使用 AIxCoding | — |
| 非注释命中 | docs/zh-Hans/start/what-is-aixcoding.md:25 | AIxCoding 提供多种使用入口，可以根据不同的工作场景选择合适的方式： | — |
| 非注释命中 | docs/zh-Hans/start/what-is-aixcoding.md:27 | - **TUI**：AIxCoding 的主要交互界面，适合交互式任务。支持在会话中查看工具调用、处理审批请求，以及切换智能体和模型配置。 | — |
| 非注释命中 | docs/zh-Hans/start/what-is-aixcoding.md:30 | - **ACP 服务**：将 AIxCoding 作为智能体后端，[接入支持 ACP 的编辑器或其他开发工具](../guides/running/aixcoding-acp.md)。 | — |
| 非注释命中 | docs/zh-Hans/start/what-is-aixcoding.md:34 | 如果准备开始使用 AIxCoding，请阅读 [开始使用 AIxCoding](getting-started.md)，完成安装、模型配置和首次运行。 | — |
| 非注释命中 | mock_server/README.md:11 | \| `aixcoding_auth/` \| AIxCoding 设备码登录认证服务 \| `/api/v1/auth/...`、`/api/v1/user/info` \| | — |
| 非注释命中 | mock_server/README.md:12 | \| `aixcoding_update/` \| AIxCoding TUI 版本更新检测服务 \| `/csas/api/v2/releases/check` \| | — |
| 非注释命中 | mock_server/README.md:23 | ├── aixcoding_auth/         # AIxCoding 登录认证 mock | — |
| 非注释命中 | mock_server/README.md:27 | ├── aixcoding_update/       # AIxCoding 版本更新检测 mock | — |
| 非注释命中 | mock_server/__init__.py:3 | """Local mock servers for development, integration, and contract testing.

This package is a **registry of mocks** for the external services the iCode
agent platform depends on. Each mock is an isolated, self-contained
subpackage that simulates one real backend so product code can be exercised
end-to-end without hitting staging or production.

The umbrella is intentionally thin: there is no shared runtime — each
subpackage owns its own server, fixtures, tests, and README. New mocks are
added by creating a new subdirectory under ``mock_server/`` and following
the same shape.

Current subpackages:

- :mod:`mock_server.aixcoding_auth` — AIxCoding device-code auth service
  (``/api/v1/auth/...``, ``/api/v1/user/info``)
- :mod:`mock_server.aixcoding_update` — AIxCoding TUI update-detection service
  (``/csas/api/v2/releases/check``)
- :mod:`mock_server.chrys_model_catalog` — server-published model catalog
  (``/model-catalog``, ``/llm/api/v1/continue-config/dispatch``)

Conventions for new subpackages:

- Name the directory after the **service or capability** it mocks, with a
  short product prefix where the namespace is shared. Avoid generic names
  like ``api`` or ``backend``.
- Include at least: ``__init__.py`` (docstring), ``server.py`` (or a
  similarly descriptive module) and ``README.md`` (endpoints + usage);
  put the tests wherever the subpackage's README documents
  (``mock_server/aixcoding_auth`` keeps them in ``tests/app/aixcoding/``).
- Bind only to loopback addresses. The starting helper must reject any
  non-loopback host at startup.
- Keep the mock black-box with respect to the contract it pretends to
  speak — stdlib-only, never import the product package.
- Tests bypass any system proxy (``direct_route``), bind port 0 and read
  back the kernel-assigned port through the listening socket — never probe
  for a free port.
- ``pyproject.toml``'s ``testpaths = ["tests", "mock_server"]`` already
  includes this directory; new subpackages are picked up automatically.
""" | — |
| 非注释命中 | mock_server/aixcoding_auth/README.md:1 | # AIxCoding Auth Mock Server | — |
| 非注释命中 | mock_server/aixcoding_auth/README.md:3 | `mock_server/aixcoding_auth/` —— AIxCoding 设备码登录认证服务的本地模拟。**不随产品 | — |
| 非注释命中 | mock_server/aixcoding_auth/__init__.py:3 | """AIxCoding device-code auth mock server (local debug tool, never shipped).

Simulates the intranet auth service behind ``82.187.34.98`` (PROD) /
``81.89.182.150`` (DEV), which is unreachable off the bank network: the
device-code endpoints (``/auth/device/code``, ``/auth/device/token``), the
``/user/info`` endpoint, and a bundled local verification page that decides
pending grants in ``manual`` mode. Wire quirks of the real backend (the
``result`` vs ``data`` envelope split, ``success: true`` while pending, the
``success``-less unknown-token body) are reproduced byte-for-byte so the
client must parse the envelope, never the HTTP status.

Public API lives in :mod:`mock_server.aixcoding_auth.server`; the canonical
entry points are :func:`mock_server.aixcoding_auth.server.create_server`
(tests) and ``python mock_server/aixcoding_auth/server.py`` (CLI, port 7777).
Point iCode at it with ``CHRYS_AUTH_ENVIRONMENT=local``.

Layout::

    mock_server/
        aixcoding_auth/       # this subpackage
            __init__.py      # this file
            server.py        # HTTP server, grant state machine, verify page
            README.md        # endpoints, modes, usage

Behaviour tests live in ``tests/app/aixcoding/`` (they exercise this mock
through the real ``AuthClient``), so no ``test_server.py``/``conftest.py``
is duplicated here; see the README for the reasoning.
""" | — |
| 非注释命中 | mock_server/aixcoding_update/README.md:1 | # AIxCoding Update-Detection Mock Server | — |
| 非注释命中 | mock_server/aixcoding_update/README.md:3 | `mock_server/aixcoding_update/` —— AIxCoding TUI 版本更新检测服务 | — |
| 非注释命中 | mock_server/aixcoding_update/__init__.py:3 | """AIxCoding TUI update-detection mock server (local debug tool, never shipped).

Simulates ``GET /csas/api/v2/releases/check`` — the release-check contract the
TUI update-detection feature will call at startup. The real backend does not
exist yet; this mock freezes the wire contract so client work and manual runs
can proceed: strict query validation
(unknown/missing/invalid → ``400 invalid_app_release_query``), v2 manifest
answers with ``ETag``/``304`` support, ``204`` for "no applicable release",
plus fault modes (``error`` / ``garbage`` / slow) covering the client's
silent-failure paths.

Public API lives in :mod:`mock_server.aixcoding_update.server`; the canonical
entry points are :func:`mock_server.aixcoding_update.server.create_server`
(tests, ephemeral port) and ``python mock_server/aixcoding_update/server.py``
(defaults: loopback :7778 — there are no CLI flags, every knob is steered at
runtime via ``POST /debug/config``). Point the TUI at it with
``AIXCODING_EXTENSION_BASE_URL=http://127.0.0.1:7778/csas``.

Layout::

    mock_server/
        aixcoding_update/     # this subpackage
            __init__.py      # this file
            server.py        # HTTP server, strict validation, modes, debug endpoints
            test_server.py   # contract tests (stdlib urllib, no fixtures needed)
            README.md        # endpoints, modes, /debug/config usage

The TUI client (``src/chrys/aixcoding/update_detection.py``) ships alongside
this mock: its end-to-end tests live in ``tests/app/aixcoding/``, while the
contract tests here keep guarding the mock itself.
""" | — |
| 非注释命中 | mock_server/aixcoding_update/server.py:3 | """Loopback mock of the AIxCoding TUI update-detection service.

Simulates ``GET /csas/api/v2/releases/check`` — the release-check contract the
TUI update-detection feature will call at startup. The real backend does not
exist yet; this mock freezes the wire contract so client implementation, manual
runs, and integration tests can proceed against it:

* four required query params (``clientType`` / ``platform`` / ``architecture``
  / ``currentVersion``), strict mode: unknown/missing/invalid →
  ``400 {"error": "invalid_app_release_query"}``;
* ``200`` serves the v2 manifest JSON with an ``ETag`` header (SHA-256 of the
  body) and honours ``If-None-Match`` with ``304``;
* ``204`` when there is no applicable release.

The manifest is built per request from the query — ``kind`` mirrors
``clientType`` and the artifact platform (friendly spelling derived from
``platform``) / architecture reflect the caller — around a configurable
version and download URL, so any caller gets a coherent answer.

There are no CLI arguments: the process starts with defaults (update mode,
candidate ``999.0.0``, loopback :7778) and every response-shaping knob is
steered at runtime via ``POST /debug/config``; ``POST /debug/reset`` restores
all defaults and drops the request log in one call.

Four modes (runtime ``POST /debug/config``):

``update`` (default)
    Answer like the real service would: the manifest (200, or 304 on a
    matching ``If-None-Match``) only when the candidate version is strictly
    newer than the request's ``currentVersion`` under SemVer 2.0.0
    precedence; ``204`` otherwise. ``force_update`` skips the comparison so
    a smaller candidate can be served deliberately (dirty-data drills).

``no_update``
    Valid queries get ``204`` — the "already latest" path.

``error``
    Valid queries get ``500`` — exercises the client's silent-failure path.

``garbage``
    Valid queries get ``200`` with an unparseable body — exercises the
    client's parse-failure path.

Invalid queries answer the contract's ``400`` in every mode.

Malformed-response drills (a ``/debug/config`` parameter group of their own,
both scoped to the 200 answer): ``raw_body`` replaces the manifest with any
literal body (e.g. a truncated answer) and ``drop_fields`` omits manifest
fields (dotted paths such as ``artifact.url`` allowed) — covering the
client's parse-failure and structure-mismatch silent paths respectively.

Run it from the repository root::

    uv run python mock_server/aixcoding_update/server.py    # loopback :7778, update mode

Then steer it at runtime and point the TUI at it::

    curl -X POST http://127.0.0.1:7778/debug/config -d '{"mode": "no_update"}'
    AIXCODING_EXTENSION_BASE_URL=http://127.0.0.1:7778/csas uv run aixcoding-cli

Importable for tests: ``MockUpdateConfig`` / ``MockUpdateState`` /
``create_server`` start a loopback instance on an ephemeral port.
""" | — |
| 非注释命中 | mock_server/aixcoding_update/server.py:143 | /mock-attachments/AIxCoding- | — |
| 非注释命中 | mock_server/aixcoding_update/test_server.py:3 | """Contract tests for the AIxCoding update-detection mock (mock_server/aixcoding_update/server.py).

Conventions: bind port 0 (kernel-assigned), loopback only. Requests go through
stdlib ``urllib`` with an empty ``ProxyHandler`` — no environment or system
proxy can intercept loopback traffic, the same guarantee ``chrys_model_catalog``
gets from its ``direct_route`` fixture without importing any test fixtures.
""" | — |
| 注释标记 | pyproject.toml:201 | AIxCoding TUI: user-facing Chinese prose keeps its full-width punctuation | TUI |
| 非注释命中 | release/INSTALL.md:1 | # AIxCoding-CLI 安装指南（内网用户版） | — |
| 非注释命中 | release/INSTALL.md:3 | AIxCoding-CLI 是一个运行在终端里的智能体平台（TUI）。安装包已内置 Python 和全部依赖，**无需安装 Python，全程离线可用**。 | — |
| 非注释命中 | release/INSTALL.md:120 | 错误会附带二进制输出。先用 `file <解压后的可执行文件>` 核对是否为 Linux aarch64 程序，再检查系统的 glibc 版本。此前安装过 AIxCoding-CLI 不会引发该自检错误。 | — |
| 注释标记 | scripts/install.sh:3 | AIxCoding-CLI TUI 安装器（内网友好） | — |
| 非注释命中 | scripts/install.sh:85 | AIxCoding-CLI TUI 安装器（macOS / Linux） | — |
| 注释标记 | src/chrys/app/acp/server.py:333 | AIxCoding telemetry: desktop channel from the prompt _meta envelope, | telemetry |
| 非注释命中 | src/chrys/app/cli/serve.py:1121 | """Return the AIxCoding serve startup banner (pure ASCII, safe on GBK consoles).""" | — |
| 注释标记 | src/chrys/app/tui/app.py:960 | AIxCoding credential; never blocks or disturbs the session start. | — |
| 非注释命中 | src/chrys/app/tui/app.py:1024 | """Validate the stored AIxCoding credential at startup, silently.

        Offline is not a logout, a rejected credential self-cleans inside the
        check, and startup must never be disturbed: every outcome is swallowed.
        The indicator refresh afterwards re-reads the session rather than the
        check result — a network failure keeps the credential (stays signed
        in), a rejection has already cleared it (flips the chip to logged out).
        """ | — |
| 非注释命中 | src/chrys/app/tui/screens/main/commands.py:89 | "Log in with your AIxCoding account" | — |
| 非注释命中 | src/chrys/app/tui/screens/main/commands.py:314 | "Open the AIxCoding device-code login dialog.\n\n" | — |
| 非注释命中 | src/chrys/app/tui/screens/main/commands.py:327 | "Clear the stored AIxCoding credential for the current\n" | — |
| 注释标记 | src/chrys/app/tui/screens/main/config_actions.py:234 | AIxCoding customization: model profiles are centrally managed. | customization |
| 非注释命中 | src/chrys/app/tui/screens/main/screen.py:2245 | """Open the AIxCoding device-code login dialog (/login).""" | — |
| 非注释命中 | src/chrys/app/tui/screens/main/screen.py:2271 | """Clear the stored AIxCoding credential (/logout).""" | — |
| 非注释命中 | src/chrys/foundation/branding.py:7 | "AIxCoding" | — |
| 注释标记 | src/chrys/foundation/events/types.py:416 | AIxCoding telemetry: session workspace cwd (projectName/git/fileName basis). | telemetry |
| 注释标记 | src/chrys/foundation/events/types.py:488 | AIxCoding telemetry: session workspace cwd (projectName/git/fileName basis). | telemetry |
| 注释标记 | src/chrys/orchestration/engine/assembly.py:77 | AIxCoding telemetry: tool-detail/ai-code reporting on this bus (idempotent per bus). | telemetry |
| 注释标记 | src/chrys/orchestration/engine/run/active_injection.py:422 | AIxCoding telemetry: input-trigger report for a resolved slash skill reference. | telemetry |
| 注释标记 | src/chrys/orchestration/engine/run/runner.py:585 | AIxCoding telemetry: input-trigger report for a resolved slash skill reference. | telemetry |
| 注释标记 | src/chrys/service/agent_middleware/events/sub_agent_events.py:353 | AIxCoding telemetry: workspace cwd for projectName/git/fileName. | telemetry |
| 注释标记 | src/chrys/service/agent_middleware/events/sub_agent_events.py:411 | AIxCoding telemetry: workspace cwd for projectName/git/fileName. | telemetry |
| 注释标记 | src/chrys/service/agent_middleware/events/sub_agent_events.py:654 | AIxCoding telemetry: workspace cwd for projectName/git/fileName. | telemetry |
| 注释标记 | src/chrys/service/agent_middleware/events/sub_agent_events.py:906 | AIxCoding telemetry: workspace cwd for projectName/git/fileName. | telemetry |
| 注释标记 | src/chrys/service/agent_middleware/events/tool_events.py:398 | AIxCoding telemetry: provider call id keys the per-call registry. | telemetry |
| 注释标记 | src/chrys/service/agent_middleware/events/tool_events.py:401 | AIxCoding telemetry: workspace cwd for projectName/git/fileName. | telemetry |
| 注释标记 | src/chrys/service/agent_middleware/events/tool_events.py:698 | AIxCoding telemetry: provider call id keys the per-call registry. | telemetry |
| 注释标记 | src/chrys/service/agent_middleware/events/tool_events.py:705 | AIxCoding telemetry: workspace cwd for projectName/git/fileName. | telemetry |
| 非注释命中 | src/chrys/service/llm/clients.py:139 | """The AIxCoding login token for the ``token`` header, or "" when absent.

    An AIxCoding deployment authenticates its LLM traffic with the same
    credential the login flow stored and the model catalog sends — the gateway
    in front of the models rejects a request without it. Reading the session
    performs no network I/O (the same guarantee :func:`catalog._catalog_token`
    relies on), so an unauthenticated session simply sends no header.
    """ | — |
| 非注释命中 | src/chrys/service/llm/clients.py:165 | """Build default HTTP headers for LLM client requests.

    Includes chrys platform headers (client name, version, user agent,
    ``X-Session-ID``, ``Chrys-Session-Id``, optional parent-session headers,
    and ``Chrys-Model-Id``), merged with the profile's ``http_headers``
    (parsed from JSON). Profile headers take precedence on key conflicts
    except for Chrys-managed request metadata. Instrumented chat clients
    overwrite the model header per request with the final provider
    ``model`` value, and add the AIxCoding login ``token`` header at send
    time — a construction-time snapshot would pin the empty token of a
    session built before login (the engine does not rebuild on login).
    """ | — |
| 注释标记 | src/chrys/service/llm/clients.py:525 | AIxCoding telemetry: thread the session id + workspace cwd into the instrumented stack. | telemetry |
| 注释标记 | src/chrys/service/llm/instrumented.py:898 | AIxCoding telemetry: llm-call piggyback middleware (chrys/aixcoding/telemetry/llm_telemetry.py). | chrys/aixcoding/telemetry/llm_telemetry.py |
| 注释标记 | src/chrys/service/llm/instrumented.py:908 | AIxCoding telemetry: workspace_cwd is the projectName/git basis (source #6). | telemetry |
| 非注释命中 | src/chrys/service/profiles/agents/builtins/Code.yaml:7 | You are an expert coding assistant named "AIxCoding". You help users write, review, refactor, | — |
| 非注释命中 | src/chrys/service/profiles/agents/builtins/QA.yaml:7 | You are a knowledgeable Q&A assistant named "AIxCoding". You answer questions about code, | — |
| 非注释命中 | src/chrys/service/profiles/agents/schema.py:154 | """When True, also auto-load skills from ``~/.aixcoding/skills`` (the AIxCoding
    user skills directory shared with the AIxCoding desktop clients). Default True.""" | — |
| 非注释命中 | src/chrys/service/profiles/agents/schema.py:157 | """When True, also auto-load skills from ``<cwd>/.aixcoding/skills`` — the
    project-local AIxCoding skills directory under the current working directory.
    Reloaded automatically when the workspace cwd changes. Default True.""" | — |
| 非注释命中 | src/chrys/service/skills/adapter.py:225 | """Return the AIxCoding user directory at ``~/.aixcoding``.

    Shared with the AIxCoding desktop clients; callers append sub-directories
    (e.g. ``"skills"``).  Exposed as a module-level helper for the same
    monkeypatch/testing reasons as :func:`user_agents_dir`.
    """ | — |
| 非注释命中 | src/chrys/service/skills/adapter.py:254 | """Merge profile skill paths with the default user/project skills directories.

    Six auto-loaded locations (earlier wins on same-named skills):

    * ``~/.chrys/skills/`` — always included so Chrys-specific skills added
      later in a session can be discovered without an agent rebuild.
    * ``~/.aixcoding/skills/`` — included when
      ``config.auto_load_aixcoding_user_skills`` is True.  Shared with the
      AIxCoding desktop clients (default: True); takes precedence over
      ``~/.agents/skills/``.
    * ``~/.agents/skills/`` — included when ``config.auto_load_user_agents_skills``
      is True.  This is a shared cross-tool skills directory opt-in per
      profile (default: True).
    * ``<runtime.cwd>/.aixcoding/skills/`` — included when ``runtime`` is provided
      AND ``config.auto_load_aixcoding_cwd_skills`` is True.  Shared with the
      AIxCoding desktop clients (default: True); takes precedence over
      ``<runtime.cwd>/.agents/skills/``.
    * ``<runtime.cwd>/.agents/skills/`` — included when ``runtime`` is provided
      AND ``config.auto_load_cwd_agents_skills`` is True.  Reloaded
      automatically when the workspace cwd changes because the agent is rebuilt
      with a fresh ``SessionEnvironment``.
    """ | — |
| 非注释命中 | tests/app/aixcoding/test_update_detection.py:207 | "AIxCoding-999.0.0-arm64.zip" | — |
| 非注释命中 | tests/app/cli/test_run.py:1638 | "The device running AIxCoding doesn't seem to have a network connection. Check it first." | — |
| 非注释命中 | tests/app/tui/i18n/test_command_suggestions_i18n.py:153 | "    AIxCoding - AI-powered code assistant\n" | — |
| 非注释命中 | tests/app/tui/i18n/test_command_suggestions_i18n.py:156 | "    AIxCoding is a terminal-based AI assistant for code exploration,\n" | — |
| 非注释命中 | tests/app/tui/i18n/test_command_suggestions_i18n.py:162 | "  /exit         - Exit AIxCoding\n" | — |
| 非注释命中 | tests/app/tui/i18n/test_command_suggestions_i18n.py:167 | "  /login        - Log in with your AIxCoding account\n" | — |
| 非注释命中 | tests/app/tui/i18n/test_command_suggestions_i18n.py:203 | "    Start a completely new AIxCoding session.\n" | — |
| 非注释命中 | tests/app/tui/i18n/test_command_suggestions_i18n.py:222 | "开始一个全新的 AIxCoding 会话。" | — |
| 非注释命中 | tests/app/tui/i18n/test_modal_screens.py:235 | "Exit AIxCoding and return to the terminal." | — |
| 非注释命中 | tests/app/tui/i18n/test_modal_screens.py:243 | "退出 AIxCoding 并返回终端。" | — |
| 注释标记 | tests/app/tui/screens/main/test_config_actions.py:180 | AIxCoding customization: switching profiles stays enabled; only editing | customization |
| 注释标记 | tests/app/tui/screens/main/test_config_actions.py:538 | AIxCoding customization: the config screen is read-only even while idle. | customization |
| 非注释命中 | tests/app/tui/screens/test_dialog_controllers.py:581 | "MCP server 'github' exposes permitted tool name collision with a reserved AIxCoding tool: read_file" | — |
| 非注释命中 | tests/app/tui/screens/test_mcp_config.py:1591 | "a reserved AIxCoding tool" | — |
| 非注释命中 | tests/app/tui/screens/test_rollback_modal.py:1901 | "Another AIxCoding session has an active command in this workspace; its changes may not be attributed yet." | — |
| 非注释命中 | tests/service/llm/test_aixcoding_project_telemetry.py:3 | """Workspace path attribution in AIxCoding model telemetry.""" | — |
| 注释标记 | tests/service/llm/test_openai_chat_stream_assembly.py:181 | AIxCoding telemetry: mirrors source #6. | telemetry |
| 非注释命中 | tests/service/mcp/test_progressive.py:261 | r"reserved AIxCoding tool.*read_file" | — |
| 非注释命中 | tests/service/mcp/test_progressive.py:315 | r"reserved AIxCoding tool.*read_file" | — |
| 非注释命中 | tests/service/mcp/test_progressive.py:377 | r"reserved AIxCoding tool.*read_file" | — |

## 定制资产清单（ROADMAP §4 盘点输入）

- `aixcoding/__init__.py`
- `aixcoding/auth/__init__.py`
- `aixcoding/auth/client.py`
- `aixcoding/auth/crypto.py`
- `aixcoding/auth/delegation.py`
- `aixcoding/auth/environments.py`
- `aixcoding/auth/errors.py`
- `aixcoding/auth/session.py`
- `aixcoding/auth/storage.py`
- `aixcoding/auth/types.py`
- `aixcoding/doc/aixocding_cli_发布Releases操作指南.md`
- `aixcoding/doc/LLM模型对接获取说明.md`
- `aixcoding/doc/TUI登录执行计划.md`
- `aixcoding/doc/TUI登录改造方案.md`
- `aixcoding/doc/启动与登录人工验证指南.md`
- `aixcoding/doc/桌面端集成登录开发计划.md`
- `aixcoding/doc/桌面端集成登录方案.md`
- `aixcoding/doc/测试所需文档/安全护栏/MANUAL_TESTS.md`
- `aixcoding/doc/项目索引.md`
- `aixcoding/docs/telemetry/iCode-数据上报直改源码方案.md`
- `aixcoding/docs/telemetry/plan.md`
- `aixcoding/docs/telemetry/埋点技术总结.md`
- `aixcoding/docs/telemetry/埋点测试用例.md`
- `aixcoding/docs/telemetry/实现方案/01-llm-call搭车上报实现.md`
- `aixcoding/docs/telemetry/实现方案/02-tool-detail上报实现.md`
- `aixcoding/docs/telemetry/实现方案/03-ai-code上报实现.md`
- `aixcoding/docs/telemetry/观测与调试/01-llm-call搭车数据观察.md`
- `aixcoding/docs/telemetry/观测与调试/02-独立通道数据观察.md`
- `aixcoding/README.md`
- `aixcoding/telemetry-mock/faults.py`
- `aixcoding/telemetry-mock/README.md`
- `aixcoding/telemetry-mock/server.py`
- `aixcoding/telemetry-mock/store.py`
- `aixcoding/tests/conftest.py`
- `aixcoding/tests/test_ai_code.py`
- `aixcoding/tests/test_infra.py`
- `aixcoding/tests/test_llm_telemetry.py`
- `aixcoding/tests/test_telemetry_mock.py`
- `aixcoding/tests/test_tool_detail.py`
- `aixcoding/tui/__init__.py`
- `aixcoding/tui/login.py`
- `aixcoding/tui/login.tcss`
- `src/chrys/aixcoding/__init__.py`
- `src/chrys/aixcoding/config.py`
- `src/chrys/aixcoding/context.py`
- `src/chrys/aixcoding/git_info.py`
- `src/chrys/aixcoding/http.py`
- `src/chrys/aixcoding/telemetry/__init__.py`
- `src/chrys/aixcoding/telemetry/acp_meta.py`
- `src/chrys/aixcoding/telemetry/llm_telemetry.py`
- `src/chrys/aixcoding/telemetry/outcome.py`
- `src/chrys/aixcoding/telemetry/reporters/__init__.py`
- `src/chrys/aixcoding/telemetry/reporters/ai_code.py`
- `src/chrys/aixcoding/telemetry/reporters/tool_detail.py`
- `src/chrys/aixcoding/telemetry/subscriber.py`
- `src/chrys/aixcoding/telemetry/types.py`
- `src/chrys/aixcoding/update_detection.py`
