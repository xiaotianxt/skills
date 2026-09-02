---
name: calendar
description: Govern and maintain the user's personal calendar system across Google Calendar, Apple Calendar.app, school/legacy accounts, and automation. Use when Codex needs to audit calendar state, choose the correct write target, create or verify calendar events, clean up cluttered calendar lists, rename or hide calendars, migrate away from school/Apple/iCloud/legacy sources, prevent non-authoritative accounts from owning personal events, or reason about Google Calendar vs macOS Calendar.app behavior.
---

# Calendar

## Purpose

Use this as the single calendar entrypoint. It decides source of truth, write targets, audit depth, and safety level before delegating Google operations to lower-level `gws-calendar` skills or using its bundled helpers for local Apple Calendar.app work.

## First Principles

- Treat calendars as data ownership boundaries, not folders. A separate calendar is justified only by a different owner, lifecycle, permission model, visibility need, reminder policy, or read-only source. Otherwise put context in the event title, description, location, guests, or reminders.
- Make `tianyupeiandy@gmail.com` in Google Calendar the durable source of truth for personal commitments. Default personal writes target calendar ID `tianyupeiandy@gmail.com`.
- Treat `yupeit@andrew.cmu.edu` and other school calendars as transition sources because the account may expire. Read and migrate from them; avoid new durable writes there unless the user explicitly requests school-owned placement.
- Treat Apple Calendar.app as a local view and legacy/transition layer. It can reveal defaults, duplicate names, and local sources, but it is not the default automation write path.
- Treat `1241811980i59@gmail.com`, `yupeigemini@gmail.com`, iCloud, Reminders, Siri Suggestions, subscribed calendars, and browser account defaults as non-authoritative for personal calendar ownership unless the user explicitly overrides this.
- Do not infer ownership from display names. Use authenticated account, calendar ID, `primary`, `accessRole`, real calendar metadata, and Apple store/account audit output.
- Prefer reversible changes first: `selected`, `hidden`, `summaryOverride`, and documented renames. Delete, unsubscribe, or bulk-copy only after explicit confirmation, backups, and rollback notes.
- Optimize for the user's real workflows: fast event capture, reliable agenda reads, low visual clutter, account-lifecycle resilience, and no surprise ownership drift.

## Default Write Policy

For event creation when the user says "my calendar" or gives no target:

1. Use the `personal` gws profile and run `gws auth status` through its
   explicit config directory.
2. Require `token_valid == true`, then resolve Calendar ID `primary` through
   the Calendar API and require its returned `id` to equal the profile's local
   `expected-user` value.
3. Write to Google Calendar ID `tianyupeiandy@gmail.com`.
4. State the active account, target calendar ID, title, and exact local start/end before writing.
5. Use Apple Calendar only when the user explicitly asks for Apple Calendar or Calendar.app.

Do not rely on:

- Google Calendar web UI account switcher default labels.
- Calendar.app's default calendar.
- Display names alone when duplicate names exist.
- `primary` in multi-account or account-confusing contexts.

## gws Account Profiles

`gws` does not currently provide a reliable native named-profile switch. Keep
each account in an isolated encrypted config directory and prefix every command:

- `personal`: `/Users/yupeit/.config/gws/profiles/personal`
- `cmu`: `/Users/yupeit/.config/gws/profiles/cmu`

Each profile directory must contain a mode-`0600` `expected-user` file with the
one exact account email authorized for that profile. Keep this identity mapping
local instead of publishing every account address in the skill.

Example:

```bash
profile_dir=/Users/yupeit/.config/gws/profiles/personal
expected_user="$(<"$profile_dir/expected-user")"
export GOOGLE_WORKSPACE_CLI_CONFIG_DIR="$profile_dir"
gws auth status | jq -e '.token_valid == true'
gws calendar calendars get --params '{"calendarId":"primary"}' \
  | jq -e --arg expected "$expected_user" '.id == $expected'
```

Never use bare `gws` for multi-account calendar work. Before every read or
write sequence, verify `token_valid` and the selected profile's exact primary
Calendar ID; `gws auth status` 0.22.5 does not report the account email. Do not
infer identity from a calendar name or browser account. Read
`references/operations.md` when logging in, adding a profile, or handling gws
quota-project failures.

## Scenario Router

### Read or Agenda

