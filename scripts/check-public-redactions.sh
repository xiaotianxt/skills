#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TG_SKILL="${TG_SKILL_CHECK_FILE:-$ROOT/skills/tg/SKILL.md}"

if grep -En 'WeChat|微信|/Applications/WeChat\.app' "$TG_SKILL"; then
  cat >&2 <<'EOF'
error: public skills/tg/SKILL.md contains private upstream app wording.

Keep the public tg skill in Telegram/neutral wording. Use `tg skill install`
from the tg project to render a local machine-specific skill from dictionary
values instead of committing those values to this public skills repo.
EOF
  exit 1
fi

if ! grep -Eq 'Telegram|telegram' "$TG_SKILL"; then
  cat >&2 <<'EOF'
error: public skills/tg/SKILL.md no longer contains the expected Telegram wording.
This usually means the public placeholder was overwritten by a local rendered skill.
EOF
  exit 1
fi
