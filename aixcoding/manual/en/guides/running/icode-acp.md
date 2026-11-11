# Run AIxCoding-CLI in a browser

`aixcoding-cli serve` displays the AIxCoding-CLI terminal user interface (TUI) in a browser, supporting conversations, tool-call approval, and editing configuration.

Startup options can be viewed with `aixcoding-cli serve --help`.

This article calls the device running the browser the "local machine" and the machine running the AIxCoding-CLI service the "server". The server can be the local machine or a remote server accessed over the network.

Before starting, the server should have AIxCoding-CLI installed. The browser provides the operating interface, while AIxCoding-CLI uses the server's configuration to read, modify files, and execute commands with the permissions of the system user that started the service. All of these operations happen on the server; all visitors share the server's configuration, files, and sessions, and do not get separate accounts.

After the first sign-in you can start chatting. Keep the page connected while a task is running; closing or refreshing the page, or losing the connection, interrupts the task running in that page.

Depending on where the server is and how you access it, see the matching section:

| Scenario | Section |
| --- | --- |
| Run and access on the local machine | [Start AIxCoding-CLI on the local machine](#1-start-aixcoding-cli-on-the-local-machine) |
| Access AIxCoding-CLI on a remote server over SSH | [Access remote AIxCoding-CLI from the local machine](#2-access-remote-aixcoding-cli-from-the-local-machine) |
| Access through a fixed HTTPS domain | [Access through a fixed HTTPS domain](#3-access-through-a-fixed-https-domain) |

## 1. Start AIxCoding-CLI on the local machine

### Start the service

In a terminal on the local machine, enter the working directory, then start the service:

```shell
aixcoding-cli serve --auth-required
```

Enter and confirm the browser sign-in password as prompted in the terminal; the password cannot be empty. `--auth-required` enables password sign-in; when no authentication option is specified, the service is accessible without signing in.

The service is up once the terminal shows `Serving AIxCoding TUI on ...` and the access address.

### Sign in from the browser

Open `http://localhost:7777` in the browser on the local machine and enter the password set at startup. `localhost` means the local machine, and `7777` is the service port.

The AIxCoding-CLI interface should appear after sign-in. Send "hello" and check that you get a reply.

The directory where the service started is the initial working directory. Click the directory path on the right side of the bottom border of the chat area to switch the working directory. `aixcoding-cli serve` does not accept the TUI's `--workdir`, `--agent`, `--model`, or `--session` options; switching agents and models and restoring sessions are all done in the page.

### Stop using it

Keep the service terminal running while in use. When you are done, press `Ctrl+C` in that terminal to stop the service.

Every time a page is opened and connected, the server starts a separate AIxCoding-CLI instance. Conversations are saved on the server; after reopening the page, saved sessions can be restored.

The browser sign-in state is valid for 12 hours, and you must sign in again after the service restarts. After 5 consecutive wrong passwords from the same client address, that address is locked, and only restarting the service unlocks it. Restarting disconnects all connected pages.

## 2. Access remote AIxCoding-CLI from the local machine

If you can already sign in to a remote server over SSH, you can build an SSH tunnel that forwards the local browser's connection to the remote AIxCoding-CLI through an encrypted channel, with no domain setup required. The following steps use two terminal windows on the local machine.

### In the first terminal, sign in to the remote server and start AIxCoding-CLI

```shell
ssh <user>@<server>
```

Replace `<user>` with the server's SSH username and `<server>` with its IP address or hostname, and sign in with an SSH key or a password.

After signing in, commands run in that terminal execute on the remote server. Enter the remote working directory, then start AIxCoding-CLI:

```shell
aixcoding-cli serve --auth-required
```

Set the browser sign-in password, confirm the terminal shows the service address, and keep the terminal running.

### In the second terminal, build the tunnel

Open a second terminal on the local machine and run the following command to build the tunnel:

```shell
ssh -N -o ExitOnForwardFailure=yes -L 7777:localhost:7777 <user>@<server>
```

The username and server address are the same as in the previous step. After SSH authentication, the terminal usually produces no further output and does not return to a prompt; keep it running.

If SSH sign-in requires a custom port or key, add the same connection options to both commands.

### Access from the browser on the local machine

Visit `http://localhost:7777` and enter the AIxCoding-CLI browser sign-in password set in the first step.

After the browser visits `localhost:7777` on the local machine, the SSH tunnel forwards the connection to the remote AIxCoding-CLI. Therefore the browser address in this example must stay `localhost`; do not change it to the remote IP.

When you are done, press `Ctrl+C` in the first terminal to stop AIxCoding-CLI, and press `Ctrl+C` in the second terminal to close the SSH tunnel.

## 3. Access through a fixed HTTPS domain

Access via a fixed address such as `https://aixcoding-cli.example.com` requires a reverse proxy: the browser establishes an encrypted connection with the proxy, which then forwards requests to AIxCoding-CLI.

This section applies to environments that already have an HTTPS proxy. The domain and certificate are configured on the proxy side; AIxCoding-CLI itself does not provide HTTPS service.

### Start AIxCoding-CLI

The following example assumes the proxy and AIxCoding-CLI run on the same server. In a server terminal, enter the working directory, replace `aixcoding-cli.example.com` with the actual domain, and run:

```shell
aixcoding-cli serve --host 127.0.0.1 --port 7777 --public-url https://aixcoding-cli.example.com --auth-required
```

Set the browser sign-in password and keep the terminal running. This command makes AIxCoding-CLI accept connections only from the same server, while the browser reaches the address given by `--public-url` through the proxy.

### Configure the proxy connection

The proxy must meet these requirements:

- Forward requests for the domain to `http://127.0.0.1:7777`.
- Preserve the original `Host` header from browser requests so AIxCoding-CLI can verify the visited domain.
- Support WebSocket connections so the page can continuously send input and receive replies.

By default, AIxCoding-CLI counts wrong password attempts against the proxy address, and multiple visitors may share the failure counter. If the proxy is trusted and correctly rewrites `X-Forwarded-For` (the client address request header), add `--auth-trust-forwarded-for` to the AIxCoding-CLI start command to count attempts by the visitor address provided by the proxy instead.

### Verify access

Replace `aixcoding-cli.example.com` with the actual domain and open the matching HTTPS address in a browser on the local machine, for example `https://aixcoding-cli.example.com`, without adding AIxCoding-CLI's port `:7777`. The browser should show the AIxCoding-CLI sign-in page without certificate warnings. After signing in, send a message and confirm you get a reply.

The connection from the browser to the proxy is encrypted; the proxy to AIxCoding-CLI still uses plain HTTP inside the server.

### Other deployment layouts

When the proxy runs on another server or in a separate container, `127.0.0.1` may not reach AIxCoding-CLI. After changing the listening address, restrict the backend port to trusted proxies only via firewall or container network rules, so the HTTPS proxy cannot be bypassed with a direct connection. Setting an HTTPS `--public-url` does not encrypt the proxy-to-AIxCoding-CLI HTTP connection.

## 4. Read the password from a file or environment variable

When the password cannot be entered interactively in a terminal, provide it via a file or an environment variable. Both methods automatically enable authentication, so `--auth-required` is not needed, and they cannot be combined.

### Use a password file

On the server, prepare a UTF-8 plain-text file and write the sign-in password into it. The password cannot be empty; trailing newlines in the file are ignored.

Enter the working directory and start with the password file:

```shell
aixcoding-cli serve --auth-password-file "<password-file>"
```

Replace `<password-file>` with the server-side path to the password file. Startup no longer prompts for the password, and the browser signs in with the password from the file.

### Use an environment variable

On the server, set an environment variable for the AIxCoding-CLI startup process, for example `CHRYS_SERVE_PASSWORD`, with a non-empty sign-in password as its value. Then run:

```shell
aixcoding-cli serve --auth-password-env CHRYS_SERVE_PASSWORD
```

The argument of `--auth-password-env` is the environment variable name. Startup no longer prompts for the password, and the browser signs in with that variable's value.

## 5. Access directly over the LAN by IP

Accessing directly over the LAN by IP transmits the sign-in password and conversation content in plain text, and is only suitable for network environments that explicitly accept this risk.

On the server, enter the working directory, replace `192.168.1.20` with the server's actual LAN IP, and run:

```shell
aixcoding-cli serve --host 0.0.0.0 --public-url http://192.168.1.20:7777 --auth-required --allow-insecure-auth
```

`--host 0.0.0.0` lets other devices connect to AIxCoding-CLI. `--allow-insecure-auth` explicitly allows plain-text password sign-in over the network; without it, AIxCoding-CLI refuses to start with this configuration.

In a browser on the local machine, visit using the server's actual LAN IP, for example `http://192.168.1.20:7777`, and sign in. If it cannot connect, check that the local machine and the server can reach each other and that the server firewall allows clients to reach TCP port `7777`.

## Finishing interactions in the client

When a task fails, the error the client shows is the failure itself — for example, an out-of-balance model service account shows `Error code: 402 - Insufficient Balance` instead of a vague "Internal error". Clients that read AIxCoding-CLI error details can also tell you the failure category (such as insufficient balance, a wrong API key, or rate limiting) and whether a retry may succeed. When a sub-agent fails, the task continues: the agent receives the error and decides what to do next. Only clients that can display the failure and let you click "Retry" or "Abort" pause the sub-agent like the TUI and wait for your choice.

If the client offers a full reload, changes to files take effect without restarting the service: AIxCoding-CLI re-reads settings, agent profiles, and models, memory, skills, and hooks for the current session, and reconnects the session's MCP servers. Unless you have selected a model for that session or set `CHRYS_MODEL_PROFILE` when starting the service, the session switches to the model in the settings file; if the selected model was deleted, the session falls back to the default model, and the reload result says so. Sessions created afterwards also use the model in the settings file, unless the client has set a service default model: sessions without a separately selected model switch to the client's default model. Other open sessions keep their own models and connections; if a model used by one of them was deleted, it may switch to another model after its settings change, working directory changes, or its agent is switched, or it may have no usable model until you pick one for it or run a full reload in that session. New sessions still use the agent and approval mode from service startup; themes and shortcuts belong to the TUI and are not changed by a full reload. If the session's agent file was deleted, the session falls back to the default agent, and the reload result says so. If the reload fails, the session keeps running with its previous content.

## 7. Troubleshooting

### `aixcoding-cli` command not found

Confirm AIxCoding-CLI is installed on the server and its installation directory is in `PATH`. If you just installed it, reopen a terminal and verify with:

```shell
aixcoding-cli --version
```

### Local startup says the port is in use

Pick a free port with `--port` and use the same port in the browser address. For example, if `8888` is free:

```shell
aixcoding-cli serve --port 8888 --auth-required
```

Then visit `http://localhost:8888`.

### The SSH tunnel says the local port is in use

Change the first port after `-L` to a free local port and keep the last port as the remote AIxCoding-CLI listening port. For example, if remote AIxCoding-CLI uses `7777` and local `8888` is free, run on the local machine:

```shell
ssh -N -o ExitOnForwardFailure=yes -L 8888:localhost:7777 <user>@<server>
```

Replace `<user>` and `<server>` with the SSH username and server address. Also restart AIxCoding-CLI on the remote server with the new browser address:

```shell
aixcoding-cli serve --public-url http://localhost:8888 --auth-required
```

Then visit `http://localhost:8888` on the local machine.

### The browser says the site cannot be reached

First confirm the AIxCoding-CLI service is still running, then check the browser address matches the method in use: `localhost` for the local or SSH examples, the configured domain for HTTPS access, or the server IP for direct LAN access.

If the address is correct but still unreachable, the SSH method also needs the tunnel checked, and the HTTPS method needs DNS resolution and the proxy service checked.

### The HTTPS page shows a certificate warning

Confirm the browser uses the configured domain, and check whether the proxy certificate is expired, matches the domain, and whether the browser trusts its issuer.

### The HTTPS page returns `502`

Check that AIxCoding-CLI is still running, that the address and port the proxy forwards to match AIxCoding-CLI's listening configuration, and that the proxy can reach that address; the proxy log shows the specific cause.

### The page returns `421`

Use the domain or IP and port shown when AIxCoding-CLI started. When accessing through a proxy, check whether the proxy preserves the original `Host` header.

### The WebSocket connection returns `403`

Check that the browser address matches the address given by `--public-url`, including the protocol (`http` or `https`), domain, and port. AIxCoding-CLI rejects connections whose origin does not match.

### Sign-in returns `403`

If it reports `Invalid login token`, reopen the sign-in page and enter the password again; if it reports `Invalid login origin`, check that the browser address matches the access address configured for AIxCoding-CLI.

### Too many password attempts reported

That client address is locked. First confirm no page is running a task, then press `Ctrl+C` in the AIxCoding-CLI terminal and restart. When multiple visitors behind a proxy are locked at once, check the HTTPS section for whether `--auth-trust-forwarded-for` applies.

### The original conversation is gone after a refresh or disconnect

After the page reconnects, the server starts a new AIxCoding-CLI instance. You can restore the conversation by following the steps in "restore saved sessions", but interrupted tasks do not resume automatically.

### Copying fails

If a copy dialog appears, click **Copy**. If it still fails, select the text in the dialog and copy it manually with the browser's copy shortcut.

---
