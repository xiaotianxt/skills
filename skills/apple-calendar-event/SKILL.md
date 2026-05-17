---
name: apple-calendar-event
description: Inspect, create, and verify events in macOS Calendar.app with osascript-backed local automation. Use when Codex needs to audit local Apple Calendar sources/defaults, understand Calendar.sqlitedb cache state, or add an event directly to a specific Apple Calendar calendar on the current Mac. Prefer Google Calendar skills for durable calendar writes unless the user explicitly asks for Apple Calendar.
---

# Apple Calendar Event

Use this skill for local `Calendar.app` inspection and direct Apple Calendar writes.

## Guardrails

- Prefer Google Calendar (`gws-calendar` / `gws-calendar-insert`) for durable user calendar writes unless the user explicitly asks for Apple Calendar.
- Treat `Calendar.sqlitedb` as a read-only cache for inspection. Never edit it directly.
- Do not trust Calendar.app's default calendar for automation. It may be `UseLastSelectedAsDefaultCalendar` or point at an unsuitable source.
- Do not identify a write target by display name alone when names are duplicated. Audit first, then use the exact calendar name only after confirming it is unambiguous enough for the requested write.
- Expect Apple Calendar to contain mixed stores: Google, iCloud, school CalDAV, subscribed calendars, Reminders, Siri suggestions, birthdays, and local/system stores.

## Workflow

### Audit local Calendar.app state

Use this before cleanup, migration planning, or any Apple write where the target source is unclear:

```bash
python3 scripts/calendar_audit.py
python3 scripts/calendar_audit.py --json
```

The audit reads `~/Library/Group Containers/group.com.apple.calendar/Calendar.sqlitedb` in read-only mode, maps calendars to their stores/accounts, reports duplicate display names, and maps the Calendar.app default calendar UUID when possible.

### Create an Apple Calendar event

1. Confirm the event title, target calendar name, local date, start time, and end time.
2. If the target account/source is uncertain, run `scripts/calendar_audit.py` first.
3. If only the calendar name is uncertain, run `scripts/calendar_event.py list-calendars` and pick the exact calendar name from the output.
4. Put video links in `--location`. Put meeting numbers, interview notes, and buffer details in `--notes`.
5. If the user asks to reserve buffer time, reflect that in the final blocked time range before writing the event.
6. Create the event with `scripts/calendar_event.py create-event ...`.
7. Verify the write with `scripts/calendar_event.py verify-event ...`.

## Commands

List calendars:

```bash
python3 scripts/calendar_event.py list-calendars
```

Audit calendar sources and defaults:

```bash
python3 scripts/calendar_audit.py
```

Create an event:

```bash
python3 scripts/calendar_event.py create-event \
  --calendar "重要事件" \
  --title "视频面试" \
  --start "2026-04-15 11:30" \
  --end "2026-04-15 12:45" \
  --location "https://vc.feishu.cn/j/268399244" \
  --notes $'面试时长：1小时，已额外预留缓冲时间至 12:45\n会议号：268399244'
```

Verify the event:

```bash
python3 scripts/calendar_event.py verify-event \
  --calendar "重要事件" \
  --title "视频面试" \
  --start "2026-04-15 11:30"
```

## Notes

- Expect macOS to prompt for `Calendar` and `Automation` access the first time `osascript` runs.
- Keep times explicit in local time. Do not rely on phrases like “tomorrow morning” without converting them to exact timestamps first.
- Prefer editing the title only when the title itself is user-visible. Put operational detail, meeting IDs, and links in `location` and `notes`.
- Verify after every write. If verification fails, inspect the target calendar name again before retrying.
