#!/usr/bin/env python3
"""Register (or remove) My Claude Kit hooks and deny rules in Claude Code's settings.json.

Kit hooks are recognised by their command, so re-running is idempotent and
never touches the user's own hooks. Earlier installs of guard.sh and
post-edit-format.sh straight under ~/.claude/hooks/ are replaced by the kit copy.
Deny rules from settings/permissions.json are merged into permissions.deny;
the user's own allow/deny rules are kept. --remove strips kit hooks only and
leaves permissions alone, because a deny rule may also be the user's own.

Usage:
  merge-settings.py [--claude-dir DIR] [--remove] [--dry-run]
"""
import argparse
import copy
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

KIT_MARKERS = (
    "continuous-learning-v2/hooks/observe.sh",
    "my-claude-kit/inject-instincts.py",
)
# guard/format hooks, both the kit copy and a legacy copy directly in ~/.claude/hooks/
GUARD_HOOK_RE = re.compile(r"hooks/(my-claude-kit/)?(guard|post-edit-format)\.sh\"?\s*$")
OBSERVE_TIMEOUT_SECONDS = 10
INJECT_TIMEOUT_SECONDS = 15
GUARD_TIMEOUT_SECONDS = 10
FORMAT_TIMEOUT_SECONDS = 30
GUARD_MATCHER = "Read|Edit|Write|MultiEdit|NotebookEdit|Bash"
FORMAT_MATCHER = "Edit|Write|MultiEdit"
KIT_PERMISSIONS = Path(__file__).resolve().parents[1] / "settings" / "permissions.json"


def kit_hooks(claude_dir):
    """Kit hook groups per event, in the order they should run (guard before observe)."""
    kit = f"{claude_dir}/hooks/my-claude-kit"
    observe = f"{claude_dir}/skills/continuous-learning-v2/hooks/observe.sh"

    def group(command, timeout, matcher=None):
        entry = {"hooks": [{"type": "command", "command": command, "timeout": timeout}]}
        return {"matcher": matcher, **entry} if matcher else entry

    return {
        "PreToolUse": [
            group(f'bash "{kit}/guard.sh"', GUARD_TIMEOUT_SECONDS, GUARD_MATCHER),
            group(f'bash "{observe}" pre', OBSERVE_TIMEOUT_SECONDS, "*"),
        ],
        "PostToolUse": [
            group(f'bash "{kit}/post-edit-format.sh"', FORMAT_TIMEOUT_SECONDS, FORMAT_MATCHER),
            group(f'bash "{observe}" post', OBSERVE_TIMEOUT_SECONDS, "*"),
        ],
        "SessionStart": [group(f'python3 "{kit}/inject-instincts.py"', INJECT_TIMEOUT_SECONDS)],
    }


def is_kit_hook(hook):
    command = hook.get("command", "") if isinstance(hook, dict) else ""
    return any(marker in command for marker in KIT_MARKERS) or bool(GUARD_HOOK_RE.search(command))


def kit_deny_rules():
    if not KIT_PERMISSIONS.exists():
        return []
    return json.loads(KIT_PERMISSIONS.read_text(encoding="utf-8")).get("deny", [])


def with_kit_denies(permissions, rules):
    """Append kit deny rules that are missing; keep the user's order and entries."""
    merged = copy.deepcopy(permissions) if isinstance(permissions, dict) else {}
    deny = list(merged.get("deny", []))
    deny += [rule for rule in rules if rule not in deny]
    if deny:
        merged["deny"] = deny
    return merged


def without_kit_hooks(hooks):
    """Return a copy of the hooks map with every kit hook stripped out."""
    cleaned = {}
    for event, groups in hooks.items():
        kept_groups = []
        for group in groups:
            kept = [h for h in group.get("hooks", []) if not is_kit_hook(h)]
            if kept:
                kept_groups.append({**group, "hooks": kept})
        if kept_groups:
            cleaned[event] = kept_groups
    return cleaned


def merged_settings(settings, claude_dir, remove):
    result = copy.deepcopy(settings)
    hooks = without_kit_hooks(result.get("hooks", {}))
    if not remove:
        for event, groups in kit_hooks(claude_dir).items():
            hooks[event] = [*hooks.get(event, []), *groups]
        permissions = with_kit_denies(result.get("permissions", {}), kit_deny_rules())
        if permissions:
            result["permissions"] = permissions
    if hooks:
        result["hooks"] = hooks
    else:
        result.pop("hooks", None)
    return result


def load_settings(path):
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as error:
        raise SystemExit(f"[merge-settings] {path} is not valid JSON ({error}); fix it first, nothing written")
    if not isinstance(data, dict):
        raise SystemExit(f"[merge-settings] {path} must contain a JSON object; nothing written")
    return data


def write_atomic(path, data):
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".settings.", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    os.replace(tmp, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--claude-dir", default=str(Path.home() / ".claude"))
    parser.add_argument("--remove", action="store_true", help="remove kit hooks only")
    parser.add_argument("--dry-run", action="store_true", help="print resulting hooks, write nothing")
    args = parser.parse_args()

    claude_dir = Path(args.claude_dir).expanduser().resolve()
    path = claude_dir / "settings.json"
    if path.is_symlink():  # dotfiles setups: write through the link, keep it intact
        path = path.resolve()
    current = load_settings(path)
    updated = merged_settings(current, str(claude_dir), args.remove)

    if args.dry_run:
        preview = {"hooks": updated.get("hooks", {}), "permissions.deny": updated.get("permissions", {}).get("deny", [])}
        print(json.dumps(preview, indent=2))
        return
    if updated == current and path.exists():
        print("[merge-settings] settings.json already up to date")
        return
    if path.exists():
        backup = path.with_name(f"settings.json.bak-{datetime.now():%Y%m%d-%H%M%S}")
        backup.write_bytes(path.read_bytes())
        print(f"[merge-settings] backup: {backup}")
    claude_dir.mkdir(parents=True, exist_ok=True)
    write_atomic(path, updated)
    print(f"[merge-settings] {'removed kit hooks from' if args.remove else 'registered kit hooks and deny rules in'} {path}")


if __name__ == "__main__":
    sys.exit(main())
