---
name: grill-with-docs
description: Use bundled upstream interviewing and domain-modeling skills to resolve material decisions without inventing requirements
---

# Interview and grill

## Load the upstream skills locally

Read these bundled source copies completely, then apply the L3 adaptations below:

- Matt Pocock's [grill-with-docs](../../third_party/mattpocock-skills/skills/engineering/grill-with-docs/SKILL.md.txt),
  its [grilling](../../third_party/mattpocock-skills/skills/productivity/grilling/SKILL.md.txt) interview,
  and [domain-modeling](../../third_party/mattpocock-skills/skills/engineering/domain-modeling/SKILL.md.txt).

When purpose or a material approach remains unclear, also read Superpowers'
[brainstorming](../../third_party/obra-superpowers/skills/brainstorming/SKILL.md.txt) for intent
discovery, meaningful alternatives and scope reduction. Do not load every vendor file for a
bounded, settled request.

These are real source files, not instructions to install or invoke another plugin. Source revisions,
licenses, dependency mappings and deliberate exclusions are in [the vendor guide](../../third_party/README.md).
Do not fetch upstream, use global skills, enable tools, or inherit upstream model/agent quotas.

## L3 adaptations

Apply the shared [contextual-question guidance](../user-questions.md). Put the current situation,
concrete example and decision consequences inside the question, including when using a host UI.

Use the upstream decision tree for both requirements and technical design, separating known facts,
settled decisions and unresolved choices. Read existing CONTEXT.md, CONTEXT-MAP.md and relevant
ADRs when present; check repository facts yourself. Use domain-modeling's concrete counterexamples to challenge
ambiguous terms and boundaries, even when the brief looks detailed. Keep each domain entity,
state, owner and downstream effect distinct; for money-handling changes, distinguish financial
invariants only when applicable. Never introduce unrelated financial requirements.

Ask **one question at a time**, not the upstream whole-frontier questionnaire. Choose the earliest
unresolved decision that changes an outcome, scope or material risk. Ask it as a complete question
naming the AC, scope or design choice it changes. For a design decision, compare viable options
against the same concrete scenario, including their important benefits and costs. Recommend only
from known user priorities and evidence, stating what would change the recommendation. If the
goal is unknown, ask about the desired experience first; ask factual clarifications neutrally.
Accept corrections outside the suggested options, then wait. Do not simulate the user's answer. Decisions already supplied by the
user stand unless new evidence contradicts them; ordinary reversible implementation details are
the agent's responsibility. Challenge assumptions with a realistic failure case, not hypothetical
complexity. Zero questions is correct when that inspection finds no material gap. Explain only
trade-offs supported by evidence; a shorter persistence lifetime does not itself guarantee that
permissions are current, and a recommendation is not a verified safety property.

In `specify` mode, keep the decision tree and evidence in local working notes, not the final spec.
Do not create glossary or ADR files, commit design documents, start a visual server, or hand off
to implementation/planning. Record a clarified term in the spec only if needed to interpret a
requirement. Apply Specify's [technical-design interview](../../skills/specify/references/technical-design.md).
Then return to `specify` only once observable success/failure, relevant boundaries and consequential
technical choices are settled. Write its concise draft with the agreed approach and obtain
one human confirmation covering requirements and design before completion or coding. Do not add upstream
per-section, path-classification or separate design approval ceremonies.

Outside `specify`, write a glossary or ADR only when the user asked for that artifact. Bundled
[context format](../../third_party/mattpocock-skills/skills/engineering/domain-modeling/CONTEXT-FORMAT.md.txt)
and [ADR format](../../third_party/mattpocock-skills/skills/engineering/domain-modeling/ADR-FORMAT.md.txt)
resolve those upstream references without another skill. An ADR is useful only for a hard-to-reverse,
non-obvious trade-off, not every answer. Return to the calling workflow; the caller owns authority.

Apply [unslop](../unslop/PROCEDURE.md) to prose. Preserve unresolved decisions and evidence honestly;
brevity never permits inventing an answer or removing a material constraint.
