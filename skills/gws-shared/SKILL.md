---
name: gws-shared
description: Shared authentication, security, and command conventions for locally generated Google Workspace gws skills.
---

# gws-shared

Use this reference before running any `gws-*` skill.

## Auth

- Use the local `gws` CLI auth state. Do not print tokens, refresh tokens, cookies, or raw credential files.
- If authentication is missing, run the narrowest relevant login flow, for example `gws auth login --services gmail`.
- Prefer read-only scopes unless the user explicitly asks to send, create, update, delete, or watch resources.

## Command Safety

- Inspect command shape with `gws <service> --help` and method schemas with `gws schema <service>.<resource>.<method>`.
- Prefer `--json` output for agent workflows and summarize only the fields needed for the task.
- For email and document content, avoid dumping full bodies unless the user asked for exact content.
- For write operations, state the target account, recipient, calendar, document, or Drive path before executing.

## Data Handling

- Treat Gmail messages, Calendar events, Docs content, Drive files, and contact-like metadata as private.
- Keep exports local by default.
- Do not include user data, OAuth files, cache directories, or raw API responses in commits.
