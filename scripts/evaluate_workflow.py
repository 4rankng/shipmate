#!/usr/bin/env python3
"""Score independent L3 workflow decisions against bundled regression cases."""
import argparse
import json
from pathlib import Path


ACTIONS = {
    "adopt_existing",
    "block",
    "bounded_review",
    "clarify_resume",
    "continue",
    "refresh_affected",
    "repair_resume",
    "sequence",
    "wait_verify",
}
RISKS = {"none", "low", "high"}
COHORTS = {"none", "one_combined", "two_personas"}
DECISION_KEYS = {"action", "risk", "cohort"}
RESPONSE_KEYS = {"id", *DECISION_KEYS}
RESPONSE_KEYS_WITH_RATIONALE = {*RESPONSE_KEYS, "rationale"}


def _decision(value, *, response=False):
    required = RESPONSE_KEYS_WITH_RATIONALE if response else DECISION_KEYS
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError(f"decision must contain exactly: {', '.join(sorted(required))}")
    if not isinstance(value["action"], str) or value["action"] not in ACTIONS:
        raise ValueError(f"invalid action: {value['action']}")
    if not isinstance(value["risk"], str) or value["risk"] not in RISKS:
        raise ValueError(f"invalid risk: {value['risk']}")
    if not isinstance(value["cohort"], str) or value["cohort"] not in COHORTS:
        raise ValueError(f"invalid cohort: {value['cohort']}")
    result = {
        "action": value["action"],
        "risk": value["risk"],
        "cohort": value["cohort"],
    }
    if response:
        rationale = value["rationale"]
        if not isinstance(rationale, str) or not rationale.strip():
            raise ValueError("rationale must be a nonempty string")
        result["rationale"] = rationale
    return result


def score(expected, responses):
    if not isinstance(expected, dict) or not expected:
        raise ValueError("expected decisions must be a nonempty object")
    normalized_expected = {}
    for case_id, decision in expected.items():
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError("expected case IDs must be nonempty strings")
        normalized_expected[case_id] = _decision(decision)

    if not isinstance(responses, list):
        raise ValueError("responses must be a JSON array")
    observed = {}
    for response in responses:
        if not isinstance(response, dict):
            raise ValueError("each response must be an object")
        case_id = response.get("id")
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError("response id must be a nonempty string")
        if case_id in observed:
            raise ValueError(f"duplicate case: {case_id}")
        if case_id not in normalized_expected:
            raise ValueError(f"unknown case: {case_id}")
        observed[case_id] = _decision(response, response=True)

    mismatches = [
        {
            "id": case_id,
            "expected": decision,
            "actual": observed.get(case_id),
        }
        for case_id, decision in normalized_expected.items()
        if ({key: observed[case_id][key] for key in DECISION_KEYS}
            if case_id in observed else None) != decision
    ]
    return {
        "total": len(normalized_expected),
        "answered": len(observed),
        "correct": len(normalized_expected) - len(mismatches),
        "mismatches": mismatches,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("responses", type=Path)
    args = parser.parse_args()
    root = Path(__file__).parent
    try:
        expected = json.loads((root / "evals/workflow-expected.json").read_text())
        responses = json.loads(args.responses.read_text())
        result = score(expected, responses)
    except (KeyError, TypeError, ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))
    return bool(result["mismatches"])


if __name__ == "__main__":
    raise SystemExit(main())
