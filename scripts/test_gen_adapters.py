"""Adapter generator guarantees: link retargeting, byte-clean regeneration, derived pins."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from gen_adapters import rewrite_links

SCRIPT = Path(__file__).parent / "gen_adapters.py"
PLUGIN_ROOT = SCRIPT.parent.parent

SKILLS = ("specify", "run", "review", "walkthrough", "quiz", "ask")
TREES = ("commands", ".cursor/rules", ".windsurf/workflows", ".continue/prompts")

SENTINELS = {
    "specify": "no minimum interview length or question quota",
    "run": "Never merge, approve or deploy",
    "review": "never fixes, commits, comments, approves, pushes, deploys, or merges",
    "walkthrough": "Never present two layers in one pass",
    "quiz": "Nothing leaves the chat",
    "ask": "Findings propose; the developer decides",
}


class RewriteLinksTests(unittest.TestCase):
    def test_retargets_repo_root_links_for_depth_one_outputs(self):
        body = "Read [workflow-policy](../../internal/workflow-policy.md) and [quiz](../quiz/SKILL.md)."
        rewritten = rewrite_links(body, source_dir="skills/run", output_dir="commands")
        self.assertIn("(../internal/workflow-policy.md)", rewritten)
        self.assertIn("(../skills/quiz/SKILL.md)", rewritten)

    def test_keeps_depth_for_depth_two_outputs_and_absolute_links(self):
        body = ("See [diagrams](references/diagrams.md) and "
                "[policy](../../internal/workflow-policy.md) plus [site](https://example.com).")
        rewritten = rewrite_links(body, source_dir="skills/walkthrough",
                                  output_dir=".cursor/rules")
        self.assertIn("(../../skills/walkthrough/references/diagrams.md)", rewritten)
        self.assertIn("(../../internal/workflow-policy.md)", rewritten)
        self.assertIn("(https://example.com)", rewritten)


class RegenerationCleanTests(unittest.TestCase):
    def test_committed_adapter_tree_is_byte_clean(self):
        run = subprocess.run([sys.executable, str(SCRIPT), "--check", "--root", str(PLUGIN_ROOT)],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

    def test_check_detects_drift_in_a_scratch_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for skill in SKILLS:
                skill_dir = root / "skills" / skill
                skill_dir.mkdir(parents=True)
                (skill_dir / "SKILL.md").write_text(
                    f"---\nname: {skill}\ndescription: {skill} contract\n---\n\n# {skill}\n\n"
                    f"Sentinel for {skill}: {SENTINELS[skill]}.\n",
                    encoding="utf-8",
                )
            (root / "adapters.json").write_text(
                (PLUGIN_ROOT / "adapters.json").read_text(encoding="utf-8"), encoding="utf-8")
            generate = subprocess.run(
                [sys.executable, str(SCRIPT), "--root", str(root)],
                capture_output=True, text=True)
            self.assertEqual(generate.returncode, 0, generate.stdout + generate.stderr)
            for skill in SKILLS:
                self.assertTrue((root / "commands" / f"{skill}.md").exists(), skill)
                self.assertTrue((root / ".continue" / "prompts" / f"{skill}.prompt").exists(),
                                skill)
            victim = root / "commands" / "quiz.md"
            victim.write_text("drifted", encoding="utf-8")
            check = subprocess.run(
                [sys.executable, str(SCRIPT), "--check", "--root", str(root)],
                capture_output=True, text=True)
            self.assertEqual(check.returncode, 1)
            self.assertIn("commands/quiz.md", check.stdout)


class DerivedPinCoverageTests(unittest.TestCase):
    def test_every_generated_surface_carries_its_skill_sentinel(self):
        for skill in SKILLS:
            for tree in TREES:
                suffix = ".mdc" if tree == ".cursor/rules" else (".prompt" if tree ==
                                                                 ".continue/prompts" else ".md")
                surface = PLUGIN_ROOT / tree / f"shipmate-{skill}{suffix}" if tree == \
                    ".cursor/rules" else PLUGIN_ROOT / tree / f"{skill}{suffix}"
                text = surface.read_text(encoding="utf-8")
                self.assertIn(SENTINELS[skill], text, f"{tree}/{skill}")


if __name__ == "__main__":
    unittest.main()
