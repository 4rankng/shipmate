"""Cross-document regressions for seamless, risk-proportional L3 execution."""
import re
from pathlib import Path
from unittest import TestCase


PLUGIN_ROOT = Path(__file__).resolve().parents[1]


class SeamlessWorkflowContractTests(TestCase):
    @classmethod
    def setUpClass(cls):
        paths = {
            "policy": "internal/workflow-policy.md",
            "run": "skills/run/SKILL.md",
            "review": "skills/review/SKILL.md",
            "specify": "skills/specify/SKILL.md",
            "requirements": "internal/requirements-source/PROCEDURE.md",
            "plans": "internal/writing-plans/PROCEDURE.md",
            "executing": "internal/executing-plans/PROCEDURE.md",
            "verification": "internal/verification-before-completion/PROCEDURE.md",
            "reviewer": "internal/reviewer/PROCEDURE.md",
            "freshness": "internal/reviewer/references/review-freshness.md",
            "catalog": "internal/reviewer/references/persona-catalog.md",
            "spec_personas": "internal/reviewer/references/specification-personas.md",
            "plan_personas": "internal/reviewer/references/plan-personas.md",
            "candidate": "internal/reviewer/references/candidate-review-envelope.md",
        }
        cls.paths = {name: PLUGIN_ROOT / path for name, path in paths.items()}
        cls.docs = {name: path.read_text(encoding="utf-8") for name, path in cls.paths.items()}

    def assertContains(self, document, text):
        self.assertIn(text, self.docs[document], f"{document} must state: {text}")

    def assertNormalizedContains(self, document, text):
        self.assertIn(" ".join(text.split()), " ".join(self.docs[document].split()),
                      f"{document} must state: {text}")

    def assertAbsentEverywhere(self, text, documents=None):
        documents = documents or self.docs
        hits = [name for name in documents if text in self.docs[name]]
        self.assertFalse(hits, f"stale clause {text!r} remains in: {', '.join(hits)}")

    def test_policy_links_resolve_for_documents_that_invoke_it(self):
        for name in ("run", "review", "requirements", "plans", "verification", "reviewer"):
            document = self.docs[name]
            match = re.search(r"\[[^]]*workflow[ -]policy[^]]*\]\(([^)]+)\)", document, re.IGNORECASE)
            self.assertIsNotNone(match, f"{name} must link the shared policy")
            self.assertTrue((self.paths[name].parent / match.group(1)).resolve().is_file())

    def test_recoverable_and_clear_work_continues_without_abort_or_reasking(self):
        self.assertContains("policy", "Repair within existing authority, revalidate affected evidence, continue")
        self.assertContains("policy", "Never repeat a settled question")
        self.assertNormalizedContains("run", "Do not ask the user to restate a clear request")
        self.assertContains("requirements", "ask one precise question and resume after its answer")
        self.assertContains("plans", "resume here after the answer")
        self.assertAbsentEverywhere("asynchronous source-mode abort protocol")
        self.assertAbsentEverywhere("selected-source `spec-gap` abort")
        self.assertAbsentEverywhere("stable comment inventory")

    def test_plan_is_machine_local_unless_user_or_repository_requires_commit(self):
        self.assertContains("policy", "machine-local by default")
        self.assertContains("run", "Committing a plan into the PR is not required")
        self.assertContains("plans", "Persist the plan machine-locally by default")
        self.assertContains("plans", "Commit a design document only when repository policy\nor the user requires one")
        self.assertContains("candidate", "machine-local by default")
        self.assertAbsentEverywhere("must commit the plan")

    def test_risk_roster_is_one_independent_candidate_review_for_low_risk_and_two_for_higher_risk(self):
        self.assertContains("policy", "one independent\n  `requirements-code-quality` candidate reviewer")
        self.assertContains("policy", "use the two applicable catalog personas")
        self.assertContains("run", "one independent requirements/code-quality reviewer")
        self.assertContains("candidate", "It does not claim a separate security persona\nran")
        self.assertContains("catalog", "There is no\nminimum or quota")
        self.assertAbsentEverywhere("Select only the two phase personas", ("review",))
        self.assertAbsentEverywhere("selected two-persona cohort", ("specify",))

    def test_current_candidate_review_never_reuses_stale_pass(self):
        self.assertContains("policy", "Never relabel an old PASS with a new SHA")
        self.assertContains("run", "Never attach an old PASS to a new SHA")
        self.assertContains("reviewer", "prior `PASS` is never reused for a new SHA")
        self.assertContains("freshness", "require an independent delta or full readback")
        self.assertContains("verification", "never carry an\nold PASS to a new SHA")

    def test_each_phase_is_independent_even_for_low_risk(self):
        self.assertNormalizedContains("policy", "one independent `requirements-testability` specification reviewer")
        self.assertNormalizedContains("policy", "independent `architecture-simplicity` plan reviewer")
        self.assertNormalizedContains("specify", "one independent Requirements & Testability reviewer")
        self.assertNormalizedContains("plans", "Low-risk work receives an independent Architecture & Simplicity review")
        self.assertAbsentEverywhere("controller review is sufficient")
        self.assertAbsentEverywhere("controller plan assessment")
        self.assertAbsentEverywhere("controller clarity check")

    def test_delivery_loop_returns_to_affected_phase_without_claiming_merge(self):
        self.assertContains("policy", "refresh its selected\n   reviews, and return to implementation")
        self.assertContains("policy", "failures through Build & review")
        self.assertContains("policy", "ready for human review, not approval, merge or deployment")
        self.assertContains("policy", "three-cycle/no-progress bound")
        self.assertContains("run", "Revise the plan\nonly if the approach changed")

    def test_existing_mr_adoption_uses_current_evidence_not_historical_provenance(self):
        self.assertContains("policy", "Label its scope `adopted-candidate`, not\n`full-lifecycle`")
        self.assertContains("policy", "Missing old approval/hash/spec/plan artifacts are not admission blockers")
        self.assertContains("candidate", "For `adopted-candidate` review, old L3 provenance is optional")
        self.assertContains("verification", "does not certify prior lifecycle phases")
        self.assertContains("reviewer", "`full-lifecycle` or `adopted-candidate`")

    def test_safe_fallback_preserves_authority_and_distinguishes_optional_from_required(self):
        self.assertContains("policy", "Never bypass a denied permission")
        self.assertContains("executing", "Do not invent credentials, disable checks, or expand permissions")
        self.assertContains("policy", "Optional hook failures are advisory")
        self.assertContains("policy", "Required failed tests,\nsecurity findings, and secret hits prevent successful delivery")
        self.assertContains("verification", "Report required checks as passed, failed, unavailable or pending")
        self.assertContains("verification", "Optional hook failures are advisory")
        for status in ("`needs-input`", "`review-pending`", "`verification-pending`", "`stopped`"):
            self.assertIn(status, self.docs["policy"])

    def test_capability_and_dependency_discovery_precedes_scope_gap_and_has_no_estimate_quota(self):
        self.assertContains("policy", "Before declaring a missing implementation or dependency a specification gap")
        self.assertContains("policy", "Inspect the actual owning code/API/schema")
        self.assertContains("policy", "Distinguish existing capability")
        self.assertContains("requirements", "discovery before a scope-gap judgment")
        self.assertContains("plans", "Inspect directly linked dependency tickets/MRs before calling\na missing capability a scope gap")
        self.assertContains("policy", "There is no story-point hard gate")
        self.assertContains("plans", "Order by real dependency, not story-point estimates")
        self.assertContains("catalog", "minimum or quota")
