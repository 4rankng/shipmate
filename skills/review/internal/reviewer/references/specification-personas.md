# Specification Review Personas

## Purpose

Produce an evidence-backed implementation contract from Local Markdown before autonomous L3 starts. Select the
focused existing persona(s) required by the shared workflow policy; the phase maximum is four and there is no quota. Persona names are
review lenses, not installed agents. Every persona runs through `reviewer` in a distinct review-only
delegated context using the explicit model routing in `persona-catalog.md`.

## Shared review and evidence rules

Read `PROCEDURE.md`, `references/persona-catalog.md`, and this complete reference from the same
internal procedure directory. Record the contract files used by each review. Content hashes may be
stored as audit metadata, but never use them to lock the requirement or decide whether a clear
current specification may proceed.

Store review objects as UTF-8 JSON. Snapshot paths plus host/model/runtime metadata are local audit
data. Formatting-only changes do not invalidate a semantic review. A material but clear change
receives a fresh review; only ambiguity, contradiction, or a missing decision blocks.

Each delegated review gets a unique `review_run_id`. Persist its exact response and controller
adjudication as separate artifacts. Distinct personas require distinct run IDs and review inputs. A
typed `PASS` without the response and adjudication artifacts is not evidence.

## Controller evidence and decision work

The controller builds the evidence input from the `work_item`, current requirement, sources actually
inspected, repository evidence, and a source record separating facts, inferences, contradictions,
and unknowns. In ticket-based source mode it reads the full current description and complete comment inventory.
In Local Markdown mode it reads the current requirement file. It corrects source gaps before
drafting without requiring an earlier snapshot or digest.

When a material business, authorization, data-ownership, public-contract, recovery, or security decision
remains unresolved, the controller compares two or three sourced options covering
behavior, security, ownership, blast radius, deployment, rollback, and reversibility. It presents
the comparison for a human decision. Do not delegate option comparison as another persona; a
recommendation never becomes the decision.

## Independent draft cohort

After evidence is complete and every required human decision is recorded, persist the current draft,
evidence sources, and decisions. Qualifying low-risk work uses an independent Requirements &
Testability reviewer; higher-risk work uses both personas below in separate review-only contexts:

| Persona ID | Persona | Focus |
|---|---|---|
| `requirements-testability` | Requirements & Testability Reviewer | goal, required behaviour, scope, non-goals, Given/When/Then acceptance-criterion clarity and testability, and source contradictions |
| `integration-operability` | Integration & Operability Reviewer | technical approach, component boundaries, applicable integration and operational constraints, and whether consequential design choices are settled with the human; never require irrelevant API, event, data, timeout, observability, rollout, or rollback boilerplate |

Each review input identifies phase=`spec-draft`, persona ID, the current requirement, and evidence.
For changed trust/data boundaries, use [secure engineering](../../secure-engineering.md) to check
that the agreed behaviour names the actual control and a meaningful failure outcome. Do not demand
irrelevant controls or a separate security section. Record this reference with the contract files.
The requirements reviewer also checks [content selection](../../../skills/specify/references/content-selection.md):
does each criterion express a ticket-owned decision, and does each GWT bullet have a clear test
oracle? Check that unfamiliar shorthand and necessary state codes have verified, readable meanings.
Reject invented acronym expansions, state mappings and unsupported delivery/recovery guarantees;
distinguish producer retries from duplicate delivery and consumer-side deduplication.
Challenge mixed workflows, copied dependency internals and repeated rules. Suggest the
smallest cut or accessible reference while preserving every material constraint. Verbosity alone
is an editorial correction, not a new approval veto; ambiguity, missing outcomes or changed
requirements remain substantive findings. Do not reward a short but incomplete specification.
For rewrites, compare source and draft obligations, numbers, deadlines, permitted actors and
side-effect ordering. Missing constraints or must-to-may changes are requirements defects, not
writing preferences. Distinct outcomes need distinct test oracles even if that adds AC rows.
For Specify rewrites, confirm the complete original is backed up locally rather than duplicated
inside the source. If the validated draft exceeds the 1,200-character / fewer-than-150-words target,
check that the stated reason is strong (distinct ticket-owned outcomes, needed Definitions or
essential dependency constraints) and flag unjustified length as an editorial correction. Check
that ACs state only ticket-owned behaviour and other teams' work sits in Out of Scope. Assess
settled requirements, including any verified supporting reference, not superseded historical wording.
Unjustified length needs editorial repair, not automatic loss of material constraints or new tickets.

Verdicts are `PASS`, `CHANGES_REQUIRED`, `DECISION_REQUIRED`, or `UNABLE_TO_REVIEW`. Every
finding contains stable ID, persona ID, severity, exact draft section, source evidence, concrete
ambiguity or failure path, impact, and smallest correction or decision question. A material
unreviewed area cannot pass.

## Review cohort and human gate

Correct specification defects and rerun the affected reviewers; stop after three unsuccessful cycles.
Ask the human only for a decision gap, then resume automatically when it is answered. For interactive
`specify`, when the selected reviews pass, present the requirements and technical approach together
for explicit human approval before declaring the specification complete. In both source modes,
record approval evidence as the approving chat-turn/body digest in the machine-local review record;
never create, edit, or delete a source comment. Direct `run` does not require a historic approval
artifact, but must resolve and confirm any new material design choice before coding. A review PASS
does not substitute for human agreement.

Selected reviews must ground acceptance criteria and scope. Other semantic domains are conditional:
assign and verify them only when they materially affect the requested behaviour. A reviewer must
not fail a concise requirement merely because an irrelevant domain has no dedicated heading.

## Machine review record

Persist a safe `Specification Review Record` JSON object containing the current requirement
reference, source record, contract files, every review artifact and disposition, and optional
approval identity as a separate machine-local artifact in both source modes.
Never append it to the source description or Local Markdown requirement: human-facing requirements
contain only the concise specification contract. Redact
protected data. The record is traceability, not proof that a reviewer ran; L3 performs the
current policy-selected clarity assessment before planning.

Cross-session traceability comes from the machine-local record. Do not paste the source record,
phase inputs, reviewer responses, adjudications, hashes, verdicts, or canonical JSON into the source
description, and never use a source comment as attestation transport.

A normal L3 intake reads the current source and dispatches the policy-selected clarity review. It never requires
this prior record, reconstructs approval, or blocks on a changed requirement hash. Formatting-only
changes continue; material clear changes are re-reviewed; semantic or decision gaps still fail
closed.
