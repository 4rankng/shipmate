"""SKILL.md frontmatter schema guarantees for every shipped skill.

The link checker validates links and gen_adapters validates generated copies,
but neither validates frontmatter: a skill with a missing description, a name
that diverges from its directory, or an oversized description can ship green
and then break skill discovery or ranking in the host.
"""
import re
import unittest
from pathlib import Path

FRONT_MATTER = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
NAME = re.compile(r"^name:\s*(\S+)\s*$", re.MULTILINE)
DESCRIPTION = re.compile(r"^description:\s*(.+)$", re.MULTILINE)

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SKILLS = PLUGIN_ROOT / "skills"


class SkillFrontmatterTests(unittest.TestCase):
    def test_every_skill_frontmatter_is_wellformed(self):
        skills = sorted(p for p in SKILLS.iterdir() if (p / "SKILL.md").is_file())
        self.assertGreater(len(skills), 0, "no skills discovered")
        for skill_dir in skills:
            with self.subTest(skill=skill_dir.name):
                text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
                match = FRONT_MATTER.match(text)
                self.assertIsNotNone(match, "missing front matter block")
                front = match.group(1)
                name = NAME.search(front)
                self.assertIsNotNone(name, "missing name key")
                self.assertEqual(name.group(1), skill_dir.name,
                                 "name diverges from directory")
                self.assertRegex(name.group(1), r"^[a-z0-9][a-z0-9-]{0,63}$")
                description = DESCRIPTION.search(front)
                self.assertIsNotNone(description, "missing description key")
                self.assertGreater(len(description.group(1).strip()), 0,
                                   "empty description")
                self.assertLessEqual(len(description.group(1).strip()), 1024,
                                     "description over 1024 chars")


if __name__ == "__main__":
    unittest.main()
