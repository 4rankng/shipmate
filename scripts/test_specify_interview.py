"""Structural guards complement the independent model trials in evals/specify-cases.json."""
import json
from pathlib import Path
from unittest import TestCase
from validate_spec import validate

ROOT = Path(__file__).resolve().parents[1]


class SpecifyInterviewTests(TestCase):
    def test_interview_is_evidence_first_with_bounded_draft_not_question_quota(self):
        text = (ROOT / "skills/specify/SKILL.md").read_text()
        for clause in (
            "Diagnose the likely cause",
            "decision-tree interview",
            "assumption with a concrete scenario",
            "Wait for the answer",
            "zero questions",
            "target, not a hard cap",
            "strong\nreason",
            "never\ntruncate or remove material requirements",
            "technical business analyst",
            "Technical Notes",
            "scripts/validate_spec.py",
        ):
            self.assertIn(clause, text)

    def test_interview_does_not_expand_authority_or_create_unrequested_docs(self):
        text = (ROOT / "internal/grill-with-docs/PROCEDURE.md").read_text()
        for clause in (
            "Do not simulate the user's answer",
            "Do not create glossary or ADR files",
            "return to `specify`",
            "only when the user asked",
            "Do not fetch upstream",
        ):
            self.assertIn(clause, text)
        self.assertNotIn("Update\nthe repository's glossary immediately", text)

    def test_compact_example_keeps_gwt_and_conditional_evidence(self):
        text = (ROOT / "skills/specify/references/concise-spec.md").read_text()
        draft = text.split("```md\n", 1)[1].split("```", 1)[0]
        self.assertTrue(validate(draft)["valid"])
        self.assertEqual(draft.count("- AC-"), 3)
        self.assertIn("no longer permitted", draft)

    def test_worked_drafts_validate_and_recovery_example_preserves_scope(self):
        import re
        text = (ROOT / "skills/specify/references/concise-spec.md").read_text()
        drafts = re.findall(r"```md\n(.*?)```", text, re.DOTALL)
        self.assertEqual(len(drafts), 2)
        for draft in drafts:
            self.assertTrue(validate(draft)["valid"], validate(draft))
        recovery = drafts[1]
        for rule in ("## Definitions", "original result and event ID", "published to Kafka for the report service", "210 or 400",
                     "Out of Scope\n- Duplicate-event handling in the report service (ABC-3956)",
                     "Resending acknowledgments", "AC-06 (Buyer cancel)"):
            self.assertIn(rule, recovery)
        self.assertNotIn("exactly-once", recovery.lower())
        self.assertFalse(validate(recovery)["within_target"])
        self.assertIn("reason given in chat", text)
        self.assertIn("Proposed summary", text)

    def test_translation_checks_evidence_not_just_word_count(self):
        selection = (ROOT / "skills/specify/references/content-selection.md").read_text()
        review = (ROOT / "internal/reviewer/references/specification-personas.md").read_text()
        for clause in ("Do not guess an acronym expansion or state mapping", "consumer deduplication",
                       "length\nlimits remain a target", "component ownership", "Out of Scope with its owner"):
            self.assertIn(clause, selection)
        self.assertIn("unsupported delivery/recovery guarantees", review)
        cases = json.loads((ROOT / "scripts/evals/specify-cases.json").read_text())["cases"]
        self.assertTrue({"translate-recovery-shorthand", "unknown-state-meaning",
                         "producer-consumer-guarantee-boundary", "justified-over-target"}.issubset({c["id"] for c in cases}))

    def test_forward_cases_are_distinct_from_rubric(self):
        path = ROOT / "scripts/evals/specify-cases.json"
        cases = json.loads(path.read_text())["cases"]
        self.assertEqual(len({c["id"] for c in cases}), len(cases))
        for case in cases:
            self.assertEqual(set(case), {"id", "brief", "evidence"})
        self.assertTrue((path.parent / "specify-rubric.md").is_file())

    def test_dense_contract_reduction_preserves_essential_rules(self):
        text = (ROOT / "skills/specify/references/content-selection.md").read_text()
        reviewer = (ROOT / "internal/reviewer/references/specification-personas.md").read_text()
        self.assertIn("Do not silently discard a requirement", text)
        self.assertIn("distinct outcomes", text)
        self.assertIn("lookup failure", text)
        self.assertIn("passing the validator does not establish semantic completeness", text)
        self.assertIn("must versus may", text)
        self.assertIn("deadlines", text)
        self.assertIn("inaccessible machine-local notes", text)
        self.assertIn("content-selection.md", reviewer)
        self.assertIn("not a new approval veto", reviewer)

    def test_technical_design_interview_is_reachable_from_specify_and_run(self):
        reference = ROOT / "skills/specify/references/technical-design.md"
        self.assertTrue(reference.is_file())
        for route in (
            "skills/specify/SKILL.md",
            "skills/run/SKILL.md",
            "internal/grill-with-docs/PROCEDURE.md",
            "internal/workflow-policy.md",
        ):
            text = (ROOT / route).read_text()
            self.assertIn("technical-design.md", text, route)
        design = reference.read_text()
        for constraint in (
            "requirements and design",
            "one question at a time",
            "Wait for the answer",
            "do not start coding",
            "already explicit design",
            "not approval of a new material design",
            "mechanics remain the agent's responsibility",
        ):
            self.assertIn(constraint.lower(), design.lower())

    def test_repository_fit_is_checked_before_design_and_during_review(self):
        design = (ROOT / "skills/specify/references/technical-design.md").read_text()
        self.assertIn("## Repository fit before proposing new code", design)
        self.assertIn("real caller", design)
        self.assertIn("not proof of absence", design)
        for route in (
            "internal/writing-plans/PROCEDURE.md",
            "internal/reviewer/references/plan-personas.md",
            "internal/reviewer/references/requirements-code-quality-reviewer.md",
        ):
            self.assertIn("technical-design.md", (ROOT / route).read_text(), route)
