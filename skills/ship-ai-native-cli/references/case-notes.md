# Case Notes From tg, cx, mon

## Shared Project Shape

All three converge on:

- short binary name and repo under `~/dev/<name>`;
- Rust CLI with `clap` and small modules;
- `README.md` for humans;
- `SKILL.md` for Codex operation;
- `docs/architecture.md` or workflow design notes for maintainers;
- `Makefile`;
- `scripts/install.sh`;
- `scripts/release.sh`;
- GitHub CI and tag-triggered release workflow;
- Homebrew tap formula that installs prebuilt arm64 binaries;
- real installed-binary verification after release.

## tg Lessons

`tg` started from a fragile local-data problem and became usable by hiding
low-level recovery steps behind task-level commands.

Useful patterns:

- default command maps to the primary user job;
- `refresh` and `doctor` separate maintenance from diagnosis;
- `sessions` provides discovery before exact reads;
- exports support `txt`, `csv`, and `json`;
- sensitive local data stays local;
- `SKILL.md` tells agents how to operate the tool, not how internals work.

Product lesson: users want a chat-history tool, not a database-decryption
toolkit. Low-level commands can exist, but they should not dominate the product
frame.

## cx Lessons

`cx` wrapped an everyday manual workflow into one fast command.

Useful patterns:

- direct default action: `cx` launches through the best slot;
- management commands are explicit: `status`, `select`, `add`, `login`, `doctor`;
- stdin wrapping is part of the product contract;
- status output needed iteration to become human-readable;
- transient network failure gets a conservative fallback;
- release automation came early because the tool is used constantly.

Product lesson: for a workflow tool, optimize the default path first. Users
should not have to remember the implementation model on every run.

## mon Lessons

`mon` is the boundary-discipline case.

Useful patterns:

- expose the remote service as a general, structured, agent-native API surface;
- provide `auth`, `accounts`, `transactions`, `gql`, `doctor`;
- test against real credentials and real API responses;
- treat rate limits, MFA, redirects, and CAPTCHA as product behavior;
- reuse sessions before attempting password login;
- keep domain-specific reconciliation outside the generic API tool.

Product lesson: the first concrete use case can reveal the tool, but should not
own the tool. Put one-off settlement or reconciliation logic in a separate
project folder or downstream skill.

## Conversation-Derived Method

The successful sessions followed this rhythm:

1. User states a concrete pain.
2. Codex inspects existing local evidence before designing.
3. First version ships a narrow but real vertical slice.
4. User tries it immediately.
5. Failures become product requirements, not just bug fixes.
6. The repo gains release/Homebrew automation once the loop proves useful.
7. Scope mistakes are corrected by moving domain-specific logic out of the core.

Use this loop intentionally. Do not wait for perfect architecture before the
first real smoke test.
