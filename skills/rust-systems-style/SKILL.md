---
name: rust-systems-style
description: "Use when Codex is writing, editing, reviewing, or designing Rust systems code, Rust CLIs, async runtimes, FFI wrappers, unsafe abstractions, security-sensitive crates, local-first developer tools, or code style guidance for this user's Rust projects. Also use when a non-Rust engineering task would benefit from the same discipline: small APIs, explicit invariants, reviewable failure behavior, and conservative dependency/security choices."
---

# Rust Systems Style

Use this skill as an engineering governor, not a formatting checklist. The aim is code that can be read under pressure, reviewed locally, and trusted at the boundary where types, operating systems, networks, files, processes, and humans fail.

This is not a product-shipping workflow. When creating a new CLI product, use
`ship-ai-native-cli` for product scope and release shape, then apply this skill
continuously to the Rust and systems-code decisions.

## Operating Posture

Before editing, ask what must remain true after this change:

- Which invariant is being protected, moved, or newly introduced?
- Which failure is environmental, user-caused, adversarial, or impossible by construction?
- Which behavior is mechanism, and which behavior is policy?
- Which API surface will future callers have to live with?
- Which parts of the change are mechanical, and which parts change meaning?

Prefer the smallest change that makes these answers more local and easier to audit.

## Style Hierarchy

Follow local project style first, then this skill, then the primary sources in [style-sources.md](references/style-sources.md). Use `rustfmt` defaults unless the repository already has a different checked-in configuration.

When sources conflict, choose the rule that improves reviewability for the current repository. In this user's Rust CLI/tool projects, prefer:

- `rustfmt` formatting and explicit import grouping if the project already groups imports.
- Small modules with clear ownership over broad utility files.
- Mechanism separated from policy, especially around CLI behavior, retries, caching, logging, and FFI.
- Safe public APIs over exposing raw pointers, handles, unchecked states, or caller-managed invariants.
- Dependency restraint and local-first behavior when code touches private user data.
- Semantic boundaries over cosmetic boundaries: extract modules around domain ownership, invariants, and failure behavior rather than file size alone.
- Neutral internal vocabulary for sensitive local-first tools: confine upstream schema names, provider names, and raw protocol terminology to narrow adapter/dictionary layers when those names create privacy, security, or product-surface risk.

## Rust Rules

Design APIs so callers can do the right thing without remembering hidden rules:

- Use concrete domain types and newtypes when `bool`, `usize`, `String`, or `Option<T>` would hide meaning.
- Prefer `Result` for recoverable failure. Do not turn environmental failure into panic.
- Avoid `unwrap` and `expect` in production paths unless a local invariant makes failure impossible; leave a short comment for that invariant.
- Prefer parse/construct-once APIs that make invalid states unrepresentable over `validate` methods on already-invalid objects.
- Keep function arguments readable. Around six parameters is a design prompt for an options struct or a smaller responsibility.
- Put conversions on the most specific involved type. Use `From`, `TryFrom`, `AsRef`, and `AsMut` when they match the semantics.
- Keep public dependencies, features, re-exports, and configuration knobs small. Add a knob only when a caller genuinely needs policy control.
- Prefer exhaustive matches for closed enums. Use catch-all patterns only for intentionally open or `#[non_exhaustive]` types.
- Treat ignored results as a review event. Bind them with a type or name when discarding is intentional.
- Avoid storing derived state when a named method can compute the value from canonical fields. If the derived value is policy, name the policy explicitly.
- Keep debug tools out of the default shipped surface. Gate diagnostic binaries, verbose probes, and risky helpers behind explicit features or separate commands, and keep those features covered by CI.

For deeper Rust review, read [rust-review-checklist.md](references/rust-review-checklist.md).

## Unsafe Rules

Unsafe code is a proof obligation. Write it so a reviewer can check the proof without reconstructing the whole program.

- Avoid `unsafe` unless it is needed for FFI/platform calls, a carefully designed abstraction, or measured performance.
- Keep unsafe operations localized. Prefer a small unsafe core behind a safe API that restores invariants before returning.
- Enable or honor `unsafe_op_in_unsafe_fn`; unsafe functions still need explicit unsafe blocks around unsafe operations.
- Put `// SAFETY:` immediately before every unsafe block or unsafe impl. Explain why each precondition is met, not merely that it is safe.
- Document every unsafe function or trait with a `# Safety` section explaining the caller or implementor contract.
- For performance-motivated unsafe, require a benchmark or a precise reason why safe code is unacceptable.
- Audit the whole module when changing code near unsafe, because safe-looking edits can break an unsafe invariant at a distance.

## Tests And Verification

Scale verification to the blast radius:

- Run `cargo fmt --all -- --check`, `cargo clippy --all-targets -- -D warnings`, and `cargo test` when the project supports them.
- Prefer `--all-features` in CI when optional features contain shipped, debug, or diagnostic code that should not bitrot.
- Add focused tests for new behavior, regression fixes, parsing boundaries, and user-visible CLI errors.
- For async/concurrency primitives, consider deterministic concurrency tests such as loom if the project already uses it.
- For unsafe or low-level parsing, consider Miri, fuzzing, property tests, or adversarial tests when practical.
- Keep tests readable top-to-bottom. Prefer Arrange-Act-Assert, explicit inputs and expected outputs, and separate tests for separate behaviors.

## Review Stance

When reviewing or editing, lead with bugs and risk:

- Hidden policy in low-level code.
- Silent fallback, ignored flags, swallowed errors, or logs that obscure what happened.
- Unbounded retries, timeouts without enforcement, or operations that can block destructors/drop paths.
- Public APIs that expose implementation details or force callers into unsafe usage.
- New dependencies whose maintenance, transitive code, unsafe usage, or license cost is not justified.
- Refactors mixed with behavior changes in a way that makes review harder.
- Source vocabulary leaks: names from private schemas, vendors, protocols, or internal file layouts spreading beyond the narrow layer that has to speak them.
- Default build and release surfaces that include exploratory tools, secret-printing diagnostics, or other code paths not intended for normal users.
- CI and release warnings with dated deadlines. Treat them as maintenance debt before the deadline turns into a broken release path.

Do not beautify code for its own sake. Improve code when the change makes ownership, invariants, failure, or review boundaries clearer.
