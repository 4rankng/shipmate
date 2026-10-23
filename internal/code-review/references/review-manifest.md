# Review Manifest

Keep one resumable, machine-local record under
`~/.local/share/gx-marketplace/l3-runs/<work-item-id>/review.yaml`. Store exact review inputs,
responses, and adjudications beside it. Never commit local paths, credentials, customer data, or
raw logs.

Requirement and plan hashes are optional audit metadata, never admission or design locks. The
controller decides freshness semantically: formatting-only changes continue, material clear changes
receive fresh affected reviews, and vague, contradictory, or decision-incomplete changes block.
Only the final candidate commit is identity-pinned because candidate reviewers and CI must validate
the same code. Plans and review evidence are machine-local unless repository policy or the user
requires committing them. Existing MRs may use `adopted-candidate` scope without reconstructed
specification or plan provenance.

The expanded shape below illustrates available fields, not mandatory fabricated reviews. Populate
only the selected route: specification/plan reviews record their selected independent personas;
independent assessments omit `controller_assessment`
and contain only selected real persona IDs/responses. A low-risk candidate selects only
`requirements-code-quality`, omitting the security persona's bundle/response. An adopted candidate
omits absent earlier phases. Never copy example PASS values as execution evidence.

```yaml
work_item: {id: TEAM-0000-or-local-run-id, kind: jira-or-local-markdown, source_ref: ticket-key-or-source-path-or-artifact-reference}
current_requirement:
  kind: jira-or-local-markdown
  requirement_file: relative-artifact
  observed_at: timestamp
  artifact_sha256: optional-audit-only
requirement_admission:
  clarity_status: PASS
  prior_approval_required: false
  content_hash_is_gate: false
risk_classification:
  class: low-risk-or-higher-risk
  rationale: concise-controller-evidence

current_specification_review: # optional for an adopted candidate; independent in a full lifecycle
  cycle: 1
  reviewed_at: timestamp
  assessment_kind: independent
  selected_roster: [] # actual selected persona IDs for independent assessment
  contract_bundle_file: spec-contract-bundle.json
  contract_bundle:
    - {path: PROCEDURE.md, sha256: audit-only-sha256}
    - {path: references/persona-catalog.md, sha256: audit-only-sha256}
    - {path: references/specification-personas.md, sha256: audit-only-sha256}
  contract_bundle_sha256: audit-only-sha256
  phase_input_file: spec-phase-input.json
  phase_input_sha256: audit-only-sha256
  reviews:
    - persona_id: requirements-testability
      review_run_id: unique
      review_input_file: spec-requirements-input.json
      review_input_sha256: audit-only-sha256
      response_file: spec-requirements-response.json
      response_sha256: sha256
      adjudication_file: spec-requirements-adjudication.json
      adjudication_sha256: sha256
      verdict: PASS
      findings: []
      unreviewed_areas: []
    - persona_id: integration-operability
      review_run_id: unique
      review_input_file: spec-integration-input.json
      review_input_sha256: audit-only-sha256
      response_file: spec-integration-response.json
      response_sha256: sha256
      adjudication_file: spec-integration-adjudication.json
      adjudication_sha256: sha256
      verdict: PASS
      findings: []
      unreviewed_areas: []
  review_cohort_sha256: audit-only-sha256

human_approved_spec_review: # optional traceability from interactive specify; run does not require it
  approval: {kind: chat-turn, reference: task-turn-reference}
  reviewed_at: timestamp

plan_review: # optional for an adopted candidate; independent in a full lifecycle
  cycle: 1
  plan_path: machine-local-plan-path-or-repository-path
  reviewed_at: timestamp
  assessment_kind: independent
  selected_roster: [] # actual selected persona IDs for independent assessment
  contract_bundle_file: plan-contract-bundle.json
  contract_bundle_sha256: audit-only-sha256
  phase_input_file: plan-phase-input.json
  phase_input_sha256: audit-only-sha256
  reviews:
    - persona_id: architecture-simplicity
      review_run_id: unique
      review_input_file: plan-architecture-input.json
      review_input_sha256: audit-only-sha256
      response_file: plan-architecture-response.json
      response_sha256: sha256
      adjudication_file: plan-architecture-adjudication.json
      adjudication_sha256: sha256
      verdict: PASS
      findings: []
      unreviewed_areas: []
    - persona_id: failure-security-rollback
      review_run_id: unique
      review_input_file: plan-failure-input.json
      review_input_sha256: audit-only-sha256
      response_file: plan-failure-response.json
      response_sha256: sha256
      adjudication_file: plan-failure-adjudication.json
      adjudication_sha256: sha256
      verdict: PASS
      findings: []
      unreviewed_areas: []
  review_cohort_sha256: audit-only-sha256

candidate:
  review_scope: full-lifecycle-or-adopted-candidate # required; imported legacy record may be unknown
  selected_roster: [requirements-code-quality] # add security-reliability for higher-risk
  current_requirement_review_cycle: optional
  current_plan_path: optional-machine-local-or-committed-path
  current_plan_review_cycle: optional
  target_repository: canonical-identity
  context_repositories: [{repository: canonical-identity, sha: full-sha}]
  base_sha: full-sha
  sha: full-candidate-commit-sha
  tree_sha: full-sha
  patch_sha256: sha256-of-complete-binary-base-to-candidate-patch
  impact_surface_sha256: sha256
  ac_evidence_sha256: sha256
  verification_evidence_sha256: sha256
  identity_file: candidate-review-identity.json
  identity_sha256: sha256
  contract_bundles:
    requirements-code-quality:
      manifest_file: candidate-requirements-quality-contract-bundle.json
      files:
        - {path: ../workflow-policy.md, sha256: sha256}
        - {path: ../secure-engineering.md, sha256: sha256}
        - {path: ../coding-guideline.md, sha256: sha256}
        - {path: PROCEDURE.md, sha256: sha256}
        - {path: references/persona-catalog.md, sha256: sha256}
        - {path: references/candidate-review-envelope.md, sha256: sha256}
        - {path: references/requirements-code-quality-reviewer.md, sha256: sha256}
        - {path: references/findings-and-adjudication.md, sha256: sha256}
        - {path: references/review-freshness.md, sha256: sha256}
        - {path: references/candidate-review-dialogue.md, sha256: sha256}
      contract_bundle_sha256: sha256
    security-reliability: # present only when selected for higher-risk work
      manifest_file: candidate-security-reliability-contract-bundle.json
      files:
        - {path: ../workflow-policy.md, sha256: sha256}
        - {path: ../secure-engineering.md, sha256: sha256}
        - {path: ../coding-guideline.md, sha256: sha256}
        - {path: PROCEDURE.md, sha256: sha256}
        - {path: references/persona-catalog.md, sha256: sha256}
        - {path: references/candidate-review-envelope.md, sha256: sha256}
        - {path: references/security-reliability-reviewer.md, sha256: sha256}
        - {path: references/findings-and-adjudication.md, sha256: sha256}
        - {path: references/review-freshness.md, sha256: sha256}
        - {path: references/candidate-review-dialogue.md, sha256: sha256}
      contract_bundle_sha256: sha256
  reviews: # selected by risk classification; requirements-code-quality is always required
    - persona_id: requirements-code-quality
      review_run_id: unique
      review_input_file: candidate-requirements-quality-input.json
      review_input_sha256: sha256
      response_file: candidate-requirements-quality-response.json
      response_sha256: sha256
      adjudication_file: candidate-requirements-quality-adjudication.json
      adjudication_sha256: sha256
      candidate_identity_sha256: same-candidate-identity
      echoed_identities_match: true
      verdict: PASS
      findings: []
      unreviewed_areas: []
      affected_scope: full-or-delta
      current_readback: full-diff-or-delta-and-impact
      prior_coverage_rationale: optional-baseline-full-diff-delta-impact-and-coverage
      baseline_security_reliability_checks: [] # required for low-risk; not a second persona verdict
    - persona_id: security-reliability # required only when selected by risk policy
      review_run_id: unique
      review_input_file: candidate-security-reliability-input.json
      review_input_sha256: sha256
      response_file: candidate-security-reliability-response.json
      response_sha256: sha256
      adjudication_file: candidate-security-reliability-adjudication.json
      adjudication_sha256: sha256
      candidate_identity_sha256: same-candidate-identity
      echoed_identities_match: true
      verdict: PASS
      findings: []
      unreviewed_areas: []
      affected_scope: full-or-delta
      current_readback: full-diff-or-delta-and-impact
      prior_coverage_rationale: optional-baseline-full-diff-delta-impact-and-coverage
  review_cohort_sha256: sha256-of-ordered-selected-review-records
  candidate_gate_sha256: sha256-of-candidate-identity-and-review-artifacts
  responder_dialogue: # present only when a challenger has supported questions/findings
    requested_model: host-selected-model-id
    requested_capability_class: balanced
    requested_reasoning_effort: host-supported-non-maximum-or-null
    actual_model: null # populate only when runtime metadata exposes it
    challenger_review_run_ids: [unique]
    responder_input_file: candidate-responder-input.json
    responder_input_sha256: sha256
    responder_response_file: candidate-responder-response.json
    responder_response_sha256: sha256
    mode: answer-propose-or-authorized-repair
    repair_worktree: machine-local-path-or-null
    resulting_candidate_identity_sha256: optional-new-candidate-identity

verification: {candidate_identity_sha256: same-candidate-identity, candidate_gate_sha256: same-candidate-gate, commands: []}
delivery:
  project: canonical-project
  branch: feature-branch
  mr_iid: 0
  mr_url: url
  label_status: verified-or-advisory-unavailable
  remote_sha: full-sha
  mr_sha: full-sha
  required_checks: [{name: actual-ci-job, status: passed-or-failed-or-unavailable-or-pending, candidate_sha: full-sha, evidence: artifact-or-job-url}]
  pipeline: {url: url, sha: full-sha, status: pending-or-failed-or-success}
run_state: running-or-needs-input-or-review-pending-or-verification-pending-or-stopped-or-completed
unreviewed_areas: []
unresolved_blockers: []
overall_verdict: NO_BLOCKING_FINDINGS_IN_REVIEWED_SCOPE
```

Review artifacts keep unique run IDs and exact response/adjudication digests so evidence can be
read back. They do not freeze requirements or plans. On resume, reread current sources and apply
the shared [freshness rules](../../reviewer/references/review-freshness.md). Changed code/base
requires fresh candidate verification and policy-selected independent current readback. Changed
requirements, plans, contracts, or evidence can also invalidate affected candidate reviews even
with unchanged code; refresh their inputs and downstream gate rather than manufacturing a new commit.
