import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from evaluate_review_findings import score

SCRIPT = Path(__file__).parent / "evaluate_review_findings.py"
EVALS = Path(__file__).parent / "evals"
HUNK = re.compile(r"@@ -(\d+),(\d+) \+(\d+),(\d+) @@")


def _bundled():
    cases = json.loads((EVALS / "review-findings-cases.json").read_text())["cases"]
    expected = json.loads((EVALS / "review-findings-expected.json").read_text())
    return cases, expected


def _perfect(expected):
    responses = []
    for case_id, want in expected.items():
        key = want["key_bug"]
        findings = [] if key is None else [
            {"file": key["file"], "line": key["lines"][0], "category": key["category"]}]
        responses.append({"id": case_id, "verdict": want["verdict"], "blocking_findings": findings})
    return responses


def _added_lines(diff):
    """Map each file to its added lines in new-file coordinates, checking hunk counts."""
    added, current, hunk = {}, None, None
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
            continue
        if line.startswith("--- a/"):
            continue
        match = HUNK.match(line)
        if match:
            if hunk:
                assert hunk[1] == hunk[2] == 0, hunk
            old_start, old_count, new_start, new_count = map(int, match.groups())
            hunk = [new_start, old_count, new_count]
            continue
        kind = line[:1]
        if kind in (" ", "-"):
            hunk[1] -= 1
        if kind in (" ", "+"):
            if kind == "+":
                added.setdefault(current, set()).add(hunk[0])
            hunk[0] += 1
            hunk[2] -= 1
    assert hunk[1] == hunk[2] == 0, hunk
    return added


class ReviewFindingsScorerTests(unittest.TestCase):
    def _run(self, responses):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump(responses, handle)
        try:
            return subprocess.run([sys.executable, str(SCRIPT), handle.name],
                                  capture_output=True, text=True, check=False)
        finally:
            Path(handle.name).unlink()

    def test_perfect_responses_score_full_inclusion_and_no_false_blocks(self):
        _, expected = _bundled()
        result = self._run(_perfect(expected))
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report, {"key_bug_inclusion": "4/4", "false_blocks": "0/4",
                                  "mismatches": [], "sample_size": 8})

    def test_blocking_everything_without_findings_misses_bugs_and_blocks_controls(self):
        _, expected = _bundled()
        responses = [{"id": case_id, "verdict": "CHANGES_REQUIRED", "blocking_findings": []}
                     for case_id in expected]
        result = self._run(responses)
        self.assertEqual(result.returncode, 1, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["key_bug_inclusion"], "0/4")
        self.assertEqual(report["false_blocks"], "4/4")
        self.assertEqual(len(report["mismatches"]), 8)

    def test_duplicate_id_exits_2(self):
        _, expected = _bundled()
        responses = _perfect(expected)
        result = self._run(responses + responses[:1])
        self.assertEqual(result.returncode, 2)
        self.assertIn("duplicate or unknown case", result.stderr)

    def test_unrelated_categories_at_bug_locations_do_not_count(self):
        _, expected = _bundled()
        responses = _perfect(expected)
        for response in responses:
            for finding in response["blocking_findings"]:
                finding["category"] = "style-only"
        result = self._run(responses)
        self.assertEqual(result.returncode, 1, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["key_bug_inclusion"], "0/4")
        self.assertEqual(report["false_blocks"], "0/4")
        self.assertEqual({m["id"] for m in report["mismatches"]},
                         {case_id for case_id, want in expected.items() if want["key_bug"]})

    def test_file_line_and_category_must_match_the_same_finding(self):
        expected = {"bug": {"verdict": "CHANGES_REQUIRED",
                            "key_bug": {"file": "a.go", "lines": [3, 4], "category": "x"}}}
        findings = [{"file": "a.go", "line": 3, "category": "style-only"},
                    {"file": "a.go", "line": 5, "category": "x"}]
        response = {"id": "bug", "verdict": "CHANGES_REQUIRED", "blocking_findings": findings}
        self.assertEqual(score(expected, [response])["key_bug_inclusion"], "0/1")
        for line in (3, 4):
            with self.subTest(line=line):
                response["blocking_findings"] = findings + [
                    {"file": "a.go", "line": line, "category": "x"}]
                self.assertEqual(score(expected, [response])["key_bug_inclusion"], "1/1")

    def test_unknown_missing_and_invalid_inputs_fail(self):
        expected = {"bug": {"verdict": "CHANGES_REQUIRED",
                            "key_bug": {"file": "a.go", "lines": [3, 4], "category": "x"}}}
        good = {"id": "bug", "verdict": "CHANGES_REQUIRED",
                "blocking_findings": [{"file": "a.go", "line": 3, "category": "x"}]}
        for responses in ([], [good, {**good, "id": "other"}], [{**good, "verdict": "LGTM"}],
                          [{**good, "blocking_findings": [{"file": "a.go", "line": "3",
                                                            "category": "x"}]}]):
            with self.subTest(responses=responses), self.assertRaises(ValueError):
                score(expected, responses)

    def test_wrong_file_or_line_misses_key_bug(self):
        expected = {"bug": {"verdict": "CHANGES_REQUIRED",
                            "key_bug": {"file": "a.go", "lines": [3, 4], "category": "x"}}}
        for finding in ({"file": "b.go", "line": 3, "category": "x"},
                        {"file": "a.go", "line": 5, "category": "x"}):
            with self.subTest(finding=finding):
                result = score(expected, [{"id": "bug", "verdict": "CHANGES_REQUIRED",
                                           "blocking_findings": [finding]}])
                self.assertEqual(result["key_bug_inclusion"], "0/1")
                self.assertFalse(result["mismatches"][0]["key_bug_found"])

    def test_bundled_cases_are_consistent(self):
        cases, expected = _bundled()
        ids = [case["id"] for case in cases]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids), set(expected))
        self.assertEqual(sum(want["key_bug"] is None for want in expected.values()), 4)
        for case in cases:
            with self.subTest(case=case["id"]):
                self.assertTrue(case["requirement"])
                self.assertIsInstance(case["context_slices"], list)
                added = _added_lines(case["diff"])
                want = expected[case["id"]]
                self.assertIn(want["verdict"], ("PASS", "CHANGES_REQUIRED"))
                key = want["key_bug"]
                if key is not None:
                    low, high = key["lines"]
                    self.assertTrue(added.get(key["file"], set()) & set(range(low, high + 1)))


if __name__ == "__main__":
    unittest.main()
