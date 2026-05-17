# Codex — Memory queries

Codex stores sessions as individual JSONL files organized by date, plus a session
index and a prompt history file.

## File layout

```
~/.codex/
├── session_index.jsonl          # maps session ID → title + date
├── history.jsonl                # prompt log: {session_id, ts, text}
└── sessions/
    └── YYYY/
        └── MM/
            └── DD/
                └── rollout-YYYY-MM-DDTHH-mm-ss-UUID.jsonl
```

## Session index format

Each line in `session_index.jsonl`:

```json
{"id": "019cdb9f-e66d-...", "thread_name": "Implement MAGIC...", "updated_at": "2026-03-11T06:40:24.9048Z"}
```

## Session file format

Each line in a session JSONL file is one event, discriminated by `type`:

| `type` | Contains |
|---|---|
| `session_meta` | `payload.id`, `payload.cwd`, `payload.cli_version`, `payload.model_provider` |
| `event_msg` | `payload.type` (`task_started`, etc.), `payload.turn_id` |
| `turn_context` | `payload.turn_id`, `payload.cwd`, `payload.model` |
| `response_item` → `message` / `user` | User input: `payload.content[].text` |
| `response_item` → `message` / `assistant` | Assistant output: `payload.content[].text` + `payload.phase` (`"commentary"` or `"final"`) |
| `response_item` → `message` / `developer` | System/developer instructions |
| `response_item` → `reasoning` | Thinking blocks: `payload.encrypted_content` (encrypted) or `payload.content` |
| `response_item` → `function_call` | Tool call: `payload.name`, `payload.arguments`, `payload.call_id` |
| `response_item` → `function_call_output` | Tool result: `payload.call_id`, `payload.output` |
| `response_item` → `custom_tool_call` | Custom tool invocation |
| `response_item` → `custom_tool_call_output` | Custom tool result |
| `response_item` → `web_search_call` | Web search usage |

## Query recipes

### List all sessions (sorted by updated)

```bash
python3 -c "
import json
sessions = []
with open('$HOME/.codex/session_index.jsonl') as f:
    for line in f:
        s = json.loads(line)
        sessions.append((s.get('updated_at',''), s['id'], s.get('thread_name','')))
for ts, sid, name in sorted(sessions, reverse=True)[:30]:
    print(f'{sid}  {ts[:10]}  {name[:80]}')
"
```

### Find a session file by ID

```bash
# Session IDs are UUIDs in the filename after the time portion
find ~/.codex/sessions -name "*SESSION_ID_SHORT*.jsonl" 2>/dev/null
```

Or by date from the index:

```bash
# First get the date from index
python3 -c "
import json
with open('$HOME/.codex/session_index.jsonl') as f:
    for line in f:
        s = json.loads(line)
        if s['id'] == 'YOUR_SESSION_ID':
            print(s['updated_at'][:10])  # YYYY-MM-DD
            break
"
```

### Search sessions by keyword (fast, uses `rg`)

```bash
# Search across all session files
rg -l "keyword" ~/.codex/sessions/

# Search and show matching lines with context
rg -C 2 "keyword" ~/.codex/sessions/2026/03/11/

# Restrict to user messages only
rg '"type":"input_text"' ~/.codex/sessions/ -l | xargs rg "keyword"
```

### Search prompts only

```bash
rg "keyword" ~/.codex/history.jsonl
```

### Read human-readable conversation for a session

```bash
python3 -c "
import json, sys
with open('PATH_TO_SESSION_FILE') as f:
    for line in f:
        obj = json.loads(line)
        t = obj['type']
        if t == 'response_item':
            p = obj.get('payload', {})
            if p.get('type') == 'message':
                role = p.get('role', '?')
                phase = p.get('phase', '')
                for c in p.get('content', []):
                    ct = c.get('type', '')
                    text = c.get('text', '')
                    if text:
                        label = f'{role}'
                        if phase == 'commentary':
                            label += ' (commentary)'
                        elif phase == 'final':
                            label += ' (final)'
                        print(f'[{label}] {text[:500]}')
                        print('---')
            elif p.get('type') == 'function_call':
                print(f'[tool] {p[\"name\"]}: {p.get(\"arguments\",\"\")[:200]}')
            elif p.get('type') == 'function_call_output':
                output = p.get('output', '')
                # output contains chunk headers, skip for readability
                print(f'[tool_result] call_id={p[\"call_id\"]}')
"
```

### Extract user prompts only

```bash
python3 -c "
import json
with open('PATH_TO_SESSION_FILE') as f:
    for line in f:
        obj = json.loads(line)
        if obj.get('type') == 'response_item':
            p = obj.get('payload', {})
            if p.get('type') == 'message' and p.get('role') == 'user':
                for c in p.get('content', []):
                    text = c.get('text', '')
                    if text:
                        print(text[:500])
                        print('---')
"
```

### Read session metadata

```bash
python3 -c "
import json
with open('PATH_TO_SESSION_FILE') as f:
    for line in f:
        obj = json.loads(line)
        if obj.get('type') == 'session_meta':
            p = obj['payload']
            print(f'Session: {p[\"id\"]}')
            print(f'CWD: {p.get(\"cwd\",\"?\")}')
            print(f'Version: {p.get(\"cli_version\",\"?\")}')
            print(f'Model: {p.get(\"model_provider\",\"?\")}')
            break
"
```

## Notes

- **Reasoning is encrypted**: The `reasoning` events usually contain
  `encrypted_content` (base64-encoded), not plaintext. You cannot read
  reasoning content from the JSONL files directly.
- **File path convention**: Session filenames include the UUID after a
  timestamp, e.g. `rollout-2026-03-11T02-40-15-019cdb9f-e66d-7601-8cfe-303c6bbab575.jsonl`.
  The session ID is `019cdb9f-e66d-7601-8cfe-303c6bbab575`.
- **`history.jsonl`**: Contains only user prompts (truncated to first ~3KB),
  keyed by `session_id`. Good for fast prompt-only search.
- **Function call output**: Contains chunk headers and metadata. For clean
  output, search for the actual stdout content within the output string.
