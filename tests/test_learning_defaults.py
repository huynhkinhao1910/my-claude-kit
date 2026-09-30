"""Continuous learning ships with the observer on, so a fresh install learns per project."""
import json
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]


class LearningDefaultsTest(unittest.TestCase):
    def test_observer_enabled_by_default(self):
        config = json.loads((KIT / "skills/continuous-learning-v2/config.json").read_text(encoding="utf-8"))
        self.assertIs(config["observer"]["enabled"], True)


if __name__ == "__main__":
    unittest.main()
