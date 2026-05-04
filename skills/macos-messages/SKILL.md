---
name: macos-messages
description: Read and search local macOS Messages.app iMessage/SMS history directly through the chat.db SQLite database. Use when the user wants to read, search, or analyze local iPhone messages, SMS, iMessage conversations, or message attachments on this Mac.
---

# macOS Messages

Direct read-only SQLite access to `~/Library/Messages/chat.db` for local iMessage and SMS history. No CLI wrapper — use `sqlite3` with the queries below.

## Privacy

Chat data is private. Keep all work local. Print only the message content the user asked for. Never export `chat.db` to external services. Treat message bodies, sender identities, and attachment paths as sensitive.

## Setup

The terminal needs **Full Disk Access** in System Settings → Privacy & Security → Full Disk Access. Without it, `~/Library/Messages/chat.db` is permission-denied.

Verify:

```bash
sqlite3 ~/Library/Messages/chat.db "SELECT COUNT(*) FROM message"
```

## Schema

Four core tables, three join tables:

| Table | Role |
| --- | --- |
| `chat` | Conversation. `chat_identifier` is phone/email/group-id. `display_name` is the group name. |
| `message` | Individual message. `text` or `attributedBody` holds the body, `date` is timestamp, `is_from_me`=1 means sent. |
| `handle` | Contact. `id` is phone or email, `service` is iMessage/SMS/RCS. |
| `attachment` | Media file. `filename` is the on-disk path, `mime_type` is MIME type. |

Join tables: `chat_message_join`, `chat_handle_join`, `message_attachment_join`.

## Text vs attributedBody

**This is the most common pitfall.** `message.text` is frequently NULL because Messages.app stores the body in `attributedBody` (NSKeyedArchiver binary blob) instead. This happens for most SMS, RCS, and rich iMessages. Plain-text iMessages are the main case where `text` is populated.

To extract readable text from `attributedBody`:

```bash
sqlite3 ~/Library/Messages/chat.db \
  "SELECT HEX(attributedBody) FROM message WHERE ROWID=<MSG_ID>" \
  | xxd -r -p | strings | grep -vE '^(NS|__)' | grep -v streamtyped | head -20
```

To run this in a single pipeline for a full chat read, see **Reading with extraction** below.

## Date Conversion

All timestamps use Mac absolute time (since 2001-01-01). Convert:

```sql
-- message.date: nanoseconds since 2001-01-01
datetime(date/1000000000 + 978307200, 'unixepoch', 'localtime')

-- attachment.created_date: seconds since 2001-01-01
datetime(created_date + 978307200, 'unixepoch', 'localtime')
```

`978307200` = delta in seconds between Unix epoch (1970-01-01) and Mac epoch (2001-01-01).

## Common Queries

### List recent chats

```sql
SELECT c.ROWID, c.chat_identifier, c.display_name, c.service_name,
       datetime(MAX(m.date)/1000000000 + 978307200, 'unixepoch', 'localtime') AS last_msg
FROM chat c
JOIN chat_message_join cmj ON c.ROWID = cmj.chat_id
JOIN message m ON cmj.message_id = m.ROWID
GROUP BY c.ROWID
ORDER BY MAX(m.date) DESC
LIMIT 20
```

### Find a chat

```sql
SELECT ROWID, chat_identifier, display_name, service_name
FROM chat
WHERE chat_identifier LIKE '%KEYWORD%'
   OR display_name LIKE '%KEYWORD%'
LIMIT 10
```

### Read messages from a chat (with extraction)

Replace `<CHAT_ID>` with the chat ROWID. This extracts text from both `text` and `attributedBody`:

```bash
sqlite3 ~/Library/Messages/chat.db -separator $'\t' \
  "SELECT m.ROWID, datetime(m.date/1000000000 + 978307200, 'unixepoch', 'localtime') AS time,
          CASE WHEN m.is_from_me THEN 'Me' ELSE COALESCE(h.id, m.service) END AS sender,
          COALESCE(m.text, HEX(m.attributedBody)) AS body
   FROM message m
   JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
   LEFT JOIN handle h ON m.handle_id = h.ROWID
   WHERE cmj.chat_id = <CHAT_ID>
   ORDER BY m.date DESC
   LIMIT 50" \
  | while IFS=$'\t' read rowid time sender body; do
      text="$body"
      if [[ "$body" =~ ^[0-9A-Fa-f]+$ ]] && [ ${#body} -gt 40 ]; then
        text=$(echo "$body" | xxd -r -p | strings | grep -vE '^(NS|__)' | grep -v streamtyped | tr '\n' ' ' 2>/dev/null | head -c 500)
      fi
      echo "$time | $sender | ${text:0:300}"
    done
```

For ascending order (oldest first): change `DESC` to `ASC`.

For a quick peek (no extraction, just see which messages have body):

```sql
SELECT datetime(m.date/1000000000 + 978307200, 'unixepoch', 'localtime') AS time,
       CASE WHEN m.is_from_me THEN 'Me' ELSE COALESCE(h.id, m.service) END AS sender,
       CASE WHEN m.text IS NOT NULL THEN SUBSTR(m.text, 1, 80)
            WHEN m.attributedBody IS NOT NULL THEN '[attributedBody: ' || LENGTH(m.attributedBody) || ' bytes]'
            ELSE '[empty]' END AS preview
FROM message m
JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
LEFT JOIN handle h ON m.handle_id = h.ROWID
WHERE cmj.chat_id = <CHAT_ID>
ORDER BY m.date DESC
LIMIT 50
```

### Read messages in a date range

```sql
WHERE cmj.chat_id = <CHAT_ID>
  AND m.date >= strftime('%s', '2026-04-01', 'localtime') * 1000000000 - 978307200000000000
  AND m.date <  strftime('%s', '2026-05-01', 'localtime') * 1000000000 - 978307200000000000
```

