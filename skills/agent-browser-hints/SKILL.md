---
name: agent-browser-hints
description: Companion skill for agent-browser. Use together with the official agent-browser skill when a task involves browser automation, authentication, session persistence, or local CDP attachment. For this user, browser automation must attach only to the already-running Helium Chromium CDP endpoint.
---

# Agent Browser Hints

Use this skill alongside the official `agent-browser` skill when browser automation needs reliable login reuse through a user-managed browser.

For this user, the only allowed browser automation path is attaching to the already-running Helium Chromium browser through its CDP endpoint. Do not launch a new Chrome, Chromium, Playwright browser, temporary profile, persistent profile, or `agent-browser`-managed browser as a fallback.

`agent-browser --session <name>` is an agent-browser daemon/socket identity. It is not a browser login session, Chromium profile, cookie jar, or SSO state. When it is paired with `--cdp 9223`, page actions still occur inside the running Helium browser and its active Helium profile.

Source note: current `agent-browser` 0.26.x is daemon-based. If a daemon for a session name is already running, the CLI can reuse that daemon before reapplying `--cdp`. The launch logic distinguishes local launch vs external CDP, but does not fully prove that a reused external CDP daemon still points at the requested Helium endpoint. For Helium work, use a fresh task-scoped agent-browser daemon session and verify the CDP URL before touching pages.

Source note for windows/background work: current `agent-browser` tracks page targets globally across the attached browser, not per Helium window. New page targets from any Helium window are attached and registered. In current source, registering a new page sets `active_page_index` to that new page, and `tab <label>` calls CDP `Page.bringToFront`.

Design note from Obscura review, 2026-05-04: Obscura is useful as a CDP session/target design reference. It runs a separate lightweight headless engine and simulated CDP server, so it cannot replace this skill's Helium workflow. It does not attach to the user's Helium profile, extensions, cookies, OAuth/SSO state, or active tabs. For this skill, borrow only the architectural idea of explicit `sessionId -> targetId/pageId` routing.

## Decision Rules

- Attach only to Helium Chromium's existing CDP endpoint with `agent-browser --session <task-session> --cdp <helium-cdp-endpoint>`.
  On this machine, the expected Helium CDP port is `9223` unless the user says otherwise. If the endpoint is unknown or unreachable, stop and ask for the Helium CDP endpoint or for Helium to be started with CDP enabled.
- Use a short, task-scoped agent-browser session name, such as `helium-cmu-payroll` or `helium-download-check`. This isolates the agent-browser daemon from stale agent-browser state while preserving the Helium browser profile and login state.
- Do not use the default agent-browser session, a previously used session, or any named session whose CDP endpoint has not been verified in the current task.
- Every `agent-browser` command that touches a page must include the same `--session <task-session> --cdp <helium-cdp-endpoint>` pair.
- If a maintained target-pinned helper or target-id-aware `agent-browser` patch exists, prefer it for hard background work. It must attach to Helium's existing CDP endpoint, select one explicit page `targetId`, open a CDP session for that target, and route every page command through that session. It must not create a new browser profile or launch another browser.
- Prefer `tab new --label <label> <url>` and then `tab <label>` for task pages. The tab switch path calls CDP `Page.bringToFront`. Avoid `open <url>` unless you intentionally selected a disposable tab, because `open` navigates the current active tab inside Helium.
- For background operation, first bind the task target by label, snapshot it, then run action clusters without calling `tab`, `tab new`, `open`, or `window new`. If agent-browser's active tab drifts, re-bind with `tab <label>` and re-snapshot before continuing.
- Do not promise window-scoped isolation with stock agent-browser. It can target a labeled page, but it does not expose "only this Helium window" semantics.
- Do not use `--auto-connect`, `--profile`, `--session-name`, `state load`, or any command that can start or restore a different browser context.
- Do not use `agent-browser window new` for Helium login reuse. Current source creates a new browser context for `window new`, which is not the same as continuing in the user's normal Helium profile.
- Do not launch Chrome, Chromium, Helium, Playwright, or any browser process yourself for browser automation. Helium must already be running.
- For OAuth/SSO, 2FA, IndexedDB-heavy apps, service workers, extensions, and flaky login restore, continue using the same Helium CDP path. If Helium cannot satisfy the task, report the blocker instead of choosing another browser path.
- Use auth-vault or 1Password flows only for secret injection into page actions after attaching to Helium CDP. Do not use them to create a separate browser login/session path.

## Guardrails

