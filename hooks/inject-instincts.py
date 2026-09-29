#!/usr/bin/env python3
"""SessionStart hook: inject learned instincts into the new session.

Reuses continuous-learning-v2's own instinct-cli.py for project detection and
instinct loading, so project hashes always match what observe.sh recorded.

Env:
  ECC_INSTINCT_CONFIDENCE_THRESHOLD  minimum confidence, decimal in [0, 1] (default 0.5)
  ECC_MAX_INJECTED_INSTINCTS         max instincts injected, positive int (default 10)
  CLV2_INSTINCT_CLI                  explicit path to instinct-cli.py
  CLV2_HOMUNCULUS_DIR                data dir (same resolution as the skill)

Never blocks the session: every failure logs to stderr and exits 0.
"""
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

DEFAULT_THRESHOLD = 0.5
DEFAULT_MAX = 10
PROJECT_SCOPE_BOOST = 0.25
CLI_RELATIVE = Path("skills") / "continuous-learning-v2" / "scripts" / "instinct-cli.py"


def log(message):
    print(f"[inject-instincts] {message}", file=sys.stderr)


def read_threshold():
    raw = os.environ.get("ECC_INSTINCT_CONFIDENCE_THRESHOLD", "").strip()
    if not re.fullmatch(r"\d+(\.\d+)?", raw):
        return DEFAULT_THRESHOLD
    value = float(raw)
    return value if 0 <= value <= 1 else DEFAULT_THRESHOLD


def read_max():
    raw = os.environ.get("ECC_MAX_INJECTED_INSTINCTS", "").strip()
    if not re.fullmatch(r"\d+", raw) or int(raw) == 0:
        return DEFAULT_MAX
    return int(raw)


def find_cli():
    explicit = os.environ.get("CLV2_INSTINCT_CLI")
    if explicit:
        return Path(explicit)
    here = Path(__file__).resolve()
    # Installed: ~/.claude/hooks/my-claude-kit/<hook>; repo: <kit>/hooks/<hook>
    for base in (here.parents[2], here.parents[1]):
        candidate = base / CLI_RELATIVE
        if candidate.is_file():
            return candidate
    return Path.home() / ".claude" / CLI_RELATIVE


def load_cli(cli_path):
    if not cli_path.is_file():
        raise FileNotFoundError(f"instinct-cli.py not found at {cli_path}")
    spec = importlib.util.spec_from_file_location("instinct_cli", cli_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def switch_to_session_cwd():
    """Run detection from the session's cwd (sent on stdin) when available."""
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except (ValueError, OSError):
        return
    cwd = payload.get("cwd") if isinstance(payload, dict) else None
    if cwd and os.path.isdir(cwd):
        os.chdir(cwd)


def extract_action(content):
    match = re.search(r"## Action\s*\n+([\s\S]+?)(?:\n## |\n---|$)", content or "")
    block = match.group(1) if match else (content or "")
    return next((line.strip() for line in block.splitlines() if line.strip()), "")


def rank(instincts, threshold, limit):
    candidates = []
    for item in instincts:
        confidence = item.get("confidence", 0)
        action = extract_action(item.get("content", ""))
        if not isinstance(confidence, (int, float)) or confidence < threshold or not action:
            continue
        is_project = item.get("_scope_label") == "project"
        score = confidence + (PROJECT_SCOPE_BOOST if is_project else 0)
        candidates.append((score, confidence, "project" if is_project else "global", action))
    candidates.sort(key=lambda c: c[0], reverse=True)
    return candidates[:limit]


def format_context(ranked):
    lines = [f"- [{scope} {round(conf * 100)}%] {action}" for _, conf, scope, action in ranked]
    return "Active instincts (learned from past sessions):\n" + "\n".join(lines)


def main():
    switch_to_session_cwd()
    cli = load_cli(find_cli())
    if (Path(cli.HOMUNCULUS_DIR) / "disabled").exists():
        return
    # load_all_instincts already lets project-scoped instincts win on id conflicts.
    instincts = cli.load_all_instincts(cli.detect_project())
    ranked = rank(instincts, read_threshold(), read_max())
    if not ranked:
        return
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": format_context(ranked),
        }
    }))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:  # never block session start
        log(f"skipped: {error}")
    sys.exit(0)
