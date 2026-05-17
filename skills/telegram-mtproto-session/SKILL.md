---
name: telegram-mtproto-session
description: Create, verify, and use local Telegram MTProto user sessions with Telethon, including fast date-bounded chat history sync into local SQLite/FTS and local history queries. Use when Codex needs to log in to Telegram with a phone account, validate an existing .session file, read Telegram channel/group/chat history, search or inspect Telegram chats through the user API, or recover from broken/unauthorized sessions while keeping Telegram app credentials in macOS Keychain.
---

# Telegram MTProto Session

Use this skill for Telegram user-account access through MTProto/Telethon. This is separate from bot-token workflows and separate from the `tg` skill, which is for local WeChat history on this machine.

## Rules

- Read Telegram app credentials from macOS Keychain; do not paste API IDs, hashes, phone numbers, login codes, or 2FA passwords into files or final responses.
- Prefer these Keychain entries:
  - `keychain-secret get codex.telegram api_id`
  - `keychain-secret get codex.telegram api_hash`
  - `keychain-secret get codex.telegram phone`
- One-time migration from 1Password, when needed:
  - `keychain-secret import-op codex.telegram api_id 'op://Private/Telegram Apps/api_id'`
  - `keychain-secret import-op codex.telegram api_hash 'op://Private/Telegram Apps/api_hash'`
  - `keychain-secret import-op codex.telegram phone 'op://Private/Telegram Apps/telegram_phone'`
- Use a dedicated session path under `~/.local/share/codex-telegram/` unless the user asks for another location.
- Use the bundled SQLite history store for high-volume reads:
  `~/.local/share/codex-telegram/history.sqlite3`.
- Treat `.session` files as sensitive account credentials. Do not commit, upload, or print their raw contents.
- If Keychain reads, Telethon network calls, or SQLite opens under `~/.local/share`
  fail under sandboxing, rerun the same scoped command with approval.
- Respect Telegram rate limits. If a command reports `FloodWaitError`, stop and report the wait duration.

## Script

Use `scripts/telegram_session.py` from this skill directory. It requires Telethon and reads credentials from environment variables:

```bash
TELEGRAM_API_ID="$(keychain-secret get codex.telegram api_id)" \
TELEGRAM_API_HASH="$(keychain-secret get codex.telegram api_hash)" \
TELEGRAM_PHONE="$(keychain-secret get codex.telegram phone)" \
python3 scripts/telegram_session.py --session ~/.local/share/codex-telegram/telegram login
```

When login sends a Telegram code, ask the user for the code in chat or have them type it into the running command. If Telegram asks for 2FA, prefer prompting interactively with `getpass`; do not ask the user to paste a long-lived password into chat unless they explicitly choose that path.

## Workflows

### Verify A Session

```bash
TELEGRAM_API_ID="$(keychain-secret get codex.telegram api_id)" \
TELEGRAM_API_HASH="$(keychain-secret get codex.telegram api_hash)" \
python3 scripts/telegram_session.py --session ~/.local/share/codex-telegram/telegram verify
```

Expected successful output includes `authorized=True`, the session path, and the Telegram user id/username. If `authorized=False`, run `login`.

### Search Public Telegram Chats

```bash
TELEGRAM_API_ID="$(keychain-secret get codex.telegram api_id)" \
TELEGRAM_API_HASH="$(keychain-secret get codex.telegram api_hash)" \
python3 scripts/telegram_session.py --session ~/.local/share/codex-telegram/telegram search 'linux.do'
```

Use this for public channel/group discovery. It prints title, username, kind, participants, and id.

### Inspect A Channel Or Group

```bash
TELEGRAM_API_ID="$(keychain-secret get codex.telegram api_id)" \
TELEGRAM_API_HASH="$(keychain-secret get codex.telegram api_hash)" \
python3 scripts/telegram_session.py --session ~/.local/share/codex-telegram/telegram inspect linux_do --limit 5
```

Use `inspect` to resolve a known username, print channel metadata, and summarize recent messages. Message summaries include reply/comment metadata when Telegram exposes it.

### Fast History Sync And Local Query

For date-bounded history, prefer `today` or `sync` so messages are cached in
local SQLite with WAL and FTS5 indexes. `today` syncs one local day and prints
the resulting rows:

```bash
TELEGRAM_API_ID="$(keychain-secret get codex.telegram api_id)" \
TELEGRAM_API_HASH="$(keychain-secret get codex.telegram api_hash)" \
python3 scripts/telegram_session.py --session ~/.local/share/codex-telegram/telegram \
  today @linux_do_channel --day 2026-05-08 --timezone America/Los_Angeles
```

Use `sync` when you want to warm the local cache without printing messages:

```bash
TELEGRAM_API_ID="$(keychain-secret get codex.telegram api_id)" \
TELEGRAM_API_HASH="$(keychain-secret get codex.telegram api_hash)" \
python3 scripts/telegram_session.py --session ~/.local/share/codex-telegram/telegram \
  sync @linux_do_channel --since 2026-05-01 --until 2026-05-08 --timezone America/Los_Angeles
```

Use `query` for local-only reads after sync:

```bash
python3 scripts/telegram_session.py query @linux_do_channel \
  --since 2026-05-08 --until 2026-05-08 --timezone America/Los_Angeles
```

Add `--match '<fts expression>'` to search message text through SQLite FTS5.
Add `--format jsonl` when downstream tooling should parse rows.

### List Joined Dialogs

```bash
TELEGRAM_API_ID="$(keychain-secret get codex.telegram api_id)" \
TELEGRAM_API_HASH="$(keychain-secret get codex.telegram api_hash)" \
python3 scripts/telegram_session.py --session ~/.local/share/codex-telegram/telegram dialogs --match linux
```

Use this when the user says the session is already joined to a group/channel but the public username is unknown.

## Common Fixes

- `missing required env`: load credentials through the exact `keychain-secret get` commands above.
- `authorized=False`: the session file is missing, expired, or was created for another account; run `login`.
- `SessionPasswordNeededError`: Telegram account has 2FA enabled; let the script prompt via `getpass`.
- `FloodWaitError`: stop and report the wait duration; do not retry aggressively.
- Public search finds candidates but `inspect` fails: the channel may require joining, may be private, or may be blocked by account restrictions.
- `query` returns no rows: run `sync` or `today` for that chat/date first, or check that the local date and `--timezone` match the intended day.
- `sqlite3.OperationalError: unable to open database file` in Codex sandbox:
  run the same query with approval, or point `--db` at a writable/readable task-local path.
