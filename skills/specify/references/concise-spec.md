# Compact specification example

Synthetic facts: session-only environment selection; existing permission checks and the Primary default.
The human has settled these choices. The draft below is the entire requirement, not a quota.

```md
## Problem / Context
Refreshing resets the selected environment to the Primary environment.

## Objective
On-call engineers keep inspecting the environment they selected after a refresh.

## Acceptance Criteria
- AC-01: Given Secondary is selected and permitted, When I refresh this tab, Then Secondary remains selected.
- AC-02: Given the saved selection is invalid or no longer permitted, When the tool loads, Then it uses the existing permitted default.
- AC-03: Given a new tab has no saved selection, When the tool loads, Then it selects the Primary environment.

## Technical Notes
- Persist only for this tab session; do not change permissions.
```

Validate the extracted draft with `scripts/validate_spec.py`. Do not append this explanation to
the ticket. Preserve the original description in a complete local backup and share its location,
not a duplicate inside the replacement or a massive chat echo. Ask about persistence lifetime only
when unsettled; do not ask about storage API mechanics or invent analytics/latency targets.

## Translate developer shorthand into a readable contract

Before: “210/400 replay on boot, same eid; RS dedup; no ack resend; race 100 first-final wins;
buyer cancel pre-redirect = local fail. Exactly-once publication to RS.”

Synthetic, verified facts for this example only; they are not default gateway state definitions.
Code and the user confirmed each state meaning, the event-ID rule and both exclusions. RS's
duplicate handling belongs to another ticket and is unverified here, so the draft drops
the “exactly-once” promise and names that work as out of scope.

Proposed summary: `[report-export] Recover unpublished export results for the report service`.

```md
## Problem / Context
After a verified gateway callback, a crash or failed database commit can leave the final result unpublished to Kafka. The report service then keeps the record in PROCESSING.

## Definitions
- **100**: Awaiting upstream callback or timeout.
- **210**: Callback verified; result awaiting publication.
- **400**: Publication pending or failed; retryable.
- **500**: Final FAILED.
- **900**: Final SUCCESS.

## Objective
Every verified gateway result is published to Kafka for the report service with its original result and event ID, even after publish failures, failed commits or restarts.

## Acceptance Criteria
- AC-01 (Happy path): Given a verified callback, When its result is published and committed, Then success moves to 900 and failure to 500.
- AC-02 (Publish failure): Given publishing fails, When the retry job runs, Then the record stays in 400 until a publish succeeds.
- AC-03 (Commit failure): Given a publish succeeded but the commit failed, When recovery runs, Then it republishes with the original event ID.
- AC-04 (Restart): Given records in 210 or 400, including zero-attempt records, When the adapter restarts, Then it publishes them.
- AC-05 (Race): Given a record in 100, When an upstream result and a timeout both arrive, Then the first committed final state wins and the later one is ignored.
- AC-06 (Buyer cancel): Given the buyer cancels before redirect to the gateway, When cancellation is processed, Then the record is FAILED locally without a Kafka publish.

## Out of Scope
- Duplicate-event handling in the report service (ABC-3956).
- Resending acknowledgments upstream.

## Technical Notes
- Never regenerate transaction or event IDs on republish.
```

This draft is over the length target. The reason given in chat beside the draft, not inside it:
six ticket-owned outcomes with distinct test oracles, and state codes the ACs depend on. If a
code's meaning or a consumer guarantee is unknown, investigate rather than borrowing these
meanings. Over-target length never authorizes background history or implementation mechanics.
