# Style Sources

This reference compresses the source documents behind the skill. Load it when you need to justify a rule, resolve a style conflict, or explain the taste behind a Rust systems-programming decision.

## Primary Sources

- Rust Style Guide: `rustfmt` defaults, 4-space indentation, 100-column line width, block indent over visual indent, trailing commas for multiline lists, line comments over block comments, doc comments before attributes.
  - https://doc.rust-lang.org/style-guide/
- Rust API Guidelines: naming, conversions, common traits, error types, documentation, predictability, type safety, future-proofing, dependency/license expectations.
  - https://rust-lang.github.io/api-guidelines/checklist.html
- Standard Library safety comments policy: every unsafe block needs `// SAFETY:`; unsafe functions need caller contracts in `# Safety`; `unsafe_op_in_unsafe_fn` makes unsafe operations locally reviewable.
  - https://std-dev-guide.rust-lang.org/policy/safety-comments.html
- Rust for Linux coding guidelines: use rustfmt defaults, keep comments/doc comments Markdown-like, distinguish implementation comments from API docs, document panics and safety, prefer `expect` over `allow` for temporary lint suppressions when appropriate.
  - https://docs.kernel.org/rust/coding-guidelines.html
- crosvm coding style: prefer mechanism over policy, security over reuse/speed, single-responsibility functions, avoid large argument lists and rightward drift, minimize unsafe, write standard safety statements, make unit tests readable.
  - https://crosvm.dev/book/contributing/coding_style.html
- Firecracker contribution standards: separate logical changes, tests and style must pass, public functions need docs, unsafe is heavily discouraged, performance unsafe needs evidence, avoid `unwrap`/`expect` in production paths.
  - https://github.com/firecracker-microvm/firecracker/blob/main/CONTRIBUTING.md
- Wasmtime coding guidelines: rustfmt in CI, warnings as errors, selective Clippy, all-target Clippy, MSRV awareness, dependency and safety discipline in a runtime/sandbox project.
  - https://docs.wasmtime.dev/contributing-coding-guidelines.html
- Fuchsia Rust Rubric and Netstack Rust Patterns: reviewable code with less working memory, explicit ignored results, careful imports, exhaustive matches where possible, useful log severity, detailed unsafe justification.
  - https://fuchsia.dev/fuchsia-src/development/api/rust
  - https://fuchsia.dev/fuchsia-src/contribute/contributing-to-netstack/rust-patterns
- Chromium Rust style, API design, and unsafe policy: follow Rust style/API guidelines, APIs must be usable and minimize misuse, safe API around FFI, unsafe changes need specialized review, dependencies need audit attention.
  - https://chromium.googlesource.com/chromium/src/+/main/styleguide/rust/rust.md
  - https://chromium.googlesource.com/chromium/src/+/main/docs/rust/api_design.md
  - https://chromium.googlesource.com/chromium/src/+/refs/tags/135.0.7018.2/docs/rust-unsafe.md
- rustls contributing guide: clean commit history, top-down module ordering, type-local methods, parse-don't-validate, error handling over panics, safe defaults, small mandatory API, separate mechanism and policy.
  - https://github.com/rustls/rustls/blob/main/CONTRIBUTING.md
- Tokio contributing guide: feature-aware build/test commands, docs.rs-equivalent docs, integration/doc/fuzz tests, Miri and loom for relevant low-level async changes, logical commits.
  - https://github.com/tokio-rs/tokio/blob/master/docs/contributing/pull-requests.md
- Android Rust docs: Rust is used for native OS components; value expressive types, mandatory error handling, explicit integer conversions, initialization, platform lint sets, and clippy in Android builds.
  - https://source.android.com/docs/setup/build/rust/building-rust-modules/overview
  - https://source.android.com/docs/setup/build/rust/building-rust-modules/android-rust-modules
- PingCAP/TiKV style guide: Rustfmt/Clippy, Rust conventions even near FFI/protobuf boundaries, careful modules/data structures/traits/error/performance guidance, benchmark-backed unsafe performance choices.
  - https://pingcap.github.io/style-guide/rust/
  - https://pingcap.github.io/style-guide/rust/unsafe.html
- Ferrocene Safety Manual, handling unsafety: localize unsafety, keep unsafe modules single-purpose, use assertions/preconditions/postconditions/invariants, review the whole module, test unsafe code and clients.
  - https://public-docs.ferrocene.dev/main/safety-manual/rustc/unsafety.html

## Compressed Taste

The strongest documents converge on one idea: style is a way of lowering audit cost.

- Formatting exists to remove argument and conserve attention.
- Names should reveal domain meaning, not implementation convenience.
- APIs should make illegal states hard to express and dangerous states visibly named.
- Failure should be explicit at the boundary where it can be handled.
- Unsafe code should read like a proof with a small trusted base.
- Tests should be executable explanations of behavior, not only coverage counters.
- Dependencies are part of the codebase's risk surface.
- Local style matters because rhythm helps readers notice semantic anomalies.

## Conflict Resolution

Use this order when documents disagree:

1. Repository style and existing automated checks.
2. Safety/security/reviewability.
3. Public API compatibility.
4. Rust ecosystem conventions.
5. Personal preference.

Examples:

- crosvm prefers one imported item per `use`; Fuchsia groups imports by crate/direct child module. Follow the repository's established import style and keep provenance obvious.
- Some projects avoid Clippy's default set as too noisy; others require `-D warnings`. Run the project's configured command first. Add stricter Clippy only when it is already expected or the user asks for governance cleanup.
- Some documents prefer exhaustive matches, while open extensible types need catch-all handling. Match exhaustively for closed local enums; use catch-all for `#[non_exhaustive]` or protocol types designed to evolve.
