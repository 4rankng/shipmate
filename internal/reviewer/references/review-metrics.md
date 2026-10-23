# Review measurement

Only when the user explicitly requests local review metrics, store a machine-local `review-metrics.json` beside review artifacts, not in Jira, the MR description
or a committed requirement. One record per actual invocation:

```json
{"reviews": [{
  "review_run_id": "unique-invocation",
  "workflow_run_id": "parent-run-uuid",
  "phase": "candidate",
  "persona_id": "requirements-code-quality",
  "requested_model": "host-selected-model-id",
  "actual_model": null,
  "requested_capability_class": "balanced",
  "reasoning_effort": null,
  "duration_seconds": null,
  "total_tokens": null,
  "findings": [{"issue_id": "controller-assigned-root-cause", "disposition": "accepted"}]
}]}
```

`disposition` is `accepted`, `rejected` or `unverified`, mirroring ACCEPT/REJECT/UNVERIFIED adjudication.

Record the requested route and exposed runtime values; never infer actual model, tokens, price
or duration from the requested model or message length. Unavailable telemetry stays null.
Link `workflow_run_id` only to an existing explicitly requested [local run record](../../run-metrics.md);
never create a parent record solely for review metrics. The controller,
not the reviewer, writes these observations. Omitted or null `findings` means the inventory is
unknown; only an explicit `findings: []` means observed zero. Finding totals and cost per accepted
issue remain unknown for partial inventories, with known/total invocation coverage reported.
Use a new run ID for each retry. The same root cause across personas/cycles shares a controller-
adjudicated issue ID within its parent workflow; identical issue IDs in different workflows are
separate issues. Legacy records without a parent remain one cohort. Preserve rejected findings too.
Include only concise identifiers, not raw
prompts, credentials, customer records or logs. Telemetry is best-effort and never a new L3 gate.

Run `python3 scripts/review_metrics.py review-metrics.json` from the plugin root.
The report deduplicates identical copies of a run and rejects conflicting copies. It reports
invocations, accepted/rejected/unverified reports, unique accepted issues, duplicate accepted reports and
telemetry coverage. Duration sums measure reviewer work, not end-to-end latency (parallel reviews
overlap). Accepted findings are controller judgments, not an accuracy or recall benchmark.

For behavioral evaluation, supply an independent agent the raw cases in
`scripts/evals/freshness-cases.json` and the current reviewer/freshness instructions, without the
answer key. Ask for one `{"id": "...", "action": "continue|refresh|block"}` per case in a JSON array and a short
reason. No network or mutations are needed. Run `python3 scripts/evaluate_freshness.py responses.json`
to compare with `freshness-expected.json`; report every
mismatch and sample size, including incomplete responses. This small curated set is a regression
check, not a production accuracy estimate. Unit tests alone do not prove agent behavior.

For candidate finding quality, give an independent `requirements-code-quality` reviewer each case
in `scripts/evals/review-findings-cases.json` with the current reviewer contracts, without the
expected file. Return `{id, verdict, blocking_findings: [{file, line, category}]}` per case. Use
`requirement-boundary`, `authorization`, `idempotency` or `error-handling` for those defect types;
other findings may use other categories. Score with
`python3 scripts/evaluate_review_findings.py responses.json`. Key-bug credit requires the category,
file and inclusive line range to match in the same finding. Report key-bug inclusion and false
blocks with sample size; this curated set is a regression check, not a production precision or
recall estimate.

For broader workflow decisions, supply `scripts/evals/workflow-cases.json` plus the current public
run/review skills and shared workflow policy to an independent native agent, without the expected
file or scorer tests. Return the public `{id, action, risk, cohort, rationale}` schema as a JSON
array; score it with `python3 scripts/evaluate_workflow.py responses.json`. Inspect the rationales
as well as the discrete score. Record and adjudicate ambiguous fixtures separately from unsafe
workflow decisions; do not silently tune expectations or present the curated score as production
accuracy. This evaluation is a development check, never a runtime admission gate.

## Skill output quality trials

For Specify, Run, Walkthrough and Quiz output quality, use the paired normal/pressure cases in
`scripts/evals/skill-quality-cases.json` and its companion `skill-quality-rubric.md`. Keep the
rubric out of trial context and report unexecuted native-agent cases as not run. These inspect
useful work, not whether a particular harness's installation command succeeds. Existing packaging
and adapter tests remain separate compatibility evidence; they do not establish skill behavior.

## Optional workflow-adoption telemetry

The same local file may also contain `workflow_runs`. This is optional and does not alter the
review summary above. Each run has a stable `workflow_run_id`, one outcome, and zero or more
identified events. Include `events: []` to record that a run had no events; an omitted `events`
field means the legacy event inventory is unknown. Identical duplicate run or event copies are
deduplicated; conflicting copies with the same ID are rejected.

```json
{"workflow_runs": [{
  "workflow_run_id": "local-workflow-42",
  "outcome": "completed",
  "events": [
    {"event_id": "stop-1", "type": "stop", "reason_code": "jira-unavailable", "classification": "degradable", "avoidable": true},
    {"event_id": "question-1", "type": "settled-question", "question_id": "scope-boundary"},
    {"event_id": "scope-1", "type": "scope-reduction", "actor": "user"},
    {"event_id": "overturn-1", "type": "user-overturn", "actor": "user"},
    {"event_id": "clarification-1", "type": "clarification-resolved", "clarification_to_resume_seconds": null}
  ]
}]}
```

Outcomes are `running`, `completed`, `needs-input`, `review-pending`, `verification-pending`, or
`stopped`; only `completed` is successful. Valid event types are `stop`, `user-intervention`,
`settled-question`, `clarification-resolved`, `restart`, `discarded-work`, `scope-reduction`, and
`material-post-pass-correction`, and `user-overturn`. A stop requires a concise `reason_code` and `classification`
(`hard` or `degradable`). Count an avoidable stop only when its controller-adjudicated
`avoidable` field is explicitly `true`; absent means unknown, not false. A settled question needs
a stable `question_id`; repeated IDs within one workflow run report repeated settled questions.
A scope reduction may record `actor` as `user`, `controller`, or `reviewer`; only an explicit
`user` actor contributes to `user_scope_reductions`. A `user-overturn` requires `actor: user` and
records that the user reversed a workflow decision without implying whether safety was weakened.
Clarification-to-resume
duration is a non-negative seconds value or `null` when unavailable.

An omitted `workflow_runs` section means workflow telemetry is unknown; it does not mean zero
runs or events. The summary reports whether workflow telemetry and per-run event inventories are
known. Event aggregates are `null` unless every recorded workflow has an explicit event inventory.
Stop reason, avoidability, and scope-actor coverage expose their known and total denominators so an
unknown field is never counted as `false`. These counts describe recorded events only; they do not
claim that uninstrumented work had no stops, scope changes, or user overturns.

For optional review cost, add paired `cost_amount` and `cost_currency` to a review invocation.
The summary reports review cost per unique accepted issue only when every unique invocation has a
known cost in one currency and at least one accepted issue exists. Otherwise it remains `null`;
it never invents an exchange rate, an accuracy metric, a cost, or zero for unknown telemetry.
