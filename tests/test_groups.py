"""groups.txt must only name items that exist in the kit."""
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]


def load_groups() -> dict[str, list[str]]:
    groups = {}
    for line in (KIT / "groups.txt").read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            name, _, items = line.partition(":")
            groups[name.strip()] = items.split()
    return groups


class GroupsTest(unittest.TestCase):
    def test_every_item_exists(self):
        for group, items in load_groups().items():
            for item in items:
                kind, _, name = item.partition("/")
                path = KIT / kind / (f"{name}.md" if kind in ("agents", "commands") else name)
                self.assertTrue(path.exists(), f"{group}: {item} not found")

    def test_group_names_are_plain_words(self):
        for name in load_groups():
            self.assertRegex(name, r"^[a-z]+$")


if __name__ == "__main__":
    unittest.main()
