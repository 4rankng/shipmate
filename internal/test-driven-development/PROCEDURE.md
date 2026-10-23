---
name: test-driven-development
description: Use when implementing a feature, bug fix, refactor, or other observable behavior change
---

# Test-Driven Development

## Core principle

Prove the test can detect the missing behavior before writing production code.

## Red, green, refactor

1. Identify one behavior and the production change that would make its test fail.
2. Write the smallest test against real behavior; mock only an unavoidable external boundary.
   Derive expected values by hand from the requirement, never from the code under test.
3. Run it and confirm it fails for the expected missing behavior, not setup or syntax.
4. Implement the smallest change that passes.
5. Run the focused test and affected suite.
6. Refactor only while tests remain green, then repeat.

Code written before its test is not test-first evidence. Remove or set aside exploratory code and implement from the failing test unless the user explicitly approves a documented exception for generated code, configuration-only work, or a disposable spike.

A test that has never failed proves nothing. When it was written after its code (repair, CI fix, adopted or delegated work), run it against the recorded base in a detached snapshot: it must fail there for the expected reason (a missing new interface counts) and pass on the candidate. A test passing on both is not acceptance-criterion evidence.

## Domain invariants

Tests must cover the affected domain boundaries and negative cases, including:

- authorization, access, and entity or tenant ownership;
- idempotent retry without duplicate side effects or audit events;
- allowed state transitions and concurrent updates;
- input validation, data integrity, precision, and contract fidelity;
- dependency ambiguity, timeout, duplicate delivery, and out-of-order event behavior;
- audit evidence without restricted project or customer data leakage.

For changes with exact values or external side effects, additionally prove precision and rounding,
idempotency across external calls and audit events, and ambiguous downstream outcomes.

Use synthetic identifiers and values. Do not copy restricted production data into fixtures or
prompts.

## Pressure and completion

Do not skip, weaken, quarantine, or rewrite a failing control merely to unblock delivery.
Change an existing test assertion only when a cited acceptance criterion changes that behaviour. If a test contradicts the current requirement, stop that slice, cite both and ask the one clarification question; never special-case fixture inputs, branch on test-only state, or shape code to satisfy a test the requirement does not support.
Investigate flaky behavior with the bundled sibling
[`systematic-debugging` skill](../systematic-debugging/PROCEDURE.md). Temporary containment requires
explicit risk acceptance and remains a reported gap.

If the test runner or dependency is unavailable, preserve the change boundary, state what could not
be proven, and stop before claiming success. Finish with the bundled sibling
[`verification-before-completion` skill](../verification-before-completion/PROCEDURE.md). Outside
`shipmate`, remote retry and push remain separately approved. Inside L3, return to its controller,
which owns its authorized feature-branch push and draft-pipeline repair loop. Release, deployment,
ready/approve/merge, production writes, and protected-branch changes always remain human gates.
