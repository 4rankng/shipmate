# Select content before polishing prose

An overloaded requirement is not fixed by replacing adjectives or hiding a long paragraph in a
table. First identify the change this ticket owns, the rules it relies on, and the details that
belong in the implementation plan. Then apply the bundled interview and unslop methods.

Back up the complete original locally before replacement. Do not duplicate it
in the new description. Aim for 1,200 characters and fewer than 150 words for the entire draft,
including links and headings. Exceed that target only for a strong reason stated beside the draft.
Retain essential outcomes, not historical narration.

| Content | Treatment |
|---|---|
| Goal, new observable behaviour, acceptance condition | Keep in Objective and Acceptance Criteria. |
| Ordering, authorization, data-integrity or failure rule that changes correctness | Keep explicit, even when technical. |
| Human-agreed component boundaries, interface, persistence or recovery choice | Keep essential decisions in Technical Notes or a named accessible supporting reference. Do not discard them as implementation detail. |
| Existing dependency contract that this change does not alter | Name the dependency and the essential compatibility constraint once. Reference its authoritative source rather than retelling its full workflow. |
| File navigation, retry-loop mechanics, helper names, commands, implementation sequence | Move to machine-local implementation notes unless the user explicitly made the detail a contract. |
| Review transcript, prior failed approaches, approval hashes | Keep outside the human requirement. |
| Repeated rule | Keep one canonical statement. ACs demonstrate it, not narrate its whole implementation again. |
| Unsettled or contradictory outcome | Investigate, then ask one material decision question. Editing is not permission to choose behaviour. |

Do not silently discard a requirement when moving implementation detail out of the ticket.
Retain necessary notes and exact constraints for the implementing agent. A dependency reference
is useful only when it identifies the relevant contract and the agent can retrieve it; if it
cannot, keep the necessary rule inline and record the evidence gap.

## Plain-language translation

Write for an engineer, QA tester or stakeholder who did not attend the discussion. Start with
the affected user's problem and required outcome. Explain an unfamiliar acronym on first use
only when relevant and verified in the supplied evidence or authoritative source. Describe a state
by its meaning; retain a numeric code only when implementation or testing needs the exact value.
Do not guess an acronym expansion or state mapping. Investigate first; ask one question only if
the remaining ambiguity changes a material requirement.

Each Given/When/Then names a concrete starting condition, trigger and observable result. Preserve
exact identifiers, side-effect ordering, failure outcomes and component ownership when they
determine correctness. Do not replace a precise rule with “handle correctly” or a vague benefit.

Distinguish retrying delivery, receiving duplicate events and applying a business update once.
Reusing an event ID does not itself prove consumer deduplication or exactly-once delivery. Do not
promise “exactly once”, “never stuck” or “automatic recovery” without evidence for that guarantee,
including its boundaries. A dependency's existing behaviour is not new work owned by this ticket.
Put another team's behaviour in Out of Scope with its owner or ticket, not in an AC. Explain a
term inline when one use needs it. Use the optional Definitions section only when several ACs depend
on codes or terms a reader could not otherwise follow; each meaning must be verified. The length
limits remain a target, and the accessible-reference policy still applies.

## Dense recovery example

Suppose one row mixes request validation, result selection, sending, publication, inherited
handler retries and crash recovery. Organize the ticket-owned decisions instead:

- Before the decision is committed: state which result wins and what conflicting action it prevents.
- After the decision is committed: return that result without choosing another outcome.
- Final state: respond without publishing again.
- Unknown record: distinguish confirmed absence from incomplete state and lookup failure.
- Delivery and recovery: distinguish build/sign failure from an attempted send that returned an
  error, if those conditions authorize different next actions.

Keep these as short Given/When/Then bullets. Reference unchanged parent
retry behaviour instead of copying its whole algorithm. Do not generalize away a real difference
such as “build failure does not resume” versus “a returned send error still resumes.”

An AC saying “Given any retry, signing, send or publication failure, When anything retries,
Then recover correctly” has no single test oracle. Use separate GWT scenarios for distinct outcomes:
build failure causes no resume; returned send error preserves the decision and resumes unfinished
work; final-state requests do not republish. Keep concurrency and true-absence checks when material.
These are synthetic illustration facts, not default behaviour for other systems.

The editorial pass should shorten repeated or misplaced content, not weaken the contract. The
reviewer checks that every removed material rule is retained once or has an accessible authoritative
reference. Validate the complete draft's length and structure before presentation/publication;
passing the validator does not establish semantic completeness.

## Meaning-preservation check

Before presenting a rewrite, compare it with the source for changed obligations: must versus may,
always/only/never, deadlines, counts, identifiers, permitted actors and the order of side effects.
A shorter sentence is wrong if it makes required recovery optional or drops a timing constraint.
For a dense contract, keep a temporary coverage note mapping each material source rule to its
retained statement or verified dependency. Do not publish that note as another specification section.

Do not move an essential rule into inaccessible machine-local notes just to shorten the ticket.
Notes may hold implementation mechanics; the human requirement or a named, verified dependency
must still expose every decision necessary to implement and test the requested behaviour.
If a rewrite loses a material rule, restore it before polishing again. If new text combines cases
with different observable results, split those cases. A general phrase such as “preserve the
allowed retry boundaries” cannot replace the concrete bounds it is meant to preserve.
