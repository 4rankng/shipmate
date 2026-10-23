# Candidate Challenger–Responder Dialogue

## Purpose

Candidate review is a short evidence-based dialogue, not a second approval ceremony. The existing
selected candidate reviewer is the challenger: it probes the current immutable candidate for a
real requirement, code-quality, security, or reliability shortcoming. For higher-risk work, the
policy-selected security/reliability reviewer remains an additional independent challenger; this
does not create a new persona or quota.

When a challenger raises a material finding, uncertainty, or a concrete verification question,
dispatch one distinct **candidate-review-responder**. It is not a reviewer persona and not a voter:
it cannot alter a verdict, adjudicate a finding, approve a candidate, or certify its own repair.
Do not dispatch it merely to restate a clean PASS.

## Inputs, model, and boundary

Give the responder the current requirement, candidate identity, complete challenger response,
finding IDs/questions, relevant snapshot paths, and the exact evidence needed to answer. From
current host metadata, the controller selects a supported Claude/GPT route in the balanced
capability class. Request supported non-maximum reasoning effort when configurable; otherwise
leave it unset and verify the documented/default route is not maximum. If balanced is absent, use
the closest supported efficient Claude/GPT route and record why. Never inherit an unknown,
frontier, `xhigh`, `max`, or `ultra` setting. Return `review-pending` only when no explicit safe
route is available; do not hard-veto merely because a historical model alias is unavailable.

The immutable candidate snapshot is read-only evidence for both roles. For a read-only `review`
action, the responder may only answer or propose a resolution, evidence, test, or clarification;
it must not edit code, run repairs, commit, push, comment, approve, or change external state.

For an authorized `run`/fix, the responder may repair accepted findings only in a writable
implementation worktree separate from the immutable candidate snapshot. It may reuse the existing
run-owned implementation worktree when that separation is preserved; it must not create another
worktree for every repair round. It must leave the immutable candidate snapshot unchanged, use
focused tests, and return changed paths, commands/results, remaining concerns, and the proposed
new candidate reference. It cannot invent a missing business or material-risk decision; return one
decision-bearing question instead.

## Bounded loop

1. The controller preserves exact challenger responses and sends the responder only supported
   questions/findings. The responder answers each ID with evidence, proposed disposition, and—when
   authorized—an implementation/test plan or repair result.
2. The controller independently adjudicates. Rejected or unanswered findings do not permit a
   repair by implication. A read-only review returns the answer/proposal and remains non-mutating.
   For each disputed material ID, require the responder's code evidence, verification result or
   concrete counterexample under findings-and-adjudication. Agreement alone cannot close it.
3. After an authorized repair, create a new candidate identity and issue a fresh independent
   challenger invocation over the full current diff plus affected delta. The challenger must not
   self-certify the responder's repair; use a new run ID and distinct review context.
4. Repeat only for supported affected findings, at most three repair cycles. Preserve evidence and
   report the unresolved finding and required decision after no progress or the third cycle.

A follow-up starts from the prior finding IDs, proposed repair and changed surfaces, then inspects
the full current diff and affected callers. Recheck for regressions caused by the repair; do not
merely confirm that the named lines changed. Preserve unaffected settled decisions and evidence
with the existing freshness rationale. Do not reopen resolved arguments without contradictory
new evidence or repeat earlier phases for unrelated formatting changes.

Persist the responder response separately with its input identity and SHA-256. It is traceability
for the controller, never MR/Jira prose and never a candidate-review verdict or cohort member.
