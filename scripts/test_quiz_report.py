"""Scoring and completeness checks for the screenshot report, independent of prose."""
import io
import json
from contextlib import redirect_stdout
from unittest import TestCase
from unittest.mock import patch

import quiz_report


def questions(answers):
    return [{"id": i + 1, "topic": "Ownership" if i < 2 else "Recovery",
             "correct": 0, "answer": answer} for i, answer in enumerate(answers)]


class QuizReportTests(TestCase):
    def test_completed_report_preserves_skips_in_denominator(self):
        result = quiz_report.summarize(questions([0, 0, 1, "skip"]))
        self.assertEqual(result["status"], "Completed")
        self.assertEqual(result["counts"], {"correct": 2, "wrong": 1, "skipped": 1, "unanswered": 0})
        self.assertEqual(result["percent"], 50)
        self.assertEqual(result["level"], "Needs review")
        self.assertFalse(result["passed"])
        self.assertEqual(result["topics"], {"Ownership": "Demonstrated", "Recovery": "Needs review"})

    def test_incomplete_quiz_never_has_final_level_or_pass(self):
        result = quiz_report.summarize(questions([0, 0, None, None]))
        self.assertEqual(result["status"], "Incomplete")
        self.assertEqual(result["percent"], 50)
        self.assertIsNone(result["level"])
        self.assertIsNone(result["passed"])

    def test_no_answers_is_not_assessed(self):
        result = quiz_report.summarize(questions([None, None, None]))
        self.assertEqual(result["status"], "Not assessed")
        self.assertIsNone(result["percent"])

    def test_insufficient_settled_questions_cannot_produce_scored_quiz(self):
        result = quiz_report.summarize(questions([0, 0]))
        self.assertEqual(result["status"], "Not assessed")
        self.assertIsNone(result["level"])
        self.assertIsNone(result["percent"])

    def test_stale_source_suppresses_final_score_and_topic_claims(self):
        result = quiz_report.summarize(questions([0, 0, 0]), freshness="stale")
        self.assertEqual(result["status"], "Stale")
        self.assertIsNone(result["percent"])
        self.assertIsNone(result["level"])
        self.assertIsNone(result["passed"])
        self.assertTrue(all(v == "Not assessed" for v in result["topics"].values()))

    def test_mixed_stale_answers_preserve_counts_without_current_score(self):
        result = quiz_report.summarize(questions([0, 1, "skip", 0]), freshness="stale")
        self.assertEqual(result["counts"], {"correct": 2, "wrong": 1, "skipped": 1, "unanswered": 0})
        self.assertIsNone(result["percent"])
        self.assertIsNone(result["level"])
        self.assertTrue(all(v == "Not assessed" for v in result["topics"].values()))

    def test_recommended_answer_cannot_produce_understanding_score(self):
        result = quiz_report.summarize(questions([0, 0, 0]), integrity="compromised")
        self.assertEqual(result["status"], "Not assessed")
        self.assertEqual(result["counts"]["correct"], 3)
        self.assertIsNone(result["percent"])
        self.assertIsNone(result["level"])
        self.assertIsNone(result["passed"])
        self.assertTrue(all(v == "Not assessed" for v in result["topics"].values()))

    def test_unverified_freshness_is_explicit(self):
        result = quiz_report.summarize(questions([0, 0, 0]), freshness="unverified")
        self.assertEqual(result["freshness"], "unverified")
        self.assertEqual(result["level"], "Strong")

    def test_levels_and_js_rounding(self):
        for answers, percent, level, passed in [
            ([0, 0, 0], 100, "Strong", True),
            ([0, 0, 0, 1], 75, "Developing", True),
            ([0, 0, 1], 67, "Needs review", False),
            ([0] * 7 + [1], 88, "Developing", True),
        ]:
            with self.subTest(answers=answers):
                result = quiz_report.summarize(questions(answers))
                self.assertEqual((result["percent"], result["level"], result["passed"]),
                                 (percent, level, passed))

    def test_topic_with_some_correct_and_skips_is_only_partly_assessed(self):
        result = quiz_report.summarize(questions([0, "skip", 0]))
        self.assertEqual(result["topics"]["Ownership"], "Partly assessed")

    def test_all_skipped_has_no_demonstrated_level(self):
        result = quiz_report.summarize(questions(["skip"] * 3))
        self.assertEqual(result["status"], "Not assessed")
        self.assertIsNone(result["percent"])
        self.assertIsNone(result["passed"])

    def test_invalid_keys_answers_and_duplicate_ids_rejected(self):
        cases = [questions([True, 0, 0]), questions([4, 0, 0]), questions(["A", 0, 0]),
                 questions([0] * 9), [{**q, "correct": False} for q in questions([0] * 3)],
                 [questions([0])[0]] * 3,
                 [{**q, "topic": ""} for q in questions([0] * 3)]]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                quiz_report.summarize(case)
        with self.assertRaises(ValueError):
            quiz_report.summarize(questions([0] * 3), freshness="guess")

    def test_cli_preserves_compromised_integrity(self):
        stdout = io.StringIO()
        payload = {"questions": questions([0, 0, 0]), "integrity": "compromised"}
        with patch("sys.stdin", io.StringIO(json.dumps(payload))), redirect_stdout(stdout):
            self.assertEqual(quiz_report.main([]), 0)
        output = json.loads(stdout.getvalue())
        self.assertEqual(output["status"], "Not assessed")
        self.assertIsNone(output["percent"])
        self.assertIsNone(output["level"])

    def test_output_never_contains_answer_key(self):
        stdout = io.StringIO()
        with patch("sys.stdin", io.StringIO(json.dumps({"questions": questions([0, 1, "skip"])}))), redirect_stdout(stdout):
            self.assertEqual(quiz_report.main([]), 0)
        output = json.loads(stdout.getvalue())
        self.assertNotIn("questions", output)
        self.assertNotIn('"answer":', stdout.getvalue())
        self.assertEqual(output["counts"]["correct"], 1)
