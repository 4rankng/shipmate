---
name: run
description: Use when Jira, local Markdown, or a clear task should become a verified draft merge request with risk-proportional review and resumable clarification
---

# Run Shipmate

Apply [contextual questions](../../internal/user-questions.md) when asking the user: include the
situation and a concrete example/reference. Ask facts neutrally; compare decision options fairly
and recommend only from known goals. Apply the answer and resume without repeating settled choices.

Take a clear requirement to a verified draft MR. Jira is optional; local Markdown is a
first-class source. Guided execution is the default: resolve evidence-backed details yourself,
ask only for material missing decisions, and resume without throwing away useful work.

## Core principle and authority

Read [workflow-policy](../../internal/workflow-policy.md) completely first. It defines recovery,
engineering discretion, review risk, artifacts, and required-versus-optional checks for all stages.
Read the bundled [coding guideline](../../internal/coding-guideline.md) and
[secure engineering](../../internal/secure-engineering.md). Apply relevant rules during planning,
implementation and verification, using the target repository's actual contracts and tooling.
An explicit run authorizes implementation, its isolated feature branch, draft MR, and bounded CI
repair in the selected scope. It does not authorize new business behaviour, additional writable
repositories/MRs, merging, deploying, production customer data access, or Doorman DML.

Never repair or infer business behavior, authorization, domain invariants, ownership, or state
transitions. Financial constraints apply when applicable, not to every team. Use `needs-input`
with one decision-bearing question for a real `spec-gap`. Preserve settled decisions and resume
the affected stage after the answer. Use unattended mode only when explicitly requested; it saves
the same checkpoint and reports the question rather than inventing an answer. Pending/stopped
runs are not successful completion.

## Preflight

Local run records are off by default. Do not create/update local run JSON/CSV or invoke
`run_metrics.py` unless the user explicitly requests local metrics files. Do not include record
links or capture-disabled notices in handoffs. The optional [legacy utility](../../internal/run-metrics.md)
is separate from opted-in Langfuse telemetry; keep resumable status in the conversation.
Use verified Langfuse observations for AI-session metrics. Missing telemetry is unavailable;
never create a local metrics file as a fallback or invent values.
For an already opted-in SNS session, follow its optional skill-session reporting step for this
actual `run` entry, without creating a local run record. Do not enable external tracking at intake.

Derive `PAYMENT_PLUGIN_ROOT` from this installed skill's ancestor containing `plugin.json`.
The variable is a compatibility name, not a payment-repository requirement.
Read linked procedures completely before using their stage. Prefer bundled procedures over
similarly named personal/global skills; same-authority tool recovery follows workflow-policy.

| Responsibility | Bundled resource |
|---|---|
| Source selection and refresh | [`requirements-source`](../../internal/requirements-source/PROCEDURE.md) |
| Jira description and read-only comment evidence | [`jira`](../../internal/jira/PROCEDURE.md) |
| Linked Confluence evidence | [`confluence`](../../internal/confluence/PROCEDURE.md) |
| Concise requirement structure | [`specify`](../specify/SKILL.md) |
| Requirements and technical-design interview | [`grill-with-docs`](../../internal/grill-with-docs/PROCEDURE.md) |
| Independent review dispatch | [`reviewer`](../../internal/reviewer/PROCEDURE.md) |
| Repository/dependency context | [`repo-context`](../../internal/repo-context/PROCEDURE.md) |
| Isolated workspace | [`using-git-worktrees`](../../internal/using-git-worktrees/PROCEDURE.md) |
| Branch and candidate commit | [`git-commit`](../../internal/git-commit/PROCEDURE.md) |
| Compact plan | [`writing-plans`](../../internal/writing-plans/PROCEDURE.md) |
| Dependency-aware implementation | [`executing-plans`](../../internal/executing-plans/PROCEDURE.md) |
| Implementation tests | [`test-driven-development`](../../internal/test-driven-development/PROCEDURE.md) |
| Failed evidence | [`systematic-debugging`](../../internal/systematic-debugging/PROCEDURE.md) |
| Verification | [`verification-before-completion`](../../internal/verification-before-completion/PROCEDURE.md) |
| Candidate review | [`code-review`](../../internal/code-review/PROCEDURE.md) |
| MR and CI | [`gitlab-mr`](../../internal/gitlab-mr/PROCEDURE.md) |
| SNS tracking at final handoff | [`sns-l3-labelling`](../../internal/sns-l3-labelling/PROCEDURE.md) |
| Human-facing prose | [`unslop`](../../internal/unslop/PROCEDURE.md) |

