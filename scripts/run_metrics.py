#!/usr/bin/env python3
"""Maintain one private, cooperative L3 run-metrics snapshot per workflow run."""

import argparse
import copy
import csv
import datetime as dt
import fcntl
import json
import math
import os
import stat
import sys
import tempfile
import uuid
from pathlib import Path


SCHEMA_VERSION = "l3-run-metrics/1.0"
METRIC_SOURCE = {"page_id": 2233074585, "page_version": 17, "attachment_version": 3}
# Retain the historical store so rename does not hide existing runs or checkpoints.
DEFAULT_OUTPUT_DIR = Path.home() / ".local" / "state" / "l3-workflow" / "runs"
MODES = {"run", "specify", "review"}
SOURCE_KINDS = {"jira", "markdown", "chat", "mr"}
RUN_STATUSES = {"not_started", "running", "mr_created", "failed", "cancelled", "interrupted"}
HUMAN_COVERAGE = {"complete", "partial", "not_observed"}
WAIT_COVERAGE = {"complete", "partial", "not_observed"}
EFFORT_METHODS = {"timer", "self_reported", "self_reported_estimate"}
COST_BASES = {"billed", "estimated"}
CI_RESULTS = {"pending", "passed", "code_failure", "environment_blocked", "not_applicable"}
REVIEW_RESULTS = {"not_yet_reviewed", "accepted_without_changes", "changes_requested"}
FOLLOWUP_STATUSES = {"pending", "in_progress", "complete", "not_applicable"}
DEFECT_SEVERITIES = {"critical", "major", "minor", "unknown"}
DEFECT_STAGES = {"review", "after_delivery"}
PRE_MR_PHASE = "before_mr"
PLAN_APPROVAL_ACTION = "plan_approval"
PRE_MR_HELP_ACTIONS = {
    "clarification", "requested_plan_revision", "manual_command", "manual_edit", "rescue",
}
PRE_MR_NON_HELP_ACTIONS = {PLAN_APPROVAL_ACTION, "metrics_report"} | PRE_MR_HELP_ACTIONS
WORKFLOW_STATUSES = {
    "running", "completed", "needs-input", "review-pending", "verification-pending", "stopped",
}
TERMINAL_NO_MR_STATUSES = {"failed", "cancelled"}
DERIVED_POINTERS = {
    "/outcome/classification", "/outcome/reason",
    "/ticket/preparation_elapsed_minutes", "/timing/time_to_mr_minutes",
    "/timing/execution_minutes", "/timing/waiting_minutes",
    "/timing/elapsed_to_stop_minutes",
}
READ_ONLY_POINTERS = {
    "/schema_version", "/metric_source", "/run_id", "/updated_at", "/repository",
    "/harness/name", "/harness/version", "/run/first_invoked_at",
    "/measurement_notes/l3/revision", "/measurement_notes/l3/mode",
    "/measurement_notes/l3/source_kind", "/measurement_notes/l3/source_work_item",
}
ALLOWED_EXACT_POINTERS = {
    "/restarted_after_run_id", "/engineer_id",
    "/ticket/id", "/ticket/url", "/ticket/preparation_id",
    "/ticket/preparation_started_at", "/ticket/preflight_passed_at",
    "/harness/models", "/harness/native_run_ids",
    "/run/status", "/run/stopped_at",
    "/outcome/plan_approvals_before_mr", "/outcome/extra_human_help_before_mr",
    "/outcome/human_event_coverage",
    "/mr/url", "/mr/initial_sha", "/mr/created_at",
    "/timing/ticket_submitted_at", "/timing/wait_coverage", "/timing/wait_intervals",
    "/human_effort/before_mr_or_stop_active_minutes", "/human_effort/before_method",
    "/human_effort/after_mr_active_minutes", "/human_effort/after_method",
    "/plan_revisions/human_requested", "/plan_revisions/autonomous",
    "/resources/generation", "/resources/corrections",
    "/review/initial_ci", "/review/initial_review", "/review/revision_rounds",
    "/review/additional_commits", "/review/confirmed_defect_count",
    "/review/confirmed_defects", "/review/observed_through", "/review/followup_status",
    "/human_events", "/evidence", "/missing_reasons",
    "/measurement_notes/l3/workflow_status", "/measurement_notes/l3/next_action",
}
RESOURCE_FIELDS = {
    "input_tokens", "cached_input_tokens", "output_tokens", "tool_calls", "model_turns",
    "cost", "currency", "cost_basis", "cost_source",
}
TOP_LEVEL_FIELDS = {
    "schema_version", "metric_source", "run_id", "restarted_after_run_id", "updated_at",
    "engineer_id", "repository", "ticket", "harness", "run", "outcome", "mr", "timing",
    "human_effort", "plan_revisions", "resources", "review", "human_events", "evidence",
    "measurement_notes", "missing_reasons",
}


class RevisionConflict(ValueError):
    """The caller tried to update an older revision of a run snapshot."""


class MetricsBusy(ValueError):
    """Another process is updating this optional local metrics snapshot."""


def _utc_now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _plugin_version():
    plugin_file = Path(__file__).resolve().parents[1] / "plugin.json"
    data = json.loads(plugin_file.read_text(encoding="utf-8"))
    value = data.get("version")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("plugin.json version must be a nonempty string")
    return value


def _resource():
    return {
        "input_tokens": None,
        "cached_input_tokens": None,
        "output_tokens": None,
        "tool_calls": None,
        "model_turns": None,
        "cost": None,
        "currency": None,
        "cost_basis": None,
        "cost_source": None,
    }


