# Shipmate Review Workflow

Execute Shipmate's review procedure using the complete contract below.

# Review with Shipmate

Apply [contextual questions](../../internal/user-questions.md) when a finding needs a human
decision: show its triggering example, consequence and viable choices, not an unexplained verdict.

This is one of the plugin's five public entrypoints. It challenges an artifact without changing
the artifact, its repository, Jira, Confluence, GitLab, or pipeline state.

Read the bundled [coding guideline](../../internal/coding-guideline.md) and
[secure engineering](../../internal/secure-engineering.md). Check applicable rules against the
selected artifact and affected code, not a generic checklist. Findings need concrete evidence and
impact; these guides do not authorize fixes or demand irrelevant financial/service-creation work.

Apply the shared
[telemetry rules](../../internal/workflow-policy.md#langfuse-metrics-and-workflow-status): local
run records stay off, and an already opted-in SNS session follows its optional skill-session
reporting step for this actual `review` entry.
Standalone completion means the requested review was delivered, not that its artifact passed.

## Select one review phase

Use the phase explicitly requested by the user. Otherwise infer it from the supplied artifact:

- **Specification** — requirements, outcomes, constraints, acceptance criteria, or a Jira/local Markdown contract.
- **Plan** — an implementation plan that maps settled requirements to concrete changes and checks.
- **Candidate** — an immutable commit/MR candidate with its complete diff and verification evidence.

Do not collapse phases into one review or treat a review of one phase as evidence for another. If
the artifact is still moving, capture its current content for review. If the phase or current
artifact cannot be established from available evidence, return `UNABLE_TO_REVIEW` with the missing
input instead of reviewing an assumption.

## Internal contracts

Read the bundled [`reviewer` procedure](../../internal/reviewer/PROCEDURE.md) and
[`workflow policy`](../../internal/workflow-policy.md) and
[`persona catalog`](../../internal/reviewer/references/persona-catalog.md), then load only the
phase-specific contracts below:

| Phase | Additional contracts |
|---|---|
| Specification | [`specification-personas.md`](../../internal/reviewer/references/specification-personas.md) |
| Plan | [`plan-personas.md`](../../internal/reviewer/references/plan-personas.md) and [`plan-verification-methods.md`](../../internal/reviewer/references/plan-verification-methods.md) |
| Candidate | [`code-review`](../../internal/code-review/PROCEDURE.md), [`candidate-review-envelope.md`](../../internal/reviewer/references/candidate-review-envelope.md), policy-selected candidate persona files, and [`findings-and-adjudication.md`](../../internal/reviewer/references/findings-and-adjudication.md) |

Internal procedures are implementation resources, not separately invocable chat actions. Do not
substitute similarly named global, personal, or other-plugin skills.

## Review gate

1. Read the complete current input and required contracts. Apply the shared
   [freshness rules](../../internal/reviewer/references/review-freshness.md): specification and plan
   reviews track meaning, not content hashes; only candidate evidence requires exact identities.
2. Classify risk using the shared workflow policy and select only the applicable existing personas.
   Dispatch each in a distinct review-only context using current host metadata and an explicit
   efficient Claude/GPT capability class. Set supported non-maximum reasoning effort when
   configurable; otherwise leave it unset after verifying the documented/default route is not
   maximum. Never inherit an unknown or maximum-frontier setting.
3. Require phase/persona/run identification, evidence-backed findings, explicit unreviewed areas,
   and a permitted verdict from each selected independent review. Candidate reviews also require
   review scope and matching digest echoes.
4. Check freshness, then adjudicate every finding without modifying the artifact. Material
   unreviewed scope blocks; specification/plan formatting or audit-hash changes do not.
   Separate defects, unnecessary code, requirement changes and pre-existing issues. Resolve
   disputed material findings through evidence, not agreement; propose unavailable verification
   without executing reviewed code or expanding the task.
5. Return the phase, reviewed artifact reference, selected controller assessments or persona
   verdicts, accepted/rejected findings with
   rationale, unreviewed areas, and the bounded combined result.

The public `review` action reports what must change. Use `run` for an authorized implementation and
fresh candidate cycle; review never fixes, commits, comments, approves, pushes, deploys, or merges.
---

Reference: `skills/review/SKILL.md`
