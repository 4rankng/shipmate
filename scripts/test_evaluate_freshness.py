import json
import unittest
from pathlib import Path
from evaluate_freshness import score


class FreshnessScorerTests(unittest.TestCase):
    def test_missing_answers_are_failures(self):
        result = score({"a": "continue", "b": "block"}, [{"id": "a", "action": "continue"}])
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["correct"], 1)
        self.assertEqual(result["mismatches"], [{"id": "b", "expected": "block", "actual": None}])

    def test_wrong_answers_report_expected_and_actual(self):
        result = score({"a": "block"}, [{"id": "a", "action": "continue"}])
        self.assertEqual(result["correct"], 0)
        self.assertEqual(result["mismatches"][0]["actual"], "continue")

    def test_duplicates_unknown_cases_and_invalid_actions_fail(self):
        for answers in (
            [{"id": "a", "action": "block"}] * 2,
            [{"id": "b", "action": "block"}],
            [{"id": "a", "action": "PASS"}],
        ):
            with self.subTest(answers=answers), self.assertRaises(ValueError):
                score({"a": "block"}, answers)

    def test_all_bundled_cases_have_one_valid_expected_action(self):
        root = Path(__file__).parent / "evals"
        cases = json.loads((root / "freshness-cases.json").read_text())
        expected = json.loads((root / "freshness-expected.json").read_text())
        self.assertEqual(len(cases), len({case["id"] for case in cases}))
        self.assertEqual({case["id"] for case in cases}, set(expected))
        self.assertLessEqual(set(expected.values()), {"continue", "refresh", "block"})
