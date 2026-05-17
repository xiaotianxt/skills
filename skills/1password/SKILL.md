---
name: 1password
description: "Use when Codex needs to work with 1Password or the `op` CLI: reading a specific secret reference, injecting API keys or credentials into local commands, using `op run` or `op inject`, checking 1Password CLI auth state, handling `API_CREDENTIAL` items, creating or updating 1Password items, or deciding how to keep secrets out of code, logs, shell history, issues, PRs, and final responses."
---

# 1Password

Use the local 1Password CLI only for scoped 1Password work. For local machine-only API keys on this Mac, prefer macOS Keychain through `keychain-secret` and use 1Password as an import/fallback source. Keep workflows local and avoid exposing secret values to chat, logs, files, source control, or command history.

## Default Rules

- Use only the specific credential needed for the current task.
- Prefer `keychain-secret get <service> <account>` for local API-key reads after a secret has been migrated to Keychain.
- Prefer `keychain-secret import-op <service> <account> <op-ref>` for one-time migration from a known 1Password reference.
- Prefer a user-provided `op://...` secret reference over searching vaults.
- Do not enumerate vaults, accounts, or items unless the user asks or the reference is ambiguous.
- Do not print, summarize, quote, or reveal secret values in chat or final responses.
- Do not paste plaintext secrets into source files, `.env` files, logs, issues, PRs, commit messages, or shell history.
- Prefer `op run` only for workflows that cannot use Keychain yet and accept environment variables.
- Prefer templates with secret references plus `op inject` only when a real config file is required and Keychain is unsuitable; delete resolved files when no longer needed.
- Avoid `op run --no-masking` and `op item get --reveal` unless the user explicitly asks to display a secret.
- Treat service account tokens, exported `.env` files, one-time passwords, private keys, cookies, and raw item JSON as sensitive.

## Local Setup

- Verify availability with `op --version`.
- When a command needs to read secrets through the 1Password desktop app integration, request `sandbox_permissions="require_escalated"` by default. The workspace sandbox can block the local app socket and produce misleading errors such as "couldn't connect to the 1Password desktop app" even when 1Password is installed and working.
- If `op read`, `op run`, or `op signin` fails with a desktop app connection error inside the sandbox, rerun the exact scoped command outside the sandbox with a concise approval request before asking the user to restart 1Password.
- If auth is missing, use `op signin` and expect the user to approve in 1Password.
- If multiple accounts are configured, use `--account` or `OP_ACCOUNT` only after identifying the intended account.
- Do not require `tmux`; this machine may not have it. Use normal serialized shell commands unless an interactive TTY is genuinely needed.

## Common Workflows

### Inject A Secret Into A Command

For local API keys, prefer Keychain:

```bash
API_KEY="$(keychain-secret get codex.service credential)" my-command
```

When the secret exists only in 1Password, ask for the secret reference, then run the target command without exposing the value:

```bash
API_KEY='op://Private/Service API/credential' op run -- my-command
```

For project commands, prefer a template env file containing `op://` references:

```bash
op run --env-file .env.op -- npm run dev
```

### Read A Specific Secret

Use `op read` only when the secret is not yet migrated to Keychain and must be passed to a local process that cannot consume `op run` references. Do not echo the value back to the user.

```bash
op read 'op://Private/Service API/credential'
```

For `API_CREDENTIAL` items in this setup, the preferred field is `credential`:

```bash
op read 'op://Private/<title-or-id>/credential'
```

To migrate that item to Keychain:

```bash
keychain-secret import-op codex.service credential 'op://Private/<title-or-id>/credential'
```

### Create Or Update 1Password Items

Do not ask the user to paste secret values into chat. If CLI item creation is required, avoid command-line assignment statements for sensitive values because command arguments can be logged or visible to local processes.

Use the 1Password app when practical. If CLI is necessary, use a short-lived local JSON template or stdin flow, set restrictive file permissions, and delete any plaintext temporary file immediately after use.

## When To Load References

- Read `references/op-cli.md` for concrete `op read`, `op run`, `op inject`, auth, and account-selection patterns.
- Read `references/item-management.md` before creating, editing, copying, or exporting 1Password items.

## Stop Conditions

Stop and ask the user before:

- Listing vaults/items/accounts to discover a credential.
- Exporting secrets to disk, even temporarily.
- Creating service accounts, Connect tokens, Kubernetes secrets, or CI secrets.
- Changing global shell, git, gh, or 1Password plugin configuration.
- Running any command likely to display secret values.
