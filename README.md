# skills

Personal Codex and agent skills, collected into one public, source-controlled repo.

## Layout

Each skill lives at:

```text
skills/<skill-name>/SKILL.md
```

Optional bundled resources live next to `SKILL.md`, for example `scripts/`,
`references/`, `assets/`, or `agents/openai.yaml`.

## Install One Skill

Install exactly the skill you need. The installer intentionally has no
"install every skill" mode.

Install from npm:

```bash
npx -y @xiaotianxt/skills bro-browser
```

Or install from GitHub:

```bash
npx -y github:xiaotianxt/skills bro-browser
```

Per-project examples:

```bash
npx -y @xiaotianxt/skills bro-browser
npx -y @xiaotianxt/skills tg
npx -y @xiaotianxt/skills cx
npx -y @xiaotianxt/skills mon
```

For `tg`, prefer the project binary when it is installed:

```bash
tg skill install
```

That command renders the local machine-specific skill from tg's dictionary.
The NPX command installs the public Telegram-worded central skill template.

The default target is Codex: `~/.codex/skills/<skill-name>`. Other targets:

```bash
npx -y @xiaotianxt/skills bro-browser --target agents
npx -y @xiaotianxt/skills bro-browser --target claude
npx -y @xiaotianxt/skills bro-browser --dir ~/.codex/skills
```

List available packaged skills:

```bash
npx -y @xiaotianxt/skills list
```

Restart the target agent after installing or updating a skill.

The older Codex skill installer still works when you want to install directly
from this GitHub repo:

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo xiaotianxt/skills \
  --path skills/<skill-name>
```

## Development Model

For this machine, `~/dev/skills` is the canonical source tree for user-owned
skills. Treat `~/.codex/skills` and `~/.agents/skills` as runtime install views,
not as the place to author durable skill changes.

When creating or updating a user-owned skill:

1. Edit `~/dev/skills/skills/<skill-name>/...`.
2. Commit the change in this repo.
3. Link the installed runtime copy back to this checkout.
4. Restart Codex or the target agent when a refreshed skill must be loaded.

This keeps skill history reviewable, avoids editing generated or installed
copies directly, and makes local improvements publishable.

## Runtime Links

Create or refresh the runtime symlinks with:

```bash
git clone https://github.com/xiaotianxt/skills.git ~/dev/skills
~/dev/skills/scripts/link-local-skills.sh
```

This maps selected `~/.codex/skills/*` and `~/.agents/skills/*` entries to
`~/dev/skills/skills/*`. Existing installed directories are backed up before
being replaced by symlinks.

To update installed skills later:

```bash
git -C ~/dev/skills pull --ff-only
~/dev/skills/scripts/link-local-skills.sh
```

To mirror canonical skill docs into local open source project repos:

```bash
~/dev/skills/scripts/sync-project-skills.sh
```

That script copies:

- `~/dev/skills/skills/cx/SKILL.md` -> `~/dev/cx/SKILL.md`
- `~/dev/skills/skills/tg/SKILL.md` -> `~/dev/tg/SKILL.md`
- `~/dev/skills/skills/mimestreamctl` -> `~/dev/mimestreamctl/skills/mimestreamctl`

Project repos keep real mirrored files rather than symlinks so GitHub can render
the skill docs normally. Check drift without writing:

```bash
~/dev/skills/scripts/sync-project-skills.sh --check
```

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

## Skill Evolution

Skills are maintained as operational memory, not as project notebooks. After
real use, promote only durable lessons that improve future triggering,
workflow, safety, validation, or semantic clarity.

See [docs/skill-evolution.md](docs/skill-evolution.md) for the short-term,
long-term, and far-term maintenance model.

See [docs/skill-portfolio-governance.md](docs/skill-portfolio-governance.md)
for skill roles, boundary rules, and the current portfolio map.

## Safety

Before publication this repo was assembled from a clean copy and scanned for
credentials, local databases, decrypted chat data, generated build output, and
Git internals. See [SECURITY.md](SECURITY.md) for the policy used here.
