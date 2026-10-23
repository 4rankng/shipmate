import json
import unittest
from pathlib import Path

from evaluate_workflow import score


def decision(action="continue", risk="low", cohort="one_combined"):
    return {
        "action": action,
        "risk": risk,
        "cohort": cohort,
    }


def response(case_id="a", **overrides):
    rationale = overrides.pop("rationale", "Policy-backed rationale.")
    return {"id": case_id, **decision(**overrides), "rationale": rationale}


class WorkflowScorerTests(unittest.TestCase):
    def test_exact_public_decisions_pass_and_rationale_is_not_machine_scored(self):
        expected = {"a": decision()}
        result = score(expected, [response(rationale="A different but evidence-based explanation.")])
        self.assertEqual(result, {"total": 1, "answered": 1, "correct": 1,
                                  "mismatches": []})

    def test_missing_and_wrong_answers_are_reported_as_failures(self):
        expected = {
            "a": decision(),
            "b": decision(action="block", risk="high", cohort="none"),
        }
        result = score(expected, [response(action="repair_resume")])
        self.assertEqual(result["answered"], 1)
        self.assertEqual(result["correct"], 0)
        self.assertEqual([item["id"] for item in result["mismatches"]], ["a", "b"])
        self.assertEqual(result["mismatches"][0]["actual"]["rationale"], "Policy-backed rationale.")
        self.assertIsNone(result["mismatches"][1]["actual"])

    def test_duplicate_and_unknown_cases_fail(self):
        for answers in ([response(), response()], [response("unknown")]):
            with self.subTest(answers=answers), self.assertRaises(ValueError):
                score({"a": decision()}, answers)

    def test_malformed_responses_fail(self):
        malformed = [
            {},
            {"id": "a"},
            {**response(), "extra": True},
            response(action="PASS"),
            response(risk="medium"),
            response(cohort="three"),
            response(rationale=""),
            {**response(), "id": ["a"]},
            {**response(), "action": ["continue"]},
            {**response(), "risk": ["low"]},
            {**response(), "cohort": ["one_combined"]},
            {**response(), "rationale": ["not-a-string"]},
        ]
        for answer in malformed:
            with self.subTest(answer=answer), self.assertRaises(ValueError):
                score({"a": decision()}, [answer])
        with self.assertRaises(ValueError):
            score({"a": decision()}, {"id": "a"})

    def test_malformed_expected_decisions_fail(self):
        with self.assertRaises(ValueError):
            score({}, [])
        with self.assertRaises(ValueError):
            score({"a": {"action": "continue"}}, [])
        for field, value in (("action", ["continue"]), ("risk", ["low"]),
                             ("cohort", ["one_combined"])):
            with self.subTest(field=field), self.assertRaises(ValueError):
                score({"a": {**decision(), field: value}}, [])

    def test_bundled_cases_and_expected_decisions_are_complete_and_balanced(self):
        root = Path(__file__).parent / "evals"
        document = json.loads((root / "workflow-cases.json").read_text())
        expected = json.loads((root / "workflow-expected.json").read_text())
        cases = document["cases"]
        self.assertEqual(len(cases), 22)
        self.assertEqual(len(cases), len({case["id"] for case in cases}))
        self.assertEqual({case["id"] for case in cases}, set(expected))
        self.assertTrue(all(set(case) == {"id", "context", "question"} for case in cases))
        self.assertEqual(set(document["response_schema"]), {"id", "action", "risk", "cohort", "rationale"})
        self.assertTrue(all(isinstance(value, dict) for value in document["response_schema"].values()))
        result = score(expected, [{"id": case_id, **value, "rationale": "Expected fixture only."}
                                  for case_id, value in expected.items()])
        self.assertEqual(result["correct"], 22)
        self.assertIn("block", {value["action"] for value in expected.values()})
        self.assertIn("clarify_resume", {value["action"] for value in expected.values()})
        self.assertIn("continue", {value["action"] for value in expected.values()})
        self.assertIn("one_combined", {value["cohort"] for value in expected.values()})
        self.assertIn("two_personas", {value["cohort"] for value in expected.values()})

    def test_policy_sensitive_cases_do_not_infer_risk_from_helper_or_unknown_code(self):
        root = Path(__file__).parent / "evals"
        expected = json.loads((root / "workflow-expected.json").read_text())
        for case_id in ("optional_memory_hook_error", "local_lint_unavailable_ci_pending",
                        "same_authority_tool_fallback",
                        "capability_before_scope", "permission_denied", "wrong_checkout"):
            self.assertEqual(expected[case_id]["risk"], "none")
            self.assertEqual(expected[case_id]["cohort"], "none")
        self.assertEqual(expected["remote_plan_removed"],
                         decision("refresh_affected", "low", "one_combined"))

    def test_candidate_adoption_has_one_canonical_action_and_uses_normal_risk_policy(self):
        root = Path(__file__).parent / "evals"
        document = json.loads((root / "workflow-cases.json").read_text())
        expected = json.loads((root / "workflow-expected.json").read_text())
        cases = {case["id"]: case for case in document["cases"]}
        for case_id in ("linked_parser_candidate", "adopt_old_payment_mr"):
            self.assertEqual(expected[case_id]["action"], "adopt_existing")
        self.assertEqual(expected["linked_parser_candidate"],
                         decision("adopt_existing", "high", "two_personas"))
        self.assertIn("current candidate assessment now", cases["linked_parser_candidate"]["context"])
        self.assertIn("no authority to modify", cases["linked_parser_candidate"]["context"])
        self.assertIn("does not adopt an MR/candidate", document["response_schema"]["action"]["bounded_review"])
