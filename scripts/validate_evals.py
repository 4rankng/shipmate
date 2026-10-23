#!/usr/bin/env python3
"""Validate the bundled eval datasets: parseable, uniquely identified, and paired.

Each ``scripts/evals/<name>-cases.json`` that ships an expected-answer file must
match it case-for-case, and every expected answer must satisfy the evaluator's
own validation rules. Cases without expected answers (skill-quality) must carry
a rubric. This keeps the eval corpus runnable instead of silently rotting.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import evaluate_review_findings
import evaluate_workflow

EVALS = Path(__file__).resolve().parent / "evals"
FRESHNESS_ACTIONS = ("continue", "refresh", "block")


def load(name: str):
    return json.loads((EVALS / name).read_text(encoding="utf-8"))


def case_ids(data, name: str) -> list[str]:
    cases = data.get("cases") if isinstance(data, dict) else data
    if not isinstance(cases, list) or not cases:
        raise ValueError(f"{name}: expected a nonempty 'cases' list")
    ids = []
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get("id"), str) or not case["id"]:
            raise ValueError(f"{name}: every case needs a nonempty string id")
        ids.append(case["id"])
    if len(set(ids)) != len(ids):
        raise ValueError(f"{name}: duplicate case ids")
    return ids


def check_workflow() -> None:
    ids = case_ids(load("workflow-cases.json"), "workflow-cases.json")
    expected = load("workflow-expected.json")
    if sorted(expected) != sorted(ids):
        raise ValueError("workflow-expected.json: case ids do not match workflow-cases.json")
    for case_id, decision in expected.items():
        evaluate_workflow._decision(decision)


def check_freshness() -> None:
    ids = case_ids(load("freshness-cases.json"), "freshness-cases.json")
    expected = load("freshness-expected.json")
    if sorted(expected) != sorted(ids):
        raise ValueError("freshness-expected.json: case ids do not match freshness-cases.json")
    for case_id, action in expected.items():
        if action not in FRESHNESS_ACTIONS:
            raise ValueError(f"freshness-expected.json: invalid action {action!r}")


def check_review_findings() -> None:
    ids = case_ids(load("review-findings-cases.json"), "review-findings-cases.json")
    expected = load("review-findings-expected.json")
    if sorted(expected) != sorted(ids):
        raise ValueError(
            "review-findings-expected.json: case ids do not match review-findings-cases.json"
        )
    for case_id, record in expected.items():
        if not isinstance(record, dict) or record.get("verdict") not in evaluate_review_findings.VERDICTS:
            raise ValueError(f"review-findings-expected.json: invalid verdict for {case_id}")
        key_bug = record.get("key_bug")
        if record["verdict"] != "PASS" and key_bug is None:
            raise ValueError(f"review-findings-expected.json: {case_id} needs a key_bug")
        lines = key_bug.get("lines") if isinstance(key_bug, dict) else None
        if key_bug is not None and (
            not isinstance(key_bug, dict)
            or not isinstance(key_bug.get("file"), str)
            or not key_bug["file"]
            or not isinstance(lines, list)
            or len(lines) != 2
            or not all(isinstance(line, int) and not isinstance(line, bool) for line in lines)
            or lines[0] > lines[1]
            or not isinstance(key_bug.get("category"), str)
            or not key_bug["category"]
        ):
            raise ValueError(f"review-findings-expected.json: invalid key_bug for {case_id}")


def check_skill_quality() -> None:
    data = load("skill-quality-cases.json")
    ids = case_ids(data, "skill-quality-cases.json")
    skills = {"specify", "run", "review", "walkthrough", "quiz"}
    for case in data["cases"]:
        if case["skill"] not in skills:
            raise ValueError(f"skill-quality-cases.json: unknown skill {case['skill']!r}")
        if not case.get("brief") or not case.get("evidence"):
            raise ValueError(f"skill-quality-cases.json: case {case['id']} needs brief and evidence")
    rubric = (EVALS / "skill-quality-rubric.md").read_text(encoding="utf-8").strip()
    if not rubric:
        raise ValueError("skill-quality-rubric.md is empty")
    missing = [case_id for case_id in ids if case_id not in rubric]
    if missing:
        raise ValueError(f"skill-quality-rubric.md: no rubric entry for {missing}")


CHECKS = (check_workflow, check_freshness, check_review_findings, check_skill_quality)


def main() -> int:
    failures = 0
    for check in CHECKS:
        try:
            check()
            print(f"ok: {check.__name__}")
        except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
            failures += 1
            print(f"FAIL: {check.__name__}: {exc}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
