# Skill Portfolio Governance

This repository is a portfolio of skills, not a flat pile of prompts. Each
skill should have a clear job, a clear trigger, and a clear reason to exist next
to the others.

## Skill Roles

Use these roles when adding, reviewing, or refactoring skills:

| Role | Purpose | Examples |
| --- | --- | --- |
| Governor | Sets taste, risk posture, and review standards across tasks. | `rust-systems-style` |
| Product workflow | Turns a broad user goal into a repeatable multi-step outcome. | `ship-ai-native-cli`, `course-exam-review-planner` |
| Tool control | Operates a specific local app, CLI, API, or data source. | `tg`, `cx`, `mon`, `mimestreamctl`, `canvas`, `things3-manager`, `1password` |
| Generated tool family | Mirrors a large API surface through narrow generated commands. | `gws-*`, `gws-shared` |
| Companion | Adds decision guidance on top of another primary tool skill. | `agent-browser-hints` |
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
- A companion skill should name the primary skill it depends on and stay narrow.
- Sensitive auth and secret-handling rules should live in the narrowest shared
  layer that still prevents leaks.

## Current Boundary Map

### Academic Work

- `course-exam-review-planner` owns the study-plan workflow: exam contract,
  artifact mapping, drill plan, error log, cheat-sheet outline, and optional
  task creation.
- `canvas` owns Canvas LMS data access: courses, assignments, submissions,
  grades, files, syllabus pages, and Canvas-specific grade calculations.
- `panopto-mp4-bulk-download` owns lecture video URL extraction and bulk media
  download.
- `things3-manager` owns writing the resulting plan into Things 3.

The planner can orchestrate the others, but it should not inline Canvas API
rules, Panopto download mechanics, or Things URL details.

### Email And Calendar

- `mimestreamctl` owns direct interaction with the local Mimestream app:
  selected messages, drafts, menus, mailbox actions, and app-local state.
- `gws-gmail*` owns Gmail API work through the `gws` CLI.
- `apple-calendar-event` owns local macOS Calendar.app writes.
- `gws-calendar*` owns Google Calendar API work through the `gws` CLI.

When the user names a local app or current selection, prefer the app-control
skill. When the user names a Google Workspace account/API workflow, prefer the
`gws-*` skill.

### Product And Systems Work

- `ship-ai-native-cli` owns product shaping, release flow, Homebrew, README,
  skill integration, and installed-binary verification for new CLI products.
- `rust-systems-style` owns Rust/system-code judgment: invariants, failure
  surfaces, unsafe boundaries, dependency restraint, vocabulary leakage, and
  verification standards.

For a Rust CLI product, use both: product workflow first for scope, Rust
governor continuously for implementation taste.

### Browser Work

- Use the primary browser automation skill for navigation and interaction.
- Use `agent-browser-hints` only when auth persistence, local Chrome attachment,
  CDP, or session strategy matters.

### Secrets

- `1password` owns secret access patterns and `op` usage.
- Other skills may reference secret locations, but should defer secret-reading
  mechanics to `1password` when the task is about credentials rather than the
  domain workflow itself.

## Review Checklist

When reviewing a skill, ask:

- Does its description trigger only for the intended user goals?
- Is it a governor, workflow, tool-control, generated-family, companion, or
  transformer skill?
- Does it duplicate another skill's command details?
- Does it know when to call a neighboring skill instead of expanding itself?
- Are references one hop from `SKILL.md` and loaded only when useful?
- Are scripts used for deterministic fragile flows instead of rewritten in
  prose every time?
- Is a new skill linked through `scripts/link-local-skills.sh` if it should be
  installed in the local runtime view?
- Is the source recorded in `SOURCES.md`?

If a skill crosses roles, either split it, move detail into a reference, or add
an explicit boundary sentence.
