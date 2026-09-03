---
name: bro-browser
description: Control and inspect a real local Chromium-family browser through the bro MCP server and WebExtension. Use when Codex needs logged-in browser access, current tab inspection, page text or link extraction, multi-URL background extraction, click/fill/read flows, or browser console and network diagnostics. Do not use for ordinary web lookup when generic web browsing is sufficient.
---

# Bro Browser

## Overview

Use bro when the user wants an agent to operate the user's real local browser, especially for logged-in pages or dynamic pages that generic HTTP fetch cannot read. Treat the browser as sensitive user state.

bro is the local Rust MCP server in `/Users/yupeit/dev/bro`. It exposes:

- HTTP server: `http://127.0.0.1:3500`
- MCP endpoint: `http://127.0.0.1:3500/mcp`
- WebSocket extension bridge: `ws://127.0.0.1:3500/ws`
- settings token path: `~/.bro/settings.json`
- unpacked extension path: `/Users/yupeit/dev/bro/extension/dist`

Use `127.0.0.1`, not `localhost`, to avoid IPv6 mismatch with local services.

## Pi Integration

When native `bro_*` Pi tools are present, use them directly instead of invoking
`bro-call.mjs` through bash. Pi keeps one MCP connection per session, exposes
common extraction, flow, and one-call network capture tools initially, and loads
lower-level tools through `bro_search_tools`. Use the shell helper only as a
fallback when native tools are unavailable.

## Chrome Connector Parity

Prefer bro for parallel browser work. It has first-class batch tools with
bounded concurrency:

- `browser.batch.extract`
- `browser.batch.run`
- `browser.batch.flow`

For tasks that need the official Chrome connector style lifecycle, bro exposes
matching session primitives:

- `session_name`: name a browser automation session and update its tab group.
- `tabs_claim`: claim an already-open user tab without making it agent-owned.
- `tabs_finalize`: close owned tabs unless they are explicitly kept.

Use `/Users/yupeit/dev/bro/docs/chrome-connector-parity.md` when you need a
detailed feature comparison against the official Chrome connector.

## Fast Path First

For a known URL or a user request that can be satisfied by opening one page and reading it, start with the highest-level one-shot extraction before doing discovery:

```bash
scripts/bro-call.mjs browser.extract '{"url":"https://example.com","active":false,"cleanup":true,"maxChars":8000}'
```

Use this as the default first move for unknown page content, logged-in pages, and ordinary "look at this page" tasks. It minimizes tool calls and keeps browser state contained by opening a task-owned background tab and cleaning it up.

If the user says the target page is already open or asks about the current logged-in browser page, use current-tab extraction directly:

```bash
scripts/bro-call.mjs browser.current.extract '{"maxChars":8000}'
```

Skip these fast paths only when the task needs foreground interaction, form submission, browser/tab state discovery, or a target URL is not known.

## First Checks

Use read-only status checks when the fast path is not applicable, when an extraction fails for connection/auth reasons, or when you need to operate on existing tabs:

```bash
curl -sS http://127.0.0.1:3500/status
scripts/bro-call.mjs browsers_context
scripts/bro-call.mjs tabs_context '{"all":true}'
```

Also confirm the bro settings file exists:

```bash
ls -l ~/.bro/settings.json
```

If running from outside this skill directory, use the stable runtime helper path:

```bash
/Users/yupeit/.agents/skills/bro-browser/scripts/bro-call.mjs browsers_context
```

If the server is not running, start it from the bro repo:

```bash
cargo run --manifest-path /Users/yupeit/dev/bro/Cargo.toml -- serve
```

If no extension is connected, load `/Users/yupeit/dev/bro/extension/dist` as an unpacked extension in a Chromium-family browser, open the extension options, set server URL to `ws://127.0.0.1:3500/ws`, and paste the token from `~/.bro/settings.json`. Do not print the token.

## OpenCode Integration

OpenCode can use the stdio proxy so its config does not store the bro bearer
token:

```json
"mcp": {
  "bro": {
    "type": "local",
    "command": [
      "/Users/yupeit/dev/skills/skills/bro-browser/scripts/bro-stdio-proxy.mjs"
    ],
    "enabled": true,
    "timeout": 10000
  }
}
```

The proxy reads `~/.bro/settings.json` locally and forwards to
`http://127.0.0.1:3500/mcp`.

## Tool Choice

Choose the highest-level bro tool that matches the user outcome:

- Extract one known URL or unknown page content: call `browser.extract` first, preferably with `active:false`, `cleanup:true`, and a task-appropriate `maxChars`.
- Extract the current/open page: call `browser.current.extract` first. Do not spend separate calls on `browsers_context` and `tabs_context` unless the current page is ambiguous or extraction fails.
- Extract many independent URLs: call `browser.batch.extract`.
- Read text from many URLs when links and diagnostics are not needed: call `browser.batch.run`.
- Run the same interaction on many independent URLs: call `browser.batch.flow` with `inputs`, shared `steps`, bounded `concurrency`, and `cleanup:true`. Use this instead of starting many separate flow sessions when every page needs the same click/wait/eval/read workflow, such as opening review panels on a product set.
- Interact with one page over multiple steps: use `browser.flow.start`, `browser.flow.act`, `browser.flow.observe`, then `browser.flow.finish`.
- Inspect or operate on an existing tab: call `browsers_context`, then `tabs_context`, pin `browserId` and `tabId`, and use raw tab tools.
- Trigger and inspect a network request: use `browser.network.capture` so monitoring, trigger execution, request matching, response-body collection, and cleanup happen in one call. Use raw `read_network_requests` and `get_response_body` only for deliberate best-effort diagnostics.
- Debug console output: create or pin a tab, then use `read_console_messages`.

