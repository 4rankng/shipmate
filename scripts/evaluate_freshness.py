#!/usr/bin/env python3
"""Score independently generated freshness actions against the bundled regression cases."""
import argparse
import json
from pathlib import Path


def score(expected, responses):
    observed = {}
    for response in responses:
        case_id = response["id"]
        if case_id in observed or case_id not in expected:
            raise ValueError(f"duplicate or unknown case: {case_id}")
        action = response["action"]
        if action not in ("continue", "refresh", "block"):
            raise ValueError(f"invalid action: {action}")
        observed[case_id] = action
    mismatches = [
        {"id": case_id, "expected": action, "actual": observed.get(case_id)}
        for case_id, action in expected.items() if observed.get(case_id) != action
    ]
    return {"total": len(expected), "answered": len(observed),
            "correct": len(expected) - len(mismatches), "mismatches": mismatches}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("responses", type=Path)
    args = parser.parse_args()
    try:
        expected = json.loads((Path(__file__).parent / "evals/freshness-expected.json").read_text())
        result = score(expected, json.loads(args.responses.read_text()))
    except (KeyError, TypeError, ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))
    return bool(result["mismatches"])


if __name__ == "__main__":
    raise SystemExit(main())
