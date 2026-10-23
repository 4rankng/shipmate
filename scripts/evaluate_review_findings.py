#!/usr/bin/env python3
"""Score independent candidate-review responses against the planted-bug regression cases.

Each response is {"id", "verdict", "blocking_findings": [{"file", "line", "category"}]}.
A planted-bug case is hit when a blocking finding matches its key-bug category and file with a
line inside the expected inclusive range. A clean control is falsely blocked when its verdict is
CHANGES_REQUIRED or it carries any blocking finding. A case is a mismatch when its verdict
differs from the expected verdict, a planted-bug case misses its key bug, or a clean control
carries a blocking finding. Duplicate, unknown or missing case IDs are input errors (exit 2);
any mismatch exits 1.
"""
import argparse
import json
from pathlib import Path

VERDICTS = ("PASS", "CHANGES_REQUIRED", "UNABLE_TO_REVIEW")


def _findings(response):
    findings = response["blocking_findings"]
    if not isinstance(findings, list):
        raise ValueError(f"blocking_findings must be a list: {response['id']}")
    for finding in findings:
        if (not isinstance(finding, dict) or not isinstance(finding.get("file"), str)
                or isinstance(finding.get("line"), bool) or not isinstance(finding.get("line"), int)
                or not isinstance(finding.get("category"), str)):
            raise ValueError(f"invalid blocking finding: {response['id']}")
    return findings


def score(expected, responses):
    if not isinstance(responses, list):
        raise ValueError("responses must be a JSON array")
    observed = {}
    for response in responses:
        case_id = response["id"]
        if case_id in observed or case_id not in expected:
            raise ValueError(f"duplicate or unknown case: {case_id}")
        if response["verdict"] not in VERDICTS:
            raise ValueError(f"invalid verdict: {response['verdict']}")
        observed[case_id] = response
    missing = sorted(set(expected) - set(observed))
    if missing:
        raise ValueError(f"missing cases: {', '.join(missing)}")
    hits = false_blocks = bug_cases = 0
    mismatches = []
    for case_id, want in expected.items():
        response = observed[case_id]
        findings = _findings(response)
        key = want["key_bug"]
        if key is None:
            blocked = response["verdict"] == "CHANGES_REQUIRED" or bool(findings)
            false_blocks += blocked
            key_found = None
        else:
            bug_cases += 1
            low, high = key["lines"]
            key_found = any(f["category"] == key["category"] and f["file"] == key["file"]
                            and low <= f["line"] <= high
                            for f in findings)
            hits += key_found
        if (response["verdict"] != want["verdict"] or key_found is False
                or (key is None and findings)):
            mismatches.append({"id": case_id, "expected": want["verdict"],
                               "actual": response["verdict"], "key_bug_found": key_found,
                               "blocking_findings": len(findings)})
    clean_cases = len(expected) - bug_cases
    return {"key_bug_inclusion": f"{hits}/{bug_cases}",
            "false_blocks": f"{false_blocks}/{clean_cases}",
            "mismatches": mismatches, "sample_size": len(expected)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("responses", type=Path)
    args = parser.parse_args()
    try:
        expected = json.loads(
            (Path(__file__).parent / "evals/review-findings-expected.json").read_text())
        result = score(expected, json.loads(args.responses.read_text()))
    except (KeyError, TypeError, ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))
    return bool(result["mismatches"])


if __name__ == "__main__":
    raise SystemExit(main())