Use `gws-calendar-agenda` or raw `gws calendar events list` through the explicit
account profile against Google first. Include Apple Calendar.app only when the
user asks about local Calendar.app state, missing events in Apple, duplicate
display names, or default-calendar behavior.

### Create or Edit Personal Events

Use `gws-calendar-insert` or raw `gws calendar +insert` through the `personal`
profile with explicit `--calendar tianyupeiandy@gmail.com`. Before writing,
state the active account, calendar ID, title, exact local start/end, time zone,
and whether guests/conference/reminders will be created. If the auth account is
not `tianyupeiandy@gmail.com`, stop and re-auth instead of writing through
another account.

### Diagnose "My Calendar Is Messy"

Inventory Google CalendarList and Apple Calendar.app first. Separate issues into ownership, visibility, naming, duplication, and lifecycle. Produce a proposed table before mutating anything: calendar ID, current label, likely owner/source, role, selected/hidden, recommended taxonomy bucket, proposed action, rollback.

### Rename, Hide, or Reduce Visual Clutter

Prefer view-level changes: `selected`, `hidden`, then `summaryOverride`. Use real `calendars.patch {"summary": ...}` only when the user wants the actual Google Calendar `My calendars` name changed and the calendar is owned/controlled by the intended account. Confirm before renaming shared, external, read-only, school, holiday, birthday, task, or subscribed calendars.

### Migrate Away From School, Apple, iCloud, or Legacy Accounts

Make an inventory first, usually future actionable events only. Compare against the primary calendar by `iCalUID`, normalized title, start time, and location. Treat dedupe previews as advisory: recurrence expansion, changed titles, changed locations, time zones, guests, Meet links, attachments, reminders, privacy, and organizer semantics need explicit review before copying. Keep the source visible but unselected during migration; do not delete or unsubscribe until the user confirms the migrated state.

### Investigate Or Write Apple Calendar.app

Use the bundled `scripts/calendar_audit.py` and `scripts/calendar_event.py` helpers. Never edit `Calendar.sqlitedb`; treat it as a read-only cache.

For an Apple write:

1. Require the user to explicitly request Apple Calendar or Calendar.app.
2. Confirm the title, target calendar name, local date, start, and end.
3. Run `scripts/calendar_audit.py` when source ownership or duplicate names matter; otherwise list exact names with `scripts/calendar_event.py list-calendars` when only the target name is uncertain.
4. Put meeting links in location and operational detail in notes.
5. Create with `scripts/calendar_event.py create-event`, then verify with `scripts/calendar_event.py verify-event`.

Read `references/operations.md` for exact commands.

### Delete or Unsubscribe

Default to "hide/archive" instead. Delete, unsubscribe, or remove shared calendars only after the user confirms the exact calendar ID/source and a backup exists. Built-ins such as Birthdays and Tasks are not ordinary owned cleanup targets.

## Governance Workflow

### 1. Classify Risk

- **Read-only**: agenda, inventory, audit, explain state. No backup required unless saving a report.
- **View mutation**: select/unselect, hide/unhide, `summaryOverride`. Backup CalendarList first.
- **Metadata mutation**: real calendar `summary`, description, time zone, reminders. Backup CalendarList and affected `calendars.get`.
- **Event mutation**: create, edit, copy, migrate, delete. Verify auth, target ID, exact timestamps, and event semantics.
- **Destructive mutation**: delete calendar, unsubscribe, bulk delete, remove source after migration. Require explicit confirmation and rollback/backup discussion.

### 2. Build State From Source APIs

Use these checks before decisions that affect ownership or visibility,
prefixing every `gws` command with the intended profile as described above:

```bash
gws auth status
gws calendar calendarList list --params '{"showHidden":true,"maxResults":250}' > calendar-list-before.json
python3 /Users/yupeit/dev/skills/skills/calendar/scripts/calendar_list_review.py --calendar-list calendar-list-before.json --format tsv
python3 /Users/yupeit/dev/skills/skills/calendar/scripts/calendar_audit.py --json
```

Interpretation rules:

