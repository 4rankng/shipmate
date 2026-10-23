---
name: unslop
description: Use when drafting or revising human-facing implementation plans, technical documents, Jira or MR content, comments, and summaries so the writing is concise, concrete, and free of generic AI phrasing
---

# Unslop technical writing

## Purpose

Edit human-facing prose without changing its technical meaning. Make the text sound like an
engineer who understands this system: direct, specific, evidence-backed, and easy to review.

Apply this as the final writing pass for implementation plans, technical designs, Jira
descriptions and comments, Confluence pages, MR descriptions and comments, research findings, and
handoff summaries.

Do not apply it to source code, tests, commands, logs, SQL, JSON/YAML contracts, hashes, generated
artifacts, quoted requirements, or verbatim source evidence. Preserve identifiers, acceptance-
criterion IDs, links, citations, measured values, verdicts, and authority boundaries exactly.

## Editing pass

Read the bundled [Cursor pstack unslop source](../../third_party/cursor-pstack/pstack/skills/unslop/SKILL.md.txt)
and apply its concrete pattern checks with this procedure's technical-content exceptions. The
source is local and pinned; do not install pstack or load an external skill.

1. Preserve the facts, decisions, uncertainty, and required document structure.
2. Replace vague claims with the mechanism, source, command, result, file, or measured value.
3. Cut puffery, promotional language, generic conclusions, chatbot phrases, sycophancy, and filler.
4. Use plain words and active voice. Split sentences that require rereading.
5. Remove decorative emojis, forced groups of three, repeated synonyms, excessive bold text,
   title-case headings, and unnecessary em dashes or colons only when the calling document
   contract does not require them.
6. Keep meaningful nuance. Do not flatten a real trade-off into false certainty.
7. Read the result once more and ask: could this sentence appear unchanged in another project's
   document? If yes, make it specific or remove it.

## Technical-writing rules

- The calling workflow's required template, headings, labels, ordering, and formatting always win.
- State what changed, why this approach was selected, and what remains unchanged.
- Name the affected service, interface, state, file, command, or failure path.
- Separate verified facts, inferences, decisions, and unverified items.
- In verification artifacts and chat handoffs, give commands and results instead of saying
  "tested" or "validated." MR descriptions follow the bundled
  [description guidance](../gitlab-mr/references/mr-description.md) and omit testing details.
- Keep risks concrete: describe the failure and blast radius, not a generic risk label alone.
- End handoffs with the next human action when one exists.
- Prefer a short table or diagram only when it makes branching, ordering, state, or traceability
  clearer. Do not add structure merely to make the document look complete.

## Output check

Before publishing, confirm that the edit:

- preserved every technical claim and evidence identity;
- introduced no new requirement, result, approval, or certainty;
- contains no placeholder, invented source, or unsupported attribution;
- remains concise enough for the intended reviewer.

Adapted from Cursor pstack's `unslop` skill under the MIT License. The retained notice is at
`../../third_party/cursor-pstack/LICENSE` in the installed `shipmate` plugin.
