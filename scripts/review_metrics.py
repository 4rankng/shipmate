#!/usr/bin/env python3
"""Summarize local review telemetry without inferring missing cost or quality."""
import argparse
import json
import math
from collections import Counter
from pathlib import Path


OUTCOMES = {
    "running", "completed", "needs-input", "review-pending", "verification-pending", "stopped",
}
EVENT_TYPES = {
    "stop", "user-intervention", "settled-question", "clarification-resolved",
    "restart", "discarded-work", "scope-reduction", "material-post-pass-correction",
    "user-overturn",
}
STOP_CLASSES = {"hard", "degradable"}
EVENT_ACTORS = {"user", "controller", "reviewer"}


def _identifier(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonempty")
    return value


def _nonnegative_number(value, name):
    if (isinstance(value, bool) or not isinstance(value, (float, int))
            or not math.isfinite(value) or value < 0):
        raise ValueError(f"invalid {name}")
    return value


def _deduplicate(records, identifier, kind):
    if not isinstance(records, list):
        raise ValueError(f"{kind} must be a list")
    result = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError(f"{kind} must be objects")
        record_id = _identifier(record.get(identifier), identifier)
        if record_id in result and result[record_id] != record:
            raise ValueError(f"conflicting copies of {kind[:-1]} {record_id}")
        result[record_id] = record
    return result


def _validate_cost(review):
    amount = review.get("cost_amount")
    currency = review.get("cost_currency")
    if (amount is None) != (currency is None):
        raise ValueError("cost_amount and cost_currency must be recorded together")
    if amount is None:
        return None
    _nonnegative_number(amount, "cost_amount")
    _identifier(currency, "cost_currency")
    return amount, currency


def _workflow_metrics(data):
    if "workflow_runs" not in data:
        return {
            "workflow_telemetry_known": False,
            "workflow_runs": None,
            "outcomes": None,
            "workflow_event_coverage": {"known_runs": 0, "total_runs": None},
            "workflow_events": None,
            "stops_by_classification": None,
            "stops_by_reason": None,
            "stop_reason_coverage": {"known_stops": 0, "total_stops": None},
            "adjudicated_avoidable_stops": None,
            "avoidable_stop_coverage": {"known_stops": 0, "total_stops": None},
            "repeated_settled_questions": None,
            "clarification_to_resume_seconds": {
                "known_sum": None, "known_events": 0, "total_events": None,
            },
            "restarts": None,
            "discarded_work": None,
            "scope_reductions": None,
            "user_scope_reductions": None,
            "scope_reduction_actor_coverage": {
                "known_events": 0, "total_events": None,
            },
            "material_post_pass_corrections": None,
            "user_interventions": None,
            "user_overturns": None,
        }
    workflows = _deduplicate(data.get("workflow_runs", []), "workflow_run_id", "workflow runs")
    event_counts, stop_classes, stop_reasons = Counter(), Counter(), Counter()
    clarification_values = []
    avoidable_stops, avoidable_known = 0, 0
    repeated_questions = 0
    event_runs_known = 0
    user_scope_reductions, scope_actor_known = 0, 0
    user_overturns = 0
    for workflow in workflows.values():
        outcome = workflow.get("outcome")
        if outcome not in OUTCOMES:
            raise ValueError("unknown workflow outcome")
        if "events" not in workflow:
            continue
        events = _deduplicate(workflow["events"], "event_id", "events")
        event_runs_known += 1
        settled_questions = Counter()
        for event in events.values():
            event_type = event.get("type")
            if event_type not in EVENT_TYPES:
                raise ValueError("unknown workflow event type")
            event_counts[event_type] += 1
            if event_type == "stop":
                _identifier(event.get("reason_code"), "stop reason_code")
                classification = event.get("classification")
                if classification not in STOP_CLASSES:
                    raise ValueError("stop classification must be hard or degradable")
                stop_classes[classification] += 1
                stop_reasons[event["reason_code"]] += 1
                if "avoidable" in event and not isinstance(event["avoidable"], bool):
                    raise ValueError("stop avoidable must be boolean when recorded")
                avoidable_known += "avoidable" in event
                avoidable_stops += event.get("avoidable") is True
            elif any(key in event for key in ("reason_code", "classification", "avoidable")):
                raise ValueError("stop fields are valid only on stop events")
            if event_type == "settled-question":
                settled_questions[_identifier(event.get("question_id"), "settled question_id")] += 1
            elif "question_id" in event:
                raise ValueError("question_id is valid only on settled-question events")
            if event_type == "clarification-resolved":
                value = event.get("clarification_to_resume_seconds")
                if value is not None:
                    clarification_values.append(_nonnegative_number(value, "clarification_to_resume_seconds"))
            elif "clarification_to_resume_seconds" in event:
                raise ValueError("clarification_to_resume_seconds is valid only on clarification-resolved events")
            if event_type == "scope-reduction":
                if "actor" in event:
                    actor = event["actor"]
                    if actor not in EVENT_ACTORS:
                        raise ValueError("scope-reduction actor must be user, controller or reviewer")
                    scope_actor_known += 1
                    user_scope_reductions += actor == "user"
            elif event_type == "user-overturn":
                if event.get("actor") != "user":
                    raise ValueError("user-overturn actor must be user")
                user_overturns += 1
            elif "actor" in event:
                raise ValueError("actor is valid only on scope-reduction or user-overturn events")
        repeated_questions += sum(count - 1 for count in settled_questions.values() if count > 1)
    event_inventory_complete = event_runs_known == len(workflows)
    event_total = event_counts["clarification-resolved"] if event_inventory_complete else None
    known_clarification_sum = sum(clarification_values) if clarification_values else None
    if not event_inventory_complete:
        return {
            "workflow_telemetry_known": True,
            "workflow_runs": len(workflows),
            "outcomes": dict(Counter(w["outcome"] for w in workflows.values())),
            "workflow_event_coverage": {
                "known_runs": event_runs_known, "total_runs": len(workflows),
            },
            "workflow_events": None,
            "stops_by_classification": None,
            "stops_by_reason": None,
            "stop_reason_coverage": {
                "known_stops": event_counts["stop"], "total_stops": None,
            },
            "adjudicated_avoidable_stops": None,
            "avoidable_stop_coverage": {
                "known_stops": avoidable_known, "total_stops": None,
            },
            "repeated_settled_questions": None,
            "clarification_to_resume_seconds": {
                "known_sum": known_clarification_sum,
                "known_events": len(clarification_values),
                "total_events": event_total,
            },
            "restarts": None,
            "discarded_work": None,
            "scope_reductions": None,
            "user_scope_reductions": None,
            "scope_reduction_actor_coverage": {
                "known_events": scope_actor_known, "total_events": None,
            },
            "material_post_pass_corrections": None,
            "user_interventions": None,
            "user_overturns": None,
        }
    return {
        "workflow_telemetry_known": True,
        "workflow_runs": len(workflows),
        "outcomes": dict(Counter(w["outcome"] for w in workflows.values())),
        "workflow_event_coverage": {
            "known_runs": event_runs_known, "total_runs": len(workflows),
        },
        "workflow_events": dict(event_counts),
        "stops_by_classification": dict(stop_classes),
        "stops_by_reason": dict(stop_reasons),
        "stop_reason_coverage": {
            "known_stops": event_counts["stop"], "total_stops": event_counts["stop"],
        },
        "adjudicated_avoidable_stops": avoidable_stops,
        "avoidable_stop_coverage": {
            "known_stops": avoidable_known, "total_stops": event_counts["stop"],
        },
        "repeated_settled_questions": repeated_questions,
        "clarification_to_resume_seconds": {
            "known_sum": known_clarification_sum,
            "known_events": len(clarification_values),
            "total_events": event_total,
        },
        "restarts": event_counts["restart"],
        "discarded_work": event_counts["discarded-work"],
        "scope_reductions": event_counts["scope-reduction"],
        "user_scope_reductions": user_scope_reductions,
        "scope_reduction_actor_coverage": {
            "known_events": scope_actor_known,
            "total_events": event_counts["scope-reduction"],
        },
        "material_post_pass_corrections": event_counts["material-post-pass-correction"],
        "user_interventions": event_counts["user-intervention"],
        "user_overturns": user_overturns,
    }


def summarize(data):
    if not isinstance(data, dict) or not isinstance(data.get("reviews"), list):
        raise ValueError("reviews must be a list")
    runs = _deduplicate(data["reviews"], "review_run_id", "review runs")
    accepted, rejected, unverified = [], 0, 0
    finding_runs_known = 0
    for review in runs.values():
        findings = review.get("findings")
        if findings is None:
            continue
        if not isinstance(findings, list):
            raise ValueError("findings must be a list")
        finding_runs_known += 1
        workflow_run_id = review.get("workflow_run_id")
        finding_cohort = ("legacy",)
        if workflow_run_id is not None:
            finding_cohort = ("workflow", _identifier(workflow_run_id, "workflow_run_id"))
        for finding in findings:
            if not isinstance(finding, dict):
                raise ValueError("findings must be objects")
            issue = finding["issue_id"]
            if not isinstance(issue, str) or not issue.strip():
                raise ValueError("finding issue_id must be nonempty")
            if finding["disposition"] == "accepted":
                accepted.append((finding_cohort, issue))
            elif finding["disposition"] == "rejected":
                rejected += 1
            elif finding["disposition"] == "unverified":
                unverified += 1
            else:
                raise ValueError("findings must be adjudicated accepted, rejected or unverified")
    finding_inventory_complete = finding_runs_known == len(runs)
    unique_accepted_issues = len(set(accepted)) if finding_inventory_complete else None
    result = {
        "review_invocations": len(runs),
        "invocations_by_phase": dict(Counter(r["phase"] for r in runs.values())),
        "accepted_reports": len(accepted) if finding_inventory_complete else None,
        "rejected_reports": rejected if finding_inventory_complete else None,
        "unverified_reports": unverified if finding_inventory_complete else None,
        "unique_accepted_issues": unique_accepted_issues,
        "duplicate_accepted_reports": (
            len(accepted) - unique_accepted_issues if finding_inventory_complete else None
        ),
        "finding_inventory_coverage": {
            "known_runs": finding_runs_known, "total_runs": len(runs),
        },
    }
    for key in ("duration_seconds", "total_tokens"):
        values = [r[key] for r in runs.values() if r.get(key) is not None]
        for value in values:
            if (isinstance(value, bool) or not isinstance(value, (float, int))
                    or not math.isfinite(value) or value < 0
                    or (key == "total_tokens" and not isinstance(value, int))):
                raise ValueError(f"invalid {key}")
        result[key] = {"known_sum": sum(values) if values else None,
                       "known_runs": len(values), "total_runs": len(runs)}
    costs = [_validate_cost(r) for r in runs.values()]
    known_costs = [cost for cost in costs if cost is not None]
    currencies = {currency for _, currency in known_costs}
    cost_per_issue = None
    if (finding_inventory_complete and len(known_costs) == len(runs)
            and len(currencies) == 1 and unique_accepted_issues > 0):
        currency = next(iter(currencies))
        cost_per_issue = {"value": sum(amount for amount, _ in known_costs) / unique_accepted_issues,
                          "currency": currency}
    result["review_cost_per_unique_accepted_issue"] = cost_per_issue
    result.update(_workflow_metrics(data))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("metrics_file", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(summarize(json.loads(args.metrics_file.read_text())), indent=2))
    except (KeyError, TypeError, ValueError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
