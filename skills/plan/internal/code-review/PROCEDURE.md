---
name: code-review
description: Use when an immutable candidate must pass independent requirements/code-quality and security/reliability review before delivery
---

# Code Review

## Core contract

Read [workflow-policy](../workflow-policy.md) for risk selection, resume and pending checks.

Review an immutable candidate, not a moving worktree. Read the bundled `reviewer` procedure,
`persona-catalog.md`, `candidate-review-envelope.md`,
[`candidate-review-dialogue.md`](../reviewer/references/candidate-review-dialogue.md), `findings-and-adjudication.md`, and the
policy-selected candidate persona references. Use explicit efficient model routing and native distinct review
contexts; never invoke another agent CLI or silently self-review.

Record the current requirement, target/base/context identities, candidate commit/tree/binary-patch
identities, complete diff, impact surface, acceptance-criterion evidence, repository constraints,
verification evidence, and validated read-only snapshot roots. Add plan and earlier phase records
when available. An existing MR may be reviewed as `adopted-candidate` using current requirements,
the complete diff, and verification evidence; do not fabricate missing L3 provenance. Recompute
identities and cleanliness before and after reviews.

## Ordered gate

Before dispatch, read the bundled
[review-request source](../../third_party/obra-superpowers/skills/requesting-code-review/SKILL.md.txt)
and its [context template](../../third_party/obra-superpowers/skills/requesting-code-review/code-reviewer.md.txt).
Use their focused context preparation, not their generic prompt verbatim. Supply current
requirements, the complete integrated diff and base, affected callers, actual test evidence and
known limitations; do not send the controller's full session or its desired verdict.

Shipmate's named personas, envelope and finding schema override upstream severity/verdict formats,
per-task reviewer quotas and merge-readiness language. A “reasonable expectation” is not permission
to invent a requirement: ground a defect in the agreed contract or demonstrated correctness/security
impact; ask about material missing decisions. Reviewers do not create snapshots, mutate repositories
or delegate further reviews. The controller prepares read-only context. Requirements compliance
precedes code quality within the existing invocation, not two additional agents per task.

1. Run [edge-case scouting](references/edge-case-scouting.md) and pass its output as the impact
   surface. For each changed hunk include the enclosing function and the traced callers, guards and
   data flow it depends on; prefer these slices to whole files while keeping snapshot access for
   follow-up reads.
2. Dispatch **Requirements & Code Quality Reviewer** (`requirements-code-quality`) using
   `requirements-code-quality-reviewer.md`. Its single invocation must complete requirements-first
   traceability before assessing quality.
3. For higher-risk or uncertain work, dispatch **Security & Reliability Reviewer**
   (`security-reliability`) independently using `security-reliability-reviewer.md` against the same
   immutable candidate. For qualifying low-risk work, run the baseline security check defined by
   the shared workflow policy instead.
4. Treat the selected requirements/code-quality reviewer as the lead challenger. If a challenger
   raises a finding, uncertainty, or a concrete verification question, dispatch one distinct,
   non-voting candidate-review-responder using the dialogue contract. It answers or proposes from
   the immutable evidence; it does not add a persona, verdict, or approval. Do not spend a responder
   invocation restating a clean PASS.
5. Adjudicate every evidence-backed finding. A read-only `review` returns the responder's answer
   or proposal without mutation. In an authorized `run`/fix, the responder may repair accepted
   findings through TDD only in a separate writable worktree, then return the proposed candidate,
   verification, and residual concerns. Create a new local candidate and restart every affected
   policy-selected challenger review independently after any code change. A new business, data,
   security, or architecture decision receives one focused question and resumes when answered; it
   is not a permanent workflow exit.

Run at most three repair cycles. Rebuild stale inputs. Missing independent review context is
`review-pending`; inaccessible material scope is reported explicitly. After the third unresolved
blocking cycle, report `candidate-review-failed` with the current evidence and next decision.

Persist the exact response and adjudication artifacts with unique run IDs and distinct review inputs.
Requirement and plan hashes are optional audit metadata, not admission locks. The candidate commit
SHA remains mandatory because all selected candidate reviewers and CI must evaluate the same code.
Derive the candidate cohort/gate only after every policy-selected review passes the same identities
with no material unreviewed area. A missing independent context is `review-pending`, never a
self-certified pass. The bounded passing statement is
`NO_BLOCKING_FINDINGS_IN_REVIEWED_SCOPE`; never claim universal correctness or security.
