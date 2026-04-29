#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEV_ROOT="${DEV_ROOT:-$HOME/dev}"
MODE="${1:-sync}"

if [[ "$MODE" != "sync" && "$MODE" != "--check" ]]; then
  printf 'usage: %s [--check]\n' "$0" >&2
  exit 2
fi

ensure_parent() {
  mkdir -p "$(dirname "$1")"
}

sync_file() {
  local src="$1"
  local dest="$2"

  if [[ "$MODE" == "--check" ]]; then
    diff -u "$src" "$dest"
    return
  fi

  ensure_parent "$dest"
  if [[ -L "$dest" ]]; then
    unlink "$dest"
  fi
  install -m 0644 "$src" "$dest"
  printf 'sync %s -> %s\n' "$src" "$dest"
}

sync_dir() {
  local src="$1"
  local dest="$2"

  if [[ "$MODE" == "--check" ]]; then
    diff -qr "$src" "$dest"
    return
  fi

  ensure_parent "$dest"
  if [[ -L "$dest" ]]; then
    unlink "$dest"
  fi
  mkdir -p "$dest"
  rsync -a --delete --exclude '.DS_Store' "$src/" "$dest/"
  printf 'sync %s/ -> %s/\n' "$src" "$dest"
}

main() {
  sync_file "$ROOT/skills/cx/SKILL.md" "$DEV_ROOT/cx/SKILL.md"
  sync_file "$ROOT/skills/tg/SKILL.md" "$DEV_ROOT/tg/SKILL.md"
  sync_dir "$ROOT/skills/mimestreamctl" "$DEV_ROOT/mimestreamctl/skills/mimestreamctl"
}

main "$@"
