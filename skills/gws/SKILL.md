---
name: gws
description: Govern and operate Google Workspace (Google Calendar, Gmail, Google Drive, Docs, Sheets, etc.) through the local `gws` CLI. Manages multi-account profiles (personal vs CMU), calendar source of truth, event scheduling and cleanup, email search/reading/drafting/sending, Drive/Docs operations, and macOS Calendar.app legacy integration.
---

# Google Workspace (gws)

Use this skill as the primary entrypoint for Google Workspace automation through the local `gws` CLI (Google Calendar, Gmail, Drive, Docs, Sheets, etc.).

## 1. Auth & Multi-Account Profiles

`gws` uses isolated configuration directories per account and service to maintain strict scope and identity isolation. Never run bare `gws` without setting `GOOGLE_WORKSPACE_CLI_CONFIG_DIR`.

### Profile Directories

- **Calendar Profiles**:
  - Personal (`tianyupeiandy@gmail.com`): `/Users/yupeit/.config/gws/profiles/personal`
  - CMU (`yupeit@andrew.cmu.edu`): `/Users/yupeit/.config/gws/profiles/cmu`
- **Gmail Profiles**:
  - Personal: `/Users/yupeit/.config/gws/profiles/personal-mail`
  - CMU: `/Users/yupeit/.config/gws/profiles/cmu-mail`

Keep Calendar and Gmail credentials separated. Gmail profiles carry full email scopes; do not reuse them for Calendar tasks.

### Identity Verification Pattern

Before executing private reads or mutations:
1. Point `GOOGLE_WORKSPACE_CLI_CONFIG_DIR` to the target profile directory.
2. Verify `gws auth status` returns `token_valid: true`.
3. Verify identity against the profile's mode-`0600` `expected-user` file:

```bash
profile_dir="/Users/yupeit/.config/gws/profiles/personal"
expected_user="$(<"$profile_dir/expected-user")"
export GOOGLE_WORKSPACE_CLI_CONFIG_DIR="$profile_dir"

gws auth status | jq -e '.token_valid == true'
gws calendar calendars get --params '{"calendarId":"primary"}' \
  | jq -e --arg expected "$expected_user" '.id == $expected'
```

---

## 2. Calendar Management & Governance

### First Principles

- **Source of Truth**: `tianyupeiandy@gmail.com` in Google Calendar is the durable source of truth for personal commitments.
- **School Calendars**: `yupeit@andrew.cmu.edu` is treated as a transition source because the account may expire. Read and migrate from it; do not create new permanent personal commitments there.
- **Apple Calendar.app**: Regarded as a local view and legacy migration layer. It is not the default automation write path.
- **Write Policy**: Default event creations target calendar ID `tianyupeiandy@gmail.com` on the `personal` profile. State active account, target calendar ID, title, and local start/end times before writing.

### Common Calendar Workflows

#### Check Agenda / Upcoming Events
```bash
export GOOGLE_WORKSPACE_CLI_CONFIG_DIR="/Users/yupeit/.config/gws/profiles/personal"
# Read events from primary calendar
gws calendar events list --params '{"calendarId":"primary","timeMin":"2026-09-03T00:00:00Z","singleEvents":true,"orderBy":"startTime","maxResults":20}'
```

#### Insert Event
```bash
export GOOGLE_WORKSPACE_CLI_CONFIG_DIR="/Users/yupeit/.config/gws/profiles/personal"
gws calendar +insert --calendar "tianyupeiandy@gmail.com" \
  --summary "Meeting Title" \
  --start "2026-09-04T10:00:00-04:00" \
  --end "2026-09-04T11:00:00-04:00"
```

#### Calendar Cleanup & Audits
Use the bundled scripts in `scripts/` when reviewing Google Calendar lists or checking local Apple Calendar state:
- Review calendar list:
  ```bash
  gws calendar calendarList list --params '{"showHidden":true,"maxResults":250}' > calendar-list.json
  python3 scripts/calendar_list_review.py --calendar-list calendar-list.json --format tsv
  ```
- Reconcile with Apple Calendar:
  ```bash
  python3 scripts/calendar_audit.py --json
  ```
- Before any calendar governance mutation (hide, rename, delete), create a timestamped backup in `/Users/yupeit/Desktop/hertz/calendar-governance-backups/<timestamp>-<op>/`.

---

## 3. Gmail Operations

Use Gmail via `gws` for email search, triage, reading, drafting, and sending.

### Profile Selection
- Personal mail: `GOOGLE_WORKSPACE_CLI_CONFIG_DIR=/Users/yupeit/.config/gws/profiles/personal-mail`
- CMU mail: `GOOGLE_WORKSPACE_CLI_CONFIG_DIR=/Users/yupeit/.config/gws/profiles/cmu-mail`

### Search & Triage
Search messages with standard Gmail query syntax:
```bash
export GOOGLE_WORKSPACE_CLI_CONFIG_DIR="/Users/yupeit/.config/gws/profiles/personal-mail"
# Search messages matching query
gws gmail users messages list --params '{"userId":"me","q":"from:advisor has:attachment","maxResults":10}'
```

### Read Threads & Messages
```bash
# Get thread metadata and message snippets
gws gmail users threads get --params '{"userId":"me","id":"THREAD_ID"}'
# Get specific message details
gws gmail users messages get --params '{"userId":"me","id":"MESSAGE_ID","format":"full"}'
```
*Note*: Avoid dumping giant raw bodies to avoid flooding context; summarize content relevant to the user's inquiry.

### Create Drafts
Always prefer drafting first before sending:
```bash
gws gmail users drafts create --params '{"userId":"me"}' \
  --json '{"message":{"raw":"BASE64URL_ENCODED_MIME_MESSAGE"}}'
```

### Deletion & Modification Safety
- Full Gmail access includes permanent deletion. Require **explicit user authorization** for destructive or bulk mailbox changes.
- Prefer reversible trash (`users.messages.trash`) or label removal/archive over permanent deletion.

---

## 4. Drive, Docs, Sheets & Other Services

Inspect command shape and discovery schemas with:
```bash
gws <service> --help
gws schema <service.resource.method>
```

Examples:
```bash
# List recent Drive files
gws drive files list --params '{"pageSize":15,"fields":"files(id,name,mimeType,modifiedTime)"}'

# Get Google Doc metadata and structure
gws docs documents get --params '{"documentId":"DOC_ID"}'

# Read Google Sheets spreadsheet values
gws sheets spreadsheets values get --params '{"spreadsheetId":"SHEET_ID","range":"Sheet1!A1:D10"}'
```

---

## 5. Security & Privacy Rules

- Keep exports local by default.
- Never print tokens, refresh tokens, client secrets, or full cookies in logs or output.
- State target account, calendar, recipient, or document path before any write operation.
