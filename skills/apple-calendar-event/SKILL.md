---
name: apple-calendar-event
description: Create and verify events in macOS Calendar.app with osascript-backed local automation. Use when Codex needs to add an interview, meeting, class, reminder block, or other dated event to a specific Apple Calendar calendar on the current Mac, especially when the target calendar name must be checked first and the write should be verified afterward.
---

# Apple Calendar Event

Use this skill for direct local writes to `Calendar.app`.

## Workflow

1. Confirm the event title, target calendar name, local date, start time, and end time.
2. If the calendar name is uncertain, run `scripts/calendar_event.py list-calendars` and pick the exact calendar name from the output.
3. Put video links in `--location`. Put meeting numbers, interview notes, and buffer details in `--notes`.
4. If the user asks to reserve buffer time, reflect that in the final blocked time range before writing the event.
5. Create the event with `scripts/calendar_event.py create-event ...`.
6. Verify the write with `scripts/calendar_event.py verify-event ...`.

## Commands

List calendars:

```bash
python3 scripts/calendar_event.py list-calendars
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
