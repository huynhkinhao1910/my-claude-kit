#!/usr/bin/env python3
"""Register (or remove) my-claude-kit hooks in Claude Code's settings.json.

Kit hooks are recognised by a marker in their command, so re-running is
idempotent and never touches the user's own hooks.

Usage:
  merge-settings.py [--claude-dir DIR] [--remove] [--dry-run]
"""
import argparse
import copy
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

KIT_MARKERS = (
    "continuous-learning-v2/hooks/observe.sh",
    "my-claude-kit/inject-instincts.py",
)
OBSERVE_TIMEOUT_SECONDS = 10
INJECT_TIMEOUT_SECONDS = 15


def kit_hooks(claude_dir):
    observe = f"{claude_dir}/skills/continuous-learning-v2/hooks/observe.sh"
    inject = f"{claude_dir}/hooks/my-claude-kit/inject-instincts.py"

    def group(command, timeout, matcher=None):
        entry = {"hooks": [{"type": "command", "command": command, "timeout": timeout}]}
        return {"matcher": matcher, **entry} if matcher else entry

    return {
        "PreToolUse": group(f'bash "{observe}" pre', OBSERVE_TIMEOUT_SECONDS, "*"),
        "PostToolUse": group(f'bash "{observe}" post', OBSERVE_TIMEOUT_SECONDS, "*"),
        "SessionStart": group(f'python3 "{inject}"', INJECT_TIMEOUT_SECONDS),
    }


def is_kit_hook(hook):
    command = hook.get("command", "") if isinstance(hook, dict) else ""
    return any(marker in command for marker in KIT_MARKERS)


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
        for event, group in kit_hooks(claude_dir).items():
            hooks[event] = [*hooks.get(event, []), group]
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
        print(json.dumps(updated.get("hooks", {}), indent=2))
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
    print(f"[merge-settings] {'removed' if args.remove else 'registered'} kit hooks in {path}")


if __name__ == "__main__":
    sys.exit(main())
