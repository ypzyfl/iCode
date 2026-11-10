# Signing in and sign-in state

This section describes AIxCoding-CLI account sign-in: when you need to sign in, how to sign in with `/login`, how sign-in state is stored, and how to sign out.

**You must sign in before using AIxCoding-CLI; after signing in, you can use the model assigned by the administrator.** When you open AIxCoding-CLI, the top bar on the right shows a sign-in badge (a gray ● "Not signed in" badge when you are not signed in). If the top bar shows no sign-in indicator at all, you are running an old version that does not support sign-in. [Install the new version](./getting-started.md#1-install-aixcoding-cli) first, then follow the steps in this section to sign in.

## 1. How to sign in

Type `/login` in the input box, or click the gray ● "Not signed in" badge at the top right of the top bar. Either way opens the sign-in dialog.

1. The dialog shows a user code and automatically opens a verification page in the browser.
2. On the browser page, check your account information and confirm the authorization.
3. Return to the terminal; it reports that you are signed in, and a green ● badge appears in the top bar.

Signing in fails if the dialog countdown ends before the authorization completes; canceling the dialog does not save anything.

## 2. How sign-in state is stored

- Credentials are stored on this machine with operating-system-level encryption (Windows: `%APPDATA%\chrys\users\`; Linux / macOS: `~/.chrys/users/`).
- The next startup performs a silent validation automatically; even when started offline, the top bar still shows you as signed in as long as the local credentials remain.
- Top-bar badge: green when signed in, gray ● "Not signed in" when not; hover over the badge to see details.

## 3. What to do when sign-in expires

When the top-bar badge turns gray (not signed in), run `/login` again; any conversation in progress is not interrupted.

## 4. Signing out

Type `/logout` to clear the credentials saved on this machine and sign out. Running this command while already signed out is safe; it only reports the current state.
