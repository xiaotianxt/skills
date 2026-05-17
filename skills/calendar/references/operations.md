# Calendar Operations

## Contents

- Snapshot and backup
- Active account verification
- Read-only inventory and governance review
- Visibility, labels, and real names
- Event creation
- Apple Calendar audit
- School and legacy migration
- Commands to avoid
- Scope expectations and rollback

Use this file for copy-pastable commands. Do not run mutation commands during a planning-only request; show the command and explain the preconditions instead.

## Snapshot

```bash
backup_dir="/Users/yupeit/Desktop/hertz/calendar-governance-backups/$(date +%Y%m%d-%H%M%S)-calendar"
mkdir -p "$backup_dir"
gws auth status > "$backup_dir/gws-auth-status.json"
gws calendar calendarList list --params '{"showHidden":true,"maxResults":250}' > "$backup_dir/calendar-list-before.json"
python3 /Users/yupeit/dev/skills/skills/calendar/scripts/calendar_list_review.py \
  --calendar-list "$backup_dir/calendar-list-before.json" \
  --format tsv > "$backup_dir/calendar-list-review.tsv"
cd /Users/yupeit/dev/skills/skills/apple-calendar-event
python3 scripts/calendar_audit.py --json > "$backup_dir/apple-calendar-audit-before.json"
```

## Verify Active Account

```bash
gws auth status | jq -e '.user == "tianyupeiandy@gmail.com" and .token_valid == true'
```

If this fails, do not write events or patch calendar metadata. Re-auth with the narrowest needed scope, usually:

```bash
gws auth login --services calendar
```

## Read-Only Inventory And Governance Review

Use this when the user says the calendar is messy, asks what to rename/hide/migrate, or asks why events are going to the wrong account. These commands do not mutate calendars.

```bash
gws calendar calendarList list --params '{"showHidden":true,"maxResults":250}' \
  > "$backup_dir/calendar-list-before.json"

gws calendar calendarList list --params '{"showHidden":true,"maxResults":250}' \
  | jq -r '.items[] | [
      .summary,
      (.summaryOverride // ""),
      .id,
      (.primary // false),
      .accessRole,
      (.selected // false),
      (.hidden // false)
    ] | @tsv'

python3 /Users/yupeit/dev/skills/skills/calendar/scripts/calendar_list_review.py \
  --calendar-list "$backup_dir/calendar-list-before.json" \
  --format tsv
```

When `dataOwner` is blank, do not assume the calendar has no owner. Use:

- `primary == true` and ID `tianyupeiandy@gmail.com` for the primary source.
- `accessRole` to understand the current account's effective control.
- `gws calendar calendars get --params '{"calendarId":"CALENDAR_ID"}'` for real metadata.
- Apple audit `store_name`, `store_owner`, and identity fields when reconciling Calendar.app display entries.

For calendars that might be renamed or migrated, capture real metadata before proposing a final write:

```bash
gws calendar calendars get --params '{"calendarId":"CALENDAR_ID"}'
```

## Visibility Governance

Patch `selected` and `hidden` on the user's CalendarList entry. This affects the user's view and does not delete calendars or events.

```bash
gws calendar calendarList patch \
  --params '{"calendarId":"CALENDAR_ID"}' \
  --json '{"selected":true,"hidden":false}'
```

Hide archive calendars:

```bash
gws calendar calendarList patch \
  --params '{"calendarId":"CALENDAR_ID"}' \
  --json '{"selected":false,"hidden":true}'
```

## Display Labels vs Real Names

`summaryOverride` is a per-user CalendarList label. It is reversible and low risk, but Google Calendar web UI may still display the real `summary` under `My calendars`.

```bash
gws calendar calendarList patch \
  --params '{"calendarId":"CALENDAR_ID"}' \
  --json '{"summaryOverride":"80 Archive - Old Name"}'
```

Use real `summary` when the user wants the actual Google Calendar sidebar name changed:

```bash
gws calendar calendars patch \
  --params '{"calendarId":"CALENDAR_ID"}' \
  --json '{"summary":"00 Core - Google 主号"}'
```

If `summaryOverride` and `summary` conflict, explain this directly: Google Calendar may show the real `summary` in `My calendars`, while API/list contexts can still expose `summaryOverride`. Verify with both `calendarList.list` and `calendars.get`.

Real `summary` edits may affect what shared users see. Confirm before renaming shared calendars or calendars whose owner is not clearly `tianyupeiandy@gmail.com`.

Before real summary edits, save:

```bash
safe_id="$(printf '%s' 'CALENDAR_ID' | tr '/:@# ' '_____')"
gws calendar calendars get --params '{"calendarId":"CALENDAR_ID"}' > "$backup_dir/calendar-before-$safe_id.json"
```