- Before browser automation, verify the Helium CDP endpoint is reachable. A typical check is `curl http://127.0.0.1:<port>/json/version`, adjusted to the configured Helium endpoint.
- Verify `agent-browser --session <task-session> --cdp <port> get cdp-url` matches the Helium `/json/version` `webSocketDebuggerUrl` host and port before navigating or clicking.
- Cross-check tab inventory if anything looks stale: compare `agent-browser --session <task-session> --cdp <port> --json tab list` with `curl http://127.0.0.1:<port>/json/list`. The agent-browser list intentionally omits internal tabs such as `chrome://newtab`, extension pages, workers, and iframes.
- Before acting in the background, verify `agent-browser --session <task-session> --cdp <port> --json tab list` marks the task label as active and `agent-browser ... get url` is the expected URL.
- Treat any user-created Helium tab/window during the task as a possible active-target invalidation event. After that, do not reuse refs until `tab <label>` and a fresh `snapshot -i` have succeeded.
- Never use Playwright's default Chromium, Google Chrome, system Chromium, or `npx agent-browser` as a browser fallback.
- Never persist or replay browser state with `agent-browser state save/load` for this user's browser automation unless explicitly requested for diagnostics. The active browser state belongs to Helium.
- Do not close, restart, or mutate Helium's launch profile unless the user explicitly asks.
- It is safe to close the task-scoped agent-browser daemon after use with `agent-browser --session <task-session> close`. For external CDP connections, current agent-browser disconnects the daemon without closing Helium.
- If a login is missing, a session is stale, an extension is needed, or the CDP endpoint is down, ask the user to handle or approve the Helium-side change. Do not create another route.

## Background And Multi-Window Boundaries

What works with stock `agent-browser`:

- It can continue sending CDP actions to a labeled task tab while another Helium tab/window is visible, as long as agent-browser's internal active tab remains the task label.
- Complex background action clusters work after binding the task tab: snapshot refs, form fill, select, checkbox, CSS selector clicks, iframe refs, `wait --text`, `eval`, and screenshots.
- If a command only interacts with the current agent-browser active target (`fill`, `click`, `eval`, `snapshot`, `screenshot`, `get`, `wait`) and no new Helium page target steals active status, it does not need to bring the task tab forward.

What does not work as a stock guarantee:

- No strict "never activate my UI" guarantee. `tab <label>` calls `Page.bringToFront`, and `tab new`/Chrome target creation can surface a tab.
- No strict "only operate in this Helium window" guarantee. The attached CDP endpoint exposes all page targets in the browser profile, across Helium windows.
- No stable background guarantee while the user is opening new Helium tabs/windows. New page targets can be added to the same agent-browser daemon and become its active page.

Preferred hard-isolation direction:

- Add a small target-pinned raw CDP helper, or patch `agent-browser` to expose the same behavior.
- The helper should discover targets from `http://127.0.0.1:<port>/json/list`, select a target by explicit `targetId`, URL, or caller-provided label, and create or remember a CDP `sessionId` with `Target.attachToTarget`.
- Commands must be sent with that `sessionId`, and should never depend on `agent-browser`'s active page index, global active tab, or `Page.bringToFront`.
- Target-pinned commands may still mutate the selected page, navigate it, or trigger downloads; they are isolation from active-tab drift, not read-only safety.
- If a selected target is gone, detached, or navigated unexpectedly, stop and rediscover targets instead of falling back to the global active tab.
- Keep this helper separate from Obscura. Obscura's simulated browser is appropriate for stateless scraping experiments, while Helium login reuse requires the real Helium CDP endpoint.

Practical operating model:

1. Use a task-scoped agent-browser daemon session.
2. Create or identify one labeled task tab.
3. Run `tab <label>` once to bind the active target. Expect this to foreground that tab.
4. Snapshot and perform a cluster of actions without more `tab` or `open` calls.
5. If the user changes Helium windows/tabs or opens a new page, assume active target may have drifted. Verify with `tab list`/`get url`; if needed, re-run `tab <label>` and re-snapshot.
6. For hard background/window-pinned automation, use a target-id-specific raw CDP helper or patch agent-browser to support target/window pinning. Stock CLI is only the compatibility fallback.

## Target-Pinned Helper Contract

Use this contract when creating a helper or evaluating an `agent-browser` patch for this skill. The goal is to eliminate active-tab drift while preserving the user's existing Helium browser state.

Current local helper:

