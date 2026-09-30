#!/usr/bin/env bash
# Install My Claude Kit into a Claude Code config dir.
# Usage: ./install.sh [--target claude,codex,copilot] [--only <group,...>] [--dry-run] [--no-hooks] [--no-claude-md]
#   --target        comma list of AI tools to install for (default: claude)
#   --only          install core plus these stack groups from groups.txt (default: everything)
#   --dry-run       print what would happen, change nothing
#   --no-hooks      copy files only; do not register hooks or deny rules in settings.json
#   --no-claude-md  keep the machine's own ~/.claude/CLAUDE.md
# Env:   CLAUDE_DIR (default ~/.claude), RULES_NS (default my-claude-kit),
#        LEGACY_RULES_NS  old rule namespaces, space-separated; "." is the flat rules/ root
#                         (default "ecc ."). Kit-owned dirs found there are retired.
#        CODEX_HOME (default ~/.codex), COPILOT_HOME (default ~/.copilot), AGENTS_HOME (default ~/.agents)
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
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
COPILOT_HOME="${COPILOT_HOME:-$HOME/.copilot}"
AGENTS_HOME="${AGENTS_HOME:-$HOME/.agents}"
TARGETS="claude"
ONLY=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --no-hooks) REGISTER_HOOKS=0 ;;
    --no-claude-md) INSTALL_CLAUDE_MD=0 ;;
    --target=*) TARGETS="${1#--target=}" ;;
    --target) TARGETS="${2:-}"; [ $# -gt 1 ] && shift ;;
    --only=*) ONLY="${1#--only=}" ;;
    --only) ONLY="${2:-}"; [ $# -gt 1 ] && shift ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done
TARGETS=" ${TARGETS//,/ } "
[ -n "${TARGETS// /}" ] || { echo "--target needs a value (claude, codex, copilot)" >&2; exit 2; }
for t in $TARGETS; do
  case "$t" in claude|codex|copilot) ;; *) echo "unknown target: $t (use claude, codex, copilot)" >&2; exit 2 ;; esac
done
has_target() { case "$TARGETS" in *" $1 "*) return 0 ;; *) return 1 ;; esac; }

# --only: SKIP lists "<kind>/<name>" items that belong to groups.txt but to no selected group.
SKIP=" "
if [ -n "$ONLY" ]; then
  all_groups="" picked=" " grouped=" "
  while IFS=: read -r group items; do
    case "$group" in ''|'#'*) continue ;; esac
    all_groups="$all_groups $group"
    grouped="$grouped$items "
    case ",$ONLY," in *",$group,"*) picked="$picked$items " ;; esac
  done < "$KIT_DIR/groups.txt"
  for g in ${ONLY//,/ }; do
    case " $all_groups " in *" $g "*) ;; *) echo "unknown group: $g (use:$all_groups)" >&2; exit 2 ;; esac
  done
  for item in $grouped; do
    case "$picked" in *" $item "*) ;; *) SKIP="$SKIP$item " ;; esac
  done
fi
# want <kind>/<name>: true unless --only excluded it.
want() { case "$SKIP" in *" $1 "*) return 1 ;; *) return 0 ;; esac; }

STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$CLAUDE_DIR/.backup/my-claude-kit-$STAMP"

run() {
  if [ "$DRY_RUN" -eq 1 ]; then echo "[dry-run] $*"; else "$@"; fi
}

# install_item <src> <dest> [home]: back up dest if it exists, then copy src over it.
# home (default CLAUDE_DIR) decides where the backup goes.
install_item() {
  local src="$1" dest="$2" home="${3:-$CLAUDE_DIR}"
  local rel="${dest#"$home"/}"
  if [ -e "$dest" ]; then
    local backup="$home/.backup/my-claude-kit-$STAMP"
    run mkdir -p "$backup/$(dirname "$rel")"
    run cp -R "$dest" "$backup/$rel"
    run rm -rf "$dest"
  fi
  run mkdir -p "$(dirname "$dest")"
  run cp -R "$src" "$dest"
  echo "installed $rel"
}

