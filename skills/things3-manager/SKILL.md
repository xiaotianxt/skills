---
name: things3-manager
description: Manage Things 3 on macOS through the official Things URL scheme. Use when asked to add, batch-import, update, show, search, or programmatically locate existing open to-dos/projects in Things, especially when an auth token should be injected from an env file.
---

# Things 3 Manager

Use this skill for Things 3 automation on macOS.

## Quick start

- Requirements:
  - Things 3 is installed.
  - In Things -> Settings -> General, "Enable Things URLs" is enabled.
- Global install path:
  - `~/.codex/skills/things3-manager/`
- Global mutable state:
  - `~/.codex/skills-data/things3-manager/.env`
- Main CLI:
  - `bash ~/.codex/skills/things3-manager/scripts/things --help`

## Token handling

- The wrapper auto-sources `~/.codex/skills-data/things3-manager/.env`.
- Store the Things auth token as `THINGS_AUTH_TOKEN=...` in that file.
- You can also override it per command with `THINGS_AUTH_TOKEN=... bash .../things ...` or `--auth-token ...`.
- `update-*` commands always require a token.
- `json` only requires a token when the JSON contains update operations.

## Workflow

- Prefer `--dry-run` first for large batch imports.
- Map a task's available/start date to `when` and its due date to `deadline`. If the source only provides a due date and no reliable start date can be found, set `when` to the current local date unless the user asks for a different fallback.
- Use `json --data-file ...` for big imports with projects/headings/to-dos.
- For the Things `json` command, the file must contain a top-level JSON array of Things objects, for example `[{"type":"project","attributes":{...}}]`. Do not wrap it in an object like `{"items":[...]}`; Things may accept the URL but silently create nothing.
- Use `add-todo` or `add-project` for one-off items.
- Use `show`, `search`, `find-open-todos`, or `version` for non-destructive actions.
- For updates to existing items, resolve the item `id` first with `find-open-todos`, then call `update-todo` or `update-project`.
- For reminder-only changes on existing tasks, keep the same date and pass `--when YYYY-MM-DD@HH:MM`. The public URI uses the `when` field to set both the start date and the reminder time.
- If the requested reminder time is already in the past for that date, Things removes the reminder instead of keeping it.
- `search` only opens Things UI search. Use `find-open-todos` when you need machine-readable ids and dates for follow-up updates.
- Before write operations, summarize the exact changes and confirm unless the user has already explicitly asked you to perform them.

## Commands

- `add-todo`
- `add-project`
- `update-todo`
- `update-project`
- `json`
- `show`
- `search`
- `find-open-todos`
- `version`
- `set-token`
- `print-config`

## Examples

```bash
bash ~/.codex/skills/things3-manager/scripts/things add-todo \
  --title "Book flights" \
  --when 2026-03-25@18:00 \
  --deadline 2026-03-25
```

```bash
bash ~/.codex/skills/things3-manager/scripts/things json \
  --data-file /tmp/things-import.json \
  --reveal
```

`/tmp/things-import.json` must look like:

```json
[
  {
    "type": "project",
    "attributes": {
      "title": "Example Project",
      "items": [
        {
          "type": "heading",
          "attributes": {
            "title": "First Section"
          }
        },
        {
          "type": "to-do",
          "attributes": {
            "title": "First task"
          }
        }
      ]
    }
  }
]
```

```bash
bash ~/.codex/skills/things3-manager/scripts/things find-open-todos \
  --project "17629 Assignments" \
  --title-contains "In-Class Exercise" \
  --json
```

```bash
bash ~/.codex/skills/things3-manager/scripts/things update-todo \
  --id 3h8S39kz63CjXEqJ3aJw3m \
  --when 2026-03-26@12:30 \
  --dry-run
```

```bash
bash ~/.codex/skills/things3-manager/scripts/things set-token \
  --token "$THINGS_AUTH_TOKEN"
```
