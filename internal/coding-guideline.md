# Coding guideline for L3 implementation and review

Adapted from the supplied payment-service coding guideline. Apply the engineering principles to
existing and new services in any team's repository. Financial rules apply only to money-handling
code; service-creation requirements apply only when a new service is authorized. Service-specific
agent instructions, approved contracts, protocol rules and security requirements govern the
concrete implementation. Resolve a material conflict rather than silently replacing them with this
guide. Inspect current code first: an older implementation is evidence of behaviour, not
automatically the pattern to extend. Do not introduce payment-specific dependencies into other teams.

Run applies this guide while planning, implementing and verifying. Review checks the actual diff
and affected callers against applicable rules, with code evidence and concrete impact. Do not
create a finding for an irrelevant rule or demand a new document for each heading. Apply
[secure engineering](secure-engineering.md) alongside it, without duplicating its checklist.

## 1. Understand the change before writing code

1. State the user-visible or operational problem, its likely root cause, and the behaviour that
   must change. Identify the smallest observable success case and the failure cases that matter.
2. Trace the full operation: caller or event, validation, business decision, persistent state,
   downstream effect, response or acknowledgement. Read the interface, implementation,
   configuration and tests at each affected step.
3. Identify invariants before editing: units, identifier meaning, authorization, state transitions,
   idempotency, ordering, deadlines and side effects that may already have occurred after an error.
4. Compare intended behaviour with the current contract and code. Make discrepancies explicit.
   Resolve material product, protocol or ownership decisions with the accountable human;
   do not silently invent a rule to fill a gap.
5. Compare a focused change in the owning service with a shared library, cross-service contract
   change or new service. Choose the least complex option that meets the requirement and
   preserves invariants. Record the reason when a wider option is necessary; obtain scope
   authority before adding another writable repository or service.

## 2. Keep ownership and boundaries clear

- One service owns each business decision and authoritative record. Callers depend on its
  published contract, not its tables, internal models or deployment details. Define the source
  of truth when a value appears in more than one service.
- Place code by responsibility using the target's conventions: transport handlers decode,
  authenticate, validate and map results; domain logic decides; storage owns queries,
  transactions and conditional updates; adapters own external protocols; consumers and jobs own
  trigger and acknowledgement behaviour. A handler must not duplicate domain or SQL rules.
- Wire dependencies through the established composition path. Prefer explicit constructor or
  injected interfaces at testable boundaries. Do not copy package-level mutable clients/DAOs
  merely because legacy code has them. Keep interfaces small and tied to a real consumer.
- Share code only when callers need the same stable behaviour. Helpers should expose an invariant;
  shared packages need ownership and versioning. Do not generalize superficially similar flows
  whose failure or regulatory rules differ.
- Keep the diff focused. Exclude unrelated refactors, dependency refreshes, generated-file churn
  and formatting sweeps unless needed for correctness. Remove dead paths introduced by the change
  and correct nearby comments or documentation made false by it.

## 3. Design contracts before implementation

- Before adding an API/event, settle callers, fields and units, required/optional values,
  authentication, errors and compatibility. Give each identifier one meaning; explain relations
  between identifiers only where a consumer needs them.
- Preserve deployed callers and stored messages. Breaking changes need versioning or staged
  producer/consumer rollout. Check older messages, missing fields, duplicates and unknown enum
  values. Never assume all services deploy together.
- Change generated contracts at their source, then use the verified service generator. Inspect
  headers and repository commands first. Do not hand-edit generated API, client, mock, route or DAO
  output. If generation is unavailable, preserve the source change and report the missing check.
- Validate untrusted identity, authorization, values, ranges, formats and sizes at the boundary.
  Recheck state-dependent business preconditions at the authoritative mutation boundary; a
  caller's earlier validation is insufficient for financial or other sensitive state changes.
- Map internal failures to stable public errors. Never expose SQL, raw downstream responses,
  secrets, customer data or sensitive protocol payloads through an API error.

## 4. Preserve financial and state correctness where applicable

- For money, use the existing money type and contract-defined unit, with currency. Use integer
  minor units or decimal types as required; never binary floating point for new financial
  calculations. Define rounding and scale at conversions and test them.
- For externally visible mutations, define durable idempotency and outcomes for identical and
  conflicting replays. Enforce uniqueness or conditional writes in storage where needed; a
  process-local check alone cannot protect retries across instances or restarts.
