---
name: mimestreamctl
description: "Use when Codex needs to work with Mimestream mail on this Mac: investigate local mail, search receipts or support threads, identify actual recipients from sent mail, read selected messages, draft or reply in Mimestream, visually verify compose windows, or perform explicit mailbox actions. Prefer Gmail API skills for server-authoritative send/delivery/label/thread state that does not depend on Mimestream."
---

# Mimestream Control

This skill exists to keep agents from guessing in email workflows. Use it as a mail forensics and drafting interface, not as a generic UI-clicking script.

## First Principles

Email tasks have four different truth sources. Pick the right one before running commands:

1. **Local cache truth**: Mimestream's SQLite cache is best for searching, timelines, receipts, old sent mail, headers, and evidence.
2. **Visible UI truth**: the front Mimestream window is best only for "the message/draft currently on screen."
3. **Server truth**: Gmail/API state is best for whether a message is actually sent, delivered, trashed, labeled, or threaded.
4. **Human intent**: sending, trashing, spam, unsubscribe, and bulk actions require explicit user intent.

Default route: local cache for facts, UI for visible draft verification, Gmail API for server-authoritative state.

## Entry Point

```bash
~/.codex/skills/mimestreamctl/scripts/mimestreamctl --help
```

If the wrapper behaves oddly, retry:

```bash
~/dev/mimestreamctl/mimestreamctl --help
```

UI commands require Mimestream running in the logged-in macOS desktop session with Accessibility and Automation permissions. Run UI commands serially.

## Decision Tree

**Need facts from mail?** Use `mail search`, `mail get`, `mail headers`, `mail thread`, or `mail sent-search`. Do not start from the front UI.

**Need to know who to send to?** Search past sent mail and headers. Do not infer from a visible received message.

**Need to reply in an existing thread?** Verify the selected message, then use `reply` or `reply-all`. Do not create a new compose unless the user wants a new thread.

**Need a new draft?** Write the body to a file, open a visible draft, then verify To/Cc/From/Subject/body. Do not send unless explicitly asked.

**Need to move/delete/send?** Verify the exact target first. Destructive and send commands need `--confirm`.

## Golden Paths

### Evidence Or Timeline

```bash
~/.codex/skills/mimestreamctl/scripts/mimestreamctl mail accounts
~/.codex/skills/mimestreamctl/scripts/mimestreamctl mail search --query hertz --since 2026-01-01 --limit 100 --include-transactional --show-addresses
~/.codex/skills/mimestreamctl/scripts/mimestreamctl mail get --id 12345 --include-html --show-addresses
~/.codex/skills/mimestreamctl/scripts/mimestreamctl mail headers --id 12345
~/.codex/skills/mimestreamctl/scripts/mimestreamctl mail thread --id 12345
```

For billing, travel, legal-ish, school, or support disputes:

1. Search broad by brand/domain.
2. Search exact identifiers.
3. Separate reservation/order records, receipts, user-sent complaints, bounces, and human replies.
4. Use `mail thread --id` on promising sent messages or support replies to connect "what I sent" to "what they replied."
5. Extract dates, amounts, ids, account, sender, recipient, and thread/case ids.
6. Build the answer from source message ids.
7. State missing or ambiguous evidence.

Use `--include-transactional` for receipts, confirmations, support, billing, security, and travel records.

### Recipient Discovery

```bash
~/.codex/skills/mimestreamctl/scripts/mimestreamctl mail sent-search --query hertz --since 2025-11-01 --limit 20
~/.codex/skills/mimestreamctl/scripts/mimestreamctl mail sent-search --to hertz.com --since 2025-11-01 --limit 50
~/.codex/skills/mimestreamctl/scripts/mimestreamctl mail headers --id 12345
~/.codex/skills/mimestreamctl/scripts/mimestreamctl mail thread --id 12345
```

Classify addresses before drafting:

- **Intake address**: new outbound complaints that later produce case replies.
- **Case-reply address**: works for existing case threads.
- **No-reply/bounce address**: avoid for new disputes.
- **Specialized address**: marketing, loyalty, receipts, verification, etc.

