#!/usr/bin/env bash
# Install my-claude-kit into a Claude Code config dir.
# Usage: ./install.sh [--dry-run]
# Env:   CLAUDE_DIR (default ~/.claude), RULES_NS (default ecc)
set -euo pipefail

KIT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
RULES_NS="${RULES_NS:-ecc}"
DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

BACKUP_DIR="$CLAUDE_DIR/.backup/my-claude-kit-$(date +%Y%m%d-%H%M%S)"

run() {
  if [ "$DRY_RUN" -eq 1 ]; then echo "[dry-run] $*"; else "$@"; fi
}

# install_item <src> <dest>: back up dest if it exists, then copy src over it.
install_item() {
  local src="$1" dest="$2"
  if [ -e "$dest" ]; then
    local rel="${dest#"$CLAUDE_DIR"/}"
    run mkdir -p "$BACKUP_DIR/$(dirname "$rel")"
    run cp -R "$dest" "$BACKUP_DIR/$rel"
    run rm -rf "$dest"
  fi
  run mkdir -p "$(dirname "$dest")"
  run cp -R "$src" "$dest"
  echo "installed ${dest#"$CLAUDE_DIR"/}"
}

for f in "$KIT_DIR"/agents/*.md;   do install_item "$f" "$CLAUDE_DIR/agents/$(basename "$f")"; done
for f in "$KIT_DIR"/commands/*.md; do install_item "$f" "$CLAUDE_DIR/commands/$(basename "$f")"; done
for d in "$KIT_DIR"/skills/*/;     do d="${d%/}"; install_item "$d" "$CLAUDE_DIR/skills/$(basename "$d")"; done
# rules/php and rules/golang link to ../common, so all three share one namespace.
for d in "$KIT_DIR"/rules/*/;      do d="${d%/}"; install_item "$d" "$CLAUDE_DIR/rules/$RULES_NS/$(basename "$d")"; done

if [ "$DRY_RUN" -eq 0 ] && [ -d "$BACKUP_DIR" ]; then
  echo "backup: $BACKUP_DIR"
fi
