---
name: ship-ai-native-cli
description: Use when Codex should turn a local pain point, repeated workflow, API wrapper, or automation idea into a small shippable AI-native CLI product, especially a Rust CLI with GitHub repository, CI, release automation, Homebrew formula, install command, README, architecture docs, and optional Codex skill integration. Trigger for requests like "make this into a tool", "create a ~/dev project like tg/cx/mon", "ship a CLI product", "wrap this API for agents", "add Homebrew/GitHub release", or "abstract this workflow into a reusable developer product".
---

# Ship AI-Native CLI

Use this skill to convert a concrete workflow into a small product, not a pile
of scripts. The pattern is distilled from `~/dev/tg`, `~/dev/cx`, `~/dev/mon`,
their release history, and the Codex sessions that shaped them.

## Operating Rule

Before coding, identify the product boundary:

- **User job**: the thing the user wants done in one command.
- **Primary commands**: the smallest stable surface that satisfies that job.
- **Agent contract**: JSON output, deterministic errors, no secret leakage.
- **Non-goals**: domain-specific workflows that should live outside the generic tool.
- **Ship target**: local install, GitHub repo, release asset, Homebrew formula.

If the user asks for a `tg`/`cx`/`mon`-style product, default to a Rust CLI with
the release shape in [rust-cli-shape.md](references/rust-cli-shape.md).

## Workflow

1. **Ground the product**
   - Inspect existing project/workflow/logs before naming abstractions.
   - Write a one-sentence product frame and a short command taxonomy.
   - Keep the first slice narrow enough to test with real data today.

2. **Build the vertical slice**
   - Start with `clap` commands, local config/session paths, and one useful data command.
   - Prefer direct structured APIs over browser automation or ad hoc parsing.
   - Add `doctor` for diagnostics and `install` for local adoption.
   - Make `--json` available for commands agents will consume.

3. **Design failure behavior**
   - Treat auth, permissions, rate limits, missing local files, and changed upstream APIs as product features.
   - Fail loudly with actionable errors; do not retry blindly.
   - Reuse valid sessions/tokens before hitting login or expensive endpoints.

4. **Package while building**
   - Keep `README.md`, `docs/architecture.md`, `SKILL.md`, `Makefile`, `scripts/install.sh`,
     CI, and release workflow current as part of the implementation.
   - Avoid docs that describe internals in the user-facing skill unless users need them.
   - Use release artifacts in Homebrew so users do not install Rust just to use the tool.

5. **Verify with reality**
   - Run `cargo fmt --all -- --check`, `cargo check`, `cargo test`, release build, and CLI help.
   - Smoke-test against the real local app/API/data source when possible.
   - If the test exposes a product boundary mistake, fix the product, not only the bug.

6. **Ship deliberately**
   - Commit scoped changes.
   - Push the repo.
   - Run the release script, wait for GitHub Actions, update the Homebrew tap, and run `brew test`.
   - Verify the installed binary, not only `target/debug`.

## References

- Read [product-method.md](references/product-method.md) when framing a new tool or recovering from scope creep.
- Read [rust-cli-shape.md](references/rust-cli-shape.md) when creating or refactoring the project files.
- Read [release-checklist.md](references/release-checklist.md) before publishing GitHub/Homebrew releases.
- Read [case-notes.md](references/case-notes.md) when comparing against `tg`, `cx`, and `mon`.

## Guardrails

- Do not embed one-off user workflows into a general-purpose tool. Put them in a separate folder, script, or downstream skill.
- Do not expose tokens, local databases, chat logs, or account data in docs, logs, commits, or final messages.
- Do not overfit the CLI to the first conversation. The tool should satisfy a class of future agent/user jobs.
- Do not call a project shipped until the installed binary and release path have been exercised.
