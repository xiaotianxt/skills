# Bro Browser Workflows

Use these recipes to translate user outcomes into stable bro calls.

## Read-Only Orientation

Use this when the user asks about current browser state, open tabs, or whether bro is working.

1. Check server status:

```bash
scripts/bro-call.mjs --status
```

2. Confirm bro local state exists:

```bash
ls -l ~/.bro/settings.json
```

If the settings file is missing, initialize bro with `bro doctor` or `bro serve`.

3. Check connected browser instances:

```bash
scripts/bro-call.mjs browsers_context
```

4. List tabs only after a browser is connected:

```bash
scripts/bro-call.mjs tabs_context '{"all":true}'
```

If the output includes a `browserId`, reuse it in later calls. If you target an existing tab, record its `tabId` and pass both IDs explicitly.

## Extract Known URLs

Use `browser.extract` for one URL:

```bash
scripts/bro-call.mjs browser.extract '{"url":"https://example.com","maxChars":8000,"cleanup":true}'
```

Use `browser.batch.extract` for multiple URLs:

```bash
scripts/bro-call.mjs browser.batch.extract '{"inputs":[{"id":"a","url":"https://example.com/a"},{"id":"b","url":"https://example.com/b"}],"concurrency":4,"maxChars":6000,"cleanup":true}'
```

Prefer `inputs` with stable IDs when the answer must cite which URL produced each result. Add `includeLinks:true` only when URLs are part of the answer or the next crawl step. Keep `cleanup:true` unless the user needs to inspect the opened tabs.

## Repeated Interaction Across Known URLs

Use `browser.batch.flow` when each independent URL needs the same ordered interaction before extraction. This avoids creating, acting on, and finishing many separate flow sessions from the agent side.

Example: open product pages, wait for render, click a common reviews button by JavaScript, wait for the modal, and return a compact structured result from each page.

```bash
scripts/bro-call.mjs browser.batch.flow '{
  "inputs": [
    {"id": "item-a", "url": "https://example.com/a"},
    {"id": "item-b", "url": "https://example.com/b"}
  ],
  "steps": [
    {"type": "wait", "ms": 2000},
    {"type": "eval", "code": "(() => { const button = [...document.querySelectorAll(\"button\")].find((node) => /reviews/i.test(node.innerText || node.getAttribute(\"aria-label\") || \"\")); if (button) button.click(); return Boolean(button); })()"},
    {"type": "wait", "ms": 1000},
    {"type": "eval", "code": "(() => ({ title: document.title, text: document.body.innerText.slice(0, 4000) }))()"}
  ],
  "concurrency": 6,
  "timeoutMs": 15000,
  "cleanup": true
}' --json
```

Keep the `steps` generic and site-local to the task. Do not put site-specific scraping policy into bro itself.

## Sequential Page Interaction

Use a flow when a page needs clicks, filling, waiting, or navigation state.

1. Start a background flow:

```bash
scripts/bro-call.mjs browser.flow.start '{"url":"https://example.com","active":false,"cleanup":true}' --json
```

2. Save `sessionId` from the structured result.

3. Observe the page:

```bash
scripts/bro-call.mjs browser.flow.observe '{"sessionId":"SESSION_ID","mode":"text"}'
```

4. Act with ordered steps:

```bash
scripts/bro-call.mjs browser.flow.act '{"sessionId":"SESSION_ID","steps":[{"type":"click","css":"button[type=submit]"},{"type":"wait","ms":500},{"type":"read_text"}]}' --json
```

5. Finish even if a step failed:

```bash
scripts/bro-call.mjs browser.flow.finish '{"sessionId":"SESSION_ID","cleanup":true}'
```

Use `mode:"a11y"` when visible text is insufficient to identify controls. Ask for explicit confirmation before a flow submits data or changes user state.

## Existing Tab Inspection

Use this when the user asks about an already open tab or says to use their current logged-in browser.

If the current tab is the target, do one call:

```bash
scripts/bro-call.mjs browser.current.extract '{"maxChars":8000}'
```

Only use tab discovery when the current tab is ambiguous, the user mentioned a non-current open tab, or current extraction fails.

1. Call `browsers_context`.
2. Call `tabs_context {"all":true,"browserId":"..."}`.
3. Identify the target tab from title and URL.
4. Read the tab with `get_page_text` or `read_page`, always passing `browserId` and `tabId`.

Example:

```bash
scripts/bro-call.mjs get_page_text '{"browserId":"BROWSER_ID","tabId":123,"maxChars":12000}'
scripts/bro-call.mjs read_page '{"browserId":"BROWSER_ID","tabId":123,"filter":"interactive","compact":true,"maxChars":20000}'
```

Do not use foreground focus as identity after this point. The user may keep using the browser while the agent works.

## Debug A Local Web App

Use this for localhost app testing when the user wants browser-side console, network, or DOM evidence.

1. Create a background tab:

```bash
scripts/bro-call.mjs tabs_create '{"url":"http://127.0.0.1:3000","active":false}' --json
```

2. Save `browserId` and `tabId`.
3. Read page text or accessibility tree.
4. Inspect console and network:

```bash
scripts/bro-call.mjs read_console_messages '{"browserId":"BROWSER_ID","tabId":123,"clear":false}'
scripts/bro-call.mjs read_network_requests '{"browserId":"BROWSER_ID","tabId":123,"filter":"failed","timeoutMs":3000}'
```

5. Close task-owned tabs:

```bash
scripts/bro-call.mjs tabs_close '{"browserId":"BROWSER_ID","tabId":123}'
```

If the task needs screenshots or visual QA, use browser-specific tooling available in the session when required by the frontend workflow; bro is best for browser state and extraction.

## Cleanup

For raw tabs, call `tabs_close` on every tab you created. For flow sessions, call `browser.flow.finish`. For multi-tab agent work, `agent_done` can signal the session end:

```bash
scripts/bro-call.mjs agent_done '{"browserId":"BROWSER_ID","tabIds":[123,124]}'
```

Do not close tabs that existed before the task unless the user explicitly asked for that.
