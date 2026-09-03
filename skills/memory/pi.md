# Pi Coding Agent — Memory queries

Pi stores sessions as individual JSONL files under `~/.pi/agent/sessions/`, partitioned by the working directory where the session ran.

## File layout

```
~/.pi/agent/
├── settings.json
└── sessions/
    ├── --Users-yupeit--/
    │   ├── 2026-09-03T15-12-35-076Z_01a067d4-3304-7a3b-93b6-d561798bfebf.jsonl
    │   └── ...
    ├── --Users-yupeit-Desktop-finance--/
    └── <encoded-cwd>/
        └── <timestamp>_<session-uuid>.jsonl
```

### Directory naming

The workspace folder name is derived from the canonical CWD with slashes replaced by hyphens and wrapped in double dashes:
- `/Users/yupeit` → `--Users-yupeit--`
- `/Users/yupeit/Desktop/finance` → `--Users-yupeit-Desktop-finance--`
- `/Users/yupeit/dev/mon` → `--Users-yupeit-dev-mon--`

## Session file format

Each line in a Pi session JSONL file is a single JSON event:

| `type` | Description & Key fields |
|---|---|
| `session` | First line. Session header: `id`, `version`, `timestamp`, `cwd` |
| `session_info` | Title/display name: `name` (thread title), `timestamp`, `autoTitle` |
| `message` | Chat messages: `message.role` (`user`, `assistant`, `toolResult`), `message.content` |
| `model_change` | Model switches: `provider`, `modelId` |
| `thinking_level_change` | Thinking budget changes: `thinkingLevel` |
| `compaction` | Context compaction summaries |

### Message structure

Inside `{"type":"message", "message": {...}}`:
- `role`: `"user"`, `"assistant"`, or `"toolResult"`
- `content`: Array of content blocks.
  - Text block: `{"type": "text", "text": "..."}`
  - Tool call block: `{"type": "toolCall", "id": "...", "name": "...", "args": {...}}`
  - Thinking block: `{"type": "thinking", "thinking": "..."}`

---

## Query recipes

### 1. List recent sessions across all workspaces

```bash
python3 -c "
import json
from pathlib import Path

sessions_dir = Path.home() / '.pi' / 'agent' / 'sessions'
results = []
for p in sessions_dir.glob('*/*.jsonl'):
    if 'subagent' in p.name:
        continue
    try:
        with open(p, 'r', encoding='utf-8') as f:
            first_line = json.loads(f.readline())
            if first_line.get('type') != 'session':
                continue
            sid = first_line.get('id', p.stem)
            ts = first_line.get('timestamp', '')
            cwd = first_line.get('cwd', '')
            name = ''
            for line in f:
                obj = json.loads(line)
                if obj.get('type') == 'session_info':
                    name = obj.get('name', '')
            results.append((ts, sid, cwd, name, str(p)))
    except Exception:
        pass

results.sort(reverse=True)
for ts, sid, cwd, name, path in results[:25]:
    print(f'{ts[:19]}  {sid[:8]}  {cwd[:30]:<30}  {name[:50]}')
"
```

### 2. Search sessions by keyword (fast, using `rg`)

```bash
# Search across all Pi session files for a keyword
rg -l "keyword" ~/.pi/agent/sessions/

# Search and show 2 lines of matching context
rg -C 2 "keyword" ~/.pi/agent/sessions/

# Search only within a specific project's sessions
rg -l "keyword" ~/.pi/agent/sessions/--Users-yupeit-dev-mon--/
```

### 3. Find session file by UUID

```bash
find ~/.pi/agent/sessions -name "*SESSION_ID*.jsonl" 2>/dev/null
```

### 4. Read human-readable conversation from a session file

```bash
python3 -c "
import json, sys

session_file = 'PATH_TO_SESSION_FILE'
with open(session_file, 'r', encoding='utf-8') as f:
    for line in f:
        obj = json.loads(line)
        if obj.get('type') == 'message':
            msg = obj.get('message', {})
            role = msg.get('role', '')
            if role not in ('user', 'assistant'):
                continue
            content = msg.get('content', [])
            text_parts = []
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get('type') == 'text':
                        text_parts.append(part.get('text', ''))
                    elif isinstance(part, str):
                        text_parts.append(part)
            elif isinstance(content, str):
                text_parts.append(content)
            full_text = '\n'.join(text_parts).strip()
            if full_text:
                print(f'=== {role.upper()} ===\n{full_text}\n')
" | less
```
