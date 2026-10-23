#!/usr/bin/env python3
"""Calculate a quiz session's counts and level without printing its answer key.

Read JSON from stdin: {"questions": [{"id": 1, "topic": "Ownership", "correct": 0,
"answer": 0}], "freshness": "current"}. Answers are A-D indices 0-3, "skip", or
null (unanswered). Supply the first submitted answer for this attempt only.
Set integrity to "compromised" if a hinted question has not been neutrally replaced.
"""
from __future__ import annotations

import argparse
import json
import sys

import quiz_dashboard


def summarize(questions: list[dict], *, freshness: str = "current", integrity: str = "neutral") -> dict:
    if freshness not in ("current", "stale", "unverified"):
        raise ValueError("freshness must be current, stale or unverified")
    if integrity not in ("neutral", "compromised"):
        raise ValueError("integrity must be neutral or compromised")
    if not isinstance(questions, list) or len(questions) > 8:
        raise ValueError("questions must be a list of at most 8 entries")
    counts = dict.fromkeys(("correct", "wrong", "skipped", "unanswered"), 0)
    topics: dict[str, list[str]] = {}
    seen = set()
    for question in questions:
        if not isinstance(question, dict) or set(question) != {"id", "topic", "correct", "answer"}:
            raise ValueError("each question requires exactly id, topic, correct and answer")
        qid, topic = question["id"], question["topic"]
        correct, answer = question["correct"], question["answer"]
        if type(qid) is not int or qid < 1 or qid in seen:
            raise ValueError("question ids must be unique positive integers")
        if not isinstance(topic, str) or not topic.strip():
            raise ValueError("question topic must be nonempty text")
        if type(correct) is not int or correct not in range(4):
            raise ValueError("correct option must be an integer from 0 to 3")
        if answer is not None and answer != "skip" and (type(answer) is not int or answer not in range(4)):
            raise ValueError("answer must be an integer from 0 to 3, skip or null")
        seen.add(qid)
        outcome = ("unanswered" if answer is None else "skipped" if answer == "skip"
                   else "correct" if answer == correct else "wrong")
        counts[outcome] += 1
        topics.setdefault(topic.strip(), []).append(outcome)

    total = len(questions)
    answered = counts["correct"] + counts["wrong"]
    percent = None
    level = None
    passed = None
    if freshness == "stale":
        status = "Stale"
    elif integrity == "compromised" or total < 3 or answered == 0:
        status = "Not assessed"
    else:
        percent = (2 * counts["correct"] * 100 + total) // (2 * total)
        status = "Incomplete" if counts["unanswered"] else "Completed"
        if status == "Completed":
            level = "Strong" if percent >= 90 else "Developing" if percent >= 70 else "Needs review"
            passed = percent >= 70

    topic_results = {}
    for topic, outcomes in topics.items():
        if status in ("Stale", "Not assessed"):
            state = "Not assessed"
        elif "wrong" in outcomes:
            state = "Needs review"
        elif "correct" not in outcomes:
            state = "Not assessed"
        elif any(outcome != "correct" for outcome in outcomes):
            state = "Partly assessed"
        else:
            state = "Demonstrated"
        topic_results[topic] = state
    return {"total": total, "counts": counts, "percent": percent, "status": status,
            "level": level, "passed": passed, "freshness": freshness, "integrity": integrity,
            "topics": topic_results}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("json", "dashboard"), default="json")
    parser.add_argument("--width", type=int, default=76, help="Dashboard columns (64–120)")
    args = parser.parse_args(argv)
    try:
        payload = json.load(sys.stdin)
        allowed = {"questions", "freshness", "integrity"}
        if args.format == "dashboard":
            allowed.add("report")
        if not isinstance(payload, dict) or not {"questions"} <= payload.keys() <= allowed:
            raise ValueError("input requires questions and supported optional context")
        result = summarize(payload["questions"], freshness=payload.get("freshness", "current"),
                           integrity=payload.get("integrity", "neutral"))
        output = (quiz_dashboard.render(result, payload.get("report", {}), args.width)
                  if args.format == "dashboard" else json.dumps(result))
    except (ValueError, TypeError) as exc:
        # Never echo the input: it contains the private answer key.
        print(f"Invalid quiz report input: {exc}", file=sys.stderr)
        return 2
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
