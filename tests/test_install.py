"""Tests for install.sh: rules namespace and retiring the legacy ecc namespace."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]
KIT_RULES = sorted(p.name for p in (KIT_ROOT / "rules").iterdir() if p.is_dir())


class InstallTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.claude = Path(self.tmp.name) / ".claude"
        legacy = self.claude / "rules" / "ecc"
        (legacy / "common").mkdir(parents=True)
        (legacy / "common" / "old.md").write_text("old", encoding="utf-8")
        (legacy / "angular").mkdir()  # not owned by the kit, must survive

    def tearDown(self):
        self.tmp.cleanup()

    def install(self, *args):
        env = {**os.environ, "CLAUDE_DIR": str(self.claude)}
        return subprocess.run(
            ["bash", str(KIT_ROOT / "install.sh"), "--no-hooks", *args],
            env=env, capture_output=True, text=True, timeout=120,
        )

    def test_installs_rules_under_my_claude_kit_namespace(self):
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        installed = sorted(p.name for p in (self.claude / "rules" / "my-claude-kit").iterdir())
        self.assertEqual(installed, KIT_RULES)

    def test_retires_kit_owned_dirs_from_legacy_namespace_into_backup(self):
        self.install()
        self.assertFalse((self.claude / "rules" / "ecc" / "common").exists())
        backups = list((self.claude / ".backup").glob("my-claude-kit-*/rules/ecc/common/old.md"))
        self.assertEqual(len(backups), 1)

    def test_keeps_legacy_dirs_the_kit_does_not_own(self):
        self.install()
        self.assertTrue((self.claude / "rules" / "ecc" / "angular").is_dir())

    def test_dry_run_changes_nothing(self):
        result = self.install("--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.claude / "rules" / "ecc" / "common" / "old.md").exists())
        self.assertFalse((self.claude / "rules" / "my-claude-kit").exists())

    def test_rejects_unknown_option(self):
        result = self.install("--bogus")
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