When uncertain, propose `To`/`Cc` with rationale instead of silently choosing.

### Current Selected Message

```bash
~/.codex/skills/mimestreamctl/scripts/mimestreamctl selection --json --first
~/.codex/skills/mimestreamctl/scripts/mimestreamctl read --full --max-chars 4000
~/.codex/skills/mimestreamctl/scripts/mimestreamctl links --resolve-redirects
```

If subject/body/window do not match, stop and re-verify the Mimestream selection. UI state can drift.

### New Draft

```bash
~/.codex/skills/mimestreamctl/scripts/mimestreamctl compose \
  --to person@example.com \
  --cc team@example.com \
  --subject "Subject" \
  --body-file /tmp/body.txt
```

`compose` opens drafts with `open -a Mimestream` and falls back to `open -b com.mimestream.Mimestream` when macOS cannot resolve the app name. If both routes fail but Mimestream is visibly installed, inspect the generated URL and open it manually:

```bash
~/.codex/skills/mimestreamctl/scripts/mimestreamctl compose --dry-run ...
open -b com.mimestream.Mimestream "mailto:..."
```

Before saying the draft is ready, verify:

- To/Cc/Bcc are intended.
- From account is intended.
- Subject is correct for new case vs existing thread.
- Body starts and ends correctly.
- No placeholders or private tokens remain.
- The message is still a draft.

Use AX text when available; otherwise use a screenshot or visible window inspection. A zero exit code only means the open request returned. `selection` may still report the previously selected main-window message after a compose window opens; verify the draft window itself, not just the message selection.

### Reply Draft

```bash
~/.codex/skills/mimestreamctl/scripts/mimestreamctl read --no-body --json
~/.codex/skills/mimestreamctl/scripts/mimestreamctl reply --body-file /tmp/reply.txt
~/.codex/skills/mimestreamctl/scripts/mimestreamctl reply-all --body-file /tmp/reply.txt
```

Use `reply-all` only when thread continuity and participant preservation matter.

### Explicit Actions

```bash
~/.codex/skills/mimestreamctl/scripts/mimestreamctl archive
~/.codex/skills/mimestreamctl/scripts/mimestreamctl trash --confirm
~/.codex/skills/mimestreamctl/scripts/mimestreamctl send --confirm
```

For bulk unsubscribe or trash, dry-run first, save exact ids, inspect summaries, then confirm only after user approval.

## Command Semantics

- `mail search`: search cache by account/from/to/subject/query/date. Add `--show-addresses` when recipient or threading context matters.
- `mail sent-search`: search sent mail and always include To/Cc/Bcc and threading headers.
- `mail get --id`: read one cached message. It does not filter out transactional mail.
- `mail headers --id`: read addressing, state, message-id, reply-to, in-reply-to, and references for one message.
- `mail thread --id`: list messages in the same local Mimestream thread, with addresses and state.
- `selection`, `read`, `links`, `list`: inspect visible Mimestream UI state.
- `compose`, `reply`, `reply-all`, `insert-text`: create or edit visible drafts.
- `archive`, `move`, `trash`, `spam`, `send`: mutate mail or draft state.

## Failure Handling

- If a message appears in `mail search` but body extraction is poor, use `mail get --include-html` and convert HTML to visible text.
- If local cache evidence conflicts with server state, use Gmail API skills for the authoritative answer.
- If UI automation fails, bring Mimestream forward and retry once. For new drafts, `compose` already retries bundle-id `open`; if verification still fails, inspect the front window title with System Events or use visible screenshot verification.
- If recipient choice depends on previous successful workflows, use `sent-search` and support replies, not memory.
- Never edit Mimestream SQLite directly.

## Safety

- Never send, trash, spam, bulk unsubscribe, or bulk delete without explicit intent and confirmation.
- Never rely on the front window for bulk work.
- Never expose full tracking links, unsubscribe tokens, private message links, or secrets.
- Keep summaries evidence-based: cite message ids in working notes and report only the relevant facts to the user.