def _initial_missing_reasons(source_kind, work_item, native_run_id):
    reasons = {
        "/engineer_id": "engineer identity was not provided",
        "/restarted_after_run_id": "this run was not recorded as an independent restart",
        "/ticket/url": "ticket URL was not observed",
        "/ticket/preparation_id": "ticket preparation was not observed",
        "/ticket/preparation_started_at": "ticket preparation start was not observed",
        "/ticket/preflight_passed_at": "ticket preflight completion was not observed",
        "/ticket/preparation_elapsed_minutes": "ticket preparation timing is incomplete",
        "/harness/models": "model metadata is cooperatively supplied and was not observed",
        "/outcome/classification": "implementation-MR outcome is not yet classifiable",
        "/outcome/plan_approvals_before_mr": "plan approvals were not observed",
        "/outcome/extra_human_help_before_mr": "human assistance was not observed",
        "/mr/url": "initial implementation MR was not observed",
        "/mr/initial_sha": "initial implementation MR was not observed",
        "/mr/created_at": "initial implementation MR was not observed",
        "/timing/ticket_submitted_at": "eligible intake timestamp was not observed",
        "/timing/time_to_mr_minutes": "eligible intake or initial MR time is incomplete",
        "/timing/execution_minutes": "complete execution and wait coverage is unavailable",
        "/timing/waiting_minutes": "complete wait coverage is unavailable",
        "/timing/elapsed_to_stop_minutes": "run stop was not observed",
        "/human_effort/before_mr_or_stop_active_minutes": "human effort was not reported",
        "/human_effort/before_method": "human effort was not reported",
        "/human_effort/after_mr_active_minutes": "post-MR human effort was not reported",
        "/human_effort/after_method": "post-MR human effort was not reported",
        "/plan_revisions/human_requested": "human-requested plan revisions were not observed",
        "/plan_revisions/autonomous": "autonomous plan revisions were not observed",
        "/review/initial_ci/result": "initial CI was not observed",
        "/review/initial_ci/sha": "initial CI was not observed",
        "/review/initial_ci/evidence_ref": "initial CI was not observed",
        "/review/initial_review/result": "initial review was not observed",
        "/review/initial_review/sha": "initial review was not observed",
        "/review/initial_review/evidence_ref": "initial review was not observed",
        "/review/revision_rounds": "post-MR revisions were not observed",
        "/review/additional_commits": "post-MR commits were not observed",
        "/review/confirmed_defect_count": "confirmed-defect coverage is incomplete",
        "/review/observed_through": "review observation cutoff was not recorded",
        "/review/followup_status": "review follow-up was not observed",
        "/measurement_notes/l3/next_action": "next workflow action was not recorded",
    }
    for phase in ("generation", "corrections"):
        for field in RESOURCE_FIELDS:
            reasons["/resources/{}/{}".format(phase, field)] = (
                "native usage or billing was not supplied; cooperative capture is incomplete"
            )
    if source_kind == "jira":
        if not work_item:
            reasons["/ticket/id"] = "Jira work item was not provided"
    else:
        reasons["/ticket/id"] = "source kind {} has no Jira ticket".format(source_kind)
    if not work_item:
        reasons["/measurement_notes/l3/source_work_item"] = "source work item was not provided"
    if not native_run_id:
        reasons["/harness/native_run_ids"] = (
            "native run linkage was not supplied; total invocation coverage is unknown"
        )
    return reasons


def _new_record(mode, repository, work_item, source_kind, engineer_id, native_run_id, now):
    run_id = str(uuid.uuid4())
    ticket_id = work_item if source_kind == "jira" and work_item else None
    reasons = _initial_missing_reasons(source_kind, work_item, native_run_id)
    if engineer_id:
        reasons.pop("/engineer_id", None)
    return {
        "schema_version": SCHEMA_VERSION,
        "metric_source": copy.deepcopy(METRIC_SOURCE),
        "run_id": run_id,
        "restarted_after_run_id": None,
        "updated_at": now,
        "engineer_id": engineer_id,
        "repository": str(Path(repository).resolve()),
        "ticket": {
            "id": ticket_id,
            "url": None,
            "preparation_id": None,
            "preparation_started_at": None,
            "preflight_passed_at": None,
            "preparation_elapsed_minutes": None,
        },
        "harness": {
            "name": "Shipmate",
            "version": _plugin_version(),
            "models": [],
            "native_run_ids": [native_run_id] if native_run_id else [],
        },
        "run": {"status": "running", "first_invoked_at": now, "stopped_at": None},
        "outcome": {
            "classification": None,
            "reason": "implementation-MR outcome is not yet classifiable",
            "plan_approvals_before_mr": None,
            "extra_human_help_before_mr": None,
            "human_event_coverage": "not_observed",
        },
        "mr": {"url": None, "initial_sha": None, "created_at": None},
        "timing": {
            "ticket_submitted_at": None,
            "time_to_mr_minutes": None,
            "execution_minutes": None,
            "waiting_minutes": None,
            "elapsed_to_stop_minutes": None,
            "wait_coverage": "not_observed",
            "wait_intervals": [],
        },
        "human_effort": {
            "before_mr_or_stop_active_minutes": None,
            "before_method": None,
            "after_mr_active_minutes": None,
            "after_method": None,
        },
        "plan_revisions": {"human_requested": None, "autonomous": None},
        "resources": {"generation": _resource(), "corrections": _resource()},
        "review": {
            "initial_ci": {"result": None, "sha": None, "evidence_ref": None},
            "initial_review": {"result": None, "sha": None, "evidence_ref": None},
            "revision_rounds": None,
            "additional_commits": None,
            "confirmed_defect_count": None,
            "confirmed_defects": [],
            "observed_through": None,
            "followup_status": None,
        },
        "human_events": [],
        "evidence": [],
        "measurement_notes": {
            "l3": {
                "mode": mode,
                "source_kind": source_kind,
                "source_work_item": work_item,
                "revision": 0,
                "workflow_status": "running",
                "next_action": None,
                "capture": (
                    "cooperative local snapshot; native usage is optional and not automatically complete"
                ),
            },
        },
        "missing_reasons": reasons,
    }


def _parse_utc(value, name, nullable=True):
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError("{} must be an ISO-8601 UTC timestamp".format(name))
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("{} must be an ISO-8601 UTC timestamp".format(name)) from exc
    if parsed.tzinfo is None or parsed.utcoffset() != dt.timedelta(0):
        raise ValueError("{} must use UTC".format(name))
    return parsed


def _nonempty(value, name, nullable=False):
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError("{} must be a nonempty string".format(name))
    return value


def _number(value, name, nullable=True):
    if value is None and nullable:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("{} must be a finite nonnegative number".format(name))
    if not math.isfinite(value) or value < 0:
        raise ValueError("{} must be a finite nonnegative number".format(name))
    return value


def _counter(value, name, nullable=True):
    if value is None and nullable:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("{} must be a nonnegative integer".format(name))
    return value


def _uuid(value, name, nullable=True):
    if value is None and nullable:
        return None
    _nonempty(value, name)
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise ValueError("{} must be a UUID".format(name)) from exc


def _minutes(start, end):
    if start is None or end is None:
        return None
    seconds = (end - start).total_seconds()
    if seconds < 0:
        raise ValueError("timestamp end precedes start")
    value = seconds / 60
    return int(value) if value.is_integer() else value


def _waiting_minutes(intervals, boundary_start, boundary_end):
    clipped = []
    for interval in intervals:
        start = _parse_utc(interval["start"], "wait interval start", nullable=False)
        end = _parse_utc(interval["end"], "wait interval end", nullable=False)
        if end < start:
            raise ValueError("wait interval end precedes start")
        start = max(start, boundary_start)
        end = min(end, boundary_end)
        if end > start:
            clipped.append((start, end))
    clipped.sort()
    merged = []
    for start, end in clipped:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    seconds = sum((end - start).total_seconds() for start, end in merged)
    value = seconds / 60
    return int(value) if value.is_integer() else value