```bash
python3 "${PAYMENT_PLUGIN_ROOT}/scripts/doctor.py" --group core,gitlab
# add `jira` only in Jira mode:
python3 "${PAYMENT_PLUGIN_ROOT}/scripts/doctor.py" --group core,gitlab,jira
```

Treat diagnostics individually, not as a blanket veto. Missing delivery credentials can leave
implementation/review useful but delivery pending. Missing optional hooks, telemetry or labels is
advisory. A present credential is not validated access; verify the intended source through its API.
Investigate wrong path/site/key and permission errors without exposing secrets or bypassing access.
Never silently substitute a different requirement source.

## Stage 0 — Resolve repository context

Use `repo-context` to identify the exact user-selected checkout, canonical remote, owning modules,
and default branch. Default to the current Git root only when unambiguous. One repository is the
writable target for this slice; relevant dependency repositories remain read-only. Resolve an
incorrect checkout before describing its branch/conflict state. Preserve dirty user work.

## Stage 1 — Intake and dependency discovery

Use `requirements-source` and persist `work_item` plus the current requirement machine-locally.
A clear current requirement is sufficient admission. No previous approval, specification SHA,
Jira revision lock, plan hash, or historic attestation is required.

In Jira mode, read the full current description and complete comment inventory, then select
accepted decisions. Jira comments are read-only requirement evidence; never create, edit, or
delete one. Apply/read back the established `l3-workflow` tracking label when supported and authorized; unavailable labeling is
an advisory, not a requirement gap. Never rewrite Jira during `run`.

In Local Markdown mode, do not call Jira or require its credentials. Read the supplied safe file,
or materialize the stated request and verified facts into machine-local `requirements.md` using
the concise `specify` format and Given/When/Then acceptance criteria. Do not ask the user to
restate a clear request or obtain approval for merely transcribing it. Keep review evidence
separate; a repository file under `docs/requirements/` is optional unless requested/policy-required.

Before declaring an absent parser, endpoint, schema, or other capability a scope gap, inspect the
actual code and directly linked tickets/MRs. Distinguish authorized new work from an unmerged
dependency or missing decision. Do not invent a consumer/job/field or duplicate linked work.
Offer the smallest useful slice; if needed, propose an explicitly authorized pinned stack or split
with merge order. No story-point hard veto, extra tickets, second writable repository, or additional
MR without scope authorization. Honor one-MR-at-a-time delivery when selected.

## Stage 2 — Fresh specification clarity review

Do not mutate the selected source. Read the reviewer
[catalog](../../internal/reviewer/references/persona-catalog.md) and
[specification personas](../../internal/reviewer/references/specification-personas.md).
Assess risk using workflow-policy. Low risk uses an independent Requirements & Testability reviewer; higher-risk work
uses the two applicable independent specification personas. Record the selected roster and why.
Review hashes may identify local evidence but are not admission locks.

Check goal, required behaviour, observable Given/When/Then criteria, scope, and applicable domain,
security, integration and failure constraints against real capabilities. Missing historic review
provenance is not a defect. Fix evidence-backed wording in the working copy, not business decisions.
Also inspect the technical approach and human-settled choices using Specify's
[technical-design interview](../specify/references/technical-design.md). Requirements clarity alone
does not authorize coding while material design choices remain open.
Record `clarity_status: PASS` only with no unresolved material ambiguity; distinguish controller
assessment from independent review.

- Formatting-only changes update the snapshot and continue without review invalidation.
- A material but clear change receives fresh specification and plan review for affected scope,
  adapts implementation/tests, then continues. Do not replay unrelated completed work.
- Only a vague, contradictory, or decision-incomplete requirement blocks affected work. Ask one
  precise question, retain the answer with its source, and resume here when resolved.

Merely having two implementation options, a missing existing-file name, or a large estimate is
not a blocker. Investigate capabilities, choose reversible repository-native details, and split
reviewable delivery where needed. Customer approval proof, ownership, deadlines, auth and
money/state rules cannot be invented. A missing required reviewer leaves `review-pending`, not a
fabricated PASS; safe context gathering and planning may continue.

## Stage 3 — Ground context and scope

Read relevant repository instructions, README, build/CI configuration, APIs and dependency code.
Record the target/default-branch base and inspected dependency revisions for reproducibility, not
as design approval locks. Prefer clean detached snapshots for independent repository context.
Validate every write is inside this slice's authorized root. A needed second repository change
requires a specific coordination decision; do not abandon independent work in the first.

When a base/dependency advances, inspect its delta and revalidate affected assumptions and tests.
Never silently change a stacked base or import unreviewed dependency code. Local absolute paths
belong only in machine-local routing/run state, not human requirements or MR prose.

## Stage 4 — Resolve material decisions only

