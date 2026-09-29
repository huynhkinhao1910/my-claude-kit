#!/usr/bin/env bash
# Install My Claude Kit into a Claude Code config dir.
# Usage: ./install.sh [--dry-run] [--no-hooks] [--no-claude-md]
#   --dry-run       print what would happen, change nothing
#   --no-hooks      copy files only; do not register hooks or deny rules in settings.json
#   --no-claude-md  keep the machine's own ~/.claude/CLAUDE.md
# Env:   CLAUDE_DIR (default ~/.claude), RULES_NS (default my-claude-kit),
#        LEGACY_RULES_NS  old rule namespaces, space-separated; "." is the flat rules/ root
#                         (default "ecc ."). Kit-owned dirs found there are retired.
#        RETIRE_DUPLICATES extra entries retired from those namespaces (default "zh README.md":
#                         the Chinese copy of common and ECC install notes, both loaded as rules)
set -euo pipefail

KIT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
RULES_NS="${RULES_NS:-my-claude-kit}"
LEGACY_RULES_NS="${LEGACY_RULES_NS:-ecc .}"
RETIRE_DUPLICATES="${RETIRE_DUPLICATES-zh README.md}"
DRY_RUN=0
REGISTER_HOOKS=1
INSTALL_CLAUDE_MD=1
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --no-hooks) REGISTER_HOOKS=0 ;;
    --no-claude-md) INSTALL_CLAUDE_MD=0 ;;
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

# retire_item <path>: move a superseded install into the backup so it stops loading.
retire_item() {
  local target="$1" rel="${1#"$CLAUDE_DIR"/}"
  run mkdir -p "$BACKUP_DIR/$(dirname "$rel")"
  run mv "$target" "$BACKUP_DIR/$rel"
  echo "retired $rel (moved to backup)"
}

for f in "$KIT_DIR"/agents/*.md;   do install_item "$f" "$CLAUDE_DIR/agents/$(basename "$f")"; done
for f in "$KIT_DIR"/commands/*.md; do install_item "$f" "$CLAUDE_DIR/commands/$(basename "$f")"; done
for d in "$KIT_DIR"/skills/*/;     do d="${d%/}"; install_item "$d" "$CLAUDE_DIR/skills/$(basename "$d")"; done
# Language rules link to ../common, so every kit rule dir shares one namespace.
kit_rules=""
for d in "$KIT_DIR"/rules/*/; do
  d="${d%/}"; name="$(basename "$d")"
  install_item "$d" "$CLAUDE_DIR/rules/$RULES_NS/$name"
  kit_rules="$kit_rules $name"
done

# Old installs of the same rules would load twice. Retire only kit-owned dirs plus the
# known duplicates; anything else in the old namespaces (e.g. angular, python) stays.
for ns in $LEGACY_RULES_NS; do
  [ "$ns" = "$RULES_NS" ] && continue
  base="$CLAUDE_DIR/rules"; [ "$ns" != "." ] && base="$base/$ns"
  for name in $kit_rules $RETIRE_DUPLICATES; do
    [ "$ns" = "." ] && [ "$name" = "$RULES_NS" ] && continue
    if [ -e "$base/$name" ]; then retire_item "$base/$name"; fi
  done
done
install_item "$KIT_DIR/hooks" "$CLAUDE_DIR/hooks/my-claude-kit"
if [ "$INSTALL_CLAUDE_MD" -eq 1 ]; then
  install_item "$KIT_DIR/claude/CLAUDE.md" "$CLAUDE_DIR/CLAUDE.md"
fi

# guard.sh and post-edit-format.sh silently allow everything without jq.
command -v jq >/dev/null 2>&1 || echo "WARNING: jq not found. guard.sh cannot block secrets or destructive commands until jq is installed (brew install jq / apt install jq)." >&2

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
