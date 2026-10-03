"""The kit itself must pass lint.py (AGENT_STANDARD.md): no missing skills/agents, valid frontmatter."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]


class KitLintTest(unittest.TestCase):
    def test_kit_has_no_lint_errors(self):
        result = subprocess.run(
            [sys.executable, str(KIT_ROOT / "lint.py"), str(KIT_ROOT)],
            capture_output=True, text=True, timeout=60,
        )
        errors = [line for line in result.stdout.splitlines() if line.startswith("ERROR ")]
        self.assertEqual(result.returncode, 0, "\n".join(errors) or result.stdout)


AGENT = """---
name: {name}
description: Does a thing. Use when testing lint. Do NOT use for anything else.
tools: ["Read"]
model: haiku
---

{body}
"""
STANDARD_BODY = "## Role\nx\n\n## Inputs\nx\n\n## Process\nx\n\n## Output\nx\n\n## Never\nx\n"


class LintRulesTest(unittest.TestCase):
    def lint(self, files: dict[str, str]) -> list[str]:
        with tempfile.TemporaryDirectory() as root:
            for rel, text in files.items():
                path = Path(root) / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
            out = subprocess.run([sys.executable, str(KIT_ROOT / "lint.py"), root],
                                 capture_output=True, text=True, timeout=60).stdout
        return [line for line in out.splitlines() if line.startswith("ERROR ") and not line[6:7].isdigit()]

    def test_agent_with_sections_in_standard_order_passes(self):
        self.assertEqual(self.lint({"agents/good.md": AGENT.format(name="good", body=STANDARD_BODY)}), [])

    def test_agent_missing_or_misordered_sections_is_an_error(self):
        bodies = {
            "missing": "## Process\nx\n\n## Output\nx\n",
            "misordered": "## Role\nx\n\n## Process\nx\n\n## Inputs\nx\n\n## Output\nx\n\n## Never\nx\n",
        }
        for name, body in bodies.items():
            errors = self.lint({f"agents/{name}.md": AGENT.format(name=name, body=body)})
            self.assertTrue(any("sections" in e for e in errors), (name, errors))

    def test_skill_over_500_lines_is_an_error(self):
        skill = "---\nname: big\ndescription: Big. Use when testing. Do NOT use otherwise.\n---\n" + "line\n" * 501
        errors = self.lint({"skills/big/SKILL.md": skill})
        self.assertTrue(any("500" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
