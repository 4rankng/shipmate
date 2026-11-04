"""Composability contract for planning: one shared engine, one artifact, consumers validate.

`shipmate:plan`, `run` stage 6 and the writing-plans procedure must agree on a single
plan producer and a mechanical freshness contract; a regression in any one of the
three surfaces silently reintroduces the two-producer drift this layout removes.
"""
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
PROCEDURE = (PLUGIN_ROOT / "internal/writing-plans/PROCEDURE.md").read_text(encoding="utf-8")
TEMPLATE = (PLUGIN_ROOT / "internal/writing-plans/references/PLAN_TEMPLATE.md").read_text(
    encoding="utf-8")
PLAN = (PLUGIN_ROOT / "skills/plan/SKILL.md").read_text(encoding="utf-8")
RUN = (PLUGIN_ROOT / "skills/run/SKILL.md").read_text(encoding="utf-8")
SPECIFY = (PLUGIN_ROOT / "skills/specify/SKILL.md").read_text(encoding="utf-8")


class SharedEngineTests(unittest.TestCase):
    def test_writing_plans_declares_single_producer_contract(self):
        self.assertIn("only plan producer", PROCEDURE)
        self.assertIn("Plan contract", PROCEDURE)
        self.assertIn("Escalate, never patch", PROCEDURE)
        self.assertIn("Re-read from disk", PROCEDURE)
        self.assertIn("Validate structure, not architecture", PROCEDURE)

    def test_plan_skill_binds_to_the_shared_engine(self):
        self.assertIn("whole", PLAN)
        self.assertIn("planning engine", PLAN)
        self.assertIn("same procedure `run` stage 6 uses", PLAN)
        self.assertIn("../../internal/writing-plans/PROCEDURE.md", PLAN)

    def test_run_stage_6_consumes_instead_of_authoring(self):
        self.assertIn("this stage owns no separate planning rules", RUN)
        self.assertIn("requirement digest matches", RUN)
        self.assertIn("re-read the plan file from disk at stage 7", RUN)
        self.assertIn("instead of patching it", RUN)
        self.assertNotIn(
            "Mark parallel-safe tasks `[P]` per the plan template",
            RUN,
            "stage 6 must not duplicate authoring rules owned by writing-plans",
        )


class PlanArtifactTests(unittest.TestCase):
    def test_template_carries_identity_and_freshness_fields(self):
        for anchor in (
            "Requirement digest:",
            "Plan status:",
            "Verify:",
            "Depends on:",
            "Revision history",
            "first detection signal",
        ):
            self.assertIn(anchor, TEMPLATE, anchor)

        self.assertIn("stable IDs", TEMPLATE)
        self.assertIn("traces to at least one AC", TEMPLATE)
        self.assertIn("explicitly in non-goals", TEMPLATE)

    def test_procedure_requires_verify_hooks_and_change_shape(self):
        self.assertIn("`Verify:` line", PROCEDURE)
        self.assertIn("prose assertion", PROCEDURE)
        self.assertIn("not full implementation bodies", PROCEDURE)
        self.assertIn("one action with a checkable result", PROCEDURE)


class HandoffTests(unittest.TestCase):
    def test_specify_names_plan_as_the_intermediate_next_step(self):
        self.assertIn("shipmate:plan", SPECIFY)


if __name__ == "__main__":
    unittest.main()