## Default Event Creation

Preflight:

```bash
gws auth status | jq -e '.user == "tianyupeiandy@gmail.com" and .token_valid == true'
```

Then write only with an explicit target:

```bash
gws calendar +insert \
  --calendar 'tianyupeiandy@gmail.com' \
  --summary 'TITLE' \
  --start 'YYYY-MM-DDTHH:MM:SS-07:00' \
  --end 'YYYY-MM-DDTHH:MM:SS-07:00' \
  --location 'LOCATION_OR_URL' \
  --description 'NOTES'
```

Always use exact local timestamps. Do not rely on relative phrases after the planning step.

Avoid these for default personal writes:

```bash
# Do not use the current browser account.
# Do not use Calendar.app's default calendar.
# Do not use --calendar primary in account-confusing contexts.
# Do not write to yupeit@andrew.cmu.edu, iCloud, or another Google account unless explicitly requested.
```

## Apple Calendar Audit

```bash
cd /Users/yupeit/dev/skills/skills/apple-calendar-event
python3 scripts/calendar_audit.py
python3 scripts/calendar_audit.py --json
```

Use this to detect:

- duplicate display names
- Calendar.app default policy and default UUID
- store/account ownership such as Google, iCloud, school CalDAV, subscribed calendars, Reminders, and system sources

Do not edit `Calendar.sqlitedb`.

## School Migration Planning

Before copying school events into the primary Google calendar:

1. Inventory future events from the school calendar with `events.list`.
2. Compare against existing primary events by `iCalUID`, title, start time, and location.
3. Keep the school calendar visible but unselected while migration is in progress.
4. Prefer copying/importing only future actionable events.
5. Do not delete the school source until the user confirms the migrated state.

Example inventory:

```bash
gws calendar events list \
  --params '{"calendarId":"yupeit@andrew.cmu.edu","timeMin":"YYYY-MM-DDT00:00:00-07:00","singleEvents":true,"showDeleted":false,"maxResults":2500,"orderBy":"startTime"}' \
  > "$backup_dir/school-source-events.json"

gws calendar events list \
  --params '{"calendarId":"tianyupeiandy@gmail.com","timeMin":"YYYY-MM-DDT00:00:00-07:00","singleEvents":true,"showDeleted":false,"maxResults":2500,"orderBy":"startTime"}' \
  > "$backup_dir/primary-target-events.json"
```

Preview source events that do not appear in the target by `iCalUID` or normalized `summary + start + location`:

```bash
python3 /Users/yupeit/dev/skills/skills/calendar/scripts/event_dedupe_preview.py \
  --source "$backup_dir/school-source-events.json" \
  --target "$backup_dir/primary-target-events.json" \
  --format tsv
```

Treat the preview as advisory. Review ambiguous events before copying.

Before copying events, decide which fields to preserve and which to drop:

- Usually preserve: summary, start, end, location, description, and intentional reminders.
- Review carefully: recurrence rules, conferenceData/Meet links, attendees, organizer, attachments, visibility/transparency, and private fields.
- Avoid blindly recreating attendees or conference links unless the user wants invitations or meeting changes to propagate.

## Commands To Avoid Unless Explicitly Requested

```bash
# Avoid defaulting to Apple Calendar for personal event creation.
# Avoid using "primary" where multiple Google accounts may be authenticated or visible.
# Avoid deleting calendars, unsubscribing, or bulk-deleting events during cleanup planning.
# Avoid direct writes to ~/Library/Group Containers/group.com.apple.calendar/Calendar.sqlitedb.
# Avoid real summary changes for shared/read-only/school/system calendars without owner confirmation.
# Avoid copying attendees/conferenceData during migration unless the user wants invitations or meeting updates.
```

## Scope Expectations

Use the narrowest calendar authorization that satisfies the operation:

- Read/audit: Calendar read access is enough.
- CalendarList `selected`, `hidden`, `summaryOverride`: CalendarList write access.
- Real `summary`: calendar metadata write access.
- Event creation/migration: event write access.

When scope is insufficient, prefer:

```bash
gws auth login --services calendar
```

## Rollback Pattern

Every mutation report should include exact rollback commands. For real `summary` edits:

```bash
gws calendar calendars patch \
  --params '{"calendarId":"CALENDAR_ID"}' \
  --json '{"summary":"PREVIOUS_SUMMARY"}'
```

For visibility edits:

```bash
gws calendar calendarList patch \
  --params '{"calendarId":"CALENDAR_ID"}' \
  --json '{"selected":PREVIOUS_SELECTED,"hidden":PREVIOUS_HIDDEN}'
```
