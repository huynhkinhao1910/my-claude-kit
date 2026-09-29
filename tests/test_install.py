"""Tests for install.sh: rules namespace and retiring legacy/duplicate rule installs."""
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
        (legacy / "zh").mkdir()
        (legacy / "README.md").write_text("ecc install notes", encoding="utf-8")
        flat = self.claude / "rules"
        (flat / "common").mkdir()
        (flat / "zh").mkdir()
        (flat / "README.md").write_text("flat install notes", encoding="utf-8")
        (flat / "python").mkdir()  # not owned by the kit, must survive

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
        self.assertTrue((self.claude / "rules" / "python").is_dir())

    def test_retires_flat_root_copies_of_kit_rules(self):
        self.install()
        self.assertFalse((self.claude / "rules" / "common").exists())
        self.assertTrue((self.claude / "rules" / "my-claude-kit" / "common").is_dir())

    def test_retires_known_duplicates_in_every_legacy_namespace(self):
        self.install()
        for rel in ("zh", "README.md", "ecc/zh", "ecc/README.md"):
            self.assertFalse((self.claude / "rules" / rel).exists(), rel)
        backups = list((self.claude / ".backup").glob("my-claude-kit-*/rules/README.md"))
        self.assertEqual(backups[0].read_text(encoding="utf-8"), "flat install notes")

    def test_retire_duplicates_can_be_disabled(self):
        env = {**os.environ, "CLAUDE_DIR": str(self.claude), "RETIRE_DUPLICATES": ""}
        subprocess.run(["bash", str(KIT_ROOT / "install.sh"), "--no-hooks"], env=env,
                       capture_output=True, text=True, timeout=120, check=True)
        self.assertTrue((self.claude / "rules" / "zh").is_dir())

    def test_dry_run_changes_nothing(self):
        result = self.install("--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.claude / "rules" / "ecc" / "common" / "old.md").exists())
        self.assertFalse((self.claude / "rules" / "my-claude-kit").exists())

    def test_installs_claude_md_with_backup(self):
        (self.claude / "CLAUDE.md").write_text("machine specific", encoding="utf-8")
        self.install()
        kit = (KIT_ROOT / "claude" / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertEqual((self.claude / "CLAUDE.md").read_text(encoding="utf-8"), kit)
        backups = list((self.claude / ".backup").glob("my-claude-kit-*/CLAUDE.md"))
        self.assertEqual(backups[0].read_text(encoding="utf-8"), "machine specific")

    def test_no_claude_md_keeps_existing_file(self):
        (self.claude / "CLAUDE.md").write_text("machine specific", encoding="utf-8")
        self.install("--no-claude-md")
        self.assertEqual((self.claude / "CLAUDE.md").read_text(encoding="utf-8"), "machine specific")

    def test_installs_guard_hooks(self):
        self.install()
        for name in ("guard.sh", "post-edit-format.sh", "inject-instincts.py"):
            self.assertTrue((self.claude / "hooks" / "my-claude-kit" / name).is_file(), name)

    def test_rejects_unknown_option(self):
        result = self.install("--bogus")
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
