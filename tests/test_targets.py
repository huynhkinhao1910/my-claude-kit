"""Tests for the hand-maintained codex/, copilot/ and dotagents/ trees."""
import re
import tomllib
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
OUT_OF_SCOPE = {"instinct-status", "instinct-export", "instinct-import", "evolve",
                "promote", "projects", "prune", "save-session", "resume-session"}
WRITE_TOOLS = {"Write", "Edit"}


def frontmatter(path: Path) -> dict:
    m = re.match(r"---\n(.*?)\n---\n", path.read_text(encoding="utf-8"), re.S)
    assert m, f"{path}: no frontmatter"
    out = {}
    for line in m.group(1).splitlines():
        k, sep, v = line.partition(":")
        if sep and not line.startswith(" "):
            out[k.strip()] = v.strip()
    return out


def claude_tools(path: Path) -> set[str]:
    return set(re.findall(r"[A-Za-z]+", frontmatter(path).get("tools", "")))


AGENTS = sorted(p.stem for p in (KIT / "agents").glob("*.md"))
COMMANDS = sorted(p.stem for p in (KIT / "commands").glob("*.md") if p.stem not in OUT_OF_SCOPE)


class TargetParityTest(unittest.TestCase):
    def test_every_agent_has_codex_and_copilot_twin(self):
        for name in AGENTS:
            self.assertTrue((KIT / "codex/agents" / f"{name}.toml").is_file(), f"codex missing {name}")
            self.assertTrue((KIT / "copilot/agents" / f"{name}.agent.md").is_file(), f"copilot missing {name}")

    def test_every_in_scope_command_has_a_skill(self):
        for name in COMMANDS:
            self.assertTrue((KIT / "dotagents/skills" / name / "SKILL.md").is_file(), f"skill missing {name}")

    def test_out_of_scope_commands_are_not_shipped(self):
        for name in OUT_OF_SCOPE:
            self.assertFalse((KIT / "dotagents/skills" / name).exists(), name)

    def test_command_skills_do_not_collide_with_shared_skills(self):
        shared = {p.name for p in (KIT / "skills").iterdir() if p.is_dir()}
        own = {p.name for p in (KIT / "dotagents/skills").iterdir() if p.is_dir()}
        self.assertEqual(shared & own, set())


class TargetFormatTest(unittest.TestCase):
    def test_codex_agents_parse_and_have_required_keys(self):
        for path in (KIT / "codex/agents").glob("*.toml"):
            data = tomllib.loads(path.read_text(encoding="utf-8"))
            for key in ("name", "description", "developer_instructions"):
                self.assertTrue(data.get(key), f"{path.name}: missing {key}")
            self.assertEqual(data["name"], path.stem)

    def test_read_only_agents_stay_read_only(self):
        for name in AGENTS:
            if claude_tools(KIT / "agents" / f"{name}.md") & WRITE_TOOLS:
                continue
            codex = tomllib.loads((KIT / "codex/agents" / f"{name}.toml").read_text(encoding="utf-8"))
            self.assertEqual(codex.get("sandbox_mode"), "read-only", name)
            copilot = frontmatter(KIT / "copilot/agents" / f"{name}.agent.md")
            self.assertNotIn("edit", copilot.get("tools", ""), name)

    def test_markdown_targets_have_name_and_description(self):
        files = list((KIT / "copilot/agents").glob("*.agent.md")) + list((KIT / "dotagents/skills").glob("*/SKILL.md"))
        self.assertTrue(files)
        for path in files:
            fm = frontmatter(path)
            self.assertTrue(fm.get("name"), f"{path}: name")
            self.assertTrue(fm.get("description"), f"{path}: description")

    def test_skill_name_matches_its_directory(self):
        for path in (KIT / "dotagents/skills").glob("*/SKILL.md"):
            self.assertEqual(frontmatter(path)["name"].strip('"'), path.parent.name)

    def test_copilot_instructions_have_apply_to(self):
        files = list((KIT / "copilot/instructions").glob("*.instructions.md"))
        self.assertTrue(files)
        for path in files:
            self.assertTrue(frontmatter(path).get("applyTo"), path.name)

    def test_codex_agents_md_fits_the_32k_limit(self):
        self.assertLessEqual((KIT / "codex/AGENTS.md").stat().st_size, 32768)

    def test_codex_rules_mirror_kit_rules(self):
        kit = sorted(p.relative_to(KIT / "rules") for p in (KIT / "rules").rglob("*.md"))
        codex_root = KIT / "codex/my-claude-kit/rules"
        codex = sorted(p.relative_to(codex_root) for p in codex_root.rglob("*.md"))
        self.assertEqual(kit, codex)


if __name__ == "__main__":
    unittest.main()