- Source: `scripts/helium-cdp-pin.mjs`
- Installed command: `helium-cdp-pin`
- Runtime: Node.js with built-in `fetch` and `WebSocket`; no npm dependencies.
- CDP discovery: defaults to `--cdp auto`, which reads Helium's `DevToolsActivePort` from `~/Library/Application Support/net.imput.helium`, verifies the exact WebSocket path, then falls back to common explicit ports.
- CDP authorization: run `helium-cdp-pin enable` to open `chrome://inspect/#remote-debugging` in Helium and wait while the user approves the Helium remote debugging prompt.
- Binding state: `~/.local/state/helium-cdp-pin/bindings.json` unless `HELIUM_CDP_PIN_STATE` is set.

Required behavior:

- Connect only to the user-provided Helium CDP endpoint or to the endpoint discovered from Helium's `DevToolsActivePort`.
- Prefer the exact WebSocket path from `DevToolsActivePort`. Do not rely on `/json/version` when Helium/Chromium remote-debugging authorization exposes only a direct WebSocket path.
- Select a page by stable `targetId` whenever possible. URL/title matching can be used for discovery, but the chosen target must be converted to a concrete `targetId` before action.
- Attach with `Target.attachToTarget` and keep the returned `sessionId`.
- Route all target-specific calls with that `sessionId`, including `Runtime.evaluate`, `DOM.*`, `Page.*`, `Input.*`, and `Network.*`.
- Keep a local mapping of task label to `{targetId, sessionId, url_at_bind}` for diagnostics.
- Before each action cluster, verify `Target.getTargetInfo` for the pinned `targetId`. If the target is missing or the URL no longer matches the task intent, stop and report the mismatch.
- Avoid `Page.bringToFront` except when the user explicitly asks to foreground the task page.
- Do not launch, close, restart, or mutate Helium itself. Closing a helper connection must only detach/disconnect from CDP.
- Do not silently fall back to stock `agent-browser` active-tab commands after a pinning failure.

Recommended command surface for a helper:

```bash
helium-cdp-pin enable
helium-cdp-pin list
helium-cdp-pin bind --label taskpage --target-id <id>
helium-cdp-pin bind --label taskpage --url-prefix https://app.example.com/
helium-cdp-pin eval --label taskpage "document.title"
helium-cdp-pin snapshot --label taskpage
helium-cdp-pin click --label taskpage "#save"
helium-cdp-pin fill --label taskpage "#name" "value"
helium-cdp-pin screenshot --label taskpage /tmp/task.png
helium-cdp-pin detach --label taskpage
```

Implementation guidance:

- Prefer a small standalone helper first. It is easier to verify than a broad `agent-browser` daemon patch.
- A patch to `agent-browser` should add an explicit `--target-id` or `--target-label` mode that bypasses global active page selection for all compatible commands.
- Keep the first version narrow: `list`, `bind`, `eval`, `get url/title`, `screenshot`, and simple selector click/fill are enough to validate the model.
- Add a regression that creates a second Helium target after binding, then proves commands still affect the pinned target without re-selecting or foregrounding it.

Validated local test, 2026-04-30:

- Attached `agent-browser --session helium-bg-qa-20260430 --cdp 9223` to Helium.
- Opened a labeled local task page, then activated a different Helium target with raw CDP.
- Verified `get url` and `snapshot -i` still targeted the labeled page when no new page target stole active status.
- Completed background form actions: fill textboxes, select an option, click by CSS selector, fill/click inside an iframe, wait for saved text, read `localStorage`, and screenshot the background task page.
- Observed failure mode: when the user opened a new Helium window/page during the task, agent-browser registered the new target and active target drifted to the user's page. Rebinding with `tab <label>` restored the task page.

## Upgrade Regression Protocol

Run this protocol whenever `agent-browser` is upgraded, rebuilt from source, or its daemon/CDP/tab code changes. The goal is to validate the Helium-only workflow rather than the general agent-browser feature set.

Behavior contract to preserve:

- Helium is the only browser process used. No Chrome/Chromium/Playwright/agent-browser-managed browser may be launched as fallback.
- A task-scoped `--session` is only an agent-browser daemon identity. It must not create a new browser profile or separate login state when paired with `--cdp 9223`.
- A fresh `--session <task> --cdp 9223` must resolve to the same WebSocket URL as `http://127.0.0.1:9223/json/version`.
- Closing the task-scoped agent-browser session must disconnect from external CDP without closing Helium.
- A labeled task tab can be created or selected and then used for snapshot/ref/click/fill/eval/wait/screenshot work.
- Background action clusters are allowed only after the task label is bound and verified active inside agent-browser.
- If a new Helium page target appears during a task, assume active target drift until verified. Future versions may fix this; until verified, keep this conservative rule.
- Stock agent-browser must not be treated as window-pinned unless a new version explicitly exposes and validates window/target pinning.
- A target-pinned helper or patched `agent-browser --target-id` mode must prove that commands continue to hit the pinned target after another Helium page target is created or activated.

