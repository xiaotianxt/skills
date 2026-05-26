---
name: helium-browser-mcp
description: Use when Codex needs to control or inspect the user's logged-in Helium browser through the locally installed OpenBrowserMCP extension. Trigger for requests about OpenBrowserMCP, Helium tabs, reading current browser tabs, browser MCP, openbrowsermcp, webpage interaction, or testing this local browser stack.
---

# Helium Browser MCP

Use this skill for the local OpenBrowserMCP + Helium setup.

## Local Services

- OpenBrowserMCP project: `/Users/yupeit/dev/openbrowsermcp`
- OpenBrowserMCP server: `http://127.0.0.1:3500`
- OpenBrowserMCP MCP endpoint: `http://127.0.0.1:3500/mcp`
- OpenBrowserMCP WebSocket bridge: `ws://127.0.0.1:3500/ws`
- Helium extension id: `ocjmfbmadhimfjoonaljbmpcfnbgiolc`
- OpenBrowserMCP token: `~/openbrowsermcp/settings.json`
Important: use `127.0.0.1`, not `localhost`, for OpenBrowserMCP. `localhost`
can resolve to IPv6 `::1`, while the server listens on IPv4.

## Privacy And Safety

Helium is the user's real browser profile. Treat tab URLs, page text, screenshots,
cookies, account state, and extension state as sensitive.

- Do not print the OpenBrowserMCP bearer token.
- Prefer read-only inspection first: `browsers_context`, `tabs_context`,
  `get_page_text`, `read_page`.
- Before submitting forms, sending messages, uploading files, making purchases,
  changing account settings, or reading highly sensitive pages, ask for explicit
  confirmation.
- For demos, create a new tab on `https://example.com` and operate only there.

## Quick Checks

```bash
curl -sS http://127.0.0.1:3500/status
```

If OpenBrowserMCP shows no connected extension, open the options page:

```bash
/usr/bin/open -b net.imput.helium chrome-extension://ocjmfbmadhimfjoonaljbmpcfnbgiolc/options.html
```

Then set:

- Server URL: `ws://127.0.0.1:3500/ws`
- Token: value from `~/openbrowsermcp/settings.json`

## Calling OpenBrowserMCP

Use the bundled helper so the token is read locally and not printed:

```bash
/Users/yupeit/dev/skills/skills/helium-browser-mcp/scripts/obmcp.mjs browsers_context
/Users/yupeit/dev/skills/skills/helium-browser-mcp/scripts/obmcp.mjs tabs_context '{"all":true}'
/Users/yupeit/dev/skills/skills/helium-browser-mcp/scripts/obmcp.mjs get_page_text '{"tabId":123,"browserId":"..."}'
```

## OpenCode Integration

OpenCode is configured globally in `/Users/yupeit/.config/opencode/opencode.json`
with an `openbrowsermcp` local MCP entry. It runs this stdio proxy:

```bash
/Users/yupeit/dev/skills/skills/helium-browser-mcp/scripts/openbrowsermcp-stdio-proxy.mjs
```

The proxy reads `~/openbrowsermcp/settings.json` locally and forwards to
`http://127.0.0.1:3500/mcp`, so the bearer token is not stored in OpenCode's
config file.

Verify OpenCode sees it:

```bash
opencode mcp list
```

Common tools:

- `browsers_context` lists connected Helium browser instances.
- `tabs_context` lists tabs. Pass `{"all":true,"browserId":"..."}`.
  After an agent has chosen a tab, pass `tabId` too so context is anchored to
  that tab's window/group instead of the user's foreground tab.
- `tabs_create` creates a new background tab by default. Pass
  `{"url":"https://example.com","browserId":"..."}` and keep the returned
  numeric tab ID for all later calls. Use `active:true` only when the user
  explicitly wants the tab brought to the foreground.
- `navigate` changes an existing tab. Pass
  `{"url":"https://example.com","tabId":123,"browserId":"..."}` when the
  current target tab can be overwritten instead of creating another tab.
- `tabs_close` closes a tab by ID. Use it for task-owned temporary tabs once
  they are no longer needed.
- `read_page` reads the accessibility tree. Requires `tabId`.
- `get_page_text` extracts `document.body.innerText`. Requires `tabId`.
- `find` searches accessible elements by description. Requires `tabId`.
- `click_element` clicks a ref from `find`/`read_page`. Requires `tabId`.
- `javascript_tool` evaluates page JavaScript. Requires `tabId`.

## Stable Tab Targeting

Do not operate by "whatever tab is active" after the first discovery step.
Helium is the user's real browser and they may continue using it while Codex is
working.

- Create or identify a target tab first, record both `browserId` and `tabId`,
  and pass them explicitly to every tab-targeted tool.
- For monitoring, call `read_network_requests`, `read_console_messages`, and
  `get_response_body` with the pinned `tabId`.
- When refreshing tab context during a task, use
  `tabs_context {"all":true,"tabId":123,"browserId":"..."}` so the listing is
  resolved relative to the pinned tab, not the user's current foreground tab.
- Avoid `tabs_activate` unless foreground focus is part of the user's request.
  CDP-backed tools such as `javascript_tool`, `read_page`, and monitoring work
  on background tabs.

## Tab Lifecycle

Keep the user's browser tidy.

- Track every tab created for the task. Before finishing, close task-owned tabs
  with `tabs_close` unless the user asked to keep them open or the tab now
  contains useful state the user expects to inspect.
- Prefer reusing the current target tab with `navigate` when moving to the next
  website and the current page can be safely overwritten. Do this for agent-
  created scratch tabs and for user-approved disposable pages.
- Do not overwrite or close tabs that existed before the task unless the user
  explicitly says the current page can be reused or closed.

For a safe smoke test:

```bash
scripts/obmcp.mjs browsers_context
scripts/obmcp.mjs tabs_context '{"all":true}'
scripts/obmcp.mjs tabs_create '{"url":"https://example.com"}'
```
