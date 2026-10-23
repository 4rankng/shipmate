#!/usr/bin/env python3
"""Validate the machine-local run state file that backs /run resume.

Read JSON from a file path or stdin ("-" with --check): {"version": 1,
"work_item": {"key": "...", "source": "jira|local"}, "stage": 0-11,
"updated_at": "...", "decisions": [{"text", "source"}], "candidate":
{"branch", "sha", "base"}, "review": {"roster", "verdict"},
"pending": {"question"}}. Prints a machine-readable verdict; exit 1 means
fix the state before resuming.
"""
from __future__ import annotations

import argparse
import json
import sys

STAGES = range(0, 12)


def _nonempty(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate(state) -> dict:
    errors: list[str] = []
    if not isinstance(state, dict):
        return {"valid": False, "errors": ["run state must be a JSON object"]}
    if state.get("version") != 1 or isinstance(state.get("version"), bool):
        errors.append("version must be 1")
    stage = state.get("stage")
    if not isinstance(stage, int) or isinstance(stage, bool) or stage not in STAGES:
        errors.append("stage must be an integer 0-11")
    work_item = state.get("work_item")
    if not isinstance(work_item, dict):
        errors.append("work_item.key must be a nonempty string")
        errors.append("work_item.source must be jira or local")
    else:
        if not _nonempty(work_item.get("key")):
            errors.append("work_item.key must be a nonempty string")
        if work_item.get("source") not in ("jira", "local"):
            errors.append("work_item.source must be jira or local")
    if not _nonempty(state.get("updated_at")):
        errors.append("updated_at must be a nonempty ISO-8601 string")
    decisions = state.get("decisions")
    if decisions is not None:
        if not isinstance(decisions, list):
            errors.append("decisions must be a list")
        else:
            for index, decision in enumerate(decisions):
                if not isinstance(decision, dict):
                    errors.append(f"decisions[{index}] must be an object")
                    continue
                if not _nonempty(decision.get("text")):
                    errors.append(f"decisions[{index}].text must be a nonempty string")
                if not _nonempty(decision.get("source")):
                    errors.append(f"decisions[{index}].source must be a nonempty string")
    for optional in ("candidate", "review"):
        if state.get(optional) is not None and not isinstance(state.get(optional), dict):
            errors.append(f"{optional} must be an object")
    pending = state.get("pending")
    if pending is not None:
        if not isinstance(pending, dict):
            errors.append("pending must be an object")
        elif not _nonempty(pending.get("question")):
            errors.append("pending.question must be a nonempty string")
    return {"valid": not errors, "errors": errors}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate a state file")
    parser.add_argument("path", nargs="?", default="-",
                        help="state file path, or '-' for stdin")
    args = parser.parse_args(argv)
    if not args.check:
        parser.print_help()
        return 2
    try:
        if args.path == "-":
            payload = json.load(sys.stdin)
        else:
            with open(args.path, encoding="utf-8") as handle:
                payload = json.load(handle)
    except json.JSONDecodeError as error:
        print(json.dumps({"valid": False, "errors": [f"invalid JSON: {error}"]}))
        return 1
    result = validate(payload)
    print(json.dumps(result))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
