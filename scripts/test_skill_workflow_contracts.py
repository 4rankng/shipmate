import json
from pathlib import Path
from unittest import TestCase


PLUGIN_ROOT = Path(__file__).resolve().parents[1]


class SpecificationAdmissionContractTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.l3 = (PLUGIN_ROOT / "skills/run/SKILL.md").read_text(encoding="utf-8")
        cls.specify = (PLUGIN_ROOT / "skills/specify/SKILL.md").read_text(encoding="utf-8")
        cls.review = (PLUGIN_ROOT / "skills/review/SKILL.md").read_text(encoding="utf-8")
        cls.spec_personas = (
            PLUGIN_ROOT / "internal/reviewer/references/specification-personas.md"
        ).read_text(encoding="utf-8")
        cls.plan_personas = (
            PLUGIN_ROOT / "internal/reviewer/references/plan-personas.md"
        ).read_text(encoding="utf-8")
        cls.candidate_envelope = (
            PLUGIN_ROOT / "internal/reviewer/references/candidate-review-envelope.md"
        ).read_text(encoding="utf-8")
        cls.review_manifest = (
            PLUGIN_ROOT / "internal/code-review/references/review-manifest.md"
        ).read_text(encoding="utf-8")
        cls.code_review = (PLUGIN_ROOT / "internal/code-review/PROCEDURE.md").read_text(
            encoding="utf-8"
        )
        cls.verification = (
            PLUGIN_ROOT / "internal/verification-before-completion/PROCEDURE.md"
        ).read_text(encoding="utf-8")
        cls.persona_catalog = (
            PLUGIN_ROOT / "internal/reviewer/references/persona-catalog.md"
        ).read_text(encoding="utf-8")
        cls.reviewer = (PLUGIN_ROOT / "internal/reviewer/PROCEDURE.md").read_text(encoding="utf-8")
        cls.repo_context = (PLUGIN_ROOT / "internal/repo-context/PROCEDURE.md").read_text(
            encoding="utf-8"
        )
        cls.requirements_source = (
            PLUGIN_ROOT / "internal/requirements-source/PROCEDURE.md"
        ).read_text(encoding="utf-8")
        cls.jira = (PLUGIN_ROOT / "internal/jira/PROCEDURE.md").read_text(encoding="utf-8")
        cls.using_superpowers = (
            PLUGIN_ROOT / "internal/using-superpowers/PROCEDURE.md"
        ).read_text(encoding="utf-8")
        cls.git_commit = (PLUGIN_ROOT / "internal/git-commit/PROCEDURE.md").read_text(encoding="utf-8")
        cls.gitlab_mr = (PLUGIN_ROOT / "internal/gitlab-mr/PROCEDURE.md").read_text(encoding="utf-8")
        cls.mr_description = (
            PLUGIN_ROOT / "internal/gitlab-mr/references/mr-description.md"
        ).read_text(encoding="utf-8")
        cls.executing = (PLUGIN_ROOT / "internal/executing-plans/PROCEDURE.md").read_text(
            encoding="utf-8"
        )
        cls.finishing = (
            PLUGIN_ROOT / "internal/finishing-a-development-branch/PROCEDURE.md"
        ).read_text(encoding="utf-8")
        cls.writing_plans = (PLUGIN_ROOT / "internal/writing-plans/PROCEDURE.md").read_text(
            encoding="utf-8"
        )
        cls.artifacts = (
            PLUGIN_ROOT / "internal/gitlab-mr/references/artifacts.md"
        ).read_text(encoding="utf-8")
        cls.tdd = (
            PLUGIN_ROOT / "internal/test-driven-development/PROCEDURE.md"
        ).read_text(encoding="utf-8")
        cls.debugging = (
            PLUGIN_ROOT / "internal/systematic-debugging/PROCEDURE.md"
        ).read_text(encoding="utf-8")
        cls.brainstorming = (
            PLUGIN_ROOT / "internal/brainstorming/PROCEDURE.md"
        ).read_text(encoding="utf-8")
        cls.grill = (
            PLUGIN_ROOT / "internal/grill-with-docs/PROCEDURE.md"
        ).read_text(encoding="utf-8")
        cls.worktrees = (
            PLUGIN_ROOT / "internal/using-git-worktrees/PROCEDURE.md"
        ).read_text(encoding="utf-8")

    def test_public_review_routes_all_phases_without_mutation(self):
        for phase in ("Specification", "Plan", "Candidate"):
            self.assertIn(phase, self.review)
        self.assertIn("five public entrypoints", self.review)
        self.assertIn("Internal procedures are implementation resources", self.review)
        self.assertIn("review never fixes, commits, comments, approves, pushes, deploys, or merges", self.review)

    def test_clear_current_requirement_runs_without_sha_admission_lock(self):
        normalized = " ".join((self.l3 + self.requirements_source).split())
        self.assertIn("A clear current requirement is sufficient admission", normalized)
        self.assertIn("Formatting-only Jira edits never block", normalized)
        self.assertIn("material but clear change", normalized)
        self.assertIn("fresh specification and plan review", normalized)
        self.assertIn("Only a vague, contradictory, or decision-incomplete requirement blocks", normalized)
        self.assertNotIn("spec_attestation.py", self.l3)
        self.assertNotIn("spec_admission_gate_sha256", self.l3)
        self.assertNotIn("spec_gate_sha256", self.l3)
        self.assertIn("candidate commit SHA", self.l3)

    def test_jira_is_optional_and_local_markdown_is_first_class(self):
        combined = "\n".join((
            self.l3, self.specify, self.requirements_source, self.spec_personas,
            self.plan_personas, self.review_manifest, self.writing_plans,
            self.verification, self.git_commit, self.gitlab_mr,
        ))
        self.assertIn("Jira mode", self.requirements_source)
        self.assertIn("Local Markdown mode", self.requirements_source)
        self.assertIn(
            "must not ask the user to create a Jira ticket",
            " ".join(self.requirements_source.split()),
        )
        self.assertIn("docs/requirements/", combined)
        self.assertIn("do not append\n   self-referential digests", self.requirements_source)
        self.assertIn("current_requirement", combined)
        self.assertIn("work_item", combined)
        self.assertIn("--group core,gitlab", self.l3)
        self.assertIn("add `jira` only in Jira mode", self.l3)
        self.assertNotIn("A Jira ticket is required", combined)
        self.assertNotIn("take one Jira ticket to a draft merge request", self.l3)

    def test_human_requirement_uses_only_the_lean_section_contract(self):
        template = self.specify.split("```md", 1)[1].split("```", 1)[0]
        headings = [line.strip() for line in template.splitlines() if line.startswith("## ")]
        self.assertEqual(
            headings,
            [
                "## Problem / Context",
                "## Definitions",
                "## Objective",
                "## Acceptance Criteria",
                "## Out of Scope",
                "## Technical Notes",
            ],
        )
        self.assertNotIn("## User Story", template)
        for marker in ("**<Code or term>**:", "- AC-01 (<Short title>): Given"):
            self.assertIn(marker, template)
        self.assertNotIn("### AC-01", template)
        for legacy_heading in (
            "Starting Points & Scope",
            "Behavioral Specification & Edge Cases",
            "Contracts & Operational Behaviour",
            "Hard Constraints",
            "Automated Verification & Feedback Loop",
            "Definition of Done",
            "Specification Review Evidence",
            "Specification Review Record",
        ):
            self.assertNotIn(legacy_heading, template)
        self.assertIn("three required\nsections and three optional ones", self.specify)
        self.assertIn("target, not a hard cap", self.specify)
        self.assertIn("review evidence remain outside", self.specify)
        self.assertNotIn(
            "append its portable representation to the description",
            self.spec_personas,
        )

    def test_l3_reads_jira_comments_but_never_writes_them(self):
        combined = "\n".join((
            self.l3,
            self.specify,
            self.review,
            self.reviewer,
            self.requirements_source,
            self.spec_personas,
            self.review_manifest,
            self.jira,
            self.executing,
            self.finishing,
            self.using_superpowers,
        ))
        for stale in (
            "comment on the ticket",
            "conditional Jira evidence comment",
            "conditional Jira evidence comments",
            "jira-comment-or-chat-turn",
            "Add a comment",
            "Delete a comment",
            "post one\n  compact Jira comment",
        ):
            self.assertNotIn(stale, combined)
        self.assertIn("Jira comments are read-only requirement evidence", combined)
        self.assertIn("Never create, edit, or delete a Jira comment", combined)
        self.assertIn("approving chat-turn/body digest", self.spec_personas)

    def test_jira_runs_use_a_dedicated_worktree_for_concurrency(self):
        normalized_l3 = " ".join(self.l3.split())
        normalized_worktrees = " ".join(self.worktrees.split())
        self.assertIn(
            "[`using-git-worktrees`](../../internal/using-git-worktrees/PROCEDURE.md)",
            self.l3,
        )
        self.assertIn("Jira mode always uses a dedicated Git worktree", normalized_l3)
        self.assertIn("one ticket cannot share writable branch state with another", normalized_l3)
        self.assertIn("unique run-owned child", normalized_worktrees)
        self.assertIn(
            "Jira-mode L3 must never fall back to the current checkout",
            normalized_worktrees,
        )
        self.assertIn("multiple Jira tickets", normalized_worktrees)

    def test_l3_never_repairs_missing_business_decisions(self):
        self.assertIn("Never repair or infer business behavior", self.l3)
        self.assertIn("authorization, domain invariants", self.l3)
        self.assertIn("when applicable", self.l3)
        self.assertIn("spec-gap", self.l3)

    def test_l3_source_refresh_is_semantic_and_read_only(self):
        stage = self.l3.split("## Stage 2 — Fresh specification clarity review", 1)[1].split(
            "## Stage 3", 1
        )[0]
        self.assertIn("Do not mutate the selected source", stage)
        self.assertIn("not admission locks", " ".join(stage.split()))
        self.assertIn("formatting-only", stage.lower())
        self.assertIn("material but clear", stage)
        self.assertNotIn("--expect-spec-sha", stage)
        self.assertNotIn("frozen specification", stage)

    def test_manifest_records_fresh_reviews_without_requirement_admission_gate(self):
        self.assertIn("current_requirement", self.review_manifest)
        self.assertIn("clarity_status: PASS", self.review_manifest)
        self.assertIn("audit-only", self.review_manifest)
        self.assertNotIn("human-approved-or-l3-validated", self.review_manifest)
        self.assertNotIn("l3-spec-admission-v3-or-null", self.review_manifest)

    def test_requirement_and_plan_hashes_are_not_design_locks(self):
        combined = "\n".join((
            self.l3,
            self.specify,
            self.review,
            self.reviewer,
            self.writing_plans,
            self.plan_personas,
            self.candidate_envelope,
            self.review_manifest,
        ))
        for stale_gate in (
            "spec_gate_sha256",
            "specification_admission_gate_sha256",
            "l3_spec_validation_gate_sha256",
            "plan_gate_sha256",
            "frozen specification",
            "frozen requirement",
            "Bind the complete immutable input and required contract bundle",
            "draft-phase identity and two distinct persona-bound review-input digests",
        ):
            self.assertNotIn(stale_gate, combined)
        normalized = " ".join(combined.split())
        self.assertIn("Formatting-only changes do not invalidate review", normalized)
        self.assertIn("Material plan changes receive fresh reviews", normalized)
        self.assertIn("Only the final candidate commit is identity-pinned", normalized)

    def test_personas_are_small_generalist_cohorts_with_dynamic_efficient_routes(self):
        expected = {
            "Specification": {"requirements-testability", "integration-operability"},
            "Plan": {"architecture-simplicity", "failure-security-rollback"},
            "Candidate": {"requirements-code-quality", "security-reliability"},
        }
        actual = {phase: [] for phase in expected}
        routes = {}
        for line in self.persona_catalog.splitlines():
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) == 5 and cells[0] in actual:
                persona_id = cells[1].strip("`")
                actual[cells[0]].append(persona_id)
                routes[persona_id] = {"capability": cells[3], "selection": cells[4]}
        self.assertEqual({phase: set(ids) for phase, ids in actual.items()}, expected)
        self.assertTrue(all(len(ids) == 2 for ids in actual.values()))
        self.assertIn("hard maximum is four", self.persona_catalog)
        self.assertIn("There is no\nminimum or quota", self.persona_catalog)
        self.assertEqual(routes["requirements-testability"]["capability"], "lightweight")
        for persona_id, route in routes.items():
            if persona_id != "requirements-testability":
                self.assertEqual(route["capability"], "balanced")
            self.assertIn("supported", route["selection"])
            self.assertIn("non-maximum if configurable", route["selection"])
        self.assertIn("current host's available model metadata", self.persona_catalog)
        self.assertIn("Claude/GPT", self.persona_catalog)
        self.assertIn("closest supported efficient class", self.persona_catalog)
        self.assertIn("cost class is unknown", self.persona_catalog)
        self.assertIn("never invent pricing", " ".join(self.persona_catalog.split()))
        self.assertIn("Never request `xhigh`, `max`, or `ultra`", " ".join(self.persona_catalog.split()))
        self.assertIn("when the host exposes that control", self.persona_catalog)
        self.assertIn("leave it unset", self.persona_catalog)
        self.assertIn("documented/default route is not maximum", " ".join(self.persona_catalog.split()))
        self.assertIn("absent effort control is not", self.persona_catalog)
        self.assertIn("documented current-host", self.persona_catalog)
        self.assertIn("leave it unset", self.reviewer)
        normalized_catalog = " ".join(self.persona_catalog.split())
        self.assertIn(
            "Requested route and actual runtime model/usage remain separate best-effort audit data",
            normalized_catalog,
        )
        # Catalog membership is not a mandatory invocation quota. Low-risk work
        # uses one independent reviewer in each phase, rather than every catalog persona.
        self.assertIn("low-risk work uses an independent Requirements &", self.spec_personas)
        self.assertIn("low-risk", self.plan_personas)
        self.assertIn("one independent requirements/code-quality reviewer", self.l3)
        self.assertNotIn("three draft reviews", self.l3)
        for persona_id in expected["Specification"]:
            self.assertEqual(self.spec_personas.count(f"`{persona_id}`"), 1)
        for persona_id in expected["Plan"]:
            self.assertEqual(self.plan_personas.count(f"`{persona_id}`"), 1)

    def test_manifest_keeps_reproducible_review_artifacts(self):
        for field in (
            "contract_bundle_file", "contract_bundle_sha256", "phase_input_sha256", "review_input_file",
            "review_input_sha256", "response_file", "response_sha256", "adjudication_file",
            "adjudication_sha256", "echoed_identities_match", "findings", "unreviewed_areas",
            "review_cohort_sha256", "candidate_gate_sha256",
        ):
            self.assertIn(field, self.review_manifest)
        self.assertEqual(self.review_manifest.count("persona_id: requirements-testability"), 1)
        self.assertEqual(self.review_manifest.count("persona_id: integration-operability"), 1)
        validation = self.review_manifest.split("current_specification_review:", 1)[1].split("plan_review:", 1)[0]
        for path in ("PROCEDURE.md", "references/persona-catalog.md", "references/specification-personas.md"):
            self.assertIn(f"{{path: {path}, sha256:", validation)
        self.assertIn("contract_bundle_file: spec-contract-bundle.json", validation)
        candidate = self.review_manifest.split("candidate:", 1)[1].split("verification:", 1)[0]
        self.assertEqual(candidate.count("manifest_file:"), 2)
        for path in (
            "PROCEDURE.md", "references/persona-catalog.md", "references/candidate-review-envelope.md",
            "references/requirements-code-quality-reviewer.md",
            "references/security-reliability-reviewer.md", "references/findings-and-adjudication.md",
        ):
            self.assertIn(f"{{path: {path}, sha256:", candidate)

    def test_core_workflow_metadata_is_general_engineering(self):
        combined = "\n".join((
            self.l3, self.reviewer, self.repo_context, self.using_superpowers, self.git_commit,
            self.gitlab_mr, self.mr_description, self.executing, self.finishing,
            self.writing_plans, self.verification, self.tdd, self.debugging,
            self.brainstorming, self.grill,
        )).lower()
        for stale in (
            "payment review persona", "using payment-team skills", "applicable payment workflow",
            "never guess a payment rule", "starting work in dakota payment or dbmy payment",
            "origin/master", "## payment changes", "for payment behavior",
            "business, payment, security", "gx-regional%2fdakota%2fpayment",
            "## payment invariants", "for payment failures, trace",
            "minimize restricted payment data", "keep payment request",
        ):
            self.assertNotIn(stale, combined)
        self.assertIn("resolve the target generically", self.repo_context.lower())
        self.assertIn("conditional compatibility reference", self.repo_context.lower())
        self.assertIn("engineering review roles", self.reviewer.lower())
        self.assertIn("refs/remotes/origin/head", self.git_commit.lower())
        self.assertIn("validated target remote", self.gitlab_mr.lower())
        self.assertIn("money-handling changes", combined)
        self.assertIn("## domain invariants", self.tdd.lower())
        self.assertIn("authoritative entity", self.debugging.lower())
        self.assertIn("authority and data ownership across domain entities", self.brainstorming.lower())
        self.assertIn("keep each domain entity", self.grill.lower())

    def test_payment_artifact_helpers_are_conditional_compatibility_only(self):
        gitlab_mr = " ".join(self.gitlab_mr.split())
        artifacts = " ".join(self.artifacts.split())
        self.assertIn("conditional compatibility tools", gitlab_mr)
        self.assertIn("supported Dakota Payment/SHIPRM services only", gitlab_mr)
        self.assertIn("Never fall back to the payment registry", gitlab_mr)
        self.assertIn("Conditional Dakota Payment / SHIPRM Artifact Compatibility", artifacts)
        self.assertIn("Do not use these registry mappings or scripts for unrelated repositories", artifacts)
        self.assertIn("follow the target repository's documented artifact or CI lookup", artifacts)
        self.assertIn("never substitute the payment registry as a fallback", artifacts)

    def test_internal_l3_evidence_is_never_published_in_mr_descriptions(self):
        self.assertNotIn("## L3 review evidence", self.mr_description)
        self.assertNotIn("## L3 Review Evidence", self.gitlab_mr)
        self.assertIn("Keep internal L3 evidence out", self.mr_description)
        self.assertIn("machine-local review manifest", self.mr_description)
        self.assertIn("remove the entire legacy L3 review-evidence", self.mr_description)
        self.assertIn("Never publish", self.gitlab_mr)
        self.assertNotIn("MR description read-back", self.gitlab_mr)
        self.assertNotIn("MR evidence read-back", self.verification)
        self.assertIn("GitLab API", self.gitlab_mr)

    def test_specify_can_resume_a_detailed_but_unattested_ticket(self):
        self.assertIn("Resume and finalize an existing specification", self.specify)
        self.assertIn("Preserve settled behavior", self.specify)
        self.assertIn("must not redraft settled requirements", self.specify)


