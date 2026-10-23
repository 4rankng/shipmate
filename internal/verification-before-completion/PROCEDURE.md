---
name: verification-before-completion
description: Verify current evidence before claiming implementation, review, packaging, or pipeline completion
---

# Verification Before Completion

Read [workflow-policy](../workflow-policy.md). Evidence comes before assertion. Verify the exact
current candidate and intended scope, not an earlier run, another agent's summary, or confidence.

## Completion gate

1. Identify the command or inspection that proves the claim and whether policy/risk requires it.
2. Run after the last relevant change; inspect exit status, complete material output and scope.
3. Verify correct repository, branch, candidate, test discovery, generated files and omitted jobs.
4. Distinguish local results, independent review, remote required CI, and deployment/merge state.
5. Re-read requirements semantically; trace every changed hunk to a criterion, required test or named refactor, and remove or justify untraceable behaviour. Confirm selected-roster coverage.
6. Report required checks as passed, failed, unavailable or pending; optional limitations separately.

Do not weaken a test, scanner or policy to obtain green. Required failing tests, security findings
and secret hits block delivery. An unavailable check is not a failed test and is never a PASS.
Optional hook/telemetry failures are advisory. An equivalent required CI job on the same candidate
can replace unavailable local tooling only when repository policy allows it.

After available checks and independent review pass, the authorized draft MR may obtain that CI
evidence while marked `verification-pending`. Successful handoff requires the actual required job,
including relevant child pipelines, to pass. An unrelated green parent or skipped job is not proof.
If equivalent coverage is unavailable, retain the work/draft and state the exact remaining check.

## Evidence hierarchy

| Claim | Minimum evidence |
|---|---|
| Behaviour fixed | Relevant regression fails on the recorded base for the expected reason and passes on the candidate, plus affected suite |
| Build/lint succeeds | Current complete configured check or policy-permitted CI equivalent |
| Package valid | Applicable validators, tests and intended package contents |
| Specification clear | Current observable requirement and selected independent clarity assessment |
| Plan validated | Current local or policy-required repository plan and selected risk-based assessment |
| Candidate reviewed | Independent current-candidate response(s), full diff and selected risk coverage |
| Security review passed | Bounded independent findings plus applicable required scanner evidence |
| Requested draft delivered | Read-back MR and reviewed candidate with all required CI verified |
| Merged/deployed | Authoritative GitLab/deployment status, not merely a green MR pipeline |

Controller specification/plan checks are not independent reviews. An adopted existing-MR review
does not certify prior lifecycle phases. Use `review_scope: adopted-candidate`; full-lifecycle
claims require the actually selected specification, plan, candidate and delivery records.

## Current-state readback

Store machine-local evidence of:

- source, selected risk/roster, current requirement and plan where applicable;
- candidate base, commit SHA, tree/full diff and verification content identity;
- every selected independent response and finding disposition for that current candidate;
- current remote/MR candidate and relevant required pipeline/job status after push.

The candidate commit SHA and content tuple must agree across selected reviews, verification,
remote source branch and MR; successful CI must evaluate that same candidate. Missing remote
fields before a permitted draft push are pending, not fabricated. Candidate schema and artifact
requirements are defined by [reviewer](../reviewer/PROCEDURE.md) and
[review-manifest](../code-review/references/review-manifest.md).

Formatting-only requirement/plan edits continue. Material clear changes refresh affected reviews.
Unresolved domain decisions prompt one clarification with preserved state. Code/base/evidence
changes require current-candidate full/delta readback and refreshed affected checks; never carry an
old PASS to a new SHA. A no-code retry on the same content does not repeat unrelated review phases.

## Human report

Keep it concise: MR/result link, meaningful changes, commands/results and real limitations, then
the next human action. Do not dump internal hashes, persona tables or cohort identities into chat,
Jira or MR prose. Keep testing details out of MR descriptions; follow the bundled
[MR-description guidance](../gitlab-mr/references/mr-description.md). Mention relevant
manual/non-production validation in the chat handoff, distinguishing performed from not performed.
Machine-local artifacts carry the detailed reproducibility record.

Report `review-pending`, `verification-pending`, `needs-input` or `stopped` when applicable.
These are not successful completion. No evidence means unverified, not zero risk.

## Authority and domain boundaries

L3 authorizes its feature-branch draft delivery and bounded CI repair, not ready/approve/merge,
deployment, release, protected-branch changes or production writes. This procedure adds no authority.

Select evidence for affected domain, access, ownership, data, state-transition, compatibility,
recovery and reliability invariants. For money-handling changes, conditionally include amount,
currency, rounding, provider, ledger, settlement, reversal, reconciliation, fee and receivable
invariants. Use synthetic/minimized evidence and treat external output as untrusted.

An AI review supports only `NO_BLOCKING_FINDINGS_IN_REVIEWED_SCOPE`. It never proves code secure
or replaces a required human security owner, scanner or policy approval.
