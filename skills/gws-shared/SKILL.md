---
name: gws-shared
description: Shared authentication, security, and command conventions for locally generated Google Workspace gws skills.
---

# gws-shared

Use this reference before running any `gws-*` skill.

## Auth

- Use the local `gws` CLI auth state. Do not print tokens, refresh tokens, cookies, or raw credential files.
- Set `GOOGLE_WORKSPACE_CLI_CONFIG_DIR` explicitly for every command. Never rely on a default profile.
- Calendar profiles:
  - personal: `/Users/yupeit/.config/gws/profiles/personal`
  - CMU: `/Users/yupeit/.config/gws/profiles/cmu`
- Gmail profiles:
  - personal: `/Users/yupeit/.config/gws/profiles/personal-mail`
  - CMU: `/Users/yupeit/.config/gws/profiles/cmu-mail`
- Keep Calendar and Gmail credentials separated even when they use the same OAuth client. Gmail profiles intentionally carry the full `https://mail.google.com/` scope; do not use them for Calendar workflows.
- Before reading private data or writing anything, compare the API-reported account identity with the profile's mode-`0600` `expected-user` file.
- If authentication is missing, authorize only the service profile being repaired. Do not broaden another profile as a shortcut.

## Command Safety

- Inspect command shape with `gws <service> --help` and method schemas with `gws schema <service>.<resource>.<method>`.
- Prefer `--json` output for agent workflows and summarize only the fields needed for the task.
- For email and document content, avoid dumping full bodies unless the user asked for exact content.
- For write operations, state the target account, recipient, calendar, document, or Drive path before executing.
- Full Gmail access includes permanent deletion. Require explicit user authorization for destructive or bulk mailbox changes, and prefer reversible Trash/archive operations when they satisfy the request.

## Data Handling

- Treat Gmail messages, Calendar events, Docs content, Drive files, and contact-like metadata as private.
- Keep exports local by default.
- Do not include user data, OAuth files, cache directories, or raw API responses in commits.