Use compact extraction defaults. Leave `includeLinks:false` unless URLs are part of the answer or the next crawl step. Leave `includeA11y:false` unless DOM extraction is partial/empty or you need controls and labels. Read `references/workflows.md` for concrete workflow recipes and `references/tool-map.md` for tool arguments and fallback rules.

## Session Lifecycle

For multi-tab work that is not fully handled by a batch facade:

1. Pick a stable `sessionId` for the task.
2. Call `session_name` with a short human-readable name.
3. Create task-owned tabs with `tabs_create` or `tabs_create_mcp` and pass that
   `sessionId`.
4. Claim user-opened tabs with `tabs_claim` and the same `sessionId`.
5. Call `tabs_finalize` once at the end. Use `keep` only for deliverable or
   handoff tabs.

Batch facade tools already own and clean up their tabs internally, so do not
wrap ordinary `browser.batch.*` calls in manual lifecycle steps unless a task
needs live tabs afterward.

## Safety Rules

- Treat tab URLs, page text, screenshots, cookies, account state, extension state, signed URLs, and tokens as sensitive.
- Never print the bro bearer token. It is acceptable to print the settings file path.
- Prefer background tabs with `active:false` unless foreground focus is part of the request.
- After discovery, never operate on "whatever tab is active". Record `browserId` and `tabId`, then pass them explicitly.
- Track every task-owned tab. Close it with `tabs_close`, `agent_done`, or `browser.flow.finish` unless the user asked to keep it open.
- In flow steps, use `select` for `<select>` option values. Eval code is a JavaScript expression with awaited Promises; wrap multiple statements in an IIFE instead of using a top-level `return`.
- Ask before submitting forms, sending messages, uploading files, making purchases, changing account settings, or reading pages likely to contain highly sensitive data.
- Keep bro generic. Do not add site-specific research policy to the bro bridge; put site workflows in downstream skills or task-local instructions.

## Common Calls

```bash
scripts/bro-call.mjs browser.extract '{"url":"https://example.com","active":false,"cleanup":true,"maxChars":8000}'
scripts/bro-call.mjs browser.current.extract '{"maxChars":8000}'
scripts/bro-call.mjs browser.batch.extract '{"urls":["https://example.com/a","https://example.com/b"],"concurrency":4,"maxChars":6000}'
scripts/bro-call.mjs browser.batch.flow '{"inputs":[{"id":"a","url":"https://example.com/a"},{"id":"b","url":"https://example.com/b"}],"steps":[{"type":"wait","ms":1000},{"type":"eval","code":"document.body.innerText"}],"concurrency":4,"cleanup":true}' --json
scripts/bro-call.mjs browser.network.capture '{"url":"https://example.com","code":"fetch(\"/api/data\").then(r => r.json())","urlIncludes":"/api/data","includeResponseBodies":true}' --json
scripts/bro-call.mjs browser.flow.start '{"url":"https://example.com","active":false}'
scripts/bro-call.mjs browser.flow.observe '{"sessionId":"SESSION_ID","mode":"text"}'
scripts/bro-call.mjs browser.flow.finish '{"sessionId":"SESSION_ID","cleanup":true}'
```

For structured output, add `--json`.

## Failure Handling

- Connection refused: start `bro serve` or verify the port.
- Missing `~/.bro/settings.json`: run `bro doctor` or `bro serve` from `/Users/yupeit/dev/bro` to initialize bro local state.
- Unauthorized MCP call: check that `~/.bro/settings.json` exists, the helper is reading that file, and the extension options use the same token.
- No browsers connected: connect the bro extension and verify `/status`.
- Unknown `browserId`: refresh `browsers_context`; do not silently fall back to another browser.
- `browser.network.capture` times out: verify the trigger expression actually executes (use `fetch(...)` or `() => fetch(...)`), narrow `urlIncludes`, and inspect the returned error. Do not replace it with cross-turn raw monitoring loops.
- `browser.extract` or `browser.current.extract` returns an error or a clearly partial/empty result: inspect diagnostics, then fall back in this order as relevant:
  1. Retry the same facade tool with `includeA11y:true`, `includeLinks:true` only if links matter, a larger `maxChars`, or a higher `minChars`.
  2. Use `browsers_context` and `tabs_context` only if you need to confirm connection state, find an existing tab, or recover a task-owned tab left open by a failed extraction.
  3. Use raw tab tools such as `get_page_text` or `extract_page` after pinning `browserId` and `tabId`.
  4. Use a browser flow when the page requires clicks, form input, navigation, or stateful observation.
