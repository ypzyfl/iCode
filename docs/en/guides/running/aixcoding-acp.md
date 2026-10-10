# Use AIxCoding ACP server

Editors and development tools that support the Agent Client Protocol (ACP) can connect to AIxCoding to use AIxCoding agents in the client. The ACP client provides the interface, while AIxCoding communicates with it over standard input and output (stdio), runs agents, executes tools, and saves sessions.

Before you begin, install AIxCoding and configure at least one model. For preparation steps, see [Getting started with AIxCoding](../../start/getting-started.md) and [Configure models](../configuration/models.md).

## Connect to AIxCoding

In the ACP client's "Add agent" or similar settings, enter the following:

| Field | Value |
| --- | --- |
| Executable | `aixcoding-cli` |
| Arguments | `acp` |

This is equivalent to the client starting:

```shell
aixcoding-cli acp
```

If the client provides only a single launch command field, enter the full command, `aixcoding-cli acp`.

After saving the configuration, verify the connection:

1. Start or connect to AIxCoding in the client.
2. Create a session and send a message.
3. Confirm that the client displays a reply from AIxCoding. A reply means the connection is configured successfully.

## Configure startup options

`aixcoding-cli acp` supports the following startup options. If the client has separate executable and arguments fields, append these options after `acp`.

| Option | Default | Purpose |
| --- | --- | --- |
| `-a`, `--agent <agent>` | `Code` | Specify the built-in or custom agent for new sessions, by name, display name, or ID. Restored sessions keep the agent they were saved with. To create a custom agent, see [Configure agents](../configuration/agents.md). |
| `--approval <mode>` | `manual` | Set the initial approval mode for every session this ACP server creates or restores: `manual`, `auto`, or `bypass`. The `bypass` approval mode skips approval and executes tool calls directly; use it with care. For the rules of each mode, see [Configure approval modes](../configuration/approval.md). |
| `-C`, `--workdir <directory>` | None | Provide a default working directory for sessions where the client does not send one. |
| `--ask-user-timeout <seconds>` | No time limit | Limit how long to wait for the client to answer an agent's question. Omit this option or set it to `0` or a negative value to wait without a time limit. |

## Working directories and sessions

When creating or restoring a session, the client can pass the project's working directory to AIxCoding. The directory supplied by the client must be an existing absolute path. If the client does not provide a working directory, AIxCoding uses the directory specified by `--workdir <project-directory>`. If both are provided, the client's working directory takes precedence.

AIxCoding checks `--workdir` at startup. The specified directory must exist even if the client will later provide a working directory; otherwise, AIxCoding cannot start.

Session data is saved in AIxCoding's session storage directory, rather than the working directory. To find the actual location, see [Find the session ID and storage location](../daily-use/sessions.md#find-the-session-id-and-storage-location). AIxCoding records the working directory when a session is created. Listing sessions through an ACP client shows only sessions that match the current working directory. AIxCoding refuses to restore a session if the working directory does not match.

Sessions used through an ACP client also appear in the TUI's "Chat Sessions" window once you check "ACP" there. See [Resume an existing session](../daily-use/sessions.md#resume-an-existing-session).

## Interact through the client

AIxCoding sends agent replies and tool call status to the client. When the client cancels a task, AIxCoding interrupts the current task.

If the client supports session management, a closed session can still be restored in the same working directory. Deleting a session removes the session record saved by AIxCoding, and the session can no longer be restored in AIxCoding.

To use the question feature through an ACP client, the client must support AIxCoding's `_chrys/request_input` extension request (shown as `chrys/request_input` in ACP SDKs that add the underscore prefix automatically). AIxCoding uses this request to send the agent's questions to the client and receive the user's answers; a client that does not support it cannot complete tasks that require user answers. Use `--ask-user-timeout` to limit how long AIxCoding waits for an answer.

If the client supports switching approval modes or models, it can change the corresponding settings for the current session. These switches, like the initial mode set with `--approval`, are not written to AIxCoding's local configuration. If the client uses AIxCoding's extension requests to change settings or agent and model profiles, however, those changes are written to AIxCoding's local configuration. The next time the ACP server starts, the initial approval mode still comes only from `--approval`; other initial settings are determined by the local configuration and the startup arguments for that launch. Model profiles and available agents remain managed through AIxCoding's local configuration.
