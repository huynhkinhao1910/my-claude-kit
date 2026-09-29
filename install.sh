#!/usr/bin/env bash
# Install my-claude-kit into a Claude Code config dir.
# Usage: ./install.sh [--dry-run] [--no-hooks]
#   --dry-run   print what would happen, change nothing
#   --no-hooks  copy files only, do not register hooks in settings.json
# Env:   CLAUDE_DIR (default ~/.claude), RULES_NS (default ecc)
set -euo pipefail

KIT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
RULES_NS="${RULES_NS:-ecc}"
DRY_RUN=0
REGISTER_HOOKS=1
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --no-hooks) REGISTER_HOOKS=0 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

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
install_item "$KIT_DIR/hooks" "$CLAUDE_DIR/hooks/my-claude-kit"

if [ "$REGISTER_HOOKS" -eq 1 ]; then
  if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found: files copied, hooks NOT registered (continuous learning needs python3)" >&2
  elif [ "$DRY_RUN" -eq 1 ]; then
    echo "[dry-run] hooks in settings.json would become:"
    python3 "$KIT_DIR/scripts/merge-settings.py" --claude-dir "$CLAUDE_DIR" --dry-run
  else
    python3 "$KIT_DIR/scripts/merge-settings.py" --claude-dir "$CLAUDE_DIR"
  fi
fi

if [ "$DRY_RUN" -eq 0 ] && [ -d "$BACKUP_DIR" ]; then
  echo "backup: $BACKUP_DIR"
fi
