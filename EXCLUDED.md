# Excluded Content

The following content was intentionally not published.

## System and Plugin Skills

- `~/.codex/skills/.system`
- `~/.codex/plugins/cache`

These are managed by Codex or plugins and should be installed from their upstream
sources instead of being re-published here.

## Third-Party Installed Skills

The following installed skills are not vendored in this repo because they are
third-party or upstream-owned. Install them via skills.sh from their respective
sources:

- `agent-browser` -> `vercel-labs/agent-browser`
- `find-skills` -> `vercel-labs/skills`
- `frontend-design` -> `pbakaus/impeccable`
- `teach-impeccable` -> `pbakaus/impeccable`
- `vercel-cli` -> `vercel/vercel`
- `typst` -> `lucifer1004/claude-skill-typst`
- `web-artifacts-builder` -> `anthropics/skills`
- `gws-*` (14 skills) -> `googleworkspace/cli`

## Project-Level Skills

The following skills have their own project repos and are not vendored here:

- `cx` -> `~/dev/cx` (repo: xiaotianxt/cx)
- `mon` -> `~/dev/mon` (repo: xiaotianxt/mon)
- `tg` -> `~/dev/tg` (repo: xiaotianxt/tg)
- `mimestreamctl` -> `~/dev/mimestreamctl` (repo: xiaotianxt/mimestreamctl)

## Local Project Data

Only skill instructions were extracted from local project repos. The following
classes of files were excluded:

- `.git/`
- `target/`
- `decrypted/`
- `exported/`
- `all_keys.json`
- local auth files
- local session files
- local databases
- build artifacts
- editor and OS metadata

In particular, the full `~/dev/tg` tree was not copied because it contained
local decrypted databases and key material.
