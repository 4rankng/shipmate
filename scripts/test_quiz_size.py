"""Tests for quiz_size.py.

The first group ports sphinx-ci's __tests__/scale-question-count.test.ts (MIT) case by case,
vendored at third_party/sphinx-ci/__tests__/scale-question-count.test.ts.txt.
"""

import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import quiz_size
from quiz_size import scale_question_count, size_quiz


class UpstreamScaleQuestionCountTests(unittest.TestCase):
    def test_scales_down_for_very_small_diffs(self):
        self.assertEqual(scale_question_count(10, 5, 1), 5)

    def test_scales_slightly_down_for_small_diffs(self):
        self.assertEqual(scale_question_count(10, 60, 1), 8)

    def test_keeps_baseline_for_medium_diffs(self):
        self.assertEqual(scale_question_count(10, 200, 2), 10)

    def test_scales_up_for_large_diffs(self):
        self.assertEqual(scale_question_count(10, 400, 3), 15)

    def test_scales_up_to_2x_for_very_large_diffs(self):
        self.assertEqual(scale_question_count(10, 900, 2), 20)

    def test_clamps_to_a_minimum_of_3_questions(self):
        self.assertEqual(scale_question_count(4, 5, 1), 3)

    def test_clamps_to_a_maximum_of_20_questions(self):
        self.assertEqual(scale_question_count(15, 2000, 4), 20)

    def test_file_count_contributes_to_the_scope_weight(self):
        self.assertGreater(scale_question_count(10, 50, 20), scale_question_count(10, 50, 1))

    def test_handles_empty_diff(self):
        self.assertEqual(scale_question_count(10, 0, 0), 5)

    def test_scales_relative_to_the_configured_baseline(self):
        self.assertEqual(scale_question_count(6, 500, 1), 9)
        self.assertEqual(scale_question_count(12, 500, 1), 18)


def make_diff(files, lines_per_file):
    chunks = []
    for index in range(files):
        chunks.append(f"diff --git a/f{index}.go b/f{index}.go")
        chunks.extend(f"+line {n}" for n in range(lines_per_file))
    return "\n".join(chunks)


class ShipmateSizingTests(unittest.TestCase):
    def test_shipmate_bands_are_3_4_5_8_8(self):
        counts = [
            scale_question_count(5, weight, 0, maximum=8)
            for weight in (10, 50, 200, 500, 1000)
        ]
        self.assertEqual(counts, [3, 4, 5, 8, 8])

    def test_sensitive_change_moves_up_one_band_but_never_above_8(self):
        self.assertEqual(scale_question_count(5, 10, 0, maximum=8, bump=1), 4)
        self.assertEqual(scale_question_count(5, 200, 0, maximum=8, bump=1), 8)
        self.assertEqual(scale_question_count(5, 1000, 0, maximum=8, bump=1), 8)

    def test_size_quiz_counts_lines_and_files_from_diff(self):
        result = size_quiz(make_diff(2, 10))
        self.assertEqual(result["files"], 2)
        self.assertEqual(result["lines"], 22)
        self.assertEqual(result["weight"], 62)
        self.assertEqual(result["questions"], 4)
        self.assertFalse(result["skip"])

    def test_tiny_diff_is_skipped_like_upstream(self):
        self.assertTrue(size_quiz("")["skip"])
        self.assertTrue(size_quiz("diff --git a/x b/x\n+y")["skip"])

    def test_cli_prints_json(self):
        stdout = io.StringIO()
        with patch("sys.stdin", io.StringIO(make_diff(1, 5))), redirect_stdout(stdout):
            self.assertEqual(quiz_size.main(["--sensitive"]), 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["questions"], 4)


if __name__ == "__main__":
    unittest.main()
