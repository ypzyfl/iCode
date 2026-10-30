# Configure AIxCoding-CLI settings

AIxCoding-CLI settings control the interface appearance, default agent, sessions, tools, notifications, and some security options. This guide explains how to configure these basics in the terminal user interface (TUI) and check when changes take effect.

To edit `settings.yaml` directly or configure settings through environment variables, see the [AIxCoding-CLI settings file reference](../../reference/settings.md) for file locations, settings keys, and source precedence.

## 1. Settings dialog

### 1. Open the Settings dialog

The Settings dialog can only be opened while the agent is idle.

Open **Settings** in any of these ways:

- Press **F10**.
- Click `f10 Settings` at the bottom of the interface.
- Type `/settings` in the input field, press **Space** or **Enter** to show the tab list, then select a tab.

You can also open a tab directly with `/settings <tab>`:

| Tab | `<tab>` | Main settings |
| --- | --- | --- |
| General | `general` | Appearance and input |
| Models & Agents | `models` | Default agent, model roles, and request retries |
| Security | `security` | Approval, project trust, diagnostics, and telemetry |
| Sessions | `sessions` | Session titles, storage, and rollback |
| Tools | `tools` | File search, web tools, agent questions, tool detail display, and workspace notices |
| Notifications | `notifications` | Notification toggles, delivery methods, and events |

For example, enter `/settings security` to open the **Security** tab directly.

### 2. Save changes and check when they take effect

Changes are saved automatically as you make them. Press **Enter** to submit a change in a text field; it is also submitted when you move to another setting or close the dialog. Closing the dialog with **Esc** does not undo changes already submitted.

The status message at the bottom right of the Settings dialog explains when changes take effect. If changes have different pending application times, the corresponding messages appear together.

| Status message | When changes take effect |
| --- | --- |
| "Changes are saved as you make them" | Changes are saved, with no changes waiting for the dialog to close or a restart |
| "Changes apply on close (reload)" | After you press **Esc** to close **Settings** |
| "Changes apply when the current turn ends" | Replaces "Changes apply on close (reload)" while a turn or workflow is running; changes apply after you close **Settings** and the run ends |
| A message showing how many changes apply after restart | Changes are saved, but you must quit and restart AIxCoding-CLI for them to take effect |

The "Takes effect" column in the following tables describes each setting's usual behavior.

## 2. Settings

### 1. General

#### Appearance

| Setting | Effect and notes | Takes effect |
| --- | --- | --- |
| Theme | Changes the TUI theme. To adjust colors or create a custom theme, see [Customize themes](themes.md). | Immediately |
| UI Language | Changes only AIxCoding-CLI interface text, not conversation content, the model's output language, or existing records. You can also switch the interface language with `/language`. | Immediately |

#### Input

