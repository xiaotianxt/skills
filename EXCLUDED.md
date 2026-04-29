# Excluded Content

The following content was intentionally not published.

## System and Plugin Skills

- `~/.codex/skills/.system`
- `~/.codex/plugins/cache`

These are managed by Codex or plugins and should be installed from their upstream
sources instead of being re-published here.

## Third-Party Installed Skills

The following installed skills were not vendored because they are third-party or
upstream-owned:

- `~/.agents/skills/agent-browser`
- `~/.agents/skills/find-skills`
- `~/.agents/skills/frontend-design`
- `~/.agents/skills/teach-impeccable`
- `~/.agents/skills/vercel-cli`
- `~/Develop.localized/agent-browser/skills/*`

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
