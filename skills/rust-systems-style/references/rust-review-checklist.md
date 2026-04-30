# Rust Review Checklist

Load this when doing a serious Rust implementation or review. It is intentionally phrased as questions because the right answer depends on the local codebase.

## Boundaries

- Does each module own one coherent concept?
- Is CLI or request handling limited to parsing, orchestration, presentation, and exit behavior?
- Are domain rules kept near the domain types that define them?
- Is policy separated from mechanism, especially in cache, retry, logging, networking, and FFI code?
- Are mechanical moves separated from behavior changes where review would benefit?

## API Shape

- Can callers discover the happy path from types and names?
- Does the function belong as a method on one of its arguments?
- Do arguments proceed from specific domain value to broader context?
- Would an options struct make call sites clearer?
- Do `bool`, `Option<T>`, integer, or string parameters deserve a domain enum/newtype?
- Are conversions expressed with standard traits where that is idiomatic?
- Are public structs protected against future field changes?
- Are enums intentionally exhaustive or intentionally open?
- Are re-exports limited to paved paths users actually need?

## Errors And Panics

- Is every recoverable environmental failure returned as `Result`?
- Is each error meaningful at the layer where it is emitted?
- Are errors wrapped with enough context without leaking sensitive data?
- Are panics limited to invariant violations, tests, or impossible states?
- If `unwrap` or `expect` remains in production code, is the invariant local and obvious?
- Are timeouts, cancellation, interruption, and partial writes handled where relevant?
- Are stdout, stderr, logs, and exit codes assigned consistently for CLI users and agents?

## Unsafe And FFI

- Is `unsafe` necessary, and is the reason documented?
- Is unsafe contained behind a safe abstraction that restores invariants?
- Does every `unsafe` block or `unsafe impl` have an adjacent `// SAFETY:` proof?
- Does every unsafe function or trait have a `# Safety` contract?
- Are raw pointers, FDs, handles, ownership transfer, aliasing, alignment, initialization, lifetimes, and thread-safety all accounted for?
- Are `Send`/`Sync` impls treated as global promises rather than local conveniences?
- Is FFI wrapped in a minimal, idiomatic Rust API?
- Were nearby safe changes reviewed for effects on unsafe invariants?

## Concurrency And Async

- Are shared states explicit about ownership and synchronization?
- Are cancellation and drop behavior understood?
- Can a lock be held across `.await` or a blocking call?
- Are retries bounded and observable?
- Does logging help diagnose races or timing without overwhelming production logs?
- Does the project need deterministic concurrency tests, loom, Miri, or fuzzing for this change?

## Tests

- Does each test name behavior and expected outcome?
- Can a reviewer read the test top-to-bottom without chasing critical helper behavior?
- Are edge cases chosen because they guard an invariant?
- Is a regression test tied to the bug's actual failure mode?
- Are public APIs covered at the level users consume them?
- Are examples and doctests succinct and correct when docs are part of the surface?

## Dependencies And Supply Chain

- Is the dependency necessary enough to justify its transitive code and maintenance cost?
- Does it introduce unsafe, native build steps, network behavior, crypto, or secret handling?
- Does the license fit the project?
- Can the standard library or an existing dependency solve the problem cleanly?
- Does adding a feature flag create a support matrix the project is ready to test?

## Final Pass

- Does the code reveal the invariant where it matters?
- Does it fail in a way the caller or operator can act on?
- Is the smallest risky region also the most heavily documented and tested?
- Would a future reviewer need less working memory after this change than before?
