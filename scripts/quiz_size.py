#!/usr/bin/env python3
"""Size a shipmate:quiz from a unified diff.

Port of `scaleQuestionCount` from sphinx-ci (MIT, Martin Vielvoye / Skillberg), vendored at
third_party/sphinx-ci/lib/claude.ts.txt. Shipmate defaults: baseline 5, 3-8 questions, and
one band higher for security-sensitive or state-changing changes.

Usage:
    git diff "$BASE...HEAD" -- . ':!*.lock' | python3 "${SHIPMATE_PLUGIN_ROOT}/scripts/quiz_size.py"
    gh pr diff 1234 | python3 "${SHIPMATE_PLUGIN_ROOT}/scripts/quiz_size.py" --sensitive

Prints JSON: lines, files, weight, questions and skip (true when the diff is too small to quiz,
the sphinx-ci "No quiz needed" rule).
"""

from __future__ import annotations

import argparse
import json
import math
import sys

UPSTREAM_MIN_QUESTIONS = 3
UPSTREAM_MAX_QUESTIONS = 20
SHIPMATE_BASELINE = 5
SHIPMATE_MAX_QUESTIONS = 8
MIN_DIFF_CHARS = 50

# (upper weight bound, factor) from sphinx-ci; the last band has no upper bound.
BANDS = ((30, 0.5), (100, 0.75), (300, 1.0), (800, 1.5), (math.inf, 2.0))


def _js_round(value: float) -> int:
    return math.floor(value + 0.5)


def band_index(weight: int) -> int:
    for index, (upper, _factor) in enumerate(BANDS):
        if weight < upper:
            return index
    return len(BANDS) - 1


def scale_question_count(
    baseline: int,
    lines: int,
    files: int,
    *,
    minimum: int = UPSTREAM_MIN_QUESTIONS,
    maximum: int = UPSTREAM_MAX_QUESTIONS,
    bump: int = 0,
) -> int:
    weight = lines + files * 20
    index = min(band_index(weight) + bump, len(BANDS) - 1)
    scaled = _js_round(baseline * BANDS[index][1])
    return max(minimum, min(maximum, scaled))


def diff_stats(diff: str) -> tuple[int, int]:
    lines = len(diff.split("\n")) if diff else 0
    files = sum(1 for line in diff.splitlines() if line.startswith("diff --git "))
    return lines, files


def size_quiz(diff: str, *, sensitive: bool = False) -> dict:
    lines, files = diff_stats(diff)
    return {
        "lines": lines,
        "files": files,
        "weight": lines + files * 20,
        "questions": scale_question_count(
            SHIPMATE_BASELINE,
            lines,
            files,
            maximum=SHIPMATE_MAX_QUESTIONS,
            bump=1 if sensitive else 0,
        ),
        "skip": len(diff.strip()) < MIN_DIFF_CHARS,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--sensitive",
        action="store_true",
        help="security-sensitive or state-changing change: move up one band",
    )
    args = parser.parse_args(argv)
    print(json.dumps(size_quiz(sys.stdin.read(), sensitive=args.sensitive)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