def _derive(record):
    preparation_start = _parse_utc(
        record["ticket"]["preparation_started_at"], "ticket.preparation_started_at"
    )
    preflight = _parse_utc(record["ticket"]["preflight_passed_at"], "ticket.preflight_passed_at")
    record["ticket"]["preparation_elapsed_minutes"] = _minutes(preparation_start, preflight)

    first = _parse_utc(record["run"]["first_invoked_at"], "run.first_invoked_at", nullable=False)
    stopped = _parse_utc(record["run"]["stopped_at"], "run.stopped_at")
    submitted = _parse_utc(record["timing"]["ticket_submitted_at"], "timing.ticket_submitted_at")
    mr_created = _parse_utc(record["mr"]["created_at"], "mr.created_at")
    record["timing"]["time_to_mr_minutes"] = _minutes(submitted, mr_created)
    record["timing"]["elapsed_to_stop_minutes"] = _minutes(first, stopped)

    boundary_end = mr_created if mr_created is not None else stopped
    if record["timing"]["wait_coverage"] == "complete" and boundary_end is not None:
        waiting = _waiting_minutes(record["timing"]["wait_intervals"], first, boundary_end)
        elapsed = _minutes(first, boundary_end)
        record["timing"]["waiting_minutes"] = waiting
        record["timing"]["execution_minutes"] = elapsed - waiting
    else:
        record["timing"]["waiting_minutes"] = None
        record["timing"]["execution_minutes"] = None

    mode = record["measurement_notes"]["l3"]["mode"]
    if mode in {"specify", "review"}:
        record["outcome"]["classification"] = None
        record["outcome"]["reason"] = (
            "{} mode is excluded from implementation-MR classification".format(mode)
        )
    elif all(record["mr"][field] is not None for field in ("url", "initial_sha", "created_at")):
        approvals = record["outcome"]["plan_approvals_before_mr"]
        help_count = record["outcome"]["extra_human_help_before_mr"]
        coverage = record["outcome"]["human_event_coverage"]
        if help_count is not None and help_count > 0:
            record["outcome"]["classification"] = "L2"
            record["outcome"]["reason"] = "human implementation help was observed before the MR"
        elif coverage == "complete" and approvals == 1 and help_count == 0:
            record["outcome"]["classification"] = "L3"
            record["outcome"]["reason"] = (
                "exactly one plan approval, no extra human help, and complete event coverage"
            )
        else:
            record["outcome"]["classification"] = None
            record["outcome"]["reason"] = "assistance classification remains unknown"
    elif record["run"]["status"] in TERMINAL_NO_MR_STATUSES:
        record["outcome"]["classification"] = "no_mr"
        record["outcome"]["reason"] = (
            "{} before an implementation MR was observed".format(record["run"]["status"])
        )
    else:
        record["outcome"]["classification"] = None
        record["outcome"]["reason"] = "implementation-MR outcome is not yet classifiable"


def _validate_resource(resource, name):
    if not isinstance(resource, dict) or set(resource) != RESOURCE_FIELDS:
        raise ValueError("{} must contain the resource contract fields".format(name))
    for field in ("input_tokens", "cached_input_tokens", "output_tokens", "tool_calls", "model_turns"):
        _counter(resource[field], "{}.{}".format(name, field))
    if (resource["input_tokens"] is not None and resource["cached_input_tokens"] is not None
            and resource["cached_input_tokens"] > resource["input_tokens"]):
        raise ValueError("cached_input_tokens must be a subset of input_tokens")
    _number(resource["cost"], "{}.cost".format(name))
    for field in ("currency", "cost_source"):
        _nonempty(resource[field], "{}.{}".format(name, field), nullable=True)
    if resource["cost_basis"] is not None and resource["cost_basis"] not in COST_BASES:
        raise ValueError("{}.cost_basis must be billed or estimated".format(name))
    cost_fields = (resource["currency"], resource["cost_basis"], resource["cost_source"])
    if resource["cost"] is None and any(value is not None for value in cost_fields):
        raise ValueError("resource cost metadata requires cost")
    if resource["cost"] is not None and any(value is None for value in cost_fields):
        raise ValueError("resource cost, currency, basis and source must be recorded together")


def _validate_initial_observation(value, kind):
    if not isinstance(value, dict) or set(value) != {"result", "sha", "evidence_ref"}:
        raise ValueError("review.{} must contain result, sha and evidence_ref".format(kind))
    allowed = CI_RESULTS if kind == "initial_ci" else REVIEW_RESULTS
    if value["result"] is not None and value["result"] not in allowed:
        raise ValueError("unknown {} result".format(kind))
    _nonempty(value["sha"], "{}.sha".format(kind), nullable=True)
    _nonempty(value["evidence_ref"], "{}.evidence_ref".format(kind), nullable=True)
    if value["result"] is not None and (value["sha"] is None or value["evidence_ref"] is None):
        raise ValueError("observed {} requires sha and evidence_ref".format(kind))


def _validate_events(record):
    if not isinstance(record["human_events"], list):
        raise ValueError("human_events must be a list")
    event_ids = set()
    for event in record["human_events"]:
        required = {"id", "at", "phase", "actor", "action", "active_minutes", "evidence_ref"}
        if not isinstance(event, dict) or set(event) != required:
            raise ValueError("human events must contain only the contract fields")
        identifier = _nonempty(event["id"], "human event id")
        if identifier in event_ids:
            raise ValueError("duplicate human event id")
        event_ids.add(identifier)
        _parse_utc(event["at"], "human event at", nullable=False)
        for field in ("phase", "actor", "action", "evidence_ref"):
            _nonempty(event[field], "human event {}".format(field))
        _number(event["active_minutes"], "human event active_minutes")

    if record["outcome"]["human_event_coverage"] == "complete":
        allowed_phases = {"preparation", PRE_MR_PHASE, "after_mr"}
        if any(event["phase"] not in allowed_phases for event in record["human_events"]):
            raise ValueError("complete human event inventory contains unrecognized phases")
        before_mr = [event for event in record["human_events"]
                     if event["phase"] == PRE_MR_PHASE]
        unknown_actions = {event["action"] for event in before_mr
                           if event["action"] not in PRE_MR_NON_HELP_ACTIONS}
        if unknown_actions:
            raise ValueError("complete pre-MR event inventory contains unrecognized actions")
        approvals = sum(event["action"] == PLAN_APPROVAL_ACTION for event in before_mr)
        help_count = sum(event["action"] in PRE_MR_HELP_ACTIONS for event in before_mr)
        if record["outcome"]["plan_approvals_before_mr"] != approvals:
            raise ValueError("plan approval count does not match complete human event inventory")
        if record["outcome"]["extra_human_help_before_mr"] != help_count:
            raise ValueError("human help count does not match complete human event inventory")
        mr_created = _parse_utc(record["mr"]["created_at"], "mr.created_at")
        first_invoked = _parse_utc(
            record["run"]["first_invoked_at"], "run.first_invoked_at", nullable=False
        )
        for event in record["human_events"]:
            event_at = _parse_utc(event["at"], "human event at", nullable=False)
            if event["phase"] == "preparation" and event_at > first_invoked:
                raise ValueError("preparation human event occurs after first invocation")
            if event["phase"] == "after_mr" and mr_created is None:
                raise ValueError("after_mr human event requires an initial MR")
        if mr_created is not None:
            for event in record["human_events"]:
                event_at = _parse_utc(event["at"], "human event at", nullable=False)
                if event["phase"] == PRE_MR_PHASE and event_at > mr_created:
                    raise ValueError("before_mr human event occurs after initial MR creation")
                if event["phase"] == "after_mr" and event_at < mr_created:
                    raise ValueError("after_mr human event occurs before initial MR creation")

    if not isinstance(record["evidence"], list):
        raise ValueError("evidence must be a list")
    evidence_ids = set()
    for evidence in record["evidence"]:
        if not isinstance(evidence, dict) or set(evidence) != {"id", "kind", "ref", "fields"}:
            raise ValueError("evidence entries must contain only the contract fields")
        identifier = _nonempty(evidence["id"], "evidence id")
        if identifier in evidence_ids:
            raise ValueError("duplicate evidence id")
        evidence_ids.add(identifier)
        _nonempty(evidence["kind"], "evidence kind")
        _nonempty(evidence["ref"], "evidence ref")
        if not isinstance(evidence["fields"], list) or not all(
                isinstance(field, str) and field.startswith("/") for field in evidence["fields"]):
            raise ValueError("evidence fields must be JSON pointers")


