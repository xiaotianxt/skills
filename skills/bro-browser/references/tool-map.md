# Bro Tool Map

Prefer facade tools before raw extension tools. They encode bro's cleanup, bounded concurrency, and readiness policy.

## Facade Tools

`browser.extract`

- Use for one URL.
- Required: `url`.
- Useful options: `id`, `minChars`, `maxChars`, `maxLinks`, `includeA11y`, `includeLinks`, `cleanup`, `active`, `browserId`.
- Defaults: `maxChars:8000`, `includeLinks:false`, `includeA11y:false`, `cleanup:true`, `active:false`.
- Output includes status, text, optional links, and diagnostics.

`browser.current.extract`

- Use for the current/default active tab when the user says the page is already open.
- Useful options: `id`, `minChars`, `maxChars`, `maxLinks`, `includeA11y`, `includeLinks`, `browserId`.
- Defaults: `maxChars:8000`, `includeLinks:false`, `includeA11y:false`.
- Prefer this over `browsers_context` + `tabs_context` + raw text reads when the current page is unambiguous.

`browser.batch.extract`

- Use for multiple independent URLs when links or diagnostics matter.
- Provide either `urls` or `inputs`; do not provide both.
- Defaults: `concurrency:6`, `maxChars:8000`, `includeLinks:false`, `cleanup:true`, `active:false`.
- Use `inputs` with `{id,url}` when stable IDs matter.

`browser.batch.flow`

- Use for multiple independent URLs that need the same ordered interaction, such as opening the same modal on every product page and reading structured page data.
- Provide either `urls` or `inputs`; do not provide both.
- Required: `steps`.
- Step types are the same as `browser.flow.act`: `goto`, `eval`, `click`, `fill`, `select`, `wait`, and `read_text`.
- Defaults: `concurrency:6`, `timeoutMs:12000` per URL, `cleanup:true`, `active:false`.
- Prefer this over many separate `browser.flow.start` + `browser.flow.act` + `browser.flow.finish` calls when the per-page workflow is identical.

`browser.console.capture`

- Use when an action or JavaScript expression should emit console logs or exceptions.
- Required: `url`, `code`.
- Monitoring, trigger execution, collection, and cleanup remain inside one call.

`browser.network.capture`

- Use when an action or JavaScript expression should trigger inspectable requests.
- Required: `url`, `code`.
- Matching requests, optional headers/post data, bounded response bodies, and cleanup remain inside one call.

`browser.flow.start`

- Use for a single stateful page interaction.
- Required: `url`.
- Defaults: `active:false`, `cleanup:true`.
- Save `sessionId`.

`browser.flow.observe`

- Required: `sessionId`.
- `mode:"text"` by default; use `mode:"a11y"` for controls and labels.

`browser.flow.act`

- Required: `sessionId`, `steps`.
- Step types: `goto`, `eval`, `click`, `fill`, `select`, `wait`, `read_text`.
- For iframe work, call `frames_list` and pass its `frameId` to eval, click, fill, select, or read_text.
- Stops at first failed step and returns prior step results plus failure location.

`browser.flow.finish`

- Required: `sessionId`.
- Use `cleanup:true` unless the user asked to keep the tab.

## Raw Browser Tools

Use raw tools when operating on an existing tab, debugging, uploading, or using page primitives unavailable through flow.

- `browsers_context`: list connected browser instances and browser IDs.
- `tabs_context`: list tabs; pass `all:true` for a full listing.
- `session_name`: name a multi-tab automation session.
- `tabs_claim`: attach an existing tab to a session without marking it owned.
- `tabs_finalize`: close owned session tabs not listed in `keep`.
- `tabs_create`: create a tab; default to `active:false`; pass `sessionId` to make it session-owned.
- `tabs_close`: close a known tab ID.
- `navigate`: navigate a known tab.
- `get_page_text`: compatibility/internal text primitive; prefer extraction or flow tools.
- `read_page`: read the accessibility tree.
- `find`: find an accessible element by description.
- `click_element`: click a `refId`.
- `fill_element`: clear and type into a `refId`.
- `form_input`: set an input value by `refId`.
- `frames_list`: list frame IDs for frame-aware flow steps.
- `javascript_tool`: evaluate page JavaScript, optionally in a frame ID.
- `read_console_messages`: best-effort cross-turn console primitive; prefer `browser.console.capture`.
- `read_network_requests` and `get_response_body`: compatibility primitives; prefer `browser.network.capture`.
- `file_upload` and `upload_image`: upload through a file input after confirmation.
- `computer`: screenshot and low-level input when DOM primitives are insufficient. Screenshots report CSS viewport/device-scale coordinate guidance. Real input activates and focuses the target tab/window; screenshots and zoom stay background-capable.

For tab-targeted raw tools, pass `browserId` and `tabId` explicitly. Do not depend on the active tab.

## Helper Script

The bundled helper calls bro's Streamable HTTP MCP endpoint and reads the bearer token from `~/.bro/settings.json`.

```bash
scripts/bro-call.mjs <tool-name> [json-arguments]
scripts/bro-call.mjs --list
scripts/bro-call.mjs --status
scripts/bro-call.mjs browser.extract '{"url":"https://example.com"}' --json
scripts/bro-call.mjs browser.batch.flow '{"urls":["https://example.com/a","https://example.com/b"],"steps":[{"type":"wait","ms":1000},{"type":"eval","code":"document.title"}],"concurrency":4}' --json
```

Use `--json` when you need `sessionId`, structured diagnostics, or exact result fields.

## Error Interpretation

- `No browsers connected`: the server is up but no extension authenticated over `/ws`.
- `Browser ... not found`: refresh `browsers_context`; never silently retarget.
- `requires tabId`: choose a tab first with `tabs_context` or create one with `tabs_create`.
- Frame element not found: refresh `frames_list` after navigation and pass the exact child `frameId` to a flow step.
- CDP input timeout: do not repeat identical coordinates; confirm the target is a normal web tab and account for the screenshot's CSS-pixel/device-scale guidance.
- `partial`: extraction produced some data but readiness did not meet quality thresholds; inspect diagnostics and retry with a better method.
- Missing `~/.bro/settings.json`: bro has not initialized local state.
- HTTP 401 or unauthorized: token mismatch between the helper, server, or extension options.
