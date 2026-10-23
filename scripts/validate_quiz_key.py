#!/usr/bin/env python3
"""Validate a private quiz answer key before question one, without scoring or showing it.

Read JSON from stdin: {"questions": [{"id": 1, "question": "...", "options":
["A) ...", "B) ...", "C) ...", "D) ..."], "correct": 0, "topic": "...",
"explanation": "..."}]}. Applies the quiz skill's clamp (3-8 questions) and per-question
schema. Pass --expected N when sizing already fixed the planned count.
Prints a machine-readable verdict and never prints option text. Exit 0 only when the
key is usable as-is; exit 1 means regenerate or drop questions.
"""
from __future__ import annotations

import argparse
import json
import sys

MIN_QUESTIONS = 3
MAX_QUESTIONS = 8


def _positive_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def validate(payload, expected: int | None = None) -> dict:
    errors: list[str] = []
    questions = payload.get("questions") if isinstance(payload, dict) else None
    if not isinstance(questions, list):
        return {"valid": False, "count": 0,
                "errors": ["key must be a JSON object with a questions list"]}
    if not MIN_QUESTIONS <= len(questions) <= MAX_QUESTIONS:
        errors.append(f"quiz needs {MIN_QUESTIONS}-{MAX_QUESTIONS} questions, got {len(questions)}")
    if expected is not None and len(questions) != expected:
        errors.append(f"planned count was {expected}, key holds {len(questions)}")
    ids: list[int] = []
    for index, question in enumerate(questions, 1):
        label = f"question {index}"
        if not isinstance(question, dict):
            errors.append(f"{label}: must be an object")
            continue
        if not _positive_int(question.get("id")):
            errors.append(f"{label}: id must be a positive integer")
        else:
            ids.append(question["id"])
        if not isinstance(question.get("question"), str) or not question["question"].strip():
            errors.append(f"{label}: question must be a nonempty string")
        options = question.get("options")
        if not isinstance(options, list) or len(options) != 4:
            errors.append(f"{label}: exactly four options are required")
        elif len({json.dumps(option, sort_keys=True) for option in options}) != 4:
            errors.append(f"{label}: options must be distinct")
        correct = question.get("correct")
        if not isinstance(correct, int) or isinstance(correct, bool) or not 0 <= correct <= 3:
            errors.append(f"{label}: correct must be an index 0-3")
        for field in ("topic", "explanation"):
            value = question.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{label}: {field} must be a nonempty string")
    if len(ids) != len(set(ids)):
        errors.append("question ids must be unique positive integers")
    return {"valid": not errors, "count": len(questions), "errors": errors}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected", type=int, default=None,
                        help="planned question count from sizing")
    args = parser.parse_args(argv)
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as error:
        print(json.dumps({"valid": False, "count": 0,
                          "errors": [f"invalid JSON on stdin: {error}"]}))
        return 1
    result = validate(payload, args.expected)
    print(json.dumps(result))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