Regression setup:

1. Confirm Helium is already running with CDP on the expected port.

   ```bash
   HELIUM_CDP="9223"
   TASK_SESSION="helium-regression-$(date +%Y%m%d-%H%M%S)"
   TASK_LABEL="helium_regression"

   curl -s "http://127.0.0.1:${HELIUM_CDP}/json/version"
   ```

2. Confirm agent-browser attaches to that exact Helium endpoint.

   ```bash
   RAW_WS="$(curl -s "http://127.0.0.1:${HELIUM_CDP}/json/version" | jq -r .webSocketDebuggerUrl)"
   AB_WS="$(agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" get cdp-url)"
   test "$RAW_WS" = "$AB_WS"
   ```

3. Use this skill's fixture page at `references/helium-regression-fixture.html`. Copy it to `/tmp/helium-agent-browser-regression.html` before opening it in Helium.

   ```bash
   cp /Users/yupeit/dev/skills/skills/agent-browser-hints/references/helium-regression-fixture.html /tmp/helium-agent-browser-regression.html
   ```

   The fixture contains:

   - normal text inputs with ids `#name`, `#email`, and `#notes`,
   - a select with id `#role` and option value `staff`,
   - a checkbox with id `#agree`,
   - buttons `#add` and `#save` that mutate DOM/localStorage,
   - an iframe `#child` with one input and one button.

4. Open the fixture as a labeled task tab and verify it appears in both agent-browser and raw Helium target inventory.

   ```bash
   FIXTURE_URL="file:///tmp/helium-agent-browser-regression.html"

   agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" tab new --label "$TASK_LABEL" "$FIXTURE_URL"
   agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" tab "$TASK_LABEL"
   agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" --json tab list
   curl -s "http://127.0.0.1:${HELIUM_CDP}/json/list"
   ```

5. Snapshot and verify refs include the main form and iframe controls.

   ```bash
   agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" snapshot -i
   ```

6. If a separate foreground target exists, activate it with raw CDP, then run a background action cluster without any `tab`, `tab new`, `open`, or `window new` command.

   ```bash
   # Optional foreground restore:
   # curl -s "http://127.0.0.1:${HELIUM_CDP}/json/activate/${USER_TARGET_ID}"

   agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" get url
   agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" fill "#name" "Grace Hopper"
   agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" fill "#email" "grace@example.test"
   agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" fill "#notes" "background regression"
   agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" select "#role" staff
   agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" check "#agree"
   agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" click "#add"
   agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" click "#add"

   # Re-snapshot before using refs. For iframe controls, either switch into
   # the iframe and use fresh refs, or use refs in the inlined iframe subtree.
   agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" frame "#child"
   agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" snapshot -i
   agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" fill @e1 "BG-9000"
   agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" click @e2
   agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" frame main

   agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" click "#save"
   agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" wait --text "saved:"
   agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" eval "localStorage.getItem('heliumBgProfile')"
   agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" screenshot /tmp/helium-agent-browser-regression.png
   ```

   Re-snapshot before using iframe refs if any frame-related CDP error appears. Frame refs are not stable across frame reloads or target changes.

7. Test active-target drift explicitly.

   ```bash
   agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" tab "$TASK_LABEL"
   NEW_TARGET_ID="$(curl -s -X PUT "http://127.0.0.1:${HELIUM_CDP}/json/new?about:blank" | jq -r .id)"
   agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" --json tab list
   agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" get url
   curl -s "http://127.0.0.1:${HELIUM_CDP}/json/close/${NEW_TARGET_ID}"
   ```

   Expected for agent-browser 0.26.x: a newly created Helium page target may become agent-browser's active tab. If a future version keeps the task label active, update this skill to describe the stronger behavior.