def validate_record(record):
    if not isinstance(record, dict) or set(record) != TOP_LEVEL_FIELDS:
        raise ValueError("record must contain exactly the l3-run-metrics/1.0 top-level fields")
    if record["schema_version"] != SCHEMA_VERSION or record["metric_source"] != METRIC_SOURCE:
        raise ValueError("schema or metric source provenance does not match the packaged contract")
    run_id = _uuid(record["run_id"], "run_id", nullable=False)
    restarted = _uuid(record["restarted_after_run_id"], "restarted_after_run_id")
    if restarted is not None and restarted == run_id:
        raise ValueError("restarted_after_run_id must identify a distinct run")
    _parse_utc(record["updated_at"], "updated_at", nullable=False)
    _nonempty(record["engineer_id"], "engineer_id", nullable=True)
    _nonempty(record["repository"], "repository")

    l3 = record.get("measurement_notes", {}).get("l3")
    if not isinstance(l3, dict) or set(l3) != {
            "mode", "source_kind", "source_work_item", "revision", "workflow_status",
            "next_action", "capture"}:
        raise ValueError("measurement_notes.l3 must contain the recorder metadata")
    if l3["mode"] not in MODES or l3["source_kind"] not in SOURCE_KINDS:
        raise ValueError("invalid recorder mode or source kind")
    _nonempty(l3["source_work_item"], "source_work_item", nullable=True)
    _counter(l3["revision"], "revision", nullable=False)
    if l3["workflow_status"] not in WORKFLOW_STATUSES:
        raise ValueError("invalid workflow status")
    _nonempty(l3["next_action"], "next_action", nullable=True)
    _nonempty(l3["capture"], "capture")

    ticket = record["ticket"]
    if not isinstance(ticket, dict) or set(ticket) != {
            "id", "url", "preparation_id", "preparation_started_at", "preflight_passed_at",
            "preparation_elapsed_minutes"}:
        raise ValueError("ticket must contain exactly the contract fields")
    for field in ("id", "url", "preparation_id"):
        _nonempty(ticket[field], "ticket.{}".format(field), nullable=True)
    _parse_utc(ticket["preparation_started_at"], "ticket.preparation_started_at")
    _parse_utc(ticket["preflight_passed_at"], "ticket.preflight_passed_at")
    _number(ticket["preparation_elapsed_minutes"], "ticket.preparation_elapsed_minutes")

    harness = record["harness"]
    if not isinstance(harness, dict) or set(harness) != {"name", "version", "models", "native_run_ids"}:
        raise ValueError("harness must contain exactly the contract fields")
    if harness["name"] not in {"Shipmate", "L3 SDLC"}:
        raise ValueError("harness name must be Shipmate or legacy L3 SDLC")
    _nonempty(harness["version"], "harness.version")
    if not isinstance(harness["models"], list):
        raise ValueError("harness.models must be a list")
    for model in harness["models"]:
        if not isinstance(model, dict) or set(model) != {"role", "name"}:
            raise ValueError("harness models require role and name")
        _nonempty(model["role"], "model role")
        _nonempty(model["name"], "model name")
    if not isinstance(harness["native_run_ids"], list) or not all(
            isinstance(value, str) and value.strip() for value in harness["native_run_ids"]):
        raise ValueError("native_run_ids must be nonempty strings")
    if len(set(harness["native_run_ids"])) != len(harness["native_run_ids"]):
        raise ValueError("native_run_ids must not contain duplicates")

    run = record["run"]
    if not isinstance(run, dict) or set(run) != {"status", "first_invoked_at", "stopped_at"}:
        raise ValueError("run must contain exactly the contract fields")
    if run["status"] not in RUN_STATUSES:
        raise ValueError("unknown run status")
    _parse_utc(run["first_invoked_at"], "run.first_invoked_at", nullable=False)
    _parse_utc(run["stopped_at"], "run.stopped_at")

    outcome = record["outcome"]
    if not isinstance(outcome, dict) or set(outcome) != {
            "classification", "reason", "plan_approvals_before_mr",
            "extra_human_help_before_mr", "human_event_coverage"}:
        raise ValueError("outcome must contain exactly the contract fields")
    if outcome["classification"] not in {None, "L3", "L2", "no_mr"}:
        raise ValueError("invalid outcome classification")
    _nonempty(outcome["reason"], "outcome.reason")
    _counter(outcome["plan_approvals_before_mr"], "plan approvals")
    _counter(outcome["extra_human_help_before_mr"], "extra human help")
    if outcome["human_event_coverage"] not in HUMAN_COVERAGE:
        raise ValueError("invalid human_event_coverage")

    mr = record["mr"]
    if not isinstance(mr, dict) or set(mr) != {"url", "initial_sha", "created_at"}:
        raise ValueError("mr must contain exactly the contract fields")
    _nonempty(mr["url"], "mr.url", nullable=True)
    _nonempty(mr["initial_sha"], "mr.initial_sha", nullable=True)
    _parse_utc(mr["created_at"], "mr.created_at")
    observed_mr_fields = sum(mr[field] is not None for field in ("url", "initial_sha", "created_at"))
    if observed_mr_fields not in (0, 3):
        raise ValueError("initial MR URL, SHA and creation time must be recorded together")
    if run["status"] == "mr_created" and observed_mr_fields != 3:
        raise ValueError("mr_created status requires complete initial MR evidence")

    timing = record["timing"]
    if not isinstance(timing, dict) or set(timing) != {
            "ticket_submitted_at", "time_to_mr_minutes", "execution_minutes", "waiting_minutes",
            "elapsed_to_stop_minutes", "wait_coverage", "wait_intervals"}:
        raise ValueError("timing must contain exactly the contract fields")
    _parse_utc(timing["ticket_submitted_at"], "timing.ticket_submitted_at")
    for field in ("time_to_mr_minutes", "execution_minutes", "waiting_minutes", "elapsed_to_stop_minutes"):
        _number(timing[field], "timing.{}".format(field))
    if timing["wait_coverage"] not in WAIT_COVERAGE or not isinstance(timing["wait_intervals"], list):
        raise ValueError("invalid wait coverage or intervals")
    for interval in timing["wait_intervals"]:
        if not isinstance(interval, dict) or set(interval) != {"start", "end", "reason", "evidence_ref"}:
            raise ValueError("wait intervals must contain only the contract fields")
        start = _parse_utc(interval["start"], "wait interval start", nullable=False)
        end = _parse_utc(interval["end"], "wait interval end", nullable=False)
        if end < start:
            raise ValueError("wait interval end precedes start")
        _nonempty(interval["reason"], "wait interval reason")
        _nonempty(interval["evidence_ref"], "wait interval evidence_ref")

    effort = record["human_effort"]
    if not isinstance(effort, dict) or set(effort) != {
            "before_mr_or_stop_active_minutes", "before_method",
            "after_mr_active_minutes", "after_method"}:
        raise ValueError("human_effort must contain exactly the contract fields")
    for minutes, method in (("before_mr_or_stop_active_minutes", "before_method"),
                            ("after_mr_active_minutes", "after_method")):
        _number(effort[minutes], "human_effort.{}".format(minutes))
        if effort[method] is not None and effort[method] not in EFFORT_METHODS:
            raise ValueError("invalid human effort method")
        if (effort[minutes] is None) != (effort[method] is None):
            raise ValueError("human effort minutes and method must be recorded together")

    revisions = record["plan_revisions"]
    if not isinstance(revisions, dict) or set(revisions) != {"human_requested", "autonomous"}:
        raise ValueError("plan_revisions must contain exactly the contract fields")
    _counter(revisions["human_requested"], "human-requested plan revisions")
    _counter(revisions["autonomous"], "autonomous plan revisions")
    if not isinstance(record["resources"], dict) or set(record["resources"]) != {"generation", "corrections"}:
        raise ValueError("resources must contain generation and corrections")
    _validate_resource(record["resources"]["generation"], "resources.generation")
    _validate_resource(record["resources"]["corrections"], "resources.corrections")

    review = record["review"]
    if not isinstance(review, dict) or set(review) != {
            "initial_ci", "initial_review", "revision_rounds", "additional_commits",
            "confirmed_defect_count", "confirmed_defects", "observed_through", "followup_status"}:
        raise ValueError("review must contain exactly the contract fields")
    _validate_initial_observation(review["initial_ci"], "initial_ci")
    _validate_initial_observation(review["initial_review"], "initial_review")
    for kind in ("initial_ci", "initial_review"):
        observed_sha = review[kind]["sha"]
        if observed_sha is not None and observed_sha != mr["initial_sha"]:
            raise ValueError("review.{} SHA must match mr.initial_sha".format(kind))
    for field in ("revision_rounds", "additional_commits", "confirmed_defect_count"):
        _counter(review[field], "review.{}".format(field))
    if not isinstance(review["confirmed_defects"], list):
        raise ValueError("confirmed_defects must be a list")
    defect_ids = set()
    for defect in review["confirmed_defects"]:
        required = {"id", "severity", "found_stage", "summary", "evidence_ref"}
        if not isinstance(defect, dict) or set(defect) != required:
            raise ValueError("confirmed defects must contain only the contract fields")
        for field in required:
            _nonempty(defect[field], "confirmed defect {}".format(field))
        if defect["severity"] not in DEFECT_SEVERITIES:
            raise ValueError("invalid confirmed defect severity")
        if defect["found_stage"] not in DEFECT_STAGES:
            raise ValueError("invalid confirmed defect found_stage")
        if defect["id"] in defect_ids:
            raise ValueError("duplicate confirmed defect id")
        defect_ids.add(defect["id"])
    if review["confirmed_defect_count"] is not None and (
            review["confirmed_defect_count"] != len(review["confirmed_defects"])):
        raise ValueError("confirmed_defect_count must equal confirmed_defects length")
    _parse_utc(review["observed_through"], "review.observed_through")
    if review["followup_status"] is not None and review["followup_status"] not in FOLLOWUP_STATUSES:
        raise ValueError("invalid review followup_status")
    _validate_events(record)

    reasons = record["missing_reasons"]
    if not isinstance(reasons, dict):
        raise ValueError("missing_reasons must be a JSON-pointer map")
    for pointer, reason in reasons.items():
        if not isinstance(pointer, str) or not pointer.startswith("/"):
            raise ValueError("missing_reasons keys must be JSON pointers")
        _nonempty(reason, "missing reason")
        try:
            _get_pointer(record, pointer)
        except (IndexError, KeyError, TypeError, ValueError) as exc:
            raise ValueError("missing_reasons key does not identify a record field: {}".format(
                pointer)) from exc
    expected = copy.deepcopy(record)
    expected["outcome"]["classification"] = None
    _derive(expected)
    for pointer in DERIVED_POINTERS:
        if _get_pointer(record, pointer) != _get_pointer(expected, pointer):
            raise ValueError("derived field does not match observations: {}".format(pointer))
    return record


