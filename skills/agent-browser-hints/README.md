# agent-browser-hints

Companion skill for [`agent-browser`](https://github.com/vercel-labs/agent-browser).

This skill does not replace the official `agent-browser` skill. It adds one narrow layer of guidance on top:

- how to choose between `--cdp` and `--session-name`
- when `state save/load` is the right tool
- when to use `auth save/login`
- how to avoid flaky login restore behavior

The goal is to give Codex and similar agents better judgment around authentication and session persistence without forking or patching the upstream `agent-browser` skill.

## What It Covers

`agent-browser-hints` focuses on the part that usually goes wrong in browser automation:

- durable login reuse
- OAuth / SSO flows
- 2FA follow-up sessions
- local Chrome attachment vs state snapshot tradeoffs
- `sessionStorage` pitfalls
- secret-safe login patterns

Core guidance:

- Default to attaching to local Google Chrome via `agent-browser --cdp 9222`.
- Prefer explicit `--cdp` over `--auto-connect` for deterministic browser selection.
- Keep durable browser state in the Chrome user data dir you launch, not in `agent-browser --profile`.
- Use `state save/load` for explicit portable snapshots.
- Treat `--session-name` as lightweight auto-restore, not a full browser profile.
- Load saved state into a fresh `agent-browser` session, not into a live `--cdp` browser.
- Use `auth save/login` when secret handling is the main concern.
- Treat `--extension <path>` as local unpacked-extension loading, not as a Web Store installer.

## Install

### Official skills CLI via mise

```bash
mise exec npm:skills -- skills add xiaotianxt/agent-browser-hints -g -a codex -y
```

### Directly with skills CLI

```bash
npx skills add xiaotianxt/agent-browser-hints -g -a codex -y
```

## Recommended Setup

Install this together with the official `agent-browser` skill:

```bash
mise exec npm:skills -- skills add vercel-labs/agent-browser -g -a codex -y
mise exec npm:skills -- skills add xiaotianxt/agent-browser-hints -g -a codex -y
```

Use the official skill for commands and workflow.
Use this companion skill for decision-making around auth and persistence.
Default attachment should be `--cdp 9222` when a local Chrome is available.

## When It Helps

Use this skill when the task involves:

- logging into a website and staying logged in
- deciding whether to attach to a local Chrome or persist a lightweight session
- debugging flaky restored sessions
- reusing sessions across multiple runs
- storing credentials without leaking them into shell history

Typical prompts:

- "Use agent-browser to log into this dashboard and keep the session reusable."
- "Should this flow use `--cdp` or `--session-name`?"
- "The restored login keeps breaking, what persistence mode should I use?"

## Design

This repository intentionally stays small.

- `SKILL.md` is the product.
- There is no fork of upstream `agent-browser`.
- The skill is meant to layer on top of the official one, not compete with it.

That keeps updates simple:

- upstream `agent-browser` can keep evolving independently
- these hints can stay opinionated and narrow
- users can install or remove this companion skill without touching the official skill

## Update

Check for updates:

```bash
mise exec npm:skills -- skills check
```

Update installed skills:

```bash
mise exec npm:skills -- skills update
```

## Repository

- Skill file: [`SKILL.md`](./SKILL.md)
- License: [`LICENSE`](./LICENSE)

## License

MIT
