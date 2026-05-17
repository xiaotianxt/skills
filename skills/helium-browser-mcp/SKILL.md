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
- `tabs_create` creates a new tab. Pass `{"url":"https://example.com","browserId":"..."}`.
- `read_page` reads the accessibility tree. Requires `tabId`.
- `get_page_text` extracts `document.body.innerText`. Requires `tabId`.
- `find` searches accessible elements by description. Requires `tabId`.
- `click_element` clicks a ref from `find`/`read_page`. Requires `tabId`.
- `javascript_tool` evaluates page JavaScript. Requires `tabId`.

For a safe smoke test:

```bash
scripts/obmcp.mjs browsers_context
scripts/obmcp.mjs tabs_context '{"all":true}'
scripts/obmcp.mjs tabs_create '{"url":"https://example.com"}'
```