### Search all messages

Searches both `text` and `attributedBody`. Pipe through grep to handle binary extraction:

```bash
sqlite3 ~/Library/Messages/chat.db -separator $'\t' \
  "SELECT m.ROWID, datetime(m.date/1000000000 + 978307200, 'unixepoch', 'localtime') AS time,
          CASE WHEN m.is_from_me THEN 'Me' ELSE COALESCE(h.id, m.service) END AS sender,
          COALESCE(m.text, HEX(m.attributedBody)) AS body,
          c.chat_identifier
   FROM message m
   JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
   JOIN chat c ON cmj.chat_id = c.ROWID
   LEFT JOIN handle h ON m.handle_id = h.ROWID
   WHERE m.text LIKE '%KEYWORD%' ESCAPE '\'
      OR HEX(m.attributedBody) LIKE '%' || REPLACE(HEX('KEYWORD'), '00', '') || '%'
   ORDER BY m.date DESC
   LIMIT 30" \
  | while IFS=$'\t' read rowid time sender body chat; do
      text="$body"
      if [[ "$body" =~ ^[0-9A-Fa-f]+$ ]] && [ ${#body} -gt 40 ]; then
        text=$(echo "$body" | xxd -r -p | strings | grep -vE '^(NS|__)' | grep -v streamtyped | tr '\n' ' ' 2>/dev/null | head -c 500)
      fi
      echo "$time | $sender | ${text:0:300} | [$chat]"
    done
```

The `REPLACE(HEX('KEYWORD'), '00', '')` accounts for UTF-16 encoding in the blob — hex matching handles ASCII text without needing full blob decode.

For a faster SQL-only search (returns matched rows, requires separate extraction):

```sql
SELECT m.ROWID, datetime(m.date/1000000000 + 978307200, 'unixepoch', 'localtime') AS time,
       CASE WHEN m.is_from_me THEN 'Me' ELSE COALESCE(h.id, m.service) END AS sender,
       SUBSTR(COALESCE(m.text, ''), 1, 80) AS snippet,
       c.chat_identifier
FROM message m
JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
JOIN chat c ON cmj.chat_id = c.ROWID
LEFT JOIN handle h ON m.handle_id = h.ROWID
WHERE m.text LIKE '%KEYWORD%' ESCAPE '\'
   OR HEX(m.attributedBody) LIKE '%' || REPLACE(HEX('KEYWORD'), '00', '') || '%'
ORDER BY m.date DESC
LIMIT 30
```

### Search by contact

Find the handle first:

```sql
SELECT ROWID, id, service FROM handle WHERE id LIKE '%PHONE_OR_EMAIL%' LIMIT 10
```

Then get their messages with extraction (replace `<HANDLE_ID>`):

```bash
sqlite3 ~/Library/Messages/chat.db -separator $'\t' \
  "SELECT m.ROWID, datetime(m.date/1000000000 + 978307200, 'unixepoch', 'localtime') AS time,
          COALESCE(m.text, HEX(m.attributedBody)) AS body, m.is_from_me
   FROM message m
   WHERE m.handle_id = <HANDLE_ID>
   ORDER BY m.date DESC
   LIMIT 50" \
  | while IFS=$'\t' read rowid time body is_from_me; do
      text="$body"
      if [[ "$body" =~ ^[0-9A-Fa-f]+$ ]] && [ ${#body} -gt 40 ]; then
        text=$(echo "$body" | xxd -r -p | strings | grep -vE '^(NS|__)' | grep -v streamtyped | tr '\n' ' ' 2>/dev/null | head -c 500)
      fi
      echo "$time | $([ "$is_from_me" = 1 ] && echo 'Me' || echo '→') | ${text:0:300}"
    done
```

### Message counts per chat

```sql
SELECT c.chat_identifier, c.display_name, COUNT(m.ROWID) AS msg_count
FROM chat c
JOIN chat_message_join cmj ON c.ROWID = cmj.chat_id
JOIN message m ON cmj.message_id = m.ROWID
GROUP BY c.ROWID
ORDER BY msg_count DESC
LIMIT 20
```

### Get attachments for a message

```sql
SELECT a.filename, a.mime_type, a.total_bytes
FROM attachment a
JOIN message_attachment_join maj ON a.ROWID = maj.attachment_id
WHERE maj.message_id = <MESSAGE_ID>
```

### Attachments by date

```sql
SELECT datetime(a.created_date + 978307200, 'unixepoch', 'localtime') AS time,
       a.filename, a.mime_type, a.total_bytes
FROM attachment a
ORDER BY a.created_date DESC
LIMIT 30
```

## Safety

- **Read-only only.** Never run INSERT, UPDATE, DELETE, or DROP against `chat.db`.
- Always add `LIMIT`. This database can have tens of thousands of rows.
- When `text` is NULL, extract from `attributedBody` using the pipeline above — never assume a NULL `text` means an empty message.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `unable to open database file` | Grant Full Disk Access to Terminal in System Settings |
| `database is locked` | Normal when Messages.app is running; sqlite3 handles concurrent reads fine |
| No results for a known contact | Try both phone number and email in `handle.id`. iMessage uses email, SMS uses phone. |
| `text` IS NULL | Body is in `attributedBody`. Extract with: `HEX(attributedBody) \| xxd -r -p \| strings \| grep -vE '^(NS\|__)' \| grep -v streamtyped` |
| Search misses expected messages | Query only searched `text`. Add `OR HEX(m.attributedBody) LIKE '%' \|\| REPLACE(HEX('KEYWORD'), '00', '') \|\| '%'` to cover attributedBody. |
