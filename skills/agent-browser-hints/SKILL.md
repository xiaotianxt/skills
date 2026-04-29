---
name: agent-browser-hints
description: Companion skill for agent-browser. Use together with the official agent-browser skill when a task involves authentication, session persistence, local Chrome attachment via --cdp, auth vault, or flaky login restore. Helps choose between --cdp, --session-name, state save/load, and auth save/login.
---

# Agent Browser Hints

Use this skill alongside the official `agent-browser` skill when browser automation needs reliable login reuse through a user-managed local Chrome.

## Decision Rules

- Default to attaching to a locally running Google Chrome with `agent-browser --cdp 9222` for website login tasks.
  Prefer explicit `--cdp` over `--auto-connect` so the target browser stays deterministic.
- For OAuth/SSO, 2FA, IndexedDB-heavy apps, service workers, Chrome Web Store extensions, and any site that breaks if restore is flaky, launch a dedicated Chrome user data dir yourself and attach to it with `--cdp`.
- Use `agent-browser --session-name <name>` for lightweight auto-save/restore between browser restarts.
  Treat it as a portable auth snapshot, not a full browser profile.
- Use `agent-browser state save/load` when you need an explicit file for backup, transfer, or one-off replay.
- Use `agent-browser auth save/login` when the main problem is secret handling.
  Keep credentials out of shell history and let the vault manage them.

## Guardrails

- Before using `--cdp`, make sure Chrome is running with `--remote-debugging-port=9222` and that `curl http://127.0.0.1:9222/json/version` returns `200 OK`.
- Do not rely on `sessionStorage` as the primary auth mechanism. If a restored session is unstable, switch to a dedicated Chrome user data dir attached via `--cdp`.
- Keep one Chrome user data dir or session-name per site, account, and environment.
  Good examples: `github-work`, `github-personal`, `staging-admin`.
- Prefer explicit `--cdp 9222` over `--auto-connect` on shared machines or when multiple Chromium instances may be running.
- Do not assume Playwright's default Chromium is equivalent to your locally installed Google Chrome for login compatibility.
- Keep extension-enabled Chrome user data dirs separate from clean automation user data dirs.
  An extension-enabled browser is intentionally "dirty": it accumulates extensions, cookies, service workers, and browser settings over time.
- Wait for the final post-login URL or a clearly authenticated UI before saving state or closing the browser.
- Set `AGENT_BROWSER_ENCRYPTION_KEY` whenever you persist state files.
- Do not mix `agent-browser --profile` with `--cdp` for the same login flow.
  When you attach via CDP, the profile belongs to the Chrome process you launched, not to `agent-browser`.
- Do not try to `state load` into an already-running `--cdp` browser.
  Save from CDP if needed, then replay that state in a fresh `agent-browser`-managed browser session.
- Avoid mixing `--session-name` with `--state` in the same workflow unless you are debugging persistence behavior.
- Do not treat `--extension <path>` as a Chrome Web Store installer.
  It is for loading local unpacked extension directories, not for installing store extensions online.
- If you need Chrome Web Store installation, launch a local Chrome with a dedicated user data dir and `--remote-debugging-port=9222`.
  Install the extension once in that browser, then keep reusing it through `agent-browser --cdp 9222`.

## Recommended Flows

### Durable CDP Login

```bash
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PROFILE_DIR="$HOME/.agent-browser/profiles/myapp-prod-user1"

"$CHROME" \
  --remote-debugging-port=9222 \
  --user-data-dir="$PROFILE_DIR" \
  about:blank

agent-browser --cdp 9222 open https://app.example.com/login
agent-browser --cdp 9222 snapshot -i
agent-browser --cdp 9222 fill @e1 "$USERNAME"
agent-browser --cdp 9222 fill @e2 "$PASSWORD"
agent-browser --cdp 9222 click @e3
agent-browser --cdp 9222 wait --url "**/dashboard"

agent-browser --cdp 9222 open https://app.example.com/dashboard
```

### Durable Extension Profile

```bash
PROFILE_DIR="$HOME/.agent-browser/profiles/chrome-ublock-lite"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

"$CHROME" \
  --remote-debugging-port=9222 \
  --user-data-dir="$PROFILE_DIR" \
  about:blank

agent-browser --cdp 9222 open "https://chromewebstore.google.com/"

# Install the extension once in the visible Chrome window, then reuse the same profile.
agent-browser --cdp 9222 open "https://example.com"
```

### Lightweight Auto-Restore

```bash
agent-browser --session-name myapp open https://app.example.com/login
# ... login flow ...
agent-browser close

agent-browser --session-name myapp open https://app.example.com/dashboard
```

### Portable Snapshot

```bash
agent-browser --cdp 9222 open https://app.example.com/login
agent-browser --cdp 9222 snapshot -i
agent-browser --cdp 9222 fill @e1 "$USERNAME"
agent-browser --cdp 9222 fill @e2 "$PASSWORD"
agent-browser --cdp 9222 click @e3
agent-browser --cdp 9222 wait --url "**/dashboard"
agent-browser --cdp 9222 state save auth.json

# Replay that snapshot in a fresh agent-browser-managed session.
agent-browser state load auth.json
agent-browser open https://app.example.com/dashboard
```

### Secret-Safe Login

```bash
echo "pass" | agent-browser auth save github --url https://github.com/login --username user --password-stdin
agent-browser auth login github
# If Chrome is already running on 9222, continue the session with:
agent-browser --cdp 9222 open https://github.com/
```