class FocusedReviewContractTests(TestCase):
    def text(self, relative):
        return " ".join((PLUGIN_ROOT / relative).read_text(encoding="utf-8").split())

    def test_run_and_candidate_review_require_concrete_reuse_evidence(self):
        run = self.text("skills/run/SKILL.md")
        quality = self.text("internal/reviewer/references/requirements-code-quality-reviewer.md")
        self.assertIn("inspect the existing utility and actual callers", run)
        self.assertIn("not a new checklist or approval step", run)
        self.assertIn("cite the existing utility/caller", quality)
        self.assertIn("Preserve justified custom behaviour", quality)

    def test_context_is_scoped_and_initial_judgment_is_independent(self):
        context = self.text("internal/repo-context/PROCEDURE.md")
        reviewer = self.text("internal/reviewer/PROCEDURE.md")
        self.assertIn("historical feature plans are discovery aids, not authority", context)
        self.assertIn("stale or absent optional KB is not a blocker", context)
        self.assertIn("preserving the complete phase input", reviewer)
        self.assertIn("do not supply another reviewer's verdict", reviewer)
        self.assertIn("Preserve each independent initial response", reviewer)

    def test_findings_distinguish_evidence_scope_and_read_only_authority(self):
        findings = self.text("internal/reviewer/references/findings-and-adjudication.md")
        review = self.text("skills/review/SKILL.md")
        for field in ("Trigger/input:", "Expected versus actual behaviour:",
                      "introduced defect | unnecessary code | pre-existing issue | requirement change"):
            self.assertIn(field, findings)
        self.assertIn("New requirements are not implementation defects", findings)
        self.assertIn("concrete code/control-flow evidence may suffice", findings)
        self.assertIn("Agreement", self.text("internal/reviewer/references/candidate-review-dialogue.md"))
        self.assertIn("concrete counterexample", findings)
        self.assertIn("read-only Review proposes that check", findings)
        self.assertIn("without executing reviewed code or expanding the task", review)

    def test_follow_up_reviews_check_regressions_without_reopening_settled_decisions(self):
        dialogue = self.text("internal/reviewer/references/candidate-review-dialogue.md")
        self.assertIn("inspects the full current diff and affected callers", dialogue)
        self.assertIn("Recheck for regressions caused by the repair", dialogue)
        self.assertIn("Preserve unaffected settled decisions", dialogue)
        self.assertIn("without contradictory new evidence", dialogue)
        self.assertIn("at most three repair cycles", dialogue)


class QuizContractTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.quiz = (PLUGIN_ROOT / "skills/quiz/SKILL.md").read_text(encoding="utf-8")
        report = (PLUGIN_ROOT / "skills/quiz/references/understanding-report.md").read_text()
        generation = (
            PLUGIN_ROOT / "skills/quiz/references/question-generation.md"
        ).read_text(encoding="utf-8")
        cls.normalized = " ".join((cls.quiz + "\n" + report + "\n" + generation).split())

    def test_quiz_is_read_only_and_stays_in_chat(self):
        self.assertIn("five public entrypoints", self.quiz)
        self.assertIn(
            "Quiz never comments, labels, approves, pushes, edits code, changes pipeline state",
            self.normalized,
        )
        self.assertIn("Nothing leaves the chat", self.quiz)
        self.assertIn("read-only inspection only", self.normalized)
        self.assertIn("untrusted input", self.quiz)

    def test_quiz_is_one_mode_for_any_user_and_not_a_gate(self):
        self.assertIn("one mode for everyone", self.normalized)
        self.assertIn("never approval", self.normalized)

    def test_quiz_questions_are_grounded_multiple_choice(self):
        for phrase in (
            "exactly four options (A–D), exactly one correct answer",
            "`file:line` evidence",
            "never asks about behaviour the code does not evidence",
            "Distribute the correct letter across A–D",
            "Wrong answers must be plausible (not trivial)",
            "third_party/sphinx-ci/lib/claude.ts.txt",
            "scripts/quiz_size.py",
            "third_party/sphinx-ci/components/DemoQuiz.tsx.txt",
            "No quiz needed",
            "fail-open",
            "70% passing score",
            "up to 3 attempts in total",
            "it unlocks and blocks nothing",
            "Never go below 3 or above 8",
        ):
            self.assertIn(phrase, self.normalized)
        # quiz_size.py is the single sizing implementation; no hand-ported formula in prose.
        self.assertIn("only sizing implementation", self.quiz)
        for formula_marker in ("const weight", "factor = 0.5", "Math.round(5 * factor)"):
            self.assertNotIn(formula_marker, self.quiz)

    def test_quiz_waits_for_the_human_one_question_at_a_time(self):
        self.assertIn("one question at a time", self.normalized)
        self.assertIn("Never reveal or hint at the answer", self.normalized)
        self.assertIn("The agent never answers its own quiz", self.normalized)
        self.assertIn("including in autopilot or unattended mode", self.normalized)

    def test_quiz_items_resist_cues_and_leakage(self):
        self.assertIn("must not be the noticeably longest", self.normalized)
        self.assertIn("without looking at your key", self.normalized)
        self.assertIn("would answer a question not yet asked", self.normalized)
        self.assertIn("':!go.sum'", self.quiz)

    def test_quiz_questions_cover_named_tiers_and_resist_grep(self):
        self.assertIn("intent (requirements/acceptance-criteria alignment)", self.normalized)
        self.assertIn("blast radius", self.normalized)
        self.assertIn("at least 3 distinct tiers", self.normalized)
        self.assertIn("answerable by a single grep or by reading one line", self.normalized)