Use the current requirement, accepted user decisions, actual code and authoritative linked docs.
Apply the bundled grill-with-docs interview to unresolved requirements and technical design.
Present the proposed approach and its consequential trade-offs; obtain human agreement before
coding. An explicit instruction to implement an already stated design counts; do not request a
new approval record or repeat settled questions. A generic run request does not approve a material
design proposed afterward. Existing clear work can proceed without a separate Specify invocation.
Choose ordinary naming, placement, simple refactoring and existing error/DI patterns yourself.
Do not reopen settled decisions without contradictory new evidence. If a new fact changes public
behaviour or material risk, ask the one question and pause affected work, not the whole workflow.

## Stage 5 — Prepare the writable branch

Use `using-git-worktrees` then `git-commit`. Jira mode always uses a dedicated Git worktree from
the recorded base: one ticket cannot share writable branch state with another. Multiple Jira
tickets may run concurrently. If isolation cannot be verified, repair it or report `needs-input`;
never fall back to a shared writable checkout. Record branch/worktree in machine-local state.

Local Markdown work uses the same isolation when parallel, dirty or shared state requires it;
otherwise follow the documented clean-workspace fallback. Do not change unrelated user files.
Copy requirement/design files into the branch only when requested or required by repository policy.

## Stage 6 — Plan proportionally

Use `writing-plans`. Persist a machine-local plan by default: a small fix may need one compact
task with intended files, AC-to-test mapping and risk. Add interface/dependency/rollback detail
only where relevant. Committing a plan into the MR is not required unless repository policy or
the user requests it; do not restore a plan intentionally removed from an MR.

Low-risk work dispatches an independent Architecture & Simplicity reviewer. Higher-risk work dispatches Architecture &
Simplicity and Failure, Security & Rollback with focused evidence. Use explicit efficient models
from the catalog and native delegation, never another agent CLI or unknown/frontier defaults.
Keep exact responses and dispositions machine-local. Fix supported findings, refresh affected
reviews for material changes, and continue once the selected plan checks pass. Formatting-only
edits do not reset review. Missing required review means `review-pending`.

Before adding a helper, layer or dependency, inspect the existing utility and actual callers.
Reuse it when it meets the requirement; record only a concrete capability gap that justifies a new
path. Do not add fallback behaviour or framework code for hypothetical future uses. Keep this
reasoning in the existing compact plan, not a new checklist or approval step.

If a finding needs a new domain/authority decision, clarify and resume; do not manufacture a
passing record. After three unsuccessful cycles or repeated no progress, save the current work
and report the specific help needed. Do not automatically restart specification or discard code.

## Stage 7 — Implement and test

Start coding only when requirements and the material technical approach are settled with the human
and the selected plan checks pass. If planning introduced a new consequential design choice, return
to that question before implementation; reviewer agreement cannot replace the human's decision.

Use `executing-plans` to execute the settled scope. A small change stays sequential; multi-slice
work follows dependencies and shared-file ownership, not ticket order. Parallel delegation is
optional and needs explicit authorization plus isolated native workspaces. Missing parallel
support means sequential execution, not a workflow veto. Do not add tickets or MRs for scheduling.

Use `test-driven-development` for executable changes: reproduce the relevant failure, make the
smallest repository-native fix, and prove the expected outcome. For documentation/configuration,
use a focused behavioural/schema/contract check rather than inventing a runtime test.
Change generator inputs and regenerate outputs when applicable. If implementation reveals a
material specification conflict, preserve work and clarify affected behaviour before proceeding.

## Stage 8 — Verify and classify checks

Use repository build, test, lint, coverage and security commands for the changed scope. Record
required/optional and passed/failed/unavailable/pending separately. Run the repository's real
coverage-producing job and threshold when configured; do not invent a generic gate. Bind results
to candidate content. Available dependency audits apply when manifests/lockfiles change.

```bash
python3 "${PAYMENT_PLUGIN_ROOT}/scripts/scan_secrets.py" <changed paths>
```

A secret hit or genuine required test/security failure blocks delivery until resolved; do not
weaken tests or bypass permissions. Missing optional hooks are advisory. If required local lint
or another check is unavailable, use an equivalent CI check only when repository policy permits.
Available checks and independent review must pass before a draft push to obtain that CI evidence;
status remains `verification-pending` until the actual required job passes. Never claim green
from an unrelated parent pipeline or skipped required child. Deployment validation is outside L3.

## Stage 9 — Review the current candidate