# retire_item <path>: move a superseded install into the backup so it stops loading.
retire_item() {
  local target="$1" rel="${1#"$CLAUDE_DIR"/}"
  run mkdir -p "$BACKUP_DIR/$(dirname "$rel")"
  run mv "$target" "$BACKUP_DIR/$rel"
  echo "retired $rel (moved to backup)"
}

if has_target claude; then
  for f in "$KIT_DIR"/agents/*.md; do
    if want "agents/$(basename "$f" .md)"; then install_item "$f" "$CLAUDE_DIR/agents/$(basename "$f")"; fi
  done
  for f in "$KIT_DIR"/commands/*.md; do
    if want "commands/$(basename "$f" .md)"; then install_item "$f" "$CLAUDE_DIR/commands/$(basename "$f")"; fi
  done
  for d in "$KIT_DIR"/skills/*/; do
    d="${d%/}"; if want "skills/$(basename "$d")"; then install_item "$d" "$CLAUDE_DIR/skills/$(basename "$d")"; fi
  done
  # Language rules link to ../common, so every kit rule dir shares one namespace.
  kit_rules=""
  for d in "$KIT_DIR"/rules/*/; do
    d="${d%/}"; name="$(basename "$d")"
    want "rules/$name" || continue
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
fi

# Codex and Copilot share ~/.agents/skills. continuous-learning-v2 hard-codes ~/.claude paths.
if has_target codex || has_target copilot; then
  for d in "$KIT_DIR"/skills/*/; do
    d="${d%/}"; name="$(basename "$d")"
    [ "$name" = "continuous-learning-v2" ] && continue
    if want "skills/$name"; then install_item "$d" "$AGENTS_HOME/skills/$name" "$AGENTS_HOME"; fi
  done
  for d in "$KIT_DIR"/dotagents/skills/*/; do  # kit commands packaged as skills
    d="${d%/}"; name="$(basename "$d")"
    if want "commands/$name"; then install_item "$d" "$AGENTS_HOME/skills/$name" "$AGENTS_HOME"; fi
  done
fi
if has_target codex; then
  for f in "$KIT_DIR"/codex/agents/*.toml; do
    if want "agents/$(basename "$f" .toml)"; then install_item "$f" "$CODEX_HOME/agents/$(basename "$f")" "$CODEX_HOME"; fi
  done
  for d in "$KIT_DIR"/codex/my-claude-kit/rules/*/; do
    d="${d%/}"; name="$(basename "$d")"
    if want "rules/$name"; then install_item "$d" "$CODEX_HOME/my-claude-kit/rules/$name" "$CODEX_HOME"; fi
  done
  if [ "$INSTALL_CLAUDE_MD" -eq 1 ]; then install_item "$KIT_DIR/codex/AGENTS.md" "$CODEX_HOME/AGENTS.md" "$CODEX_HOME"; fi
fi
if has_target copilot; then
  for f in "$KIT_DIR"/copilot/agents/*.agent.md; do
    if want "agents/$(basename "$f" .agent.md)"; then install_item "$f" "$COPILOT_HOME/agents/$(basename "$f")" "$COPILOT_HOME"; fi
  done
  for f in "$KIT_DIR"/copilot/instructions/*.instructions.md; do  # named <rule-dir>-<file>
    name="$(basename "$f")"
    if want "rules/${name%%-*}"; then install_item "$f" "$COPILOT_HOME/instructions/$name" "$COPILOT_HOME"; fi
  done
  if [ "$INSTALL_CLAUDE_MD" -eq 1 ]; then install_item "$KIT_DIR/copilot/copilot-instructions.md" "$COPILOT_HOME/copilot-instructions.md" "$COPILOT_HOME"; fi
fi

if [ "$DRY_RUN" -eq 0 ]; then
  for h in "$CLAUDE_DIR" "$CODEX_HOME" "$COPILOT_HOME" "$AGENTS_HOME"; do
    if [ -d "$h/.backup/my-claude-kit-$STAMP" ]; then echo "backup: $h/.backup/my-claude-kit-$STAMP"; fi
  done
fi
exit 0
