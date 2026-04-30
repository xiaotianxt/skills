# 1Password Item Management

Use this reference before creating, editing, copying, exporting, or deleting 1Password items.

## Creation Principles

- Prefer the 1Password app when the user needs to store a new plaintext secret.
- Do not ask the user to paste a plaintext secret into chat.
- Do not put sensitive values in command-line assignment statements. The `op item create --help` text warns that command arguments may be logged in shell history or visible to local processes.
- For CLI creation with secrets, use a short-lived JSON template or stdin, set restrictive permissions, and delete plaintext temporary files immediately.
- Use `--dry-run` for shape validation when possible.
- Use clear item titles and field names that match the service's docs.

## Field Types

Use explicit field types:

```text
Name[text]=value
Secret[concealed]=value
URL[url]=https://example.com
Old Field[delete]
```

Only conceal actual secrets: passwords, API keys, bearer tokens, refresh tokens, private keys, recovery codes, and cookies.

Use text or URL fields for usernames, account emails, client IDs, hostnames, ports, redirect URLs, docs links, and other identifiers.

## API Credential Items

For simple API keys in this user's setup, prefer an item category of `API Credential` with the secret in a field named `credential`.

Preferred read reference:

```text
op://Private/<title-or-id>/credential
```

Useful non-secret fields:

```text
Account[text]
Service[text]
Documentation[url]
Developer Portal[url]
Notes
```

OAuth-style credentials should distinguish non-secret and secret fields:

```text
Client ID[text]
Client Secret[concealed]
Authorization URL[url]
Token Request URL[url]
Redirect URL[text]
Scopes[text]
```

## Listing And Searching

Do not list vaults or items for convenience. If discovery is necessary, keep it narrow:

```bash
op item list --vault Private --categories "API Credential" --format json
```

When summarizing discovery results, report only item titles, IDs, vault names, categories, and timestamps needed for selection. Do not reveal field values.

## Service Accounts And Automation

Service accounts are production-impacting credentials. Before creating or modifying one, state:

- intended name
- target vault
- permissions
- where the token will be stored
- how it will be rotated or revoked

Do not print service account tokens in final responses. Store them directly in the intended secret manager when possible.
