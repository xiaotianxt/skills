# skills

Personal agent skills, collected into one public, source-controlled repo.

## Layout

Each skill lives at:

```text
skills/<skill-name>/SKILL.md
```

Optional bundled resources live next to `SKILL.md`, for example `scripts/`,
`references/`, `assets/`, or `agents/openai.yaml`.

## Install

Install skills using [skills.sh](https://skills.sh):

```bash
npx skills@latest add xiaotianxt/skills --global --agent opencode --skill <skill-name> -y
```

List available skills:

```bash
npx skills@latest add xiaotianxt/skills --list
```

Update installed skills:

```bash
npx skills@latest update -g
```

The legacy `@xiaotianxt/skills` npm installer is frozen at `0.1.1`. This repo
is no longer published as an npm package; skills.sh is the supported installer.

Other supported agents: `codex`, `claude-code`, `cursor`, `gemini-cli`,
`github-copilot`, and more. Use `--agent <name>` to select.

Restart the target agent after installing or updating a skill.

## Development Model

For this machine, `~/dev/skills` is the canonical source tree for user-owned
skills. Treat `~/.agents/skills` and harness-specific directories such as
`~/.codex/skills` as runtime install views, not as places to author durable
skill changes.

When creating or updating a user-owned skill:

1. Edit `~/dev/skills/skills/<skill-name>/SKILL.md`.
2. To sync the local runtime view (no commit needed):
   ```bash
   npx skills@latest add ~/dev/skills --global --agent opencode --skill <skill-name> -y
   ```
   This copies from the local working tree but does not write the skills.sh
   lock file.
3. To publish and switch the runtime copy back to the GitHub source:
   ```bash
   git -C ~/dev/skills commit -m "update <skill-name>"
   git -C ~/dev/skills push
   npx skills@latest add xiaotianxt/skills --global --agent opencode --skill <skill-name> -y
   ```
   The final command pulls from GitHub and writes the lock entry
   (`source=xiaotianxt/skills`). Later releases can use `npx skills@latest
   update -g`.

## Included Skills

This repo includes user-owned skills authored here. Third-party skills (from
googleworkspace/cli and other upstreams) are installed separately via skills.sh
and not vendored in this repo.

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
