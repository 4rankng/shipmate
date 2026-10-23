---
name: walkthrough
description: Use when someone wants a guided explanation of a Jira ticket, GitLab merge request or local branch, from behavior and interactions down to the important details
---

# Walkthrough with Shipmate

Apply [contextual questions](../../internal/user-questions.md). Ground drill-down choices and
prediction questions in a concrete situation; do not reveal a prediction's answer before the reader responds or asks to see it.

Explain the selected ticket or change so the reader can reason about it. This is a learning aid,
not an independent review, correctness verdict or approval. Walkthrough is read-only: never edit
code, Jira or Confluence, comment, label, approve, push, merge, deploy or change pipeline state.
Keep the explanation in chat; do not create reports, run records or metrics files automatically.

Read [target context](references/target-context.md) and load only the relevant source mode.
If the user supplies Jira and an MR, use the ticket for intent and the MR for implementation;
show mismatches without deciding which should change. A Jira-only session needs no code checkout.

## Explain in layers

Start with a short orientation: the problem, intended outcome, why this approach (from the ticket,
MR description or commit messages; say "Rationale not stated" rather than inferring it), source and
evidence limits. Then walk through one coherent behavior at a time, letting the reader choose where
to drill deeper:

1. **Behavior:** what changes or what the ticket requires, with a concrete before/after example
   when supported. For Jira, explain acceptance criteria and exclusions in plain language.
2. **Interactions:** ideally a Mermaid `sequenceDiagram` with real participants, important calls,
   responses and ordering. Mark Jira flows as required/proposed. If no meaningful interaction is
   evidenced, omit the diagram rather than inventing participants or a runtime flow.
3. **Details:** interfaces, fields/units, state transitions, ownership and the relevant failure or
   retry paths. In MR mode, link exact changed code and affected callers. In Jira mode, cite ACs
   and decision comments; do not invent code, endpoints or defaults to complete the narrative.

Keep the initial pass short. Explain implementation details or pseudocode only when they help
the reader understand this behavior; do not dump every file or test. Split a large MR into
behavioral slices before explaining layers inside each slice: group changed regions that define and
use the same function, type, field or contract, and list mechanical edits (renames, formatting,
generated code) in one line. Start with the slice holding the main logical change; a test that pins
the behaviour can supply its before/after example. Do not create stacked MRs or
rewrite commits. Name unresolved decisions and unread areas clearly.
Check comments, docstrings and example inputs against the inspected code before using them as
explanations. If they disagree, show the actual behavior and the mismatch; do not silently teach
the comment as truth. Use a concrete boundary input when it makes the difference clear.
End each slice with one optional, unscored prediction question grounded in that slice (for example, "what happens if the downstream call times out here?"), unless the reader asked for a summary only. Wait for an attempt or "show", then answer with citations. Never score or record these or turn them into a quiz.

End with the main points and any open questions. Offer `shipmate:quiz` on the same target when
useful; do not start it without the reader asking. Refresh context when the source changes.
A walkthrough may teach answers, so a later quiz report records whether this session included one.

## Source references

Cite the ticket URL plus AC heading/text or a specific decision comment for requirements.
For code, cite verified `file:line` locations and the inspected MR/local revision. Follow the host's
link format. Keep this explanation out of MR descriptions and external comments unless explicitly
asked to publish it; publication is a separate action.