Re-read the requirement and classify semantic changes. Formatting-only Jira edits never block.
Create a local candidate commit with only intended project changes after available verification
passes. Only the final candidate commit is identity-pinned: record candidate commit SHA, base,
tree/full diff, changed files, AC evidence, selected roster, and exact review inputs/results.
These identities prove which code was examined, not whether the human may improve a design.

Use `code-review`: one independent requirements/code-quality reviewer with baseline security
checks for low risk; the additional security/reliability reviewer for higher risk. Validate clean
candidate/context snapshots before and after review, adjudicate findings from code/spec evidence,
and fix accepted blockers through tests. When a challenger identifies a supported shortcoming, a
separate host-selected balanced-class responder may repair accepted findings only in its own
writable worktree; it is not a reviewer or voter. Required independent reviews cannot be
self-certified.

A changed candidate needs a fresh current-candidate response. Review the full current diff and
affected delta, preserve explicitly justified unaffected findings, and refresh affected checks;
do not blindly repeat all earlier phases. When impact is unclear, use full candidate review.
Never attach an old PASS to a new SHA. After repeated no progress, report the unresolved finding
and resume point without discarding useful work. The conclusion is bounded:
`NO_BLOCKING_FINDINGS_IN_REVIEWED_SCOPE`, not a claim that the code is secure.

## Stage 10 — Deliver and verify CI

Use `gitlab-mr` to push the reviewed feature candidate and create/update its draft MR. The only
pending-check exception is the policy-permitted CI-equivalent path in Stage 8. Apply/read back
the workflow label when available; labeling failure is advisory. Never merge, approve or deploy.
After first-MR API readback, retain its URL, candidate SHA and actual workflow status in the
conversation for resumption. Do not create a local run record for this milestone.

Write a concise `Description of Change` with what changed and why, plus a Mermaid sequence
diagram when the interaction can be shown meaningfully. Follow the bundled MR-description
guidance even when a global GitLab skill or optional repository template offers a longer template.
Omit `Checklist`, `Risks and limitations`, deploy-order and rollback reports, implementation caveats,
test cases, testing/validation sections and CI narration. Do not repackage them under another
heading or append them to the change explanation. Before publishing, remove this boilerplate from
agent-written prose; preserve unrelated human-authored content in an existing MR.
Keep required verification evidence machine-local and summarize meaningful results in the chat
handoff. Use `unslop`. Never publish internal L3 hashes, snapshots, persona tables,
candidate/cohort identities, finding counts or pipeline IDs in MR descriptions/comments.

Watch the actual required parent/child jobs for the candidate. A no-code retry keeps review;
code/evidence changes refresh affected verification and current-candidate review. Revise the plan
only if the approach changed. Fix in-scope failures; propose unrelated prerequisite work separately.
Read back MR content, remote candidate and required CI status before declaring completion.
Unavailable required CI remains `verification-pending`; red checks remain failed, not green.

## Stage 11 — Hand back

As the final bookkeeping step, read and use the bundled
[`sns-l3-labelling`](../../internal/sns-l3-labelling/PROCEDURE.md) once for this Run's eligible
SNS Jira/MR targets. Add/read back `sns-l3` and `l3-agent`, preserving existing labels. Supply
the run context and verified ticket/MR association; do not infer eligibility from AI usage.
Local Markdown, manual/L2, non-SNS and reference-only work is skipped. Tagging failures are
advisory: report the per-target outcome briefly and continue this handoff with the actual
engineering status. Nested or standalone read-only Review does not write tracking labels.
If the session already opted into SNS usage publishing, follow
[its handoff rules](../../internal/sns-langfuse/PROCEDURE.md): publication is pending until CLI
exit and is verified only by remote readback. Do not launch a collector, enable full content or
upload again from this stage. Keep the actual run ID correlation and coverage limitation local.

Never comment on the Jira ticket. Report the MR link, what changed, meaningful verification and
limitations, and the next human action. Keep internal traceability/telemetry machine-local and
do not dump hashes or per-persona tables into chat. State incomplete outcomes honestly:
`needs-input`, `review-pending`, `verification-pending`, or `stopped` with the concrete next action.
Only verified requested delivery is `completed`. Human review, merge and release remain separate.
Report actual status and the useful result directly. Do not create or update local metrics files
or include a local record link or capture-disabled notice in the handoff.
MR creation is not workflow completion; missing usage or human-time evidence stays unknown.

## Resuming

Read current source, worktree/status, saved decisions, plan, MR/CI and candidate/context state.
Resume the affected stage, not a new run. Do not ask settled questions again. Formatting-only
source edits continue; material clear edits refresh affected review; unresolved contradictions
need one clarification. Revalidate changed base/context assumptions, rebuild stale inputs, and
issue current-candidate review after code/evidence changes. Keep unaffected completed work.
