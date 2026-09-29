"""The kit itself must pass lint.py (AGENT_STANDARD.md): no missing skills/agents, valid frontmatter."""
import subprocess
import sys
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


if __name__ == "__main__":
    unittest.main()
