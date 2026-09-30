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


class MultiTargetInstallTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.claude, self.codex = root / ".claude", root / ".codex"
        self.copilot, self.agents = root / ".copilot", root / ".agents"
        own_skill = self.agents / "skills" / "my-own-skill"
        own_skill.mkdir(parents=True)
        (own_skill / "SKILL.md").write_text("mine", encoding="utf-8")
        (self.copilot / "agents").mkdir(parents=True)
        (self.copilot / "agents" / "mine.agent.md").write_text("mine", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def install(self, *args):
        env = {**os.environ, "CLAUDE_DIR": str(self.claude), "CODEX_HOME": str(self.codex),
               "COPILOT_HOME": str(self.copilot), "AGENTS_HOME": str(self.agents)}
        return subprocess.run(["bash", str(KIT_ROOT / "install.sh"), *args],
                              env=env, capture_output=True, text=True, timeout=120)

    def test_installs_codex_and_copilot(self):
        r = self.install("--target", "codex,copilot")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.codex / "AGENTS.md").is_file())
        self.assertTrue((self.codex / "agents" / "planner.toml").is_file())
        self.assertTrue((self.codex / "my-claude-kit" / "rules" / "php" / "coding-style.md").is_file())
        self.assertTrue((self.copilot / "copilot-instructions.md").is_file())
        self.assertTrue((self.copilot / "agents" / "planner.agent.md").is_file())
        self.assertTrue((self.copilot / "instructions" / "php-coding-style.instructions.md").is_file())
        self.assertTrue((self.agents / "skills" / "debugging" / "SKILL.md").is_file())
        self.assertTrue((self.agents / "skills" / "quick" / "SKILL.md").is_file())
        self.assertFalse((self.agents / "skills" / "continuous-learning-v2").exists())
        self.assertFalse(self.claude.exists(), "claude target must not run")

    def test_equals_form_works(self):
        r = self.install("--target=codex")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.codex / "agents" / "planner.toml").is_file())
        self.assertFalse((self.copilot / "copilot-instructions.md").exists())

    def test_keeps_items_the_kit_does_not_own(self):
        self.install("--target", "codex,copilot")
        self.assertEqual((self.agents / "skills" / "my-own-skill" / "SKILL.md").read_text(), "mine")
        self.assertEqual((self.copilot / "agents" / "mine.agent.md").read_text(), "mine")

    def test_reinstall_backs_up_overwritten_items(self):
        self.install("--target", "codex")
        (self.codex / "AGENTS.md").write_text("edited", encoding="utf-8")
        r = self.install("--target", "codex")
        self.assertEqual(r.returncode, 0, r.stderr)
        backups = list((self.codex / ".backup").glob("my-claude-kit-*/AGENTS.md"))
        self.assertEqual([b.read_text() for b in backups], ["edited"])

    def test_no_claude_md_skips_instruction_files(self):
        r = self.install("--target", "codex,copilot", "--no-claude-md")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse((self.codex / "AGENTS.md").exists())
        self.assertFalse((self.copilot / "copilot-instructions.md").exists())
        self.assertTrue((self.codex / "agents" / "planner.toml").is_file())

    def test_unknown_target_writes_nothing(self):
        r = self.install("--target", "codex,codx")
        self.assertEqual(r.returncode, 2)
        self.assertFalse(self.codex.exists())
        self.assertFalse(self.claude.exists())

    def test_empty_target_is_rejected(self):
        self.assertEqual(self.install("--target=").returncode, 2)

    def test_bare_target_is_rejected_with_message(self):
        r = self.install("--target")
        self.assertEqual(r.returncode, 2)
        self.assertIn("--target needs a value", r.stderr)

    def test_dry_run_writes_nothing(self):
        r = self.install("--target", "codex,copilot", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(self.codex.exists())
        self.assertFalse((self.copilot / "copilot-instructions.md").exists())

if __name__ == "__main__":
    unittest.main()
