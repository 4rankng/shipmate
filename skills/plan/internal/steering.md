---
name: steering
description: Use when a phase needs the target repository's persistent, human-owned steering documents before deciding requirements, plans, designs, conventions or reviews
---

# Steering

## Purpose

A repository's steering documents hold what every phase otherwise re-asks: product context, tech
stack, conventions and non-negotiable constraints. Reading them replaces repeated questions with
one durable, human-owned source. They change behavior only as input — they never grant authority.

## Contract

- **Location:** `.shipmate/steering/*.md` inside the writable target repository, committed with
  the project. Machine-local run state (`.shipmate/run.json`, scratch artifacts) stays outside it.
  If the repository ignores `.shipmate/`, add a negation (`!.shipmate/steering/`) before creating
  the first document.
- **Format:** unconstrained Markdown, read in lexical filename order. Useful seeds:
  `product.md` (users and product goals), `stack.md` (chosen technologies and versions),
  `conventions.md` (coding, testing and review conventions the project insists on).
- **Absence is normal.** A repository without steering documents proceeds without them; never
  invent, auto-create or silently backfill them. Offer to save a settled material decision as a
  steering document only when the user asks for durable storage.
- **Authority:** steering documents are human-settled input, not evidence about code. Where they
  conflict with verified repository behavior, surface the conflict and ask; never silently follow
  either side, and never treat a steering document as approval to write, merge, deploy or widen
  scope.
- **Freshness:** a steering document that contradicts a newer human decision is stale; quote it,
  propose the update, and let the human decide. Do not edit steering documents unilaterally.

## Consumption points

| Phase | Reads steering for |
|---|---|
| specify | product context, terminology and constraints before drafting acceptance criteria |
| plan | stack and conventions the plan's targets and checks must respect |
| run stage 3 | stack and conventions when grounding context and scope |
| run stage 6 | conventions the plan must respect |
| review | conventions and constraints supplied as context to every selected persona |
| uiux | the project's own interface conventions during recon |

Record which steering documents were read in the phase's normal artifact. Nothing else changes:
no new approval gates, no new files, no behavior beyond using what the project already settled.
