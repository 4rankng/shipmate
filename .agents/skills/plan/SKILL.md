---
name: plan
description: Use when a settled requirement or specification needs a reviewed, proportionate implementation plan before coding is authorized. Not for drafting the requirement itself (specify), implementing it (run), or adversarially challenging a plan someone else wrote (review).
---

# Plan with Shipmate

Apply [contextual questions](../../../internal/user-questions.md) when asking the user: state the
situation, compare options fairly, recommend only from known goals, and resume without
repeating settled choices.

This is one of the plugin's public entrypoints. Plan turns a settled requirement into a
reviewed implementation plan: tasks with exact targets, acceptance-criterion traceability,
verification evidence and risk — proportionate to the work, reviewed by an independent plan
reviewer before handback. Plan is a planning surface, not an implementation authorization: it
never edits code, creates branches or worktrees, commits, pushes, opens pull requests, comments,
approves, deploys, or starts Stage 7-style implementation work.

The only artifacts a plan run writes are the plan itself and its machine-local review records.

## Authority

Read [workflow-policy](../../../internal/workflow-policy.md) completely first: recovery,
engineering discretion, review risk and required-versus-optional checks apply unchanged.
Read the bundled [coding guideline](../../../internal/coding-guideline.md) and
[secure engineering](../../../internal/secure-engineering.md) and apply their relevant rules to
the plan's targets and checks. A plan run authorizes nothing beyond producing the plan and
dispatching its reviews.

## Intake

The requirement source is a settled specification (a `shipmate:specify` output, a repository
requirements file, or a clear task statement whose acceptance criteria are already observable).
When no source is supplied, ask one contextual question for it before anything else. Read the
repository's [steering](../../../internal/steering.md) documents when present; the plan must
respect the conventions they settle. Ground the target through
[repo-context](../../../internal/repo-context/PROCEDURE.md): owning modules, real callers, shared
utilities and existing tests. Require a concrete capability gap before planning new helpers,
layers or dependencies.

If a material design decision is open, resolve it the way run's stage 4 does: apply
[grill-with-docs](../../../internal/grill-with-docs/PROCEDURE.md), one decision-bearing question
at a time, human agreement before the plan freezes the choice. An explicit already-stated
design counts as settled. Do not reopen settled decisions without contradictory new evidence,
and do not interview for routine naming, placement or reversible mechanics — those are agent
choices recorded in the plan, not questions.

## Write the plan proportionally

Follow [writing-plans](../../../internal/writing-plans/PROCEDURE.md) and its
[template](../../../internal/writing-plans/references/PLAN_TEMPLATE.md): a small change needs one
compact task with intended files, AC-to-test mapping and risk; add interface, dependency and
rollback detail only where the work justifies it. Every task names exact files and symbols,
maps to the acceptance criterion it delivers, and states its fail-before and pass-after
evidence. Mark parallel-safe tasks `[P]`; markers never authorize parallel execution by
themselves. Record the plan machine-locally by default; commit it only when the user asks or
repository policy requires it. Do not start implementation, and do not create the branch or
worktree — that is run's Stage 5.

## Review the plan

Classify risk with workflow-policy, then dispatch through the bundled
[reviewer procedure](../../../internal/reviewer/PROCEDURE.md) and the plan-phase contracts:
[plan-personas](../../../internal/reviewer/references/plan-personas.md) and
[plan-verification-methods](../../../internal/reviewer/references/plan-verification-methods.md).
Low-risk work gets one independent Architecture & Simplicity reviewer; higher-risk work adds
Failure, Security & Rollback. Use native delegation with explicit efficient capability classes,
never another agent CLI. A missing required reviewer leaves the plan `review-pending`, never a
fabricated PASS. Adjudicate every finding from code and specification evidence; fix supported
findings in the plan and refresh affected review for material changes. After three unsuccessful
cycles, save the work and report the specific help needed.

## Hand back

Lead with the bounded review result, then the plan's location, its task count and lane-sized
summary, any `[P]` waves, unresolved questions, and the next human action — normally an
explicitly authorized `shipmate:run` on the same requirement. A plan produced here is valid
`run` input: run re-reviews only what materially changed, and never discards verified planning
work. Plan ends here; coding needs that separate authorization.

## Resume

When resuming an existing plan, preserve settled content and refresh only the affected review
for changed meaning; formatting-only edits never reset review. A requirement change returns to
intake for the affected slice, and the delta is re-planned, not rewritten wholesale.