class WalkthroughContractTests(TestCase):
    @classmethod
    def setUpClass(cls):
        skill = (PLUGIN_ROOT / "skills/walkthrough/SKILL.md").read_text(encoding="utf-8")
        context = (
            PLUGIN_ROOT / "skills/walkthrough/references/target-context.md"
        ).read_text(encoding="utf-8")
        cls.skill = " ".join(skill.split())
        cls.context = " ".join(context.split())

    def test_walkthrough_is_read_only_and_stays_in_chat(self):
        self.assertIn(
            "Walkthrough is read-only: never edit code, Jira or Confluence, comment, label, "
            "approve, push, merge, deploy or change pipeline state.",
            self.skill,
        )
        self.assertIn("Keep the explanation in chat", self.skill)

    def test_walkthrough_explains_rationale_and_slices(self):
        self.assertIn("Rationale not stated", self.skill)
        self.assertIn("define and use the same", self.skill)
        self.assertIn("optional, unscored prediction question", self.skill)

    def test_walkthrough_cites_the_source_revision(self):
        self.assertIn("Never cite line numbers from a different revision", self.context)

    def test_walkthrough_maps_boundaries_and_pauses_at_checkpoints(self):
        self.assertIn("Close the orientation with a boundary map", self.skill)
        self.assertIn("Never present two layers in one pass", self.skill)
        self.assertIn("stop and offer the reader", self.skill)

    def test_walkthrough_visuals_are_bounded_grounded_and_request_only(self):
        self.assertIn("only when it already exists", self.skill)
        self.assertIn("only when the reader explicitly asks for an artifact", self.skill)
        self.assertIn("omit a visual rather than invent its participants", self.skill)
        diagrams = " ".join(
            (PLUGIN_ROOT / "skills/walkthrough/references/diagrams.md")
            .read_text(encoding="utf-8")
            .split()
        )
        self.assertIn("One diagram per layer, at most 12 nodes", diagrams)
        self.assertIn("omitted, not invented", diagrams)
        self.assertIn("flowchart TD", diagrams)
        self.assertIn("80 columns", diagrams)
        self.assertIn("Never install, download or build a renderer", diagrams)
        self.assertIn("walkthrough-<topic>.html", diagrams)
        self.assertIn("only when the reader explicitly asks", diagrams)


