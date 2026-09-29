#!/usr/bin/env bash
# PostToolUse: format the edited file with the project's own formatter (if installed). Never blocks.
set -uo pipefail
command -v jq >/dev/null 2>&1 || exit 0
path="$(jq -r '.tool_input.file_path // empty')"
[[ -z "$path" || ! -f "$path" ]] && exit 0
root="${CLAUDE_PROJECT_DIR:-$(pwd)}"
case "$path" in
  *.php)  [[ -x "$root/vendor/bin/pint" ]] && "$root/vendor/bin/pint" -q "$path" ;;
  *.js|*.ts|*.vue|*.tsx|*.jsx) [[ -x "$root/node_modules/.bin/eslint" ]] && "$root/node_modules/.bin/eslint" --fix "$path" ;;
  *.go)   command -v gofmt >/dev/null && gofmt -w "$path" ;;
  *.py)   command -v ruff >/dev/null && ruff format -q "$path" ;;
esac >/dev/null 2>&1
exit 0
