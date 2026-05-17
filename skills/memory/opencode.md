# OpenCode — Memory queries

OpenCode stores sessions in a SQLite database with WAL mode. All paths below are
relative to `~/.local/share/opencode/`.

## Database

```
~/.local/share/opencode/opencode.db
```

Safe to query while opencode is running. Companion files (`-wal`, `-shm`) are
WAL support files — do not delete them.

## Schema

| Table | Key columns | Purpose |
|---|---|---|
| `session` | `id`, `title`, `directory`, `time_created`, `time_updated` | Session metadata |
| `message` | `id`, `session_id`, `data` (JSON) | Messages per session |
| `part` | `id`, `message_id`, `session_id`, `data` (JSON) | Message content parts |

The actual text content lives in the `part` table, joined to `message` via
`message_id`. The `data` column in both tables is JSON.

### `message.data` (minimal)

| Field | Notes |
|---|---|
| `role` | `"user"` or `"assistant"` |
| `agent` | agent name string |
| `model.providerID`, `model.modelID` | model info |
| `summary.title`, `summary.diffs` | user message only |
| `parentID`, `cost`, `tokens`, `finish` | assistant message only |

### `part.data` (discriminated by `type`)

| `type` | Content field(s) |
|---|---|
| `text` | `.text` — visible message text |
| `reasoning` | `.text` — thinking/reasoning content |
| `tool` | `.tool`, `.callID`, `.state.status`, `.state.input`, `.state.output` |
| `step-start` | `.snapshot` |
| `step-finish` | `.reason`, `.cost`, `.tokens` |

Query with `json_extract(m.data, '$.field')` and
`json_extract(p.data, '$.type')` / `json_extract(p.data, '$.field')`.

## Query recipes

### List sessions (CLI, preferred)

```bash
opencode session list
opencode session list -n 20
opencode session list --format json
```

### List sessions (SQL)

```bash
sqlite3 ~/.local/share/opencode/opencode.db \
  "SELECT id, title, directory,
          datetime(time_updated/1000, 'unixepoch', 'localtime') as updated
   FROM session ORDER BY time_updated DESC LIMIT 20;"
```

### Search sessions by keyword in any message

```bash
sqlite3 ~/.local/share/opencode/opencode.db "
  SELECT DISTINCT s.id, s.title, s.directory,
         datetime(s.time_updated/1000, 'unixepoch', 'localtime') as updated
  FROM message m
  JOIN session s ON m.session_id = s.id
  WHERE lower(m.data) LIKE '%keyword%'
  ORDER BY s.time_updated DESC
  LIMIT 20;"
```

### Search sessions by title or directory

```bash
sqlite3 ~/.local/share/opencode/opencode.db \
  "SELECT id, title, directory,
          datetime(time_updated/1000, 'unixepoch', 'localtime') as updated
   FROM session
   WHERE lower(title) LIKE '%keyword%'
   ORDER BY time_updated DESC
   LIMIT 10;"
```

### Read text messages for a session

```bash
sqlite3 ~/.local/share/opencode/opencode.db "
  SELECT json_extract(m.data, '$.role') as role,
         json_extract(p.data, '$.text') as text
  FROM message m
  JOIN part p ON p.message_id = m.id
  WHERE m.session_id='SESSION_ID'
    AND json_extract(p.data, '$.type') = 'text'
  ORDER BY p.time_created;"
```

### Read tool calls

```bash
sqlite3 ~/.local/share/opencode/opencode.db "
  SELECT json_extract(p.data, '$.tool') as tool,
         json_extract(p.data, '$.state.status') as status,
         substr(json_extract(p.data, '$.state.output'), 1, 300) as output
  FROM message m
  JOIN part p ON p.message_id = m.id
  WHERE m.session_id='SESSION_ID'
    AND json_extract(p.data, '$.type') = 'tool'
  ORDER BY p.time_created;"
```

### Read reasoning

```bash
sqlite3 ~/.local/share/opencode/opencode.db "
  SELECT substr(json_extract(p.data, '$.text'), 1, 500) as reasoning
  FROM message m
  JOIN part p ON p.message_id = m.id
  WHERE m.session_id='SESSION_ID'
    AND json_extract(p.data, '$.type') = 'reasoning'
  ORDER BY p.time_created;"
```

### Find sessions in a working directory

```bash
sqlite3 ~/.local/share/opencode/opencode.db \
  "SELECT id, title, datetime(time_updated/1000, 'unixepoch', 'localtime') as updated
   FROM session
   WHERE directory LIKE '%/path/here%'
   ORDER BY time_updated DESC
   LIMIT 10;"
```

### Count

```bash
sqlite3 ~/.local/share/opencode/opencode.db "SELECT COUNT(*) FROM session;"
sqlite3 ~/.local/share/opencode/opencode.db "SELECT COUNT(*) FROM message;"
```

## Export

```bash
opencode export SESSION_ID
```

## Prompt history (supplementary)

```
~/.local/state/opencode/prompt-history.jsonl
```

```bash
tail -20 ~/.local/state/opencode/prompt-history.jsonl
```
