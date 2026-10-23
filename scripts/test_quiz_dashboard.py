"""Exercise the report CLI with real computed scores, including non-final results."""
import json
import subprocess
import sys
import unicodedata
from pathlib import Path
from unittest import TestCase

SCRIPT = Path(__file__).with_name("quiz_report.py")


def payload(answers=(0, 0, 0, 0, 0, 0, 1, 1), **overrides):
    value = {
        "questions": [{"id": i + 1, "topic": f"Topic {i + 1}", "correct": 0, "answer": answer}
                      for i, answer in enumerate(answers)],
        "report": {"target": "example/project !42 — Retry handling", "source": "a" * 40,
                   "session": "2026-10-22 20:00 +08", "attempt": 1,
                   "walkthrough": "Provided in this chat", "replaced": 1,
                   "revisit": [{"detail": "Check the missing-data branch.",
                                "source": "src/retry.go:42"}],
                   "coverage": "Retries and ownership; documentation not quizzed."},
    }
    value.update(overrides)
    return value


def columns(text):
    return sum(0 if unicodedata.combining(c) else
               2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)


class QuizDashboardTests(TestCase):
    def run_report(self, data, *args):
        return subprocess.run([sys.executable, str(SCRIPT), "--format", "dashboard", *args],
                              input=json.dumps(data), text=True, capture_output=True)

    def test_dashboard_uses_calculated_results_and_real_metadata(self):
        result = self.run_report(payload())
        self.assertEqual(result.returncode, 0, result.stderr)
        text = result.stdout
        for expected in ("SHIPMATE", "QUIZ REPORT", "75%", "6/8", "Developing", "Quiz passed!",
                         "6 correct", "2 wrong", "0 skipped", "0 unanswered",
                         "NEEDS REVIEW (2)", "DEMONSTRATED (6)", "src/retry.go:42",
                         "Attempt 1/3", "2 remaining", "1 question replaced", "a" * 40):
            self.assertIn(expected, text)
        self.assertNotIn('"answer"', text)
        self.assertNotIn('"correct":', text)
        self.assertNotIn("\x1b", text)
        self.assertTrue(text.splitlines()[1].endswith("COMPLETED │"))
        self.assertLessEqual(len(text.splitlines()), 38)

    def test_low_score_and_nonzero_skips_are_not_hardcoded(self):
        result = self.run_report(payload((0, 1, "skip", "skip")))
        self.assertEqual(result.returncode, 0, result.stderr)
        for expected in ("25%", "1/4", "Needs review", "Not yet...", "2 skipped"):
            self.assertIn(expected, result.stdout)
        self.assertNotIn("Quiz passed!", result.stdout)

    def test_incomplete_result_has_no_pass_or_final_level(self):
        result = self.run_report(payload((0, 1, None, None)))
        self.assertEqual(result.returncode, 0, result.stderr)
        for expected in ("INCOMPLETE", "Provisional", "1/4", "2 unanswered"):
            self.assertIn(expected, result.stdout)
        for absent in ("Quiz passed!", "Not yet...", "Developing", "Strong", "Needs review"):
            self.assertNotIn(absent, result.stdout)

    def test_unassessed_and_stale_results_never_show_score_or_demonstrated_topics(self):
        cases = [payload(freshness="stale"), payload(integrity="compromised"),
                 payload((None, None, None)), payload(("skip",) * 3), payload(())]
        for data in cases:
            with self.subTest(data=data):
                result = self.run_report(data)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("No current score", result.stdout)
                for absent in ("75%", "Quiz passed!", "Not yet...", "DEMONSTRATED", "Developing"):
                    self.assertNotIn(absent, result.stdout)

    def test_unverified_source_is_qualified_in_the_dashboard(self):
        result = self.run_report(payload(freshness="unverified"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("unverified", result.stdout)
        self.assertIn("earlier snapshot only", result.stdout)

    def test_all_topic_outcomes_are_visible(self):
        data = payload((0, "skip", 0, None, 1))
        for i, topic in enumerate(("Mixed", "Mixed", "Good", "Untested", "Missed")):
            data["questions"][i]["topic"] = topic
        result = self.run_report(data)
        self.assertEqual(result.returncode, 0, result.stderr)
        for expected in ("PARTLY ASSESSED (1)", "NOT ASSESSED (1)", "Mixed", "Untested", "Missed"):
            self.assertIn(expected, result.stdout)

    def test_wrapping_handles_long_identifiers_cjk_and_combining_text(self):
        for width in (64, 76, 96):
            data = payload()
            data["report"]["target"] = "界面 e\u0301 " + "x" * 160
            data["report"]["source"] = "x/" * 90 + ":123"
            data["questions"][0]["topic"] = "客户身份" * 25
            result = self.run_report(data, "--width", str(width))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(all(columns(line) == width for line in result.stdout.splitlines()))
            self.assertIn("e\u0301", result.stdout)

    def test_unknown_context_does_not_invent_a_person_time_or_retry_allowance(self):
        data = payload()
        data.pop("report")
        result = self.run_report(data)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Chat participant", result.stdout)
        self.assertIn("Attempt not known", result.stdout)
        self.assertIn("Not supplied", result.stdout)
        self.assertNotIn("remaining", result.stdout)
        self.assertNotIn("Not supplied · current", result.stdout)

    def test_default_cli_keeps_the_existing_json_contract(self):
        data = payload((0, 0, 1))
        data.pop("report")
        result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps(data),
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["percent"], 67)
        self.assertEqual(report["status"], "Completed")
        self.assertNotIn("questions", report)
        self.assertNotIn("report", report)

    def test_terminal_controls_cannot_change_the_layout(self):
        data = payload()
        data["report"]["participant"] = "A\x1b[31mB\r\nC\tD\x00"
        data["questions"][0]["topic"] = "Topic\x1b]0;window title\x07"
        result = self.run_report(data)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("AB C D", result.stdout)
        self.assertNotIn("\x1b", result.stdout)
        self.assertNotIn("\x00", result.stdout)
        self.assertTrue(all(columns(line) == 76 for line in result.stdout.splitlines()))

    def test_context_cannot_override_scoring_or_echo_private_fields(self):
        for extra in ({"score": 100}, {"questions": "PRIVATE"}, {"attempt": True},
                      {"attempt": 4}, {"replaced": -1}, {"revisit": "PRIVATE"},
                      {"walkthrough": "invented"}, {"participant": ["PRIVATE"]}):
            data = payload()
            data["report"].update(extra)
            result = self.run_report(data)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertNotIn("PRIVATE", result.stderr)

    def test_invalid_width_and_invalid_scoring_input_fail_closed(self):
        for width in ("20", "200", "invalid"):
            result = self.run_report(payload(), "--width", width)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
        data = payload()
        data["questions"][0]["correct"] = "PRIVATE"
        result = self.run_report(data)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertNotIn("PRIVATE", result.stderr)
