---
name: memory
description: Query and read past coding-agent session/conversation history, across both opencode and codex. Use when the user wants to recall something discussed in a previous session, search past conversations by keyword, review context from old sessions, or continue prior work. Triggers include "查一下之前的聊天记录", "还记得上次那个...", "look up a past session", "what did we talk about...", or any request to recall historical context.
---

# Memory

This skill provides read-only access to past conversation history, supporting multiple coding agents.

## Agent detection

Determine which agent you are running under, then load the corresponding reference file:

| Agent | How to detect | Reference file |
|---|---|---|
| **OpenCode** | System prompt mentions "opencode" OR you have the `opencode` CLI; DB exists at `~/.local/share/opencode/opencode.db` | [opencode.md](opencode.md) |
| **Codex (OpenAI)** | System prompt mentions "Codex" or "GPT-5"; sessions in `~/.codex/sessions/` | [codex.md](codex.md) |

**Detection priority:**
1. Check your system prompt / identity (e.g. "You are Codex" vs "You are opencode").
2. If ambiguous, check which session store exists on disk.

Once detected, read the corresponding file:

- For **OpenCode**: open `opencode.md` in the same directory as this file.
- For **Codex**: open `codex.md` in the same directory as this file.

## Common safety rules (both agents)

- **Read-only**: Never modify session data (INSERT, UPDATE, DELETE, file write, etc.).
- **Limit output**: Always use `LIMIT` or piping (`head`) to avoid flooding context.
- **Privacy**: Avoid printing API keys, tokens, account emails, or raw error bodies.
- **WAL/Concurrency**: Both systems support concurrent reads; no need to stop the agent.
