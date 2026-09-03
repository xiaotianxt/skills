# Skill Portfolio Governance

This repository is a portfolio of skills, not a flat pile of prompts. Each
skill should have a clear job, a clear trigger, and a clear reason to exist next
to the others.

## Skill Roles

Use these roles when adding, reviewing, or refactoring skills:

| Role | Purpose | Examples |
| --- | --- | --- |
| Governor | Sets taste, risk posture, and review standards across tasks. | `design-decisions`, `rust-systems-style` |
| Product workflow | Turns a broad user goal into a repeatable multi-step outcome. | `ship-ai-native-cli`, `exam-review` |
| Tool control | Operates a specific local app, CLI, API, or data source. | `tg`, `cx`, `mon`, `canvas`, `things3`, `1password` |
| Generated tool family | Mirrors a large API surface through narrow generated commands. | `gws-*`, `gws-shared` |
| Router | Chooses among neighboring skills for a domain before execution. | `gws`, `github` |
| Asset transformer | Converts a specific input artifact into a specific output artifact. | `extract-transparent-signature` |

A skill can cooperate with other skills, but it should not silently absorb
their responsibilities.

## Boundary Rules

- A governor skill should not become a tool manual.
- A tool-control skill should not become a product-planning workflow.
- A product workflow may call tool skills, but it should not duplicate their API
  details.
- A generated family should keep command specifics in generated leaf skills and
  shared auth/safety rules in the shared skill.
- A router skill should choose the right neighboring skill, then hand off rather
  than absorbing every command detail.
- Sensitive auth and secret-handling rules should live in the narrowest shared
  layer that still prevents leaks.

## Current Boundary Map

### Academic Work

- `exam-review` owns the study-plan workflow: exam contract,
  artifact mapping, drill plan, error log, cheat-sheet outline, and optional
  task creation.
- `canvas` owns Canvas LMS data access: courses, assignments, submissions,
  grades, files, syllabus pages, and Canvas-specific grade calculations.
- `edstem` owns read-only, incremental archives of downloadable
  EdStem lesson and resource files.
- `gradescope` owns read-only inspection of authenticated Gradescope
  assignments, submissions, scores, and released feedback.
- `panopto` owns lecture video URL extraction and bulk media
  download.
- `things3` owns writing the resulting plan into Things 3.

The planner can orchestrate the others, but it should not inline Canvas API
rules, Panopto download mechanics, or Things URL details.

### Google Workspace, Email And Calendar

- `gws` owns Google Workspace CLI operations, calendar source-of-truth decisions,
  cleanup strategy, safe write-target choice, and local macOS Calendar.app
  audits/scripts, as well as Gmail triage, reading, and drafting.
- `gws-gmail*` owns fine-grained Gmail API leaf work through the `gws` CLI.
- `gws-calendar*` owns fine-grained Google Calendar API leaf work through the `gws` CLI.

### Product And Systems Work

- `design-decisions` owns cross-domain decision structure: decision contracts,
  viable alternatives, common criteria, evidence, explicit rationale, and
  revisit triggers. Domain skills still own the facts and execution details.
- `ship-ai-native-cli` owns product shaping, release flow, Homebrew, README,
  skill integration, and installed-binary verification for new CLI products.
- `rust-systems-style` owns Rust/system-code judgment: invariants, failure
  surfaces, unsafe boundaries, dependency restraint, vocabulary leakage, and
  verification standards.

For a Rust CLI product, use all applicable layers: product workflow for scope,
`design-decisions` for consequential choices among alternatives, and the Rust
governor continuously for implementation taste.

### Browser Work

- Use the primary browser automation skill for Codex in-app browser navigation,
  local web target testing, screenshots, and interaction.
- Use `bro-browser` when the task requires a logged-in Chromium-family browser
  through the local bro MCP extension.

### GitHub Work

- `github` owns first-pass repository, issue, and pull request orientation.
- `gh-review-workflow` owns PR review comments, inline threads, actionable
  review feedback, and post-fix thread resolution.
- `gh-fix-ci` owns failing GitHub Actions checks and CI log diagnosis.
- `yeet` owns the full local publish flow: scope, commit, push, and draft PR.

### Local History

- `memory` owns read-only search across past Pi, Codex, and OpenCode sessions.

### Secrets

- Local machine-only credentials should use macOS Keychain through
  `keychain-secret` by default.
- `1password` owns scoped `op` usage only for import/fallback flows or tasks
  that explicitly require 1Password.
- Other skills may reference Keychain service/account names, but should keep
  secret-reading mechanics small and avoid printing secret values.

## Review Checklist

When reviewing a skill, ask:

- Does its description trigger only for the intended user goals?
- Is it a governor, workflow, tool-control, generated-family, router, or
  transformer skill?
- Does it duplicate another skill's command details?
- Does it know when to call a neighboring skill instead of expanding itself?
- Are references one hop from `SKILL.md` and loaded only when useful?
- Are scripts used for deterministic fragile flows instead of rewritten in
  prose every time?
- Is a new skill installed via `npx skills@latest add xiaotianxt/skills --skill <name>` if it should be in the local runtime view?
- Is the source recorded in `SOURCES.md`?

If a skill crosses roles, either split it, move detail into a reference, or add
an explicit boundary sentence.
