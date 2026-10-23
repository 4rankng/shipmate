"""Schema checks for the private quiz answer key validator."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

from validate_quiz_key import validate


SCRIPT = Path(__file__).parent / "validate_quiz_key.py"


def question(**overrides):
    entry = {"id": 1, "question": "What happens when a report is requested at width 63?",
             "options": ["A) Rejected with a width error", "B) Rendered at 63",
                         "C) Clamped to 64", "D) Rendered with the default 76"],
             "correct": 0, "topic": "Width boundary",
             "explanation": "The guard rejects widths below 64."}
    entry.update(overrides)
    return entry


class ValidateQuizKeyTests(unittest.TestCase):
    def test_accepts_a_wellformed_key(self):
        result = validate({"questions": [question(), question(id=2), question(id=3)]})
        self.assertTrue(result["valid"])
        self.assertEqual(result["count"], 3)
        self.assertEqual(result["errors"], [])

    def test_rejects_counts_outside_the_clamp(self):
        result = validate({"questions": [question()]})
        self.assertFalse(result["valid"])
        self.assertIn("quiz needs 3-8 questions, got 1", result["errors"])

    def test_expected_count_mismatch_is_reported(self):
        result = validate({"questions": [question(), question(id=2), question(id=3)]},
                          expected=5)
        self.assertFalse(result["valid"])
        self.assertIn("planned count was 5, key holds 3", result["errors"])

    def test_rejects_duplicate_ids_and_bad_option_shapes(self):
        result = validate({"questions": [question(), question(id=1, options=["A)", "B)", "C)"]),
                                         question(id=3, correct=4)]})
        self.assertFalse(result["valid"])
        self.assertIn("question ids must be unique positive integers", result["errors"])
        self.assertIn("question 2: exactly four options are required", result["errors"])
        self.assertIn("question 3: correct must be an index 0-3", result["errors"])

    def test_rejects_blank_fields_and_duplicate_options(self):
        result = validate({"questions": [question(topic="  ", id=-2),
                                         question(id=2, options=["A)", "A)", "C)", "D)"]),
                                         question(id=3, explanation="")]})
        self.assertFalse(result["valid"])
        self.assertIn("question 1: id must be a positive integer", result["errors"])
        self.assertIn("question 1: topic must be a nonempty string", result["errors"])
        self.assertIn("question 2: options must be distinct", result["errors"])
        self.assertIn("question 3: explanation must be a nonempty string", result["errors"])

    def test_cli_exits_nonzero_on_an_invalid_key(self):
        run = subprocess.run([sys.executable, str(SCRIPT), "--expected", "5"],
                             input=json.dumps({"questions": [question()]}),
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 1)
        self.assertIn("planned count was 5", run.stdout)

    def test_cli_exits_zero_on_a_valid_key(self):
        payload = json.dumps({"questions": [question(), question(id=2), question(id=3)]})
        run = subprocess.run([sys.executable, str(SCRIPT)], input=payload,
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0)
        self.assertIn('"valid": true', run.stdout)


if __name__ == "__main__":
    unittest.main()
