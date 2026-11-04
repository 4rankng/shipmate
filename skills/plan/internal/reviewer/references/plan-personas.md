# Plan Review Personas

## Purpose and immutable inputs

Challenge the machine-local implementation plan against the current requirement source. Select the
focused existing persona(s) required by the shared workflow policy; the phase maximum is four and there is no quota.
Commit a plan only when repository policy or the user requires it.

Every reviewer receives the current clear specification and complete current plan path/content;
pinned base and context repository identities with validated read-only snapshot
roots; repository constraints; and the acceptance-criterion traceability matrix.

Read `PROCEDURE.md`, `references/persona-catalog.md`, this file, and
`references/plan-verification-methods.md` from the same installed directory. Record their versions
with the review artifacts. Repository evidence comes only from clean snapshots pinned to the
declared SHAs.

## Focused cohort

Use Architecture & Simplicity independently for qualifying low-risk work. Higher-risk work uses
both applicable separate review-only delegated contexts:

| Persona ID | Persona | Challenge | Verification role |
|---|---|---|---|
| `architecture-simplicity` | Architecture & Simplicity Reviewer | feasibility, dependency order, contract fidelity, scope control, and unnecessary complexity | Contract Verifier |
| `failure-security-rollback` | Failure, Security & Rollback Reviewer | partial failures, abuse, authorization, data exposure, recovery, rollback, and verification | Flow Tracer |

Use the explicit efficient model route in `persona-catalog.md`. Do not add reviewers merely to fill
the phase maximum. Record the selected roster and independent responses for the current plan.

The Architecture & Simplicity reviewer applies the
[repository-fit check](../../../skills/specify/references/technical-design.md). Verify the plan's
reuse claims against real callers, framework defaults and shared utilities. Challenge each new
component or layer without a required capability gap; a shorter plan is not evidence of simplicity.
Prefer deleting duplicate or speculative tasks while preserving necessary protocol/security behaviour.
Apply the [coding guideline](../../coding-guideline.md) to applicable ownership, contract,
generation, compatibility and side-effect decisions; record it among the contract files used.

The Failure, Security & Rollback reviewer applies [secure engineering](../../secure-engineering.md)
to changed trust/data boundaries. Check that the plan reuses verified controls and tests the
applicable abuse/failure cases. Include this reference in the recorded contract files when used;
do not add security infrastructure or a compliance audit beyond the agreed scope.

## Findings, loop, and gate

Each finding has a stable ID/persona, `Critical`/`High`/`Medium` severity, exact plan section,
concrete failure path and impact, violated acceptance criterion/control, repository `file:line`
evidence for code facts, and the smallest safe correction. Reject style-only feedback and quotas.
Verdicts are `PASS`, `CHANGES_REQUIRED`, or `UNABLE_TO_REVIEW`; a material unreviewed area cannot
pass.

Persist each exact response and adjudication. After the selected reviews return, reread the selected source and
revalidate repository state. On `CHANGES_REQUIRED`, correct the plan, run the whole-plan
consistency sweep, and rerun affected selected reviews. Missing independent context is
`review-pending`; a new business/domain/security/data/architecture decision becomes `needs-input`.
Stop after three cycles with the preserved plan and specific help needed.

Record the selected reviews under one plan review cycle. Implementation starts only when the policy
requirements are met, every selected reviewer reviewed the current plan content, has a unique run,
returns `PASS`, and leaves no material scope unreviewed.
Formatting-only edits do not invalidate the cycle. Material clear changes create a fresh cycle;
missing or changed hashes do not reject the design.
