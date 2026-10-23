import json
import subprocess
import sys
from pathlib import Path
from unittest import TestCase

SCRIPT = Path(__file__).with_name("validate_mr_description.py")
GOOD = "## Description of Change\n\nPreserve the stored event ID when retrying publication.\n"


class MRDescriptionTests(TestCase):
    def run_check(self, text, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], input=text,
                              text=True, capture_output=True)

    def test_concise_description_and_real_diagram_shape_pass(self):
        diagram = "\n```mermaid\nsequenceDiagram\n    A->>B: Retry stored event\n```\n"
        for text in (GOOD, GOOD + diagram):
            result = self.run_check(text)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(result.stdout)["valid"])

    def test_reports_and_checklists_fail(self):
        for extra in ("## Checklist\n- [ ] Approved\n", "### Test Evidence\nTC1: works\n",
                      "## Risks and limitations\nNone\n", "## Validation performed\nPassed\n",
                      "- [x] Compatible\n", "TC2: retry succeeds\n", "- go test -race ./...\n"):
            with self.subTest(extra=extra):
                result = self.run_check(GOOD + extra)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertFalse(json.loads(result.stdout)["valid"])

    def test_required_repository_fields_have_narrow_explicit_exceptions(self):
        text = GOOD + "\n## Test Evidence\n- [x] Required control\n\n## Checklist\n- [x] Optional\n"
        result = self.run_check(text, "--required-heading", "Test Evidence",
                                "--exception-reason", "Repository mandates this field")
        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertTrue(report["exception_used"])
        self.assertEqual(report["errors"], [{"line": 8, "code": "report-section"},
                                           {"line": 9, "code": "checklist-item"}])
        approved = self.run_check(GOOD + "\n## Test Evidence\n- [x] Required control\n",
                                  "--required-heading", "Test Evidence",
                                  "--exception-reason", "Explicit user requirement")
        self.assertEqual(approved.returncode, 0, approved.stdout)

    def test_exception_requires_reason_and_cannot_allow_everything(self):
        for args in (("--required-heading", "Checklist"),
                     ("--required-heading", "*", "--exception-reason", "Required")):
            result = self.run_check(GOOD, *args)
            self.assertEqual(result.returncode, 2)

    def test_behavior_prose_is_not_rejected_for_using_testing_words(self):
        text = GOOD + "\nFix the test runner's rollback behavior. TODO is a literal task status.\n"
        self.assertEqual(self.run_check(text).returncode, 0)

    def test_fenced_code_is_not_confused_with_report_sections(self):
        text = GOOD + "\n````md\n## Checklist\n- [ ] literal fixture\n```\nTC1: fixture\n````\n"
        self.assertEqual(self.run_check(text).returncode, 0)
        self.assertEqual(self.run_check(GOOD + "\n```mermaid\nsequenceDiagram\n").returncode, 1)

    def test_normalized_headings_and_privacy(self):
        result = self.run_check(GOOD + "\n### **TEST   EVIDENCE**\nPRIVATE_SECRET\n")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("PRIVATE_SECRET", result.stdout + result.stderr)
        self.assertEqual(self.run_check("").returncode, 1)