def _sync_missing_reasons(record):
    reasons = record["missing_reasons"]
    l3 = record["measurement_notes"]["l3"]
    defaults = _initial_missing_reasons(
        l3["source_kind"], l3["source_work_item"],
        record["harness"]["native_run_ids"][0] if record["harness"]["native_run_ids"] else None,
    )
    managed = set(defaults) | {
        "/ticket/id", "/harness/models", "/harness/native_run_ids",
        "/measurement_notes/l3/next_action",
    }
    for pointer in managed:
        try:
            value = _get_pointer(record, pointer)
        except (KeyError, TypeError, ValueError):
            continue
        missing = value is None or (pointer in {"/harness/models", "/harness/native_run_ids"}
                                    and value == [])
        if missing:
            reasons.setdefault(pointer, defaults.get(pointer, "value was not observed"))
        else:
            reasons.pop(pointer, None)
    active_pointers = set()
    if isinstance(record["human_events"], list):
        for index, event in enumerate(record["human_events"]):
            if not isinstance(event, dict) or "active_minutes" not in event:
                continue
            pointer = "/human_events/{}/active_minutes".format(index)
            active_pointers.add(pointer)
            if event["active_minutes"] is None:
                reasons.setdefault(pointer, "active human time was not measured or reported")
            else:
                reasons.pop(pointer, None)
    for pointer in list(reasons):
        if pointer.startswith("/human_events/") and pointer.endswith("/active_minutes"):
            if pointer not in active_pointers:
                reasons.pop(pointer)
    if record["outcome"]["classification"] is None:
        reasons["/outcome/classification"] = record["outcome"]["reason"]
    if record["run"]["status"] in TERMINAL_NO_MR_STATUSES and record["mr"]["url"] is None:
        message = "{} before an implementation MR".format(record["run"]["status"])
        for pointer in ("/mr/url", "/mr/initial_sha", "/mr/created_at"):
            reasons[pointer] = message