class PluginVersionContractTests(TestCase):
    def test_local_plugin_manifests_are_aligned(self):
        plugin = json.loads((PLUGIN_ROOT / "plugin.json").read_text(encoding="utf-8"))
        codex_plugin = json.loads(
            (PLUGIN_ROOT / ".codex-plugin/plugin.json").read_text(encoding="utf-8")
        )

        self.assertEqual(plugin["name"], "shipmate")
        self.assertEqual(plugin["version"], "4.5.0")
        self.assertEqual(codex_plugin["name"], plugin["name"])
        self.assertEqual(codex_plugin["version"], plugin["version"])
        self.assertEqual(codex_plugin["description"], plugin["description"])
        self.assertEqual(codex_plugin["author"], plugin["author"])
        self.assertEqual(codex_plugin["keywords"], plugin["keywords"])
        manifest_text = json.dumps([plugin, codex_plugin]).lower()
        self.assertNotIn("payment engineering", manifest_text)
        self.assertNotIn('"payments"', manifest_text)
        self.assertIn("engineering", manifest_text)
        self.assertNotIn("jira-to-mr", manifest_text)


class RunObservationContractTests(TestCase):
    def test_all_public_actions_disable_automatic_local_run_records(self):
        workflow = " ".join(
            (PLUGIN_ROOT / "internal/workflow-policy.md").read_text(encoding="utf-8").split()
        )
        self.assertIn("Do not create or update local run JSON/CSV", workflow)
        self.assertNotIn("Capture is on by default", workflow)
        self.assertIn("Langfuse is the source for AI-session metrics", workflow)
        self.assertIn("only when the user explicitly requests local metrics files", workflow)
        self.assertIn("never create a local metrics file as a fallback or invent values", workflow)
        self.assertIn(
            "without creating a local run record or enabling external tracking at intake", workflow
        )
        # The canonical telemetry rules live once in workflow-policy; public skills carry only
        # the pointer, never a copied paragraph.
        pointer = "workflow-policy.md#langfuse-metrics-and-workflow-status"
        for action in ("run", "specify", "review"):
            skill = (PLUGIN_ROOT / f"skills/{action}/SKILL.md").read_text(encoding="utf-8")
            self.assertIn(pointer, skill)
            self.assertNotIn("Local run records are off by default", skill)
            self.assertNotIn("capture-disabled notices in handoffs", skill)
            self.assertNotIn("Capture is on by default", skill)
            self.assertNotIn("Include the local record link", skill)
            self.assertNotIn("start a best-effort local", skill)
        policy = (PLUGIN_ROOT / "internal/run-metrics.md").read_text(encoding="utf-8")
        self.assertIn("Langfuse is the source for AI-session metrics", policy)
        self.assertIn("Do not start or resume collection just because old files exist", policy)
        self.assertIn("Do not estimate missing costs", policy)
        self.assertIn("No local run file is required for publishing", policy)
        self.assertNotIn("run_metrics.py` start", policy)
        self.assertNotIn("Billed and estimated costs", policy)
        self.assertNotIn("--source-kind chat", policy)

    def test_reviewer_observations_are_controller_owned_and_parent_linked(self):
        procedure = (PLUGIN_ROOT / "internal/reviewer/PROCEDURE.md").read_text(encoding="utf-8")
        self.assertIn("workflow_run_id", procedure)
        self.assertIn("reviewer never starts a separate root run", procedure)
        self.assertIn("already child-inclusive parent total", procedure)