8. If a target-pinned helper or patch is available, validate it against the same drift case.

   ```bash
   # Example command names only; adapt to the actual helper or patch.
   TASK_TARGET_ID="$(curl -s "http://127.0.0.1:${HELIUM_CDP}/json/list" | jq -r '.[] | select(.url == "file:///tmp/helium-agent-browser-regression.html") | .id' | head -n 1)"
   helium-cdp-pin --cdp "$HELIUM_CDP" bind --label "$TASK_LABEL" --target-id "$TASK_TARGET_ID"
   NEW_TARGET_ID="$(curl -s -X PUT "http://127.0.0.1:${HELIUM_CDP}/json/new?about:blank" | jq -r .id)"
   helium-cdp-pin --cdp "$HELIUM_CDP" eval --label "$TASK_LABEL" "document.location.href"
   helium-cdp-pin --cdp "$HELIUM_CDP" fill --label "$TASK_LABEL" "#name" "Pinned Target"
   helium-cdp-pin --cdp "$HELIUM_CDP" eval --label "$TASK_LABEL" "document.querySelector('#name').value"
   curl -s "http://127.0.0.1:${HELIUM_CDP}/json/close/${NEW_TARGET_ID}"
   ```

   Expected for a target-pinned implementation: the evaluated URL and DOM mutation come from the original fixture target even after a new Helium target exists.

9. Cleanup.

   ```bash
   agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" tab close "$TASK_LABEL"
   agent-browser --session "$TASK_SESSION" close
   curl -s "http://127.0.0.1:${HELIUM_CDP}/json/version"
   agent-browser session list
   ```

Pass criteria:

- The CDP WebSocket URLs match.
- Helium remains running after task session close.
- The task tab appears in raw Helium target inventory.
- The background cluster mutates the fixture page and returns the expected DOM/localStorage value.
- Screenshots come from the task page, not the user's foreground page.
- If drift occurs after creating a new target, the documented re-bind workflow (`tab <label>` then fresh `snapshot -i`) restores the task tab.
- If a target-pinned helper or patch is present, the pinned-target regression keeps acting on the original `targetId` after a second target is created or activated.

Failure triage:

- If `get cdp-url` differs from raw Helium `/json/version`, stop. The daemon is not attached to the intended Helium endpoint.
- If `tab list` shows a user page as active before an action cluster, do not continue. Re-bind the label and re-snapshot.
- If a command acts on the user's foreground page, close the task-scoped agent-browser session, leave Helium running, and inspect `tab list` plus raw `/json/list`.
- If a future version supports target/window pinning, prefer that over label rebinding after it passes the pinned-target regression. Update this skill with the exact command and result.

## Recommended Flows

### Helium CDP Attachment With Fresh Agent-Browser Daemon

```bash
HELIUM_CDP="9223"
TASK_SESSION="helium-<task>"
TASK_LABEL="taskpage"
TARGET_URL="https://app.example.com/"

curl -s "http://127.0.0.1:${HELIUM_CDP}/json/version"
agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" get cdp-url

agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" --json tab list
curl -s "http://127.0.0.1:${HELIUM_CDP}/json/list"

agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" tab new --label "$TASK_LABEL" "$TARGET_URL"
agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" tab "$TASK_LABEL"
agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" snapshot -i

agent-browser --session "$TASK_SESSION" close
```

### Background Action Cluster

```bash
HELIUM_CDP="9223"
TASK_SESSION="helium-<task>"
TASK_LABEL="taskpage"

# Bind task tab. This may foreground it once.
agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" tab "$TASK_LABEL"
agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" --json tab list
agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" get url
agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" snapshot -i

# Optional: if a known user foreground target must be restored, activate it
# with raw Helium CDP before running the action cluster.
# curl -s "http://127.0.0.1:${HELIUM_CDP}/json/activate/${USER_TARGET_ID}"

# Background-safe cluster: do not call tab/open/window commands inside it.
agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" fill @e1 "value"
agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" click "#save"
agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" wait --text "Saved"
agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" eval "document.title"
agent-browser --session "$TASK_SESSION" --cdp "$HELIUM_CDP" screenshot /tmp/task.png
```

### Target-Pinned Helper Flow

Use this only when a validated helper or patched `agent-browser` target-id mode exists.

```bash
TASK_LABEL="taskpage"
TARGET_URL_PREFIX="https://app.example.com/"

helium-cdp-pin enable
helium-cdp-pin list
helium-cdp-pin bind --label "$TASK_LABEL" --url-prefix "$TARGET_URL_PREFIX"
helium-cdp-pin eval --label "$TASK_LABEL" "document.location.href"

# These commands should stay pinned to the bound target even if the user
# opens another Helium tab or window.
helium-cdp-pin fill --label "$TASK_LABEL" "#name" "value"
helium-cdp-pin click --label "$TASK_LABEL" "#save"
helium-cdp-pin eval --label "$TASK_LABEL" "document.title"
helium-cdp-pin screenshot --label "$TASK_LABEL" /tmp/task.png
helium-cdp-pin detach --label "$TASK_LABEL"
```
