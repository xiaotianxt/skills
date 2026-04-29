# skills

Personal Codex and agent skills, collected into one public, source-controlled repo.

## Layout

Each skill lives at:

```text
skills/<skill-name>/SKILL.md
```

Optional bundled resources live next to `SKILL.md`, for example `scripts/`,
`references/`, `assets/`, or `agents/openai.yaml`.

## Install

With the Codex skill installer:

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo xiaotianxt/skills \
  --path skills/<skill-name>
```

Or install multiple skills in one command:

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo xiaotianxt/skills \
  --path skills/mimestreamctl skills/tg skills/cx
```

Restart Codex after installing or updating skills.

## Included Skills

This repo includes user-owned local skills from `~/.codex/skills`, selected
generated Google Workspace `gws-*` skills, and lightweight skill wrappers from
local `~/dev` tools.

Notable curation choices:

- System skills from `~/.codex/skills/.system` are not re-published here.
- Third-party installed skills are not vendored here unless they are user-owned.
- Large local project directories are not copied. For `~/dev/mon`, `~/dev/cx`,
  and `~/dev/tg`, only the skill instructions are included.
- The public `tg` skill keeps the Telegram-facing wording used by the open
  source tool documentation.

See [SOURCES.md](SOURCES.md) for source mapping and [EXCLUDED.md](EXCLUDED.md)
for what was intentionally left out.

## Safety

Before publication this repo was assembled from a clean copy and scanned for
credentials, local databases, decrypted chat data, generated build output, and
Git internals. See [SECURITY.md](SECURITY.md) for the policy used here.
