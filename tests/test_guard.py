"""Tests for hooks/guard.sh (PreToolUse: exit 2 blocks the tool call)."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

GUARD = Path(__file__).resolve().parents[1] / "hooks" / "guard.sh"


def run_guard(tool, **tool_input):
    payload = json.dumps({"tool_name": tool, "tool_input": tool_input})
    return subprocess.run(["bash", str(GUARD)], input=payload, capture_output=True, text=True, timeout=10)


@unittest.skipUnless(shutil.which("jq"), "guard.sh needs jq")
class GuardTest(unittest.TestCase):
    def assertBlocked(self, result):
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("BLOCKED", result.stderr)

    def assertAllowed(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_blocks_reading_env_files(self):
        self.assertBlocked(run_guard("Read", file_path="/app/.env"))
        self.assertBlocked(run_guard("Edit", file_path="/app/.env.production"))

    def test_allows_env_templates(self):
        self.assertAllowed(run_guard("Read", file_path="/app/.env.example"))
        self.assertAllowed(run_guard("Read", file_path="/app/.env.testing"))

    def test_blocks_credential_files(self):
        self.assertBlocked(run_guard("Read", file_path="/home/u/.ssh/id_ed25519"))
        self.assertBlocked(run_guard("Read", file_path="/app/storage/service-account-prod.json"))

    def test_blocks_env_via_shell(self):
        self.assertBlocked(run_guard("Bash", command="cat .env"))
        self.assertBlocked(run_guard("Bash", command="grep DB_ .env.production"))

    def test_blocks_destructive_db_commands_unless_testing(self):
        self.assertBlocked(run_guard("Bash", command="php artisan migrate:fresh --seed"))
        self.assertAllowed(run_guard("Bash", command="php artisan migrate:fresh --env=testing"))

    def test_blocks_force_push_and_protected_branch_push(self):
        self.assertBlocked(run_guard("Bash", command="git push --force origin feature/x"))
        self.assertBlocked(run_guard("Bash", command="git push origin main"))
        self.assertAllowed(run_guard("Bash", command="git push -u origin feature/orders"))

    def test_blocks_recursive_delete_of_home(self):
        self.assertBlocked(run_guard("Bash", command="rm -rf ~"))
        self.assertAllowed(run_guard("Bash", command="rm -rf node_modules"))

    def test_allows_ordinary_work(self):
        self.assertAllowed(run_guard("Read", file_path="/app/app/Models/Order.php"))
        self.assertAllowed(run_guard("Bash", command="php artisan test --filter=OrderTest"))


if __name__ == "__main__":
    unittest.main()