def _tokens(pointer):
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ValueError("patch paths must be JSON pointers")
    return [part.replace("~1", "/").replace("~0", "~") for part in pointer[1:].split("/")]


def _get_pointer(data, pointer):
    current = data
    for token in _tokens(pointer):
        if isinstance(current, list):
            if not token.isdigit():
                raise ValueError("JSON pointer list token must be an index")
            current = current[int(token)]
        else:
            current = current[token]
    return current


def _set_pointer(data, pointer, value):
    tokens = _tokens(pointer)
    if tokens[0] == "missing_reasons" and len(tokens) > 2:
        data["missing_reasons"]["/" + "/".join(tokens[1:])] = value
        return
    current = data
    for token in tokens[:-1]:
        if token not in current or not isinstance(current[token], dict):
            raise ValueError("patch path does not exist: {}".format(pointer))
        current = current[token]
    if tokens[-1] not in current:
        raise ValueError("patch path does not exist: {}".format(pointer))
    current[tokens[-1]] = value


def _pointer_allowed(pointer):
    if pointer in DERIVED_POINTERS or pointer in READ_ONLY_POINTERS:
        return False
    if pointer in ALLOWED_EXACT_POINTERS:
        return True
    parts = _tokens(pointer)
    if len(parts) == 3 and parts[:2] in (["resources", "generation"], ["resources", "corrections"]):
        return parts[2] in RESOURCE_FIELDS
    if parts and parts[0] == "missing_reasons" and len(parts) > 1:
        return True
    return False


def _check_initial_immutability(old, new):
    for field in ("url", "initial_sha", "created_at"):
        previous = old["mr"][field]
        if previous is not None and new["mr"][field] != previous:
            raise ValueError("initial MR {} is immutable once observed".format(field))
    for kind in ("initial_ci", "initial_review"):
        previous = old["review"][kind]
        candidate = new["review"][kind]
        if previous["sha"] is not None and candidate["sha"] != previous["sha"]:
            raise ValueError("{} SHA is immutable once observed".format(kind))
        pending_results = (None, "pending") if kind == "initial_ci" else (None, "not_yet_reviewed")
        if previous["result"] not in pending_results and candidate != previous:
            raise ValueError("{} is immutable once conclusive".format(kind))


