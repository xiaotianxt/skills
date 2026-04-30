# Sources

## Included

| Skill | Source |
| --- | --- |
| `1password` | Created in this repo as the local source of truth |
| `agent-browser-hints` | `~/Develop.localized/agent-browser-hints` |
| `apple-calendar-event` | `~/.codex/skills/apple-calendar-event` |
| `canvas` | Created in this repo as the local source of truth |
| `course-exam-review-planner` | `~/.codex/skills/course-exam-review-planner` |
| `cx` | `~/dev/cx/SKILL.md` |
| `extract-transparent-signature` | `~/.codex/skills/extract-transparent-signature` |
| `gh-review-workflow` | `~/.codex/skills/gh-review-workflow` |
| `gws-*` | `~/.agents/skills/gws-*` |
| `gws-shared` | Added to make generated `gws-*` skills self-contained |
| `mimestreamctl` | `~/dev/mimestreamctl/skills/mimestreamctl` |
| `mon` | `~/dev/mon/SKILL.md` |
| `panopto-mp4-bulk-download` | `~/.codex/skills/panopto-mp4-bulk-download` |
| `rust-systems-style` | Created in this repo as the local source of truth |
| `ship-ai-native-cli` | `~/.codex/skills/ship-ai-native-cli` |
| `tg` | `~/dev/tg/SKILL.md` |
| `things3-manager` | `~/.codex/skills/things3-manager` |

## Normalization

- `mon` and `cx` were given standard YAML frontmatter.
- The public `tg` skill preserves Telegram-facing wording.
- Backup files, `.DS_Store`, `.git`, build output, local databases, local keys,
  and generated cache data were excluded.

## Local Linking

Use `scripts/link-local-skills.sh` to map installed local skills to this repo.
Use `scripts/sync-project-skills.sh` to mirror canonical skill docs into local
project repos while keeping those repos readable on GitHub.
