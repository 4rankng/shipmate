# Plan Verification Methods

Use these roles to verify the current persisted implementation plan against the current clear specification and
actual repositories. They are evidence methods, not sources of new requirements.

## Fact Checker

Verify every cited file, symbol, endpoint, schema, configuration key, test target, and command.
Use repository search; cite `file:line` for positive and negative claims. A plausible name that
does not exist is a failed plan claim.

## Flow Tracer

Trace claimed behavior from entry point through guards, branches, calls, events, retries, and early
returns. Check concurrency and ordering guarantees rather than assuming synchronous behavior.
Return the traced path with `file:line` evidence or the concrete break in causality.

## Scope Auditor

Verify state lifetime, ownership, affected services, writable-repository boundary, and all
instantiation sites. Look for hidden cross-request state, duplicate concepts, indirect consumers,
and a second repository that the plan would need to change.

## Contract Verifier

Enumerate callers and consumers of every interface change. Check API/schema compatibility, tests,
generated output, configuration, CI, deployment order, and rollback. Never accept “update all
callers” without a concrete list or count backed by repository evidence.

## Whole-plan consistency sweep

After any accepted finding changes the plan:

1. list the changed decisions, names, files, interfaces, dependencies, risks, and task order;
2. reread the complete plan;
3. search for stale or contradictory copies of every changed claim;
4. reconcile the AC map, tasks, test evidence, rollout, rollback, and non-goals;
5. leave unresolved contradictions explicit and return `UNABLE_TO_REVIEW`.

Complete the sweep before capturing the refreshed plan and rerunning affected policy-selected
checks. Low-risk work uses an independent Architecture & Simplicity review; higher-risk work uses focused independent
personas. Retain unaffected evidence explicitly, not as an assumed historical PASS.