def _atomic_write(path, record):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    content = json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=str(path.parent),
                prefix=".{}-".format(path.name), delete=False) as handle:
            temp_path = Path(handle.name)
            os.fchmod(handle.fileno(), 0o600)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(temp_path), str(path))
        try:
            directory_fd = os.open(str(path.parent), os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            pass
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def start_record(mode, repository, work_item=None, source_kind="jira", engineer_id=None,
                 native_run_id=None, output_dir=DEFAULT_OUTPUT_DIR, now=None):
    if mode not in MODES:
        raise ValueError("mode must be run, specify or review")
    if source_kind not in SOURCE_KINDS:
        raise ValueError("source_kind must be jira, markdown, chat or mr")
    _nonempty(work_item, "work_item", nullable=True)
    _nonempty(engineer_id, "engineer_id", nullable=True)
    _nonempty(native_run_id, "native_run_id", nullable=True)
    now = now or _utc_now()
    _parse_utc(now, "now", nullable=False)
    repository = Path(repository).expanduser().resolve()
    output_dir = Path(output_dir).expanduser().resolve()
    try:
        output_dir.relative_to(repository)
    except ValueError:
        pass
    else:
        raise ValueError("run metrics output directory must be outside the target repository")
    record = _new_record(
        mode, repository, work_item, source_kind, engineer_id, native_run_id, now
    )
    _derive(record)
    validate_record(record)
    path = output_dir / "{}.json".format(record["run_id"])
    if path.exists():
        raise FileExistsError("run metrics path already exists: {}".format(path))
    _atomic_write(path, record)
    return path


def _open_parent(path):
    path = Path(path).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    parent = path.parent.resolve(strict=True)
    if path.name in {"", ".", ".."}:
        raise ValueError("run metrics path must name a file")
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
    return parent, path.name, os.open(str(parent), flags)


def _read_record_at(parent_fd, name):
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    record_fd = os.open(name, flags, dir_fd=parent_fd)
    try:
        file_stat = os.fstat(record_fd)
        if not stat.S_ISREG(file_stat.st_mode):
            raise ValueError("run metrics snapshot must be a regular file")
        with os.fdopen(record_fd, mode="r", encoding="utf-8") as handle:
            record_fd = None
            record = json.load(handle)
        return validate_record(record), file_stat
    finally:
        if record_fd is not None:
            os.close(record_fd)


def _atomic_write_at(parent_fd, name, record, expected_stat):
    current_stat = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    if (not stat.S_ISREG(current_stat.st_mode)
            or (current_stat.st_dev, current_stat.st_ino) !=
            (expected_stat.st_dev, expected_stat.st_ino)):
        raise MetricsBusy("run metrics path changed during update; workflow may continue")
    content = json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    temp_name = ".{}-{}.tmp".format(name, uuid.uuid4())
    flags = (os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
             | getattr(os, "O_CLOEXEC", 0))
    temp_fd = os.open(temp_name, flags, 0o600, dir_fd=parent_fd)
    try:
        with os.fdopen(temp_fd, mode="w", encoding="utf-8") as handle:
            temp_fd = None
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
        os.fsync(parent_fd)
    finally:
        if temp_fd is not None:
            os.close(temp_fd)
        try:
            os.unlink(temp_name, dir_fd=parent_fd)
        except FileNotFoundError:
            pass


def load_record(path):
    _parent, name, parent_fd = _open_parent(path)
    try:
        return _read_record_at(parent_fd, name)[0]
    finally:
        os.close(parent_fd)


def _lock_path(path):
    return path.with_name(".{}.lock".format(path.name))


def update_record(path, patch, now=None):
    if not isinstance(patch, dict) or set(patch) != {"expected_revision", "set"}:
        raise ValueError("patch must contain exactly expected_revision and set")
    expected = patch["expected_revision"]
    _counter(expected, "expected_revision", nullable=False)
    if not isinstance(patch["set"], dict) or not patch["set"]:
        raise ValueError("patch set must be a nonempty JSON-pointer map")
    _parent, name, parent_fd = _open_parent(path)
    lock_name = ".{}.lock".format(name)
    lock_flags = os.O_RDWR | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        try:
            lock_fd = os.open(
                lock_name, lock_flags | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=parent_fd
            )
        except FileExistsError:
            lock_fd = os.open(lock_name, lock_flags, dir_fd=parent_fd)
    except BaseException:
        os.close(parent_fd)
        raise
    lock_acquired = False
    try:
        if not stat.S_ISREG(os.fstat(lock_fd).st_mode):
            raise ValueError("run metrics lock must be a regular file")
        os.fchmod(lock_fd, 0o600)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            lock_acquired = True
        except BlockingIOError as exc:
            raise MetricsBusy("run metrics file is busy; workflow may continue") from exc
        current, current_stat = _read_record_at(parent_fd, name)
        revision = current["measurement_notes"]["l3"]["revision"]
        if revision != expected:
            raise RevisionConflict(
                "stale revision {}; current revision is {}".format(expected, revision)
            )
        candidate = copy.deepcopy(current)
        for pointer, value in patch["set"].items():
            if not _pointer_allowed(pointer):
                raise ValueError("patch path is read-only or unsupported: {}".format(pointer))
            _set_pointer(candidate, pointer, value)
        _check_initial_immutability(current, candidate)
        candidate["measurement_notes"]["l3"]["revision"] = revision + 1
        candidate["updated_at"] = now or _utc_now()
        _derive(candidate)
        _sync_missing_reasons(candidate)
        validate_record(candidate)
        _atomic_write_at(parent_fd, name, candidate, current_stat)
        return candidate
    finally:
        try:
            if lock_acquired:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(lock_fd)
            os.close(parent_fd)


def checkpoint_record(path, status, next_action=None, mr_url=None, mr_sha=None,
                      mr_created_at=None, end_status=None, now=None):
    """Save a workflow milestone using the recorder's existing atomic update contract."""
    if status not in WORKFLOW_STATUSES:
        raise ValueError("unknown workflow status")
    if end_status is not None and (status != "stopped" or end_status not in {
            "failed", "cancelled", "interrupted"}):
        raise ValueError("end_status requires stopped and failed, cancelled or interrupted")
    supplied = (mr_url, mr_sha, mr_created_at)
    if any(value is not None for value in supplied) and not all(supplied):
        raise ValueError("supply all three initial MR fields together")
    now = now or _utc_now()
    instant = _parse_utc(now, "now", nullable=False)
    current = load_record(path)
    notes = current["measurement_notes"]["l3"]
    has_mr = bool(mr_url or current["mr"]["url"])
    if status == "completed" and notes["mode"] == "run" and not has_mr:
        raise ValueError("completed run requires the initial MR; otherwise use stopped")
    values = {
        "/measurement_notes/l3/workflow_status": status,
        "/measurement_notes/l3/next_action": next_action,
        "/run/status": "mr_created" if has_mr else "running",
        "/run/stopped_at": None,
    }
    if mr_url:
        if _parse_utc(mr_created_at, "mr_created_at", nullable=False) > instant:
            raise ValueError("initial MR creation cannot be in the future")
        values.update({"/mr/url": mr_url, "/mr/initial_sha": mr_sha,
                       "/mr/created_at": mr_created_at})
    if status in {"completed", "stopped"}:
        values["/run/stopped_at"] = (
            current["run"]["stopped_at"] if notes["workflow_status"] == status
            and current["run"]["stopped_at"] else now
        )
    if status == "stopped":
        values["/run/status"] = end_status or (
            current["run"]["status"] if notes["workflow_status"] == "stopped"
            and current["run"]["status"] in {"failed", "cancelled", "interrupted"}
            else "interrupted"
        )
    return update_record(path, {"expected_revision": notes["revision"], "set": values}, now=now)


# Explicit columns keep empty CSV exports usable and field meanings stable.
EXPORT_PATHS = {
    "run_id": "/run_id", "mode": "/measurement_notes/l3/mode",
    "restarted_after_run_id": "/restarted_after_run_id",
    "source_kind": "/measurement_notes/l3/source_kind",
    "work_item": "/measurement_notes/l3/source_work_item", "repository": "/repository",
    "plugin_version": "/harness/version", "engineer_id": "/engineer_id",
    "workflow_status": "/measurement_notes/l3/workflow_status",
    "lifecycle_status": "/run/status", "started_at": "/run/first_invoked_at",
    "stopped_at": "/run/stopped_at", "mr_url": "/mr/url", "mr_created_at": "/mr/created_at",
    "time_to_mr_minutes": "/timing/time_to_mr_minutes",
    "elapsed_to_stop_minutes": "/timing/elapsed_to_stop_minutes",
    "execution_minutes": "/timing/execution_minutes", "waiting_minutes": "/timing/waiting_minutes",
    "wait_coverage": "/timing/wait_coverage",
    "human_minutes_before_mr": "/human_effort/before_mr_or_stop_active_minutes",
    "human_minutes_after_mr": "/human_effort/after_mr_active_minutes",
    "human_before_method": "/human_effort/before_method",
    "human_after_method": "/human_effort/after_method",
    "human_requested_plan_revisions": "/plan_revisions/human_requested",
    "autonomous_plan_revisions": "/plan_revisions/autonomous",
    "initial_ci_result": "/review/initial_ci/result",
    "initial_human_review_result": "/review/initial_review/result",
    "revision_rounds": "/review/revision_rounds", "additional_commits": "/review/additional_commits",
    "confirmed_defect_count": "/review/confirmed_defect_count",
    "observed_through": "/review/observed_through", "followup_status": "/review/followup_status",
    "assistance_classification": "/outcome/classification",
    "human_event_coverage": "/outcome/human_event_coverage",
}
for _stage in ("generation", "corrections"):
    for _field in sorted(RESOURCE_FIELDS):
        EXPORT_PATHS[_stage + "_" + _field] = "/resources/" + _stage + "/" + _field
EXPORT_PATHS["missing_reasons"] = "/missing_reasons"
EXPORT_COLUMNS = list(EXPORT_PATHS) + ["invocation_to_mr_minutes"]


def export_rows(input_dir=DEFAULT_OUTPUT_DIR, mode=None, work_item=None, since=None, before=None):
    """Collect validated snapshots without inferring missing values or success rates."""
    if mode is not None and mode not in MODES:
        raise ValueError("unknown mode")
    start = _parse_utc(since, "since")
    end = _parse_utc(before, "before")
    if start is not None and end is not None and start >= end:
        raise ValueError("since must precede before")
    directory = Path(input_dir).expanduser()
    if not directory.is_dir():
        raise FileNotFoundError("metrics directory not found: {}".format(directory))
    rows, seen = [], set()
    for path in sorted(directory.iterdir()):
        if path.suffix != ".json":
            continue
        try:
            record = load_record(path)
        except ValueError as exc:
            raise ValueError("{}: {}".format(path, exc)) from exc
        if record["run_id"] in seen:
            raise ValueError("duplicate run_id {} in {}".format(record["run_id"], path))
        seen.add(record["run_id"])
        notes = record["measurement_notes"]["l3"]
        item = notes["source_work_item"] or record["ticket"]["id"]
        invoked = _parse_utc(record["run"]["first_invoked_at"], "first_invoked_at", nullable=False)
        if ((mode is not None and notes["mode"] != mode)
                or (work_item is not None and item != work_item)
                or (start is not None and invoked < start)
                or (end is not None and invoked >= end)):
            continue
        row = {}
        for column, pointer in EXPORT_PATHS.items():
            value = record
            for part in pointer.strip("/").split("/"):
                value = value[part]
            row[column] = value
        row["work_item"] = item
        created = _parse_utc(record["mr"]["created_at"], "mr_created_at")
        row["invocation_to_mr_minutes"] = (
            _minutes(invoked, created) if created is not None and created >= invoked else None
        )
        row["missing_reasons"] = dict(row["missing_reasons"])
        if row["invocation_to_mr_minutes"] is None:
            row["missing_reasons"]["/export/invocation_to_mr_minutes"] = (
                "MR predates this invocation" if created else "first MR not recorded"
            )
        rows.append(row)
    return sorted(rows, key=lambda row: (row["started_at"], row["run_id"]))


def _csv_value(value):
    if isinstance(value, (dict, list)):
        value = json.dumps(value, sort_keys=True, ensure_ascii=False)
    if isinstance(value, str) and (value.lstrip().startswith(("=", "+", "-", "@"))
                                   or value.startswith(("\t", "\r", "\n"))):
        return "'" + value
    return value


def _display_minutes(value):
    return "unknown" if value is None else "{} min".format(value)


def _resource_card(resource):
    tokens = "input {} / cached {} / output {}".format(
        resource["input_tokens"] if resource["input_tokens"] is not None else "unknown",
        resource["cached_input_tokens"] if resource["cached_input_tokens"] is not None
        else "unknown",
        resource["output_tokens"] if resource["output_tokens"] is not None else "unknown",
    )
    cost = "unknown"
    if resource["cost"] is not None:
        cost = "{} {} ({})".format(
            resource["cost"], resource["currency"], resource["cost_basis"]
        )
    observed = [resource[key] for key in (
        "input_tokens", "cached_input_tokens", "output_tokens", "tool_calls", "model_turns"
    )]
    coverage = ("not observed" if all(value is None for value in observed)
                else "complete" if all(value is not None for value in observed)
                else "partial")
    return tokens, cost, coverage


def render_card(record, path):
    classification = record["outcome"]["classification"]
    mode = record["measurement_notes"]["l3"]["mode"]
    assistance = classification or ("not applicable" if mode != "run" else "unknown")
    timing = record["timing"]
    effort = record["human_effort"]
    generation = record["resources"]["generation"]
    corrections = record["resources"]["corrections"]
    generation_tokens, generation_cost, generation_coverage = _resource_card(generation)
    correction_tokens, correction_cost, correction_coverage = _resource_card(corrections)
    ci_result = record["review"]["initial_ci"]["result"] or "unknown"
    review_result = record["review"]["initial_review"]["result"] or "unknown"
    workflow_status = record["measurement_notes"]["l3"]["workflow_status"]
    status_label = ("{} (run {})".format(workflow_status, record["run"]["status"])
                    if mode == "run" else "{} ({} mode)".format(workflow_status, mode))
    return "\n".join([
        "{} · assistance {}: {}".format(status_label, assistance, record["outcome"]["reason"]),
        "First MR: {} · execution {} · waiting {} ({})".format(
            _display_minutes(timing["time_to_mr_minutes"]),
            _display_minutes(timing["execution_minutes"]),
            _display_minutes(timing["waiting_minutes"]), timing["wait_coverage"]),
        "Human effort: before {} · after {}".format(
            _display_minutes(effort["before_mr_or_stop_active_minutes"]),
            _display_minutes(effort["after_mr_active_minutes"])),
        "Generation: {} · cost {} | Corrections: {} · cost {}".format(
            generation_tokens, generation_cost, correction_tokens, correction_cost),
        "Coverage: usage gen {} / corr {} · human events {} · CI {} · review {}".format(
            generation_coverage, correction_coverage,
            record["outcome"]["human_event_coverage"], ci_result, review_result),
        "Metrics: {}".format(Path(path).resolve()),
    ])


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    start = subparsers.add_parser("start", help="create a private per-run snapshot")
    start.add_argument("--mode", choices=sorted(MODES), required=True)
    start.add_argument("--repository", type=Path, required=True)
    start.add_argument("--work-item")
    start.add_argument("--source-kind", choices=sorted(SOURCE_KINDS), required=True)
    start.add_argument("--engineer-id")
    start.add_argument("--native-run-id")
    start.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    update = subparsers.add_parser("update", help="atomically patch an existing snapshot")
    update.add_argument("path", type=Path)
    update.add_argument("--patch-file", type=Path, required=True)
    checkpoint = subparsers.add_parser("checkpoint", help="save a workflow milestone")
    checkpoint.add_argument("path", type=Path)
    checkpoint.add_argument("--status", choices=sorted(WORKFLOW_STATUSES), required=True)
    checkpoint.add_argument("--next-action")
    checkpoint.add_argument("--mr-url")
    checkpoint.add_argument("--mr-sha")
    checkpoint.add_argument("--mr-created-at")
    checkpoint.add_argument("--end-status", choices=["failed", "cancelled", "interrupted"])
    export = subparsers.add_parser("export", help="collect one row per run to stdout")
    export.add_argument("--input-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    export.add_argument("--format", choices=["csv", "json"], default="csv")
    export.add_argument("--mode", choices=sorted(MODES))
    export.add_argument("--work-item")
    export.add_argument("--since", help="inclusive UTC invocation timestamp")
    export.add_argument("--before", help="exclusive UTC invocation timestamp")
    show = subparsers.add_parser("show", help="print the complete JSON snapshot")
    show.add_argument("path", type=Path)
    summary = subparsers.add_parser("summary", help="print a concise run card")
    summary.add_argument("path", type=Path)
    validate = subparsers.add_parser("validate", help="validate one snapshot")
    validate.add_argument("path", type=Path)
    return parser


def run(argv=None):
    args = _parser().parse_args(argv)
    if args.command == "start":
        path = start_record(
            args.mode, args.repository, args.work_item, args.source_kind,
            args.engineer_id, args.native_run_id, args.output_dir,
        )
        print(path)
    elif args.command == "update":
        patch = json.loads(args.patch_file.read_text(encoding="utf-8"))
        update_record(args.path, patch)
        print(args.path.expanduser().resolve())
    elif args.command == "checkpoint":
        checkpoint_record(args.path, args.status, args.next_action, args.mr_url,
                          args.mr_sha, args.mr_created_at, args.end_status)
        print(args.path.expanduser().resolve())
    elif args.command == "export":
        rows = export_rows(args.input_dir, args.mode, args.work_item, args.since, args.before)
        if args.format == "json":
            print(json.dumps(rows, indent=2, ensure_ascii=False))
        else:
            writer = csv.DictWriter(sys.stdout, fieldnames=EXPORT_COLUMNS)
            writer.writeheader()
            writer.writerows({key: _csv_value(value) for key, value in row.items()} for row in rows)
    elif args.command == "show":
        print(json.dumps(load_record(args.path), indent=2, sort_keys=True, ensure_ascii=False))
    elif args.command == "summary":
        record = load_record(args.path)
        print(render_card(record, args.path))
    else:
        record = load_record(args.path)
        print("valid {} revision {}".format(
            record["run_id"], record["measurement_notes"]["l3"]["revision"]
        ))
    return 0


def main():
    try:
        return run()
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print("run_metrics: {}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
