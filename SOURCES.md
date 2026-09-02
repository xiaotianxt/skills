# Sources

## Included

This repo contains only user-owned skills authored here. Third-party skills
are installed separately via skills.sh and not vendored in this repo.

| Skill | Source |
| --- | --- |
| `1password` | Created in this repo as scoped 1Password import/fallback guidance |
| `apple-calendar-event` | Created in this repo for local Calendar.app audits and explicit writes |
| `bro-browser` | Created in this repo for the local bro browser MCP workflow |
| `calendar` | Created in this repo as personal calendar governance guidance |
| `canvas` | Created in this repo as the local source of truth |
| `course-exam-review-planner` | Created in this repo as the academic review-planning workflow |
| `edstem-course-materials` | Created in this repo for authenticated EdStem course-material archives |
| `gh-fix-ci` | Created in this repo as GitHub Actions PR check workflow guidance |
| `gh-review-workflow` | Created in this repo as local GitHub review workflow guidance (originally collected from `~/.codex/skills/gh-review-workflow`) |
| `github` | Created in this repo as GitHub triage and routing guidance |
| `gradescope-reader` | Created in this repo for read-only inspection of authenticated Gradescope pages |
| `gws-shared` | Created in this repo as shared auth and safety guidance for upstream `gws-*` skills |
| `learn` | Created in this repo as evidence-based learning workflow guidance |
| `macos-messages` | Created in this repo as local Messages history guidance |
| `memory` | Created in this repo as local agent history search guidance |
| `ocr` | Created in this repo as OCR routing guidance |
| `panopto-mp4-bulk-download` | Created in this repo for authenticated Panopto lecture archives |
| `rust-systems-style` | Created in this repo as the local source of truth for Rust systems code style |
| `ship-ai-native-cli` | Created in this repo as product and release guidance for local CLI projects |
| `telegram-mtproto-session` | Created in this repo as local Telegram MTProto session guidance |
| `things3-manager` | Created in this repo for local Things 3 automation |
| `yeet` | Created in this repo as local GitHub publish workflow guidance |

## Removed (previously vendored, now installed upstream)

The generated Google Workspace skills were previously vendored here and are now
installed directly from `googleworkspace/cli` via skills.sh:

- `gws-calendar`, `gws-calendar-agenda`, `gws-calendar-insert`
- `gws-docs`, `gws-docs-write`
- `gws-drive`, `gws-drive-upload`
- `gws-gmail`, `gws-gmail-forward`, `gws-gmail-reply`,
  `gws-gmail-reply-all`, `gws-gmail-send`, `gws-gmail-triage`,
  `gws-gmail-watch`

The following skills have their own project repos and are no longer vendored
here:

- `cx` -> `~/dev/cx/SKILL.md` (repo: xiaotianxt/cx)
- `mon` -> `~/dev/mon/SKILL.md` (repo: xiaotianxt/mon)
- `tg` -> `~/dev/tg/SKILL.md` (repo: xiaotianxt/tg)
- `mimestreamctl` -> `~/dev/mimestreamctl/skills/mimestreamctl` (repo: xiaotianxt/mimestreamctl)

## Retired

- `helium-browser-mcp` was replaced by the narrower `bro-browser` skill.
- `web-artifacts-builder` is upstream-owned and should be installed from
  `anthropics/skills` when needed.

## Normalization

- `learn` was added to the Included table (previously missing from SOURCES.md).
- `gh-review-workflow` source updated: originally collected from
  `~/.codex/skills/`, now authored in this repo (no upstream GitHub source).
- Backup files, `.DS_Store`, `.git`, build output, local databases, local keys,
  and generated cache data were excluded.

## Installation

Install skills using skills.sh:

```bash
npx skills@latest add xiaotianxt/skills --global --agent opencode --skill <name> -y
npx skills@latest update -g
```

For local development (no commit needed):

```bash
npx skills@latest add ~/dev/skills --global --agent opencode --skill <name> -y
```
