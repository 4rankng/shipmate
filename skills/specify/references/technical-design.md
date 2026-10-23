# Settle requirements and design together

Use the bundled grill-with-docs interview to walk the relevant design decisions in dependency
order. Read the owning code and existing CONTEXT.md, CONTEXT-MAP.md and ADRs when present; do not
ask the human to supply facts you can inspect. No glossary or ADR needs to be created for this step.

## Repository fit before proposing new code

Trace the nearest existing implementation through a real caller, framework defaults, shared
utilities and relevant tests. Check the installed dependency version, not an assumed API. Compare
the requested behaviour with what those paths already provide before proposing helpers, wrappers,
validation, retries, endpoints or storage. An unsuccessful name search is not proof of absence;
inspect the owning module and a comparable call path, and state any evidence you could not obtain.

For each proposed new component or layer, identify the requirement it serves, the existing option
examined, and the concrete capability gap that prevents reuse. Keep search paths and detailed
evidence in working notes; put only consequential decisions and their reasons in the spec.
No gap means reuse or extend the native path, not a parallel implementation. Do not add unused
APIs, pass-through wrappers, speculative extension points, redundant validation or fallback
behaviour for hypothetical future needs. Missing code evidence calls for investigation, not
invented design or asking the human to locate utilities.

Reuse is not a blanket ban on new code: preserve demonstrated protocol, security and correctness
needs that the existing utility cannot meet. Prefer a small local extension using the repository's
pattern over a new framework. Escalate only a material unresolved trade-off to the human.

## Interview the consequential choices

For affected trust/data boundaries, apply [secure engineering](../../../internal/secure-engineering.md).
Trace the real repository controls before proposing new ones, then settle only unresolved access,
data-handling or failure decisions with the human. Carry focused abuse cases into the existing
Given/When/Then criteria; no extra specification section or mandatory question quota.

Challenge both what the change must do and how it will fit the system. Follow applicable branches,
not a fixed questionnaire:

- Which existing component owns the change? Can it reuse an existing path instead of adding one?
- What interfaces, data ownership, persistence and state transitions change?
- What happens on partial failure, timeout, retry or concurrent requests?
- What compatibility, authorization, migration, rollout or rollback choices affect correctness?
- How will tests demonstrate the chosen behaviour and its important failure paths?

Use a concrete scenario to test each consequential assumption. Where a choice remains, compare
the viable approaches, their costs and risks using the same scenario. Recommend from the user's
known priorities and inspected evidence; ask for a missing goal rather than guessing it. Ask one question at a time.
Wait for the answer before resolving dependent choices. Requirements approval alone does not
authorize the agent to silently choose a new service, storage system, public interface or recovery
policy. Do not postpone such decisions to coding or rely on reviewers to make them for the human.

Settle the technical approach, not every line of code. Naming, file placement and equivalent
repository-native implementation mechanics remain the agent's responsibility. A small change
may need only a sentence explaining reuse of an existing path; do not invent alternatives,
questions or a new architecture to make the interview look thorough.

## Confirm and hand off

Keep the final spec concise. Record consequential choices and their reasons under
`Technical Notes` or a named accessible supporting reference; keep the interview transcript and detailed
implementation plan out of Jira. A technical constraint that determines correctness belongs in
the spec even when it is not directly user-visible.

Before ending Specify, present the requirements and approach together for human confirmation.
Existing explicit decisions count: do not re-interview settled choices or require hashes,
approval files or comments. The final confirmation covers the assembled draft, not just an
earlier statement of the goal. Until it is agreed, read-only investigation and local drafting may
continue, but do not start coding. Specify approval does not itself authorize implementation.

When Run starts directly from an existing source, inspect requirements and design before coding.
An instruction to implement an already explicit design is sufficient agreement to that design;
a generic request to run is not approval of a new material design the agent later proposes.
Resolve and confirm only the missing choices, without requiring a separate Specify invocation or
restarting settled work. If planning or coding reveals a new material trade-off, pause affected
implementation, settle that decision with the human and resume. In unattended mode report the
same needs-input point rather than guessing.