- Preserve unrelated fields on updates. Compare expected state, write only owned fields and
  handle a lost race by reading the winner when the contract requires a result. Keep workflow
  progress separate from business result and downstream status.
- State what is atomic. A database commit and network send are not one transaction. For external
  effects, identify when intent/result become durable, crash windows and recovery/reconciliation.
  Reuse an outbox/workflow only when its guarantees fit; do not add one by reflex.
- After a send, a timeout, disconnect or server error means an unknown delivery outcome unless
  the protocol proves otherwise. Classify before-send, after-attempt and confirmed rejection
  before retrying. Check duplicate handling and saved state; never add blanket retries to debits,
  captures, rail messages, reversals or publication.
- For async work, define acknowledgement, retry, stop and failure routing. Assume at-least-once
  delivery unless the infrastructure contract proves more. Test duplicates, delays, reordering
  and failed delivery when they affect correctness.
- Keep states, events and allowed callers explicit, and test invalid transitions. An HTTP/queue
  acknowledgement, adapter acceptance or successful event publication is not financial completion.

## 5. Make failures diagnosable without leaking data

- Propagate context, cancellation and deadlines. Bound waits/retries to the operation's time
  budget. Background work needs durable input or an explicit recovery design before outliving
  the initiating request.
- Return enough internal error context to locate the failing step, preserving typed error
  identity where callers use it. Use existing transport error mapping. Avoid panics in request
  and business logic; startup may fail fast on invalid mandatory configuration.
- Use structured logs and existing trace/correlation IDs, safe references and operation/state.
  Redact credentials, account/personal data, signed messages and full payment payloads. Add
  metrics for meaningful failures or stalled work, with bounded tag cardinality.
- Use typed, startup-validated configuration through the existing deployment mechanism. Do not
  hardcode environment endpoints, credentials, account numbers, partner IDs, topic names or
  country behaviour. Flags need an explicit default and defined behaviour in each state.

## 6. Add a new service only with an authorized boundary

First compare extending the existing owner. Independent ownership, deployment or scaling must
justify network failures, consistency work, contracts, infrastructure and on-call burden. Record
the owner and reason. This checklist does not authorize creating a service or infrastructure.

For an authorized new service, establish applicable foundations before calling it complete:

1. Purpose, data owner, upstream callers, downstream dependencies and exclusions.
2. API/event schemas, authentication/authorization, errors, versioning, idempotency,
   compatibility and generated-code workflow.
3. Entrypoint, dependency wiring, typed configuration/secrets, health/readiness, graceful
   shutdown, timeouts and deployment settings using the repository's service framework.
4. Schema owner, migrations/rollback, uniqueness/concurrency, retention, side-effect ordering,
   retries, recovery and ambiguous-outcome reconciliation when state or delivery is involved.
5. Logs, traces, metrics/alerts for the critical path, operations owner and a usable recovery
   procedure explaining what can safely be retried or repaired.
6. Unit/integration and relevant producer/consumer contract tests, local run instructions,
   lint/build commands, required CI and compatible deployment order.

Do not copy a neighbour's engine, database, queue or framework extension to reproduce its directory
tree. Each dependency needs a reason in the service contract. Infrastructure/CI/deployment changes
retain the workflow's separate authorization boundary.

## 7. Verify and report at the right level

1. Work in the target module/project. Read its manifest, Makefile, linter, CI and nearest agent
   instructions; use its formatter and focused tests during implementation.
2. Test affected behaviour/invariants: validation, conversions, idempotency conflicts, write
   races, ambiguous downstream results and replay. Use a database or protocol fixture when mocks
   cannot prove the changed property.
3. Run relevant full-service, static, contract and integration checks available within authority.
   Coverage floors and toolchains are service-specific. Unit success does not prove deployed
   database, broker, external protocol or end-to-end behaviour.
4. Review the final diff for compatibility, generated output, migrations, secrets, logs,
   dependency changes and rollback. Report actual commands/results and unavailable or skipped
   checks. Follow workflow-policy for pending required checks; do not invent a universal floor.

Keep completion prose short: problem/chosen design, affected owner/contract, applicable financial
or delivery invariants, changes, verification and remaining operational/compatibility risks.
Use the existing MR/handoff format, not another report. Material unresolved decisions return to
the human with options before implementing dependent behaviour; routine mechanics stay with Run.
