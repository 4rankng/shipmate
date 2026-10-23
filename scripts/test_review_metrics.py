import copy
import unittest
from review_metrics import summarize


class ReviewMetricsTests(unittest.TestCase):
    def test_deduplication_and_missing_telemetry(self):
        first = {"review_run_id": "1", "phase": "plan", "total_tokens": 20,
                 "findings": [{"issue_id": "A", "disposition": "accepted"}]}
        second = {"review_run_id": "2", "phase": "plan", "duration_seconds": 2,
                  "findings": [{"issue_id": "A", "disposition": "accepted"},
                               {"issue_id": "B", "disposition": "rejected"},
                               {"issue_id": "C", "disposition": "unverified"}]}
        result = summarize({"reviews": [first, copy.deepcopy(first), second]})
        self.assertEqual(result["review_invocations"], 2)
        self.assertEqual(result["accepted_reports"], 2)
        self.assertEqual(result["unique_accepted_issues"], 1)
        self.assertEqual(result["duplicate_accepted_reports"], 1)
        self.assertEqual(result["rejected_reports"], 1)
        self.assertEqual(result["unverified_reports"], 1)
        self.assertEqual(result["total_tokens"], {"known_sum": 20, "known_runs": 1, "total_runs": 2})

    def test_unknown_is_not_zero(self):
        result = summarize({"reviews": [{"review_run_id": "1", "phase": "spec"}]})
        self.assertIsNone(result["total_tokens"]["known_sum"])
        self.assertEqual(result["total_tokens"]["known_runs"], 0)

    def test_missing_or_null_findings_keep_finding_aggregates_unknown(self):
        result = summarize({"reviews": [
            {"review_run_id": "known-empty", "phase": "spec", "findings": []},
            {"review_run_id": "omitted", "phase": "plan"},
            {"review_run_id": "null", "phase": "review", "findings": None},
        ]})
        self.assertEqual(result["finding_inventory_coverage"],
                         {"known_runs": 1, "total_runs": 3})
        self.assertIsNone(result["accepted_reports"])
        self.assertIsNone(result["rejected_reports"])
        self.assertIsNone(result["unverified_reports"])
        self.assertIsNone(result["unique_accepted_issues"])
        self.assertIsNone(result["duplicate_accepted_reports"])
        self.assertIsNone(result["review_cost_per_unique_accepted_issue"])

    def test_explicit_empty_findings_are_known_zero(self):
        result = summarize({"reviews": [
            {"review_run_id": "1", "phase": "spec", "findings": []},
            {"review_run_id": "2", "phase": "plan", "findings": []},
        ]})
        self.assertEqual(result["finding_inventory_coverage"],
                         {"known_runs": 2, "total_runs": 2})
        self.assertEqual(result["accepted_reports"], 0)
        self.assertEqual(result["rejected_reports"], 0)
        self.assertEqual(result["unique_accepted_issues"], 0)
        self.assertEqual(result["duplicate_accepted_reports"], 0)

    def test_accepted_issue_deduplication_is_scoped_to_workflow_or_legacy_cohort(self):
        result = summarize({"reviews": [
            {"review_run_id": "first", "phase": "spec", "workflow_run_id": "workflow-1",
             "findings": [{"issue_id": "same", "disposition": "accepted"}]},
            {"review_run_id": "second", "phase": "plan", "workflow_run_id": "workflow-1",
             "findings": [{"issue_id": "same", "disposition": "accepted"}]},
            {"review_run_id": "third", "phase": "review", "workflow_run_id": "workflow-2",
             "findings": [{"issue_id": "same", "disposition": "accepted"}]},
            {"review_run_id": "legacy-first", "phase": "spec",
             "findings": [{"issue_id": "same", "disposition": "accepted"}]},
            {"review_run_id": "legacy-second", "phase": "plan", "workflow_run_id": None,
             "findings": [{"issue_id": "same", "disposition": "accepted"}]},
        ]})
        self.assertEqual(result["accepted_reports"], 5)
        self.assertEqual(result["unique_accepted_issues"], 3)
        self.assertEqual(result["duplicate_accepted_reports"], 2)

    def test_conflicting_runs_are_rejected(self):
        with self.assertRaises(ValueError):
            summarize({"reviews": [{"review_run_id": "1", "phase": "spec"},
                                   {"review_run_id": "1", "phase": "plan"}]})

    def test_invalid_measurements_are_rejected(self):
        for key, value in (("total_tokens", -1), ("total_tokens", 1.5),
                           ("duration_seconds", True), ("duration_seconds", float("nan"))):
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                summarize({"reviews": [{"review_run_id": "1", "phase": "spec", key: value}]})

    def test_workflow_events_are_deduplicated_and_counted(self):
        workflow = {
            "workflow_run_id": "workflow-1", "outcome": "completed",
            "events": [
                {"event_id": "stop-1", "type": "stop", "reason_code": "jira-unavailable",
                 "classification": "degradable", "avoidable": True},
                {"event_id": "question-1", "type": "settled-question", "question_id": "scope"},
                {"event_id": "question-2", "type": "settled-question", "question_id": "scope"},
                {"event_id": "clarification", "type": "clarification-resolved",
                 "clarification_to_resume_seconds": None},
                {"event_id": "restart", "type": "restart"},
                {"event_id": "discard", "type": "discarded-work"},
                {"event_id": "scope", "type": "scope-reduction", "actor": "user"},
                {"event_id": "correction", "type": "material-post-pass-correction"},
                {"event_id": "intervention", "type": "user-intervention"},
                {"event_id": "overturn", "type": "user-overturn", "actor": "user"},
            ],
        }
        result = summarize({"reviews": [], "workflow_runs": [workflow, copy.deepcopy(workflow)]})
        self.assertEqual(result["workflow_runs"], 1)
        self.assertEqual(result["outcomes"], {"completed": 1})
        self.assertEqual(result["adjudicated_avoidable_stops"], 1)
        self.assertEqual(result["repeated_settled_questions"], 1)
        self.assertEqual(result["clarification_to_resume_seconds"],
                         {"known_sum": None, "known_events": 0, "total_events": 1})
        self.assertEqual(result["restarts"], 1)
        self.assertEqual(result["discarded_work"], 1)
        self.assertEqual(result["user_scope_reductions"], 1)
        self.assertEqual(result["scope_reductions"], 1)
        self.assertEqual(result["user_overturns"], 1)
        self.assertEqual(result["stops_by_reason"], {"jira-unavailable": 1})
        self.assertEqual(result["avoidable_stop_coverage"],
                         {"known_stops": 1, "total_stops": 1})
        self.assertEqual(result["material_post_pass_corrections"], 1)
        self.assertEqual(result["user_interventions"], 1)

    def test_workflow_conflicts_and_invalid_events_are_rejected(self):
        base = {"workflow_run_id": "workflow-1", "outcome": "stopped",
                "events": [{"event_id": "stop", "type": "stop", "reason_code": "timeout",
                            "classification": "hard"}]}
        with self.assertRaises(ValueError):
            summarize({"reviews": [], "workflow_runs": [base, {**base, "outcome": "completed"}]})
        duplicate_event = {"event_id": "restart", "type": "restart"}
        self.assertEqual(summarize({"reviews": [], "workflow_runs": [{"workflow_run_id": "dedupe",
                                                                          "outcome": "running",
                                                                          "events": [duplicate_event, copy.deepcopy(duplicate_event)]}]}),
                         {"review_invocations": 0, "invocations_by_phase": {}, "accepted_reports": 0,
                          "rejected_reports": 0, "unverified_reports": 0, "unique_accepted_issues": 0,
                          "duplicate_accepted_reports": 0,
                          "finding_inventory_coverage": {"known_runs": 0, "total_runs": 0},
                          "duration_seconds": {"known_sum": None, "known_runs": 0, "total_runs": 0},
                          "total_tokens": {"known_sum": None, "known_runs": 0, "total_runs": 0},
                          "review_cost_per_unique_accepted_issue": None,
                          "workflow_telemetry_known": True,
                          "workflow_runs": 1, "outcomes": {"running": 1},
                          "workflow_event_coverage": {"known_runs": 1, "total_runs": 1},
                          "workflow_events": {"restart": 1}, "stops_by_classification": {},
                          "stops_by_reason": {},
                          "stop_reason_coverage": {"known_stops": 0, "total_stops": 0},
                          "adjudicated_avoidable_stops": 0,
                          "avoidable_stop_coverage": {"known_stops": 0, "total_stops": 0},
                          "repeated_settled_questions": 0,
                          "clarification_to_resume_seconds": {"known_sum": None, "known_events": 0,
                                                               "total_events": 0},
                          "restarts": 1, "discarded_work": 0, "scope_reductions": 0,
                          "user_scope_reductions": 0,
                          "scope_reduction_actor_coverage": {"known_events": 0,
                                                               "total_events": 0},
                          "material_post_pass_corrections": 0, "user_interventions": 0,
                          "user_overturns": 0})
        conflicting_events = [{"event_id": "restart", "type": "restart"},
                              {"event_id": "restart", "type": "discarded-work"}]
        with self.assertRaises(ValueError):
            summarize({"reviews": [], "workflow_runs": [{"workflow_run_id": "conflict",
                                                            "outcome": "running", "events": conflicting_events}]})
        invalid_events = [
            {"event_id": "x", "type": "stop", "reason_code": "timeout"},
            {"event_id": "x", "type": "user-intervention", "reason_code": "timeout"},
            {"event_id": "x", "type": "settled-question"},
            {"event_id": "x", "type": "clarification-resolved", "clarification_to_resume_seconds": -1},
        ]
        for event in invalid_events:
            with self.subTest(event=event), self.assertRaises(ValueError):
                summarize({"reviews": [], "workflow_runs": [{"workflow_run_id": "1",
                                                                "outcome": "completed", "events": [event]}]})
        with self.assertRaises(ValueError):
            summarize({"reviews": [], "workflow_runs": "not-a-list"})
        with self.assertRaises(ValueError):
            summarize({"reviews": [], "workflow_runs": [{"workflow_run_id": "1",
                                                            "outcome": "running", "events": "not-a-list"}]})

    def test_cost_per_issue_requires_complete_same_currency_costs(self):
        reviews = [
            {"review_run_id": "1", "phase": "spec", "cost_amount": 2.0, "cost_currency": "USD",
             "findings": [{"issue_id": "A", "disposition": "accepted"}]},
            {"review_run_id": "2", "phase": "spec", "cost_amount": 4.0, "cost_currency": "USD",
             "findings": [{"issue_id": "A", "disposition": "accepted"}]},
        ]
        self.assertEqual(summarize({"reviews": reviews})["review_cost_per_unique_accepted_issue"],
                         {"value": 6.0, "currency": "USD"})
        self.assertIsNone(summarize({"reviews": reviews + [{"review_run_id": "3", "phase": "plan"}]})[
            "review_cost_per_unique_accepted_issue"])
        mixed = copy.deepcopy(reviews)
        mixed[1]["cost_currency"] = "SGD"
        self.assertIsNone(summarize({"reviews": mixed})["review_cost_per_unique_accepted_issue"])

    def test_cost_pairs_and_outcomes_are_validated(self):
        with self.assertRaises(ValueError):
            summarize({"reviews": [{"review_run_id": "1", "phase": "spec", "cost_amount": 1}]})
        with self.assertRaises(ValueError):
            summarize({"reviews": [], "workflow_runs": [{"workflow_run_id": "1", "outcome": "success"}]})

    def test_missing_workflow_telemetry_is_unknown_but_explicit_empty_is_zero(self):
        missing = summarize({"reviews": []})
        self.assertFalse(missing["workflow_telemetry_known"])
        self.assertIsNone(missing["workflow_runs"])
        self.assertIsNone(missing["restarts"])
        self.assertEqual(missing["workflow_event_coverage"],
                         {"known_runs": 0, "total_runs": None})

        empty = summarize({"reviews": [], "workflow_runs": []})
        self.assertTrue(empty["workflow_telemetry_known"])
        self.assertEqual(empty["workflow_runs"], 0)
        self.assertEqual(empty["restarts"], 0)
        self.assertEqual(empty["workflow_event_coverage"],
                         {"known_runs": 0, "total_runs": 0})

    def test_missing_event_inventory_keeps_event_aggregates_unknown(self):
        result = summarize({"reviews": [], "workflow_runs": [
            {"workflow_run_id": "known", "outcome": "completed", "events": []},
            {"workflow_run_id": "legacy", "outcome": "stopped"},
        ]})
        self.assertEqual(result["outcomes"], {"completed": 1, "stopped": 1})
        self.assertEqual(result["workflow_event_coverage"],
                         {"known_runs": 1, "total_runs": 2})
        self.assertIsNone(result["workflow_events"])
        self.assertIsNone(result["stops_by_reason"])
        self.assertIsNone(result["adjudicated_avoidable_stops"])

    def test_avoidable_and_stop_reason_metrics_include_coverage(self):
        events = [
            {"event_id": "1", "type": "stop", "reason_code": "jira-unavailable",
             "classification": "degradable", "avoidable": True},
            {"event_id": "2", "type": "stop", "reason_code": "secret-detected",
             "classification": "hard"},
            {"event_id": "3", "type": "stop", "reason_code": "jira-unavailable",
             "classification": "degradable", "avoidable": False},
        ]
        result = summarize({"reviews": [], "workflow_runs": [
            {"workflow_run_id": "1", "outcome": "completed", "events": events},
        ]})
        self.assertEqual(result["stops_by_reason"],
                         {"jira-unavailable": 2, "secret-detected": 1})
        self.assertEqual(result["stop_reason_coverage"],
                         {"known_stops": 3, "total_stops": 3})
        self.assertEqual(result["adjudicated_avoidable_stops"], 1)
        self.assertEqual(result["avoidable_stop_coverage"],
                         {"known_stops": 2, "total_stops": 3})

    def test_repeated_questions_are_scoped_to_one_workflow(self):
        result = summarize({"reviews": [], "workflow_runs": [
            {"workflow_run_id": "1", "outcome": "completed", "events": [
                {"event_id": "q1", "type": "settled-question", "question_id": "scope"},
                {"event_id": "q2", "type": "settled-question", "question_id": "scope"},
            ]},
            {"workflow_run_id": "2", "outcome": "completed", "events": [
                {"event_id": "q3", "type": "settled-question", "question_id": "scope"},
            ]},
        ]})
        self.assertEqual(result["repeated_settled_questions"], 1)

    def test_scope_actor_and_user_overturn_are_not_inferred(self):
        events = [
            {"event_id": "scope-user", "type": "scope-reduction", "actor": "user"},
            {"event_id": "scope-reviewer", "type": "scope-reduction", "actor": "reviewer"},
            {"event_id": "scope-unknown", "type": "scope-reduction"},
            {"event_id": "overturn", "type": "user-overturn", "actor": "user"},
        ]
        result = summarize({"reviews": [], "workflow_runs": [
            {"workflow_run_id": "1", "outcome": "completed", "events": events},
        ]})
        self.assertEqual(result["scope_reductions"], 3)
        self.assertEqual(result["user_scope_reductions"], 1)
        self.assertEqual(result["scope_reduction_actor_coverage"],
                         {"known_events": 2, "total_events": 3})
        self.assertEqual(result["user_overturns"], 1)

        for event in (
            {"event_id": "x", "type": "user-overturn"},
            {"event_id": "x", "type": "user-overturn", "actor": "reviewer"},
            {"event_id": "x", "type": "restart", "actor": "user"},
            {"event_id": "x", "type": "scope-reduction", "actor": "unknown"},
        ):
            with self.subTest(event=event), self.assertRaises(ValueError):
                summarize({"reviews": [], "workflow_runs": [
                    {"workflow_run_id": "1", "outcome": "completed", "events": [event]},
                ]})