- CalendarList `dataOwner` is often absent. Infer ownership from `primary`, calendar ID, `accessRole`, real calendar metadata from `calendars.get`, and Apple audit store/account fields when reconciling with Calendar.app.
- Google `calendarList.summaryOverride` is a per-user list label. It may not consistently change `My calendars` display names in the web UI.
- Google `calendars.patch {"summary": ...}` changes the real calendar title and is the right operation when the user wants the left sidebar name itself changed.
- Real `summary` changes can affect how shared calendars appear to other users. Confirm intent before renaming shared or externally owned calendars.
- If both `summaryOverride` and real `summary` are present, explain to the user that Google UI may prefer real `summary` in `My calendars` and `summaryOverride` in shared/other list contexts. Use API output to verify the exact state.
- Google `calendarList.patch {"selected": ..., "hidden": ...}` changes sidebar visibility without deleting calendars or events.
- Google built-ins such as Birthdays and Tasks are not ordinary user calendars; do not treat them as owned cleanup targets.
- Apple `Calendar.sqlitedb` is useful for read-only source mapping, duplicate names, and default calendar diagnosis. Never edit it directly.

### 3. Propose Before Mutating

For governance work, present the plan in concrete operations:

- `keep`: authoritative or intentionally visible.
- `hide`: remove visual clutter without deleting data.
- `label`: add/change `summaryOverride`.
- `rename`: change real `summary`.
- `migrate`: copy reviewed events to `tianyupeiandy@gmail.com`.
- `archive`: hide legacy source after migration.
- `delete/unsubscribe`: only after explicit confirmation.

Mention commands you would run and commands you would avoid when the request is a planning/governance request.

### 4. Backup Before Mutations

Before any calendar governance mutation, create a timestamped backup under:

```text
/Users/yupeit/Desktop/hertz/calendar-governance-backups/<timestamp>-<operation>/
```

Save at least:

- `gws-auth-status.json`
- `calendar-list-before.json`
- affected `calendars.get` JSON files for real summary/metadata edits
- Apple audit JSON when Apple Calendar.app state is relevant
- a short `report.md` with scope, changes, and rollback values

### 5. Apply The Least Powerful Change

Use this escalation order:

1. Select/unselect calendars with `calendarList.patch selected`.
2. Hide/unhide calendars with `calendarList.patch hidden`.
3. Set `summaryOverride` for list labels where it is sufficient.
4. Patch real `summary` when the user wants Google UI `My calendars` names to change.
5. Copy/migrate events only after inventory and dedupe planning.
6. Delete/unsubscribe only after explicit confirmation.

### 6. Verify And Report

After any write, re-read the affected resource. Report the active account, exact calendar ID, changed fields, backup path, and rollback command. If verification fails, stop and diagnose before retrying.

## Current Governance Model

The user's intended taxonomy is:

- `00 Core - Google 主号`: primary personal commitments; default automation write target.
- `10 Projects - ...`: active project calendars that need independent visibility.
- `20 Shared - ...`: other people's calendars or shared views.
- `30 School Transition - ...`: school-owned or school-lifecycle calendars to migrate away from.
- `80 Archive - ...`: hidden legacy or inactive calendars.
- `90 Reference - ...`: holidays and read-only reference calendars.

Current known source-of-truth assumptions:

- Primary Google account: `tianyupeiandy@gmail.com`.
- Preferred automation target calendar ID: `tianyupeiandy@gmail.com`.
- School transition source: `yupeit@andrew.cmu.edu`.
- Apple Calendar.app: view/legacy layer, not default write target.

## Execution Layers

- Use `gws-calendar` for Calendar API discovery, list, patch, event operations, and low-level Google Calendar resources.
- Use `gws-calendar-insert` for straightforward Google event creation.
- Use `gws-calendar-agenda` for upcoming event views.
- Use this skill's bundled scripts for local Apple Calendar.app audits and explicit Apple Calendar event writes.

## OAuth Scope Expectations

- Read/audit operations may work with Calendar read scopes.
- CalendarList visibility and label changes require CalendarList write scope.
- Real calendar metadata edits require calendar metadata write scope.
- Event creation or migration requires calendar event write scope.
- If scope is missing, re-auth with the narrowest calendar service flow and avoid broad Workspace scopes unless the task needs them.

## Detailed Recipes

For copy-pastable commands, profile login and troubleshooting, migration dedupe
preview, and rollback patterns, read `references/operations.md` only when
performing authentication, governance mutations, migrations, or Apple/Google
reconciliation.
