#!/usr/bin/env bash
# PreToolUse guard: blocks secrets access and destructive commands. Exit 2 = block; stderr goes to Claude.
set -uo pipefail
command -v jq >/dev/null 2>&1 || exit 0

input="$(cat)"
tool="$(jq -r '.tool_name // empty' <<<"$input")"
path="$(jq -r '.tool_input.file_path // .tool_input.path // .tool_input.notebook_path // empty' <<<"$input")"
cmd="$(jq -r '.tool_input.command // empty' <<<"$input")"

block() { echo "BLOCKED by My Claude Kit guard (hooks/my-claude-kit/guard.sh): $1" >&2; exit 2; }

if [[ -n "$path" ]]; then
  base="$(basename "$path")"
  case "$base" in
    .env.example|.env.sample|.env.dist|.env.testing) ;;
    .env|.env.*) block "secrets file $path" ;;
    *.pem|*.key|*.p12|id_rsa*|id_ed25519*|auth.json|credentials.json|service-account*.json) block "credential file $path" ;;
  esac
fi

if [[ "$tool" == "Bash" && -n "$cmd" ]]; then
  grep -Eq '(cat|less|more|head|tail|grep|rg|source|bat|cp|scp)[[:space:]][^|;&]*\.env([[:space:]]|$|\.(local|production|prod|staging))' <<<"$cmd" \
    && block "reading .env via shell"
  if grep -Eqi 'migrate:(fresh|reset|refresh)|db:wipe|drop[[:space:]]+(table|database|schema)|truncate[[:space:]]+(table[[:space:]]+)?[a-z_`]' <<<"$cmd"; then
    grep -Eq -- '--env=testing|--database=(testing|sqlite)' <<<"$cmd" || block "destructive DB command (append --env=testing if it targets the test DB)"
  fi
  grep -Eq 'git[[:space:]]+push([^|;&]*)(--force([[:space:]]|$)|--force-with-lease|[[:space:]]-f([[:space:]]|$))' <<<"$cmd" && block "force push"
  grep -Eq 'git[[:space:]]+push[[:space:]]+[^[:space:]]+[[:space:]]+(HEAD:)?(main|master|develop)([[:space:]]|$)' <<<"$cmd" && block "direct push to protected branch"
  grep -Eq 'git[[:space:]]+reset[[:space:]]+--hard[[:space:]]+(origin/)?(main|master|develop)' <<<"$cmd" && block "hard reset to protected branch"
  grep -Eq 'rm[[:space:]]+-[a-zA-Z]*[rR][a-zA-Z]*[[:space:]]+(/|~|\$HOME|\.|\*|\.\*)/?([[:space:]]|$)' <<<"$cmd" && block "recursive delete of root/home/cwd"
fi
exit 0
