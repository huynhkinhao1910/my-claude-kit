"""Tests for hooks/inject-instincts.py (SessionStart instinct injection)."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]
HOOK = KIT_ROOT / "hooks" / "inject-instincts.py"
CLI = KIT_ROOT / "skills" / "continuous-learning-v2" / "scripts" / "instinct-cli.py"
REMOTE = "https://gitlab.com/example/shop-api.git"


def instinct(instinct_id, confidence, action, scope="project"):
    return (
        f"---\nid: {instinct_id}\ntrigger: \"when testing\"\n"
        f"confidence: {confidence}\ndomain: testing\nscope: {scope}\n---\n\n"
        f"# {instinct_id}\n\n## Action\n{action}\n\n## Evidence\n- observed\n"
    )


class InjectInstinctsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.data_dir = base / "data"
        self.repo = base / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        subprocess.run(["git", "remote", "add", "origin", REMOTE], cwd=self.repo, check=True)
        self.env = {
            "PATH": os.environ["PATH"],
            "HOME": str(base),
            "CLV2_HOMUNCULUS_DIR": str(self.data_dir),
            "CLV2_INSTINCT_CLI": str(CLI),
        }
        self.project_dir = self._detect_project_dir()

    def tearDown(self):
        self.tmp.cleanup()

    def _detect_project_dir(self):
        """Ask the real CLI where it stores this repo, so hashes never drift."""
        code = (
            "import importlib.util,sys;"
            f"s=importlib.util.spec_from_file_location('cli',{str(CLI)!r});"
            "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
            "print(m.detect_project()['project_dir'])"
        )
        out = subprocess.run(
            [sys.executable, "-c", code], cwd=self.repo, env=self.env,
            capture_output=True, text=True, check=True,
        )
        return Path(out.stdout.strip())

    def write_project(self, name, content):
        target = self.project_dir / "instincts" / "personal"
        target.mkdir(parents=True, exist_ok=True)
        (target / name).write_text(content, encoding="utf-8")

    def write_global(self, name, content):
        target = self.data_dir / "instincts" / "personal"
        target.mkdir(parents=True, exist_ok=True)
        (target / name).write_text(content, encoding="utf-8")

    def run_hook(self, extra_env=None, stdin=None):
        env = {**self.env, **(extra_env or {})}
        payload = stdin if stdin is not None else json.dumps({"cwd": str(self.repo)})
        return subprocess.run(
            [sys.executable, str(HOOK)], cwd=self.repo, env=env, input=payload,
            capture_output=True, text=True, timeout=30,
        )

    def context_of(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["hookSpecificOutput"]["hookEventName"], "SessionStart")
        return data["hookSpecificOutput"]["additionalContext"]

    def test_prints_nothing_when_no_instincts_exist(self):
        result = self.run_hook()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "")

    def test_injects_action_line_with_scope_and_confidence(self):
        self.write_project("a.yaml", instinct("use-form-request", 0.8, "Validate input with FormRequest classes."))
        context = self.context_of(self.run_hook())
        self.assertIn("- [project 80%] Validate input with FormRequest classes.", context)

    def test_skips_instincts_below_default_threshold(self):
        self.write_project("a.yaml", instinct("weak", 0.4, "Weak habit."))
        self.write_project("b.yaml", instinct("strong", 0.5, "Strong habit."))
        context = self.context_of(self.run_hook())
        self.assertIn("Strong habit.", context)
        self.assertNotIn("Weak habit.", context)

    def test_project_instinct_overrides_global_with_same_id(self):
        self.write_global("g.yaml", instinct("naming", 0.9, "Global naming rule.", scope="global"))
        self.write_project("p.yaml", instinct("naming", 0.6, "Project naming rule."))
        context = self.context_of(self.run_hook())
        self.assertIn("Project naming rule.", context)
        self.assertNotIn("Global naming rule.", context)

    def test_ranks_project_scope_above_slightly_stronger_global(self):
        self.write_global("g.yaml", instinct("global-one", 0.9, "Global rule.", scope="global"))
        self.write_project("p.yaml", instinct("project-one", 0.7, "Project rule."))
        context = self.context_of(self.run_hook())
        self.assertLess(context.index("Project rule."), context.index("Global rule."))

    def test_caps_number_of_injected_instincts(self):
        for i in range(5):
            self.write_project(f"{i}.yaml", instinct(f"rule-{i}", 0.9, f"Rule {i}."))
        context = self.context_of(self.run_hook({"ECC_MAX_INJECTED_INSTINCTS": "2"}))
        self.assertEqual(context.count("- [project"), 2)

    def test_threshold_env_override(self):
        self.write_project("a.yaml", instinct("mid", 0.6, "Mid habit."))
        result = self.run_hook({"ECC_INSTINCT_CONFIDENCE_THRESHOLD": "0.7"})
        self.assertEqual(result.stdout.strip(), "")

    def test_invalid_env_values_fall_back_to_defaults(self):
        self.write_project("a.yaml", instinct("mid", 0.6, "Mid habit."))
        context = self.context_of(self.run_hook({
            "ECC_INSTINCT_CONFIDENCE_THRESHOLD": "0x1",
            "ECC_MAX_INJECTED_INSTINCTS": "abc",
        }))
        self.assertIn("Mid habit.", context)

    def test_disabled_file_suppresses_injection(self):
        self.write_project("a.yaml", instinct("x", 0.9, "Should not appear."))
        (self.data_dir / "disabled").write_text("", encoding="utf-8")
        result = self.run_hook()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "")

    def test_missing_cli_exits_zero_without_output(self):
        result = self.run_hook({"CLV2_INSTINCT_CLI": "/nonexistent/instinct-cli.py"})
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")
        self.assertIn("[inject-instincts]", result.stderr)

    def test_malformed_stdin_is_ignored(self):
        self.write_project("a.yaml", instinct("x", 0.9, "Still injected."))
        context = self.context_of(self.run_hook(stdin="not json"))
        self.assertIn("Still injected.", context)


if __name__ == "__main__":
    unittest.main()
