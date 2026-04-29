# Product Method

## The Pattern

The repeated shape across `tg`, `cx`, and `mon` is:

1. Find a repeated local job that is painful enough to deserve a command.
2. Collapse the job into a small command taxonomy.
3. Implement a direct, local, deterministic vertical slice.
4. Add diagnostics and recovery paths before broadening features.
5. Make the tool agent-native with JSON output and stable error behavior.
6. Ship it like a real product: docs, CI, release assets, Homebrew, installed smoke test.

## Product Frame Template

Use this before writing code:

```text
<name> is a <platform/domain> CLI for <user job>.
It should let a user/agent do <primary outcome> without manually doing <old workflow>.
The first shipped slice is <smallest real command set>.
It is not <non-goals>.
```

Examples:

- `tg`: read/search/export local chat history without manually opening databases.
- `cx`: launch Codex through the best available auth slot without manual account rotation.
- `mon`: query Monarch data through a stable local CLI without browser scraping.

## Command Taxonomy

Prefer this order:

1. Primary task command: the thing users actually came for.
2. Discovery command: list/find/select available targets.
3. Data command: stable JSON for agents and scripts.
4. Maintenance command: refresh/cache/auth/install.
5. Diagnostic command: `doctor`, with read-only checks by default.
6. Escape hatch: raw API/query command for future needs.

Avoid exposing implementation chores as the first screen unless the domain
requires setup. If setup is required, make it explicit and diagnoseable.

## AI-Native Contract

AI-native means an agent can operate the tool without screen scraping or hidden
state guesses:

- `--json` for data-bearing commands.
- Machine-readable rows with stable field names.
- Human tables for quick terminal use.
- Secrets never printed by default.
- Errors include the failing subsystem and next useful action.
- Commands can be composed in shell pipelines.
- Local state paths can be overridden by env vars or flags.

## Boundary Discipline

When a user asks for a specific workflow while building a general tool, separate
the layers:

- Put **generic access** in the CLI.
- Put **domain-specific reconciliation or analysis** in a project folder,
  downstream script, or separate skill.
- Promote a domain workflow into the CLI only after it proves general and stable.

The `mon` rent detour is the cautionary case: payment reconciliation belonged in
the rent tracking folder, while `mon` should stay a general Monarch API surface.

## First Slice

For a new CLI, ship the smallest version that can be used immediately:

- `auth/status` or equivalent local setup if needed.
- One read-only command that returns real useful data.
- `--json`.
- `doctor`.
- README install/usage.
- CI and release path.

Only add mutation commands after read-only behavior is verified.
