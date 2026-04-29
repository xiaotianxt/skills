#!/usr/bin/env bash
set -euo pipefail

DEV_ROOT="${DEV_ROOT:-$HOME/dev}"
SKILLS_ROOT="${SKILLS_ROOT:-$DEV_ROOT/skills}"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_ROOT="${BACKUP_ROOT:-$SKILLS_ROOT/.local-backups/project-links-$STAMP}"

backup_path() {
  local dest="$1"
  local backup_dir="$BACKUP_ROOT/$(basename "$(dirname "$dest")")"
  local backup="$backup_dir/$(basename "$dest")"

  mkdir -p "$backup_dir"
  mv "$dest" "$backup"
  printf 'backup %s -> %s\n' "$dest" "$backup"
}

link_path() {
  local dest="$1"
  local target="$2"
  local parent

  parent="$(dirname "$dest")"
  mkdir -p "$parent"

  if [[ -L "$dest" ]]; then
    local current
    current="$(readlink "$dest")"
    if [[ "$current" == "$target" ]]; then
      printf 'ok %s -> %s\n' "$dest" "$target"
      return 0
    fi
    backup_path "$dest"
  elif [[ -e "$dest" ]]; then
    backup_path "$dest"
  fi

  ln -s "$target" "$dest"
  printf 'link %s -> %s\n' "$dest" "$target"
}

main() {
  if [[ ! -d "$SKILLS_ROOT/skills" ]]; then
    printf 'missing central skills checkout: %s\n' "$SKILLS_ROOT" >&2
    return 1
  fi

  link_path "$DEV_ROOT/cx/SKILL.md" "../skills/skills/cx/SKILL.md"
  link_path "$DEV_ROOT/tg/SKILL.md" "../skills/skills/tg/SKILL.md"
  link_path "$DEV_ROOT/mimestreamctl/skills/mimestreamctl" "../../skills/skills/mimestreamctl"
}

main "$@"
