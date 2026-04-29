#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

printf 'link-project-skills.sh is deprecated; mirroring project skills instead.\n' >&2
exec "$SCRIPT_DIR/sync-project-skills.sh" "$@"
