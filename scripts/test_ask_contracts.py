import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]


class AskContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ask = (PLUGIN_ROOT / "skills/ask/SKILL.md").read_text(encoding="utf-8")
        cls.normalized = " ".join(cls.ask.split())

    def test_ask_is_a_self_contained_public_entrypoint(self):
        self.assertIn("six public entrypoints", self.ask)
        self.assertEqual(self.frontmatter_name(), "ask")
        self.assertIn("Use when", self.description())
        self.assertIn("Not for reviewing git diffs or auditing pull requests", self.description())
        self.assertLess(len(self.ask.splitlines()), 200)

    def test_ask_is_read_only_with_a_command_policy(self):
        self.assertIn("Ask is read-only", self.ask)
        self.assertIn(
            "never writes files, installs anything, fetches the network, changes branches",
            self.normalized,
        )
        self.assertIn("Findings propose; the developer decides", self.ask)

    def test_ask_invariants_are_pinned(self):
        self.assertIn("Never query the developer for information discoverable from repository", self.normalized)
        self.assertIn("At most three questions per run", self.normalized)
        self.assertIn("No falsifier, no finding", self.normalized)
        self.assertIn("Uncited findings do not ship", self.normalized)

    def test_ask_modes_are_enumerated(self):
        for mode in ("root-cause", "explore", "improve-process", "optimize", "brainstorm", "auto"):
            self.assertIn(mode, self.ask)
        self.assertIn("never `auto`", self.normalized)

    def test_ask_layers_are_pinned(self):
        self.assertIn("scope fence holds for the whole run", self.normalized)
        self.assertIn("exclude the contaminated source from evidence, candidates, causal paths", self.normalized)
        self.assertIn("10–15 candidates without judging", self.normalized)
        self.assertIn("top 2–3 into Layer 1", self.normalized)
        self.assertIn("brainstorm mode ranks the full scored list and stops", self.normalized)
        self.assertIn("up to 12 automated inspections", self.normalized)
        self.assertIn("Cap each branch at five levels", self.normalized)
        self.assertIn("carries its own falsification test", self.normalized)

    def test_ask_guardrails_against_known_failure_modes(self):
        self.assertIn("late ideas go to the parking lot, never the register", self.normalized)
        self.assertIn("no fabricated findings, nothing is blocked", self.normalized)
        self.assertIn("substitute, combine, adapt and friends", self.normalized)
        self.assertIn("single-narrative causes that discard competing branches", self.normalized)

    def test_ask_output_contract_is_pinned(self):
        self.assertIn("Render the report inline in Markdown", self.normalized)
        self.assertIn("Never write report files or invoke scripts", self.normalized)
        self.assertIn("Causal sufficiency tree", self.normalized)
        self.assertIn("Findings register", self.normalized)
        self.assertIn("FIND-NNN", self.normalized)
        self.assertIn("meaning never depends on a renderer", self.normalized)
        self.assertIn("Brainstorm runs replace sections 2 and 3 with the scored candidate table", self.normalized)
        self.assertIn("`RESOLVED` closed", self.normalized)

    def test_ask_links_only_the_shared_contract(self):
        self.assertEqual(self.ask.count("](../../"), 1)
        self.assertIn("../../internal/user-questions.md", self.ask)

    def test_ask_references_no_other_skill_or_script(self):
        for banned in (
            "shipmate:specify",
            "shipmate:run",
            "shipmate:review",
            "shipmate:walkthrough",
            "shipmate:quiz",
            "webchat",
            "skills/",
            "${SHIPMATE_PLUGIN_ROOT}",
        ):
            self.assertNotIn(banned, self.ask)

    def test_ask_has_no_quiz_scoring_contract(self):
        self.assertNotIn("A–D", self.ask)
        self.assertNotIn("four options", self.ask)

    def frontmatter_name(self):
        block = self.ask.split("---", 2)[1]
        for line in block.splitlines():
            if line.startswith("name:"):
                return line.split(":", 1)[1].strip()
        return ""

    def description(self):
        block = self.ask.split("---", 2)[1]
        for line in block.splitlines():
            if line.startswith("description:"):
                return line.split("description:", 1)[1].strip()
        return ""


if __name__ == "__main__":
    unittest.main()
