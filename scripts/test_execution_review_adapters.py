"""Instruction/packaging guards; these do not claim to execute model behaviour trials."""
import json
from pathlib import Path
from unittest import TestCase

ROOT = Path(__file__).resolve().parents[1]


class ExecutionReviewAdapterTests(TestCase):
    def read(self, path):
        return " ".join((ROOT / path).read_text().split())

    def test_small_work_does_not_gain_per_task_agents(self):
        text = self.read("internal/executing-plans/PROCEDURE.md")
        for rule in ("Small changes stay in one implementation context", "explicitly authorized",
                     "separate writable worktrees", "Do not add per-task review agents by default"):
            self.assertIn(rule, text)

    def test_parallel_handoff_and_failed_integration_hold_dependents(self):
        text = self.read("internal/executing-plans/PROCEDURE.md")
        for rule in ("prerequisites, writable paths and shared contracts", "Serialize those changes",
                     "base and result commit", "tests actually run", "only then release dependent work",
                     "If integration fails, pause dependent slices", "preserve their worktrees"):
            self.assertIn(rule, text)
        self.assertIn("complete current candidate", text)

    def test_review_preparation_does_not_import_upstream_authority(self):
        text = self.read("internal/code-review/PROCEDURE.md")
        for rule in ("complete integrated diff", "affected callers", "known limitations",
                     "not permission to invent a requirement", "not two additional agents per task",
                     "Reviewers do not create snapshots"):
            self.assertIn(rule, text)
        self.assertIn("requirements-first", text)

    def test_feedback_keeps_evidence_and_scoped_clarification(self):
        text = self.read("internal/reviewer/references/findings-and-adjudication.md")
        for rule in ("`ACCEPT`", "`REJECT`", "`UNVERIFIED`", "only the ambiguous dependent group",
                     "never authorizes remote comments or new scope", "Never relabel an old PASS"):
            self.assertIn(rule, text)

    def test_delivery_still_requires_current_ci_and_human_merge(self):
        run = self.read("skills/run/SKILL.md")
        self.assertIn("Unavailable required CI remains `verification-pending`", run)
        self.assertIn("Never merge, approve or deploy", run)
        self.assertIn("Revise the plan only if the approach changed", run)

    def test_selected_vendor_sources_and_template_are_registered(self):
        manifest = json.loads((ROOT / "third_party/sources.json").read_text())
        source = next(s for s in manifest["sources"] if s["name"] == "obra-superpowers")
        paths = {f["upstream_path"] for f in source["files"]}
        for path in ("skills/requesting-code-review/SKILL.md", "skills/requesting-code-review/code-reviewer.md",
                     "skills/receiving-code-review/SKILL.md", "skills/dispatching-parallel-agents/SKILL.md"):
            self.assertIn(path, paths)
