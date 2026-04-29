# Rust CLI Shape

## Default File Tree

Use this shape unless the repo already has a stronger local convention:

```text
project/
  .github/workflows/ci.yml
  .github/workflows/release.yml
  .gitignore
  Cargo.toml
  Cargo.lock
  LICENSE
  Makefile
  README.md
  SKILL.md
  docs/architecture.md
  scripts/install.sh
  scripts/release.sh
  src/
    main.rs
    cli.rs
    client.rs        # API or local app boundary, if applicable
    output.rs        # human tables + JSON
    paths.rs         # local state paths
    session.rs       # auth/session state, if applicable
    install.rs
```

Add modules only when the domain forces them. Keep names boring and explicit.

## Cargo Defaults

Use `edition = "2021"` for compatibility unless there is a reason to move.

Common dependencies:

```toml
anyhow = "1"
clap = { version = "4", features = ["derive"] }
reqwest = { version = "0.12", default-features = false, features = ["blocking", "json", "rustls-tls"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
```

Use `rusqlite`, `toml`, `chrono`, `rpassword`, etc. only when the product needs
them. Avoid async runtimes unless concurrency is central to the tool.

## CLI Design

In `src/main.rs`:

- Keep `main()` as a thin `ExitCode` wrapper.
- Put command parsing in `cli.rs`.
- Dispatch commands explicitly.
- Print errors as `name: {err:#}`.

In `src/cli.rs`:

- Use `clap::{Parser, Subcommand, Args}`.
- Prefer typed args over stringly parsing.
- Add `--json` to agent-consumed data commands.
- Add `--session-file`, `--config-dir`, or env overrides where local state matters.

## Output

Split output from logic:

- Human tables should be compact and terminal-friendly.
- JSON should be uncontaminated stdout.
- Progress/warnings should go to stderr when stdout is data.
- Avoid long wrapped lines in status output; use short columns or sections.

## Local State

Use predictable paths:

```text
~/.<tool>/session.json
~/.<tool>/cache/
```

Support env overrides:

```text
TOOL_SESSION_FILE
TOOL_CONFIG_DIR
```

Secrets:

- chmod token/session files to `0600` on Unix.
- Never commit generated local state.
- Never print tokens in status output.

## Core Commands To Consider

```text
tool                 # default primary action, if unambiguous
tool status          # quick state, if status matters
tool auth ...        # login/token/logout, if remote API
tool list/find       # discovery
tool get/search      # data access
tool gql/query/raw   # escape hatch for APIs
tool refresh         # maintenance
tool doctor          # diagnostics
tool install         # local install into ~/.local/bin
```

Do not add every command. Pick the smallest taxonomy that matches the product.
