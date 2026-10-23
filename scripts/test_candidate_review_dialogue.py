#!/usr/bin/env python3
"""Regression checks for the bounded challenger/responder candidate-review loop."""

from pathlib import Path
import unittest


PLUGIN_ROOT = Path(__file__).resolve().parents[1]


class CandidateReviewDialogueContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dialogue = (
            PLUGIN_ROOT
            / "internal/reviewer/references/candidate-review-dialogue.md"
        ).read_text(encoding="utf-8")
        cls.reviewer = (PLUGIN_ROOT / "internal/reviewer/PROCEDURE.md").read_text(
            encoding="utf-8"
        )
        cls.code_review = (PLUGIN_ROOT / "internal/code-review/PROCEDURE.md").read_text(
            encoding="utf-8"
        )
        cls.envelope = (
            PLUGIN_ROOT / "internal/reviewer/references/candidate-review-envelope.md"
        ).read_text(encoding="utf-8")
        cls.manifest = (
            PLUGIN_ROOT / "internal/code-review/references/review-manifest.md"
        ).read_text(encoding="utf-8")
        cls.review = (PLUGIN_ROOT / "skills/review/SKILL.md").read_text(encoding="utf-8")
        cls.run_skill = (PLUGIN_ROOT / "skills/run/SKILL.md").read_text(encoding="utf-8")

    def assertNormalizedContains(self, needle, haystack):
        self.assertIn(" ".join(needle.split()), " ".join(haystack.split()))

    def test_candidate_review_has_a_bounded_distinct_challenger_responder_loop(self):
        self.assertIn("candidate-review-dialogue.md", self.reviewer)
        self.assertIn("candidate-review-dialogue.md", self.code_review)
        self.assertNormalizedContains("existing selected candidate reviewer", self.dialogue)
        self.assertIn("not a reviewer persona", self.dialogue)
        self.assertIn("not a voter", self.dialogue)
        self.assertNormalizedContains("balanced capability class", self.dialogue)
        self.assertIn("current host metadata", self.dialogue)
        self.assertIn("closest supported efficient Claude/GPT route", self.dialogue)
        self.assertIn("leave it unset", self.dialogue)
        self.assertIn("documented/default route is not maximum", self.dialogue)
        self.assertIn("Never inherit", self.dialogue)
        self.assertNormalizedContains("at most three repair cycles", self.dialogue)

    def test_read_only_review_cannot_repair_but_authorized_run_can(self):
        self.assertNormalizedContains("read-only `review` action", self.dialogue)
        self.assertIn("answer or propose", self.dialogue)
        self.assertNormalizedContains("authorized `run`/fix", self.dialogue)
        self.assertNormalizedContains("separate from the immutable candidate snapshot", self.dialogue)
        self.assertNormalizedContains("reuse the existing run-owned implementation worktree", self.dialogue)
        self.assertIn("immutable candidate snapshot", self.dialogue)
        self.assertIn("review never fixes", self.review)
        self.assertIn("responder may repair", self.run_skill)

    def test_repairs_receive_independent_current_candidate_recheck(self):
        self.assertNormalizedContains("fresh independent challenger invocation", self.dialogue)
        self.assertNormalizedContains("must not self-certify", self.dialogue)
        self.assertNormalizedContains("new candidate identity", self.dialogue)
        self.assertIn("responder response", self.envelope)
        self.assertNormalizedContains("controller must record one separate responder response", self.envelope)
        self.assertIn("responder_response_file", self.manifest)


if __name__ == "__main__":
    unittest.main()
