# Sources

## Included

| Skill | Source |
| --- | --- |
| `1password` | Created in this repo as scoped 1Password import/fallback guidance |
| `apple-calendar-event` | `~/.codex/skills/apple-calendar-event` |
| `calendar` | Created in this repo as personal calendar governance guidance |
| `canvas` | Created in this repo as the local source of truth |
| `course-exam-review-planner` | `~/.codex/skills/course-exam-review-planner` |
| `cx` | `~/dev/cx/SKILL.md` |
| `extract-transparent-signature` | `~/.codex/skills/extract-transparent-signature` |
| `gh-fix-ci` | Created in this repo as GitHub Actions PR check workflow guidance |
| `gh-review-workflow` | `~/.codex/skills/gh-review-workflow` |
| `github` | Created in this repo as GitHub triage and routing guidance |
| `gws-*` | `~/.agents/skills/gws-*` |
| `gws-shared` | Added to make generated `gws-*` skills self-contained |
| `helium-browser-mcp` | Created in this repo from the local Helium/OpenBrowserMCP workflow |
| `macos-messages` | Created in this repo as local Messages history guidance |
| `memory` | Created in this repo as local agent history search guidance |
| `mimestreamctl` | `~/dev/mimestreamctl/skills/mimestreamctl` |
| `mon` | `~/dev/mon/SKILL.md` |
| `panopto-mp4-bulk-download` | `~/.codex/skills/panopto-mp4-bulk-download` |
| `rust-systems-style` | Created in this repo as the local source of truth |
| `ship-ai-native-cli` | `~/.codex/skills/ship-ai-native-cli` |
| `telegram-mtproto-session` | Created in this repo as local Telegram MTProto session guidance |
| `tg` | `~/dev/tg/SKILL.md` |
| `things3-manager` | `~/.codex/skills/things3-manager` |
| `yeet` | Created in this repo as local GitHub publish workflow guidance |

## Normalization

- `mon` and `cx` were given standard YAML frontmatter.
- The public `tg` skill preserves Telegram-facing wording.
- `agent-browser-hints` was retired in favor of the narrower
  `helium-browser-mcp` skill.
- Backup files, `.DS_Store`, `.git`, build output, local databases, local keys,
  and generated cache data were excluded.

## Local Linking

Use `scripts/link-local-skills.sh` to map installed local skills to this repo.
Use `scripts/sync-project-skills.sh` to mirror canonical skill docs into local
project repos while keeping those repos readable on GitHub.
