"""Tests for scripts/merge-settings.py (registers kit hooks and deny rules in settings.json)."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = KIT_ROOT / "scripts" / "merge-settings.py"
KIT_DENY = json.loads((KIT_ROOT / "settings" / "permissions.json").read_text())["deny"]

USER_HOOKS = {
    "PreToolUse": [
        {"matcher": "Bash", "hooks": [{"type": "command", "command": "~/.claude/hooks/my-audit.sh"}]}
    ],
    "PostToolUse": [
        {"matcher": "Edit|Write", "hooks": [{"type": "command", "command": "~/.claude/hooks/format.sh"}]}
    ],
}


def commands(settings, event):
    return [
        h["command"]
        for group in settings.get("hooks", {}).get(event, [])
        for h in group.get("hooks", [])
    ]


class MergeSettingsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.claude = Path(self.tmp.name) / ".claude"
        self.claude.mkdir()
        self.settings = self.claude / "settings.json"

    def tearDown(self):
        self.tmp.cleanup()

    def run_script(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--claude-dir", str(self.claude), *args],
            capture_output=True, text=True, timeout=30,
        )

    def load(self):
        return json.loads(self.settings.read_text(encoding="utf-8"))

    def test_creates_settings_when_missing(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        data = self.load()
        pre, post = commands(data, "PreToolUse"), commands(data, "PostToolUse")
        self.assertEqual(len(pre), 2)
        self.assertIn("my-claude-kit/guard.sh", pre[0])          # guard runs before observe
        self.assertIn("observe.sh\" pre", pre[1])
        self.assertEqual(len(post), 2)
        self.assertIn("my-claude-kit/post-edit-format.sh", post[0])
        self.assertIn("observe.sh\" post", post[1])
        self.assertEqual(len(commands(data, "SessionStart")), 1)
        self.assertIn("inject-instincts.py", commands(data, "SessionStart")[0])
        self.assertEqual(data["permissions"]["deny"], KIT_DENY)

    def test_uses_absolute_claude_dir_in_commands(self):
        self.run_script()
        self.assertIn(str(self.claude), commands(self.load(), "SessionStart")[0])

    def test_preserves_user_hooks_and_other_keys(self):
        self.settings.write_text(json.dumps({"theme": "dark", "hooks": USER_HOOKS}), encoding="utf-8")
        self.run_script()
        data = self.load()
        self.assertEqual(data["theme"], "dark")
        self.assertIn("~/.claude/hooks/my-audit.sh", commands(data, "PreToolUse"))
        self.assertIn("~/.claude/hooks/format.sh", commands(data, "PostToolUse"))
        self.assertEqual(len(commands(data, "PreToolUse")), 3)

    def test_is_idempotent(self):
        self.settings.write_text(json.dumps({"hooks": USER_HOOKS}), encoding="utf-8")
        self.run_script()
        first = self.load()
        self.run_script()
        self.assertEqual(self.load(), first)

    def test_replaces_stale_manual_observe_entries(self):
        stale = {"hooks": {"PreToolUse": [{"matcher": "*", "hooks": [
            {"type": "command", "command": "~/.claude/skills/continuous-learning-v2/hooks/observe.sh"}
        ]}]}}
        self.settings.write_text(json.dumps(stale), encoding="utf-8")
        self.run_script()
        pre = commands(self.load(), "PreToolUse")
        self.assertEqual(len(pre), 2)
        self.assertEqual(sum("observe.sh" in c for c in pre), 1)
        self.assertIn("observe.sh\" pre", pre[1])

    def test_replaces_legacy_guard_and_format_hooks(self):
        legacy = {"hooks": {
            "PreToolUse": [{"matcher": "Read|Edit|Write|MultiEdit|Bash", "hooks": [
                {"type": "command", "command": '"$HOME"/.claude/hooks/guard.sh'}]}],
            "PostToolUse": [{"matcher": "Edit|Write|MultiEdit", "hooks": [
                {"type": "command", "command": '"$HOME"/.claude/hooks/post-edit-format.sh'}]}],
        }}
        self.settings.write_text(json.dumps(legacy), encoding="utf-8")
        self.run_script()
        data = self.load()
        self.assertEqual(sum("guard.sh" in c for c in commands(data, "PreToolUse")), 1)
        self.assertEqual(sum("post-edit-format.sh" in c for c in commands(data, "PostToolUse")), 1)
        self.assertNotIn('"$HOME"/.claude/hooks/guard.sh', commands(data, "PreToolUse"))

    def test_merges_deny_rules_and_keeps_user_permissions(self):
        user = {"permissions": {"allow": ["Bash(npm test)"], "deny": ["Bash(rm -rf *)", KIT_DENY[0]]}}
        self.settings.write_text(json.dumps(user), encoding="utf-8")
        self.run_script()
        self.run_script()                                       # idempotent
        perms = self.load()["permissions"]
        self.assertEqual(perms["allow"], ["Bash(npm test)"])
        self.assertEqual(perms["deny"][:2], ["Bash(rm -rf *)", KIT_DENY[0]])
        self.assertEqual(sorted(perms["deny"]), sorted(set(["Bash(rm -rf *)", *KIT_DENY])))

    def test_remove_keeps_permissions(self):
        self.run_script()
        self.run_script("--remove")
        self.assertEqual(self.load()["permissions"]["deny"], KIT_DENY)

    def test_backs_up_existing_settings_before_change(self):
        original = json.dumps({"hooks": USER_HOOKS})
        self.settings.write_text(original, encoding="utf-8")
        self.run_script()
        backups = list(self.claude.glob("settings.json.bak-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(encoding="utf-8"), original)

    def test_no_backup_when_nothing_changes(self):
        self.run_script()
        for backup in self.claude.glob("settings.json.bak-*"):
            backup.unlink()
        self.run_script()
        self.assertEqual(list(self.claude.glob("settings.json.bak-*")), [])

    def test_remove_drops_only_kit_hooks(self):
        self.settings.write_text(json.dumps({"hooks": USER_HOOKS}), encoding="utf-8")
        self.run_script()
        result = self.run_script("--remove")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = self.load()
        self.assertEqual(commands(data, "PreToolUse"), ["~/.claude/hooks/my-audit.sh"])
        self.assertEqual(commands(data, "PostToolUse"), ["~/.claude/hooks/format.sh"])
        self.assertNotIn("SessionStart", data["hooks"])

    def test_refuses_invalid_json_without_touching_file(self):
        self.settings.write_text("{ not json", encoding="utf-8")
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.settings.read_text(encoding="utf-8"), "{ not json")
        self.assertIn("settings.json", result.stderr)

    def test_writes_through_symlinked_settings(self):
        target = Path(self.tmp.name) / "dotfiles-settings.json"
        target.write_text(json.dumps({"hooks": USER_HOOKS}), encoding="utf-8")
        self.settings.symlink_to(target)
        self.run_script()
        self.assertTrue(self.settings.is_symlink())
        self.assertEqual(len(commands(json.loads(target.read_text()), "SessionStart")), 1)

    def test_dry_run_writes_nothing(self):
        result = self.run_script("--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.settings.exists())
        self.assertIn("SessionStart", result.stdout)


if __name__ == "__main__":
    unittest.main()