| Setting | Effect and notes | Takes effect |
| --- | --- | --- |
| Save prompt history | Saves submitted input across sessions for reuse. When no other dialog covers the main screen, press **Ctrl+R** to open the prompt history list above the input field. Click an entry, or select it with the up and down arrow keys and press **Enter**, to copy the prompt into the input field. The history file, `prompt_history.jsonl`, is stored in `~/.chrys/` on macOS and Linux, or `%APPDATA%\chrys\` on Windows. Turning this setting off does not delete the file; AIxCoding-CLI stops reading it, and **Ctrl+R** shows "No results". Re-enable the setting and restart AIxCoding-CLI to read the file's entries again. To clear the history, delete the history file; deletion cannot be undone. | After restart |

### 2. Models & Agents

This tab selects existing agents or models; it does not edit them. For agent operations, see [Configure agents](./agents.md).

#### Agent

| Setting | Effect and notes | Takes effect |
| --- | --- | --- |
| Default agent | Determines only the default agent for the next TUI launch; it does not affect the current session. | Saved immediately; applies at the next launch |

#### Model roles

| Setting | Effect and notes | Takes effect |
| --- | --- | --- |
| Session title model | Defaults to "Use active model". Used only when [Auto-generate session titles](None#4-sessions) is enabled. | On close |
| Approval judge model | Defaults to "Use active model". Used only in [automatic approval mode](./approval.md#1-understand-the-three-approval-modes). | On close |
| Buddy model | Defaults to "Use active model". Used for the Buddy companion feature. | On close |

#### LLM

| Setting | Effect and notes | Takes effect |
| --- | --- | --- |
| Max transient retries | Sets the maximum number of automatic retries for errors that may resolve shortly, such as temporary network interruptions, request timeouts, temporary model service unavailability, or server rate limits. It does not retry problems that waiting cannot resolve, such as model or request parameter errors. A higher limit gives temporary failures more chances to recover; if retries keep failing, it also increases the wait and the number of model requests before the final failure. Leave blank to use the TUI default; set to `0` to disable automatic retries. | On close |

### 3. Security

#### Approval

| Setting | Effect and notes | Takes effect |
| --- | --- | --- |
| Default approval mode | Sets the default approval mode for the next AIxCoding-CLI launch; it does not affect the current session. Only `manual` and `auto` are offered; to bypass approval in the current session, use `/approval bypass`. For switching the current session's mode and the differences between modes, see [Configure approval modes](./approval.md). | Saved immediately; applies at the next launch |

#### Project trust

| Setting | Effect and notes | Takes effect |
| --- | --- | --- |
| Load project settings | Reads `.chrys/settings.yaml` in the current working directory and applies its project settings, such as request retries, automatic session titles, and working directory notices. See [Project-level settings](../../reference/settings.md#5-project-level-settings) for allowed keys and override restrictions. | On close |
| Load project hooks | Controls whether AIxCoding-CLI loads hooks from `.chrys/hooks` in the current working directory; it does not affect user-level hooks. To create and validate hooks, see [Configure and write hooks](../extensions/hooks.md). For the complete configuration fields, see the [Hooks configuration reference](../../reference/hooks.md). | On close |

#### Diagnostics

| Setting | Effect and notes | Takes effect |
| --- | --- | --- |
| Capture raw HTTP traffic | Records model requests and responses for troubleshooting. **Logs may contain API keys, complete prompts, and model responses in plain text.** Enable this only while troubleshooting and protect the log files. When finished, turn it off promptly and restart AIxCoding-CLI. The log file, `llm_raw_http.jsonl`, is stored in the current session folder; see [Find the session ID and storage location](../daily-use/sessions.md#5-find-the-session-id-and-storage-location). | After restart |

### 4. Sessions

#### Titles

| Setting | Effect and notes | Takes effect |
| --- | --- | --- |
| Auto-generate session titles | Makes additional model requests to generate titles based on the conversation. **Once you set a session title manually, AIxCoding-CLI stops updating that session's title automatically.** To set or clear a manual title, see [Change a session title](../daily-use/sessions.md#2-change-the-session-title). | On close |

#### Location

| Setting | Effect and notes | Takes effect |
| --- | --- | --- |
| Session storage root | Determines where AIxCoding-CLI saves sessions. Leave blank to use the default location; sessions are stored in the root's `sessions` subdirectory. "In use" shows the `sessions` directory used by the current launch. After changing the root, restart AIxCoding-CLI to use the new location; until then, sessions continue to be saved in the directory shown under "In use". **After restart, new sessions are saved in the new directory, but existing session files are not moved automatically.** To continue using existing sessions at the new location, see [Migrate session storage](../daily-use/sessions.md#6-migrate-session-storage). | After restart |

#### Rollback

| Setting | Effect and notes | Takes effect |
| --- | --- | --- |
| Rollback snapshots to keep | Sets the maximum number of rollback snapshots kept per session. AIxCoding-CLI creates a snapshot before it starts processing each newly submitted prompt; older snapshots are deleted automatically when the limit is exceeded. Snapshots are stored in the session folder's `snapshots` subdirectory. Keeping more snapshots lets `/rollback` return to more earlier session states, but uses more disk space. | On close |

### 5. Tools

#### File search

| Setting | Effect and notes | Takes effect |
| --- | --- | --- |
| Respect .gitignore | Applies Git ignore rules to grep and glob searches. When off, hidden paths are still skipped, and other ignore files such as `.ignore` still apply. | On close |

#### Web search

These settings apply to agents that include the web tools, which are off by default. See [Configure web tools](./web-tools.md). An agent profile that sets its own mode, result count, or timeout overrides these values for that agent. Project settings cannot change them.

| Setting | Effect and notes | Takes effect |
| --- | --- | --- |
| Web search mode | `auto` (default) lets agents that include web search use it. An agent that configures no search provider sends its queries to Exa's public search endpoint, a third-party service; see [Where web requests go](./web-tools.md#2-where-web-requests-go). `off` turns web search off. An agent profile that sets its own mode uses that mode instead. | On close |
| Results per web search | Number of results a search returns when the agent does not ask for a number, from 1 to 20. The default is 8. | On close |
| Web fetch mode | `on` (default) lets agents that include web fetch read pages by URL. `off` turns web fetch off. An agent profile that sets its own mode uses that mode instead. | On close |
| Web proxy URL | An `http://` or `https://` proxy used only by web tools, without credentials or a path. Leave blank to connect directly. Web tools ignore proxy environment variables such as `HTTP_PROXY`. | On close |
| Web proxy DNS | Where host names are resolved when a proxy is set. `local` (default) resolves them on this device and checks every address before connecting. `remote` sends the host name to the proxy, as fake-IP proxies require, and leaves blocking private addresses to the proxy; see [Use a fake-IP proxy](./web-tools.md#1-use-a-fake-ip-proxy). It has no effect without a web proxy URL. | On close |
| Custom search endpoints | A JSON array of grants for custom search endpoints used in agent profiles, each written as `{"url": "...", "credential_env_names": ["..."]}`. | On close |
| Web search private-network origins | A JSON array of origins that web search may reach even though they resolve to private addresses, such as `["http://127.0.0.1:8080"]` for a local SearXNG. | On close |
| Web search plain-HTTP origins | A JSON array of origins that web search may reach over plain `http://`. | On close |

Values are checked with the same rules the web tools use before they are saved, and a rejected value says what is wrong. Clear a list field to empty the list. The web search timeout, the web fetch timeout and token budget, and the web fetch origin lists are not shown in the dialog; set them in `settings.yaml` (see [Web tools](../../reference/settings.md#6-web-tools)).

#### Ask user

| Setting | Effect and notes | Takes effect |
| --- | --- | --- |
| Show questions in the chat | When enabled, the agent's questions appear directly in the conversation. When disabled, they appear in a popup. | On close |
| Ask-user timeout (seconds) | Sets how long AIxCoding-CLI waits for an answer. When left blank, it uses the default value shown in the TUI. If no answer arrives before the timeout, AIxCoding-CLI returns a timeout result to the agent. Set to `0` to wait until an answer arrives or the task is interrupted. | On close |

#### Display

| Setting | Effect and notes | Takes effect |
| --- | --- | --- |
| Expand tool details by default | When enabled, new tool groups are expanded by default. When disabled, they are collapsed and show only a summary and the current operation. You can click a tool group at any time to expand its details. | Immediately |

#### Workspace notice

| Setting | Effect and notes | Takes effect |
| --- | --- | --- |
| Workspace change notices | When processing a newly submitted prompt, AIxCoding-CLI gives the agent a summary of working directory file changes since the previous prompt was submitted. This includes changes made by the current session's agent and its sub-agents, as well as changes made manually, by other programs, or by other AIxCoding-CLI sessions. | On close |

### 6. Notifications

#### General

| Setting | Effect and notes | Takes effect |
| --- | --- | --- |
| Enable Notifications | The master switch for event notifications. When disabled, no desktop popups or sounds are sent, but delivery and event selections are preserved and still apply when notifications are re-enabled. | Immediately |

#### Delivery

| Setting | Effect and notes | Takes effect |
| --- | --- | --- |
| Desktop popup, Sound | Can be enabled separately. If both are disabled, no notifications are delivered, even when the master switch and event switches are enabled. | Immediately |
| Suppress while AIxCoding-CLI is focused | Prevents desktop popups and sounds while AIxCoding-CLI is in the foreground. | Immediately |
| Test | Sends a test notification using the current delivery settings, regardless of the master switch, event switches, or focus state. It only checks whether desktop popups and sound work; enable at least one of "Desktop popup" or "Sound" before testing. | Immediately |

#### Events

| Setting | Effect and notes | Takes effect |
| --- | --- | --- |
| Approval required | Controls whether a notification is triggered when approval is required. | Immediately |
| Agent needs input | Controls whether a notification is triggered when the agent needs input. | Immediately |
| Agent finished | Controls whether a notification is triggered when the agent finishes a task. | Immediately |
| Agent error | Controls whether a notification is triggered when the agent encounters an error. | Immediately |
