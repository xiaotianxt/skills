#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CODEX_SKILLS_DIR="${CODEX_SKILLS_DIR:-$HOME/.codex/skills}"
AGENTS_SKILLS_DIR="${AGENTS_SKILLS_DIR:-$HOME/.agents/skills}"
STAMP="$(date +%Y%m%d-%H%M%S)"

CODEX_SKILLS=(
  apple-calendar-event
  course-exam-review-planner
  cx
  extract-transparent-signature
  gh-review-workflow
  mimestreamctl
  mon
  panopto-mp4-bulk-download
  ship-ai-native-cli
  tg
  things3-manager
)

AGENTS_SKILLS=(
  agent-browser-hints
  gws-calendar
  gws-calendar-agenda
  gws-calendar-insert
  gws-docs
  gws-docs-write
  gws-drive
  gws-drive-upload
  gws-gmail
  gws-gmail-forward
  gws-gmail-reply
  gws-gmail-reply-all
  gws-gmail-send
  gws-gmail-triage
  gws-gmail-watch
  gws-shared
)

backup_path() {
  local dest="$1"
  local backup_dir="$2"

  mkdir -p "$backup_dir"
  mv "$dest" "$backup_dir/"
  printf 'backup %s -> %s/%s\n' "$dest" "$backup_dir" "$(basename "$dest")"
}

link_skill() {
  local install_dir="$1"
  local skill="$2"
  local src="$ROOT/skills/$skill"
  local dest="$install_dir/$skill"
  local backup_dir="$install_dir/.linked-backup-$STAMP"

  if [[ ! -d "$src" ]]; then
    printf 'missing source: %s\n' "$src" >&2
    return 1
  fi

  mkdir -p "$install_dir"

  if [[ -L "$dest" ]]; then
    local target
    target="$(readlink "$dest")"
    if [[ "$target" == "$src" ]]; then
      printf 'ok %s -> %s\n' "$dest" "$src"
      return 0
    fi
    backup_path "$dest" "$backup_dir"
  elif [[ -e "$dest" ]]; then
    backup_path "$dest" "$backup_dir"
  fi

  ln -s "$src" "$dest"
  printf 'link %s -> %s\n' "$dest" "$src"
}

main() {
  local skill

  for skill in "${CODEX_SKILLS[@]}"; do
    link_skill "$CODEX_SKILLS_DIR" "$skill"
  done

  for skill in "${AGENTS_SKILLS[@]}"; do
    link_skill "$AGENTS_SKILLS_DIR" "$skill"
  done
}

main "$@"
