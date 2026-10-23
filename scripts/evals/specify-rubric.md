# Specify forward-trial rubric

Run cases from `specify-cases.json` in separate contexts with the actual installed skill and its
bundled references. Supply brief/evidence only, not this rubric. Save actual responses and loaded
paths outside the repository. These are model behavior trials, not deterministic unit-test passes.

| Case | What a useful response must do |
|---|---|
| translate-recovery-shorthand | Explain the pending-publication states and event ID in readable GWT bullets, using Definitions only for codes the ACs need. Put report-service deduplication in Out of Scope. Preserve no acknowledgment resend and unchanged report-service ownership; do not claim exactly-once transport or import other gateway behaviour. |
| unknown-state-meaning | Investigate available sources, then ask one material question about eligible recovery states/behaviour. Do not invent code meanings, retry transitions or a completed specification. |
| producer-consumer-guarantee-boundary | Explain the timeout ambiguity and duplicate-delivery possibility. Ask one consequential question to settle the unverified end-to-end guarantee; do not silently weaken the request or promise deduplication in another service. |
| reuse-framework-before-new-helper | Ground the design in the supplied framework and real sibling caller. Drop the proposed decoder, wrapper and middleware because no requirement or verified capability gap needs them. Retain current auth/error contracts, propose the native path and confirm the draft; do not ask the human to rediscover code facts. |
| reuse-does-not-erase-protocol-gap | Preserve raw signed bytes and follow the existing custom callback pattern because the default decoder has a demonstrated capability gap. Do not remove necessary behavior in the name of reuse or invent a generic framework. |
| requirements-clear-design-open | Investigate the two existing approaches, then ask one consequential technical-design question with recommendation and trade-offs before coding or completing the spec. Do not treat settled CSV criteria as settled architecture or invent file retention. |
| design-settled-confirm-draft | Draft concise requirements plus the agreed streaming approach, then request one confirmation of the assembled draft. Do not reopen settled architecture or ask about naming/file mechanics. Do not code or create extra design documents. |
| direct-run-design-open | Use Run for this case. Resolve the missing streaming-versus-worker design with the human before coding; a generic Run request cannot approve a subsequently invented architecture. Do not demand a historic approval artifact or separate Specify invocation. |
| requirement-original-content | Preserve a complete local backup, including links/tables, not a duplicate inside the replacement. Draft the concise format within both limits; no live write. |
| requirement-original-content-repeat | Back up the current legacy spec; do not nest it inside the new one. Preserve settled session-only behavior without reopening the superseded forever request. |
| requirement-original-content-empty | Do not invent original content or an empty historical section. Draft the settled contract without extra questions or live writes. |
| environment-lifetime-unknown | Ask one consequential lifetime/boundary question with recommendation and trade-off; do not invent persistence semantics or require an external tracker. |
| environment-settled | Produce a validated concise draft with GWT bullets and preserved permission boundaries; do not repeat the settled lifetime question. |
| preserve-clear-existing-spec | Preserve exact CSV behavior; ask for the actual source if it was not supplied rather than claiming to have read it; no write, hash gate, glossary or design detour. |
| ambiguous-retry | Surface the uncertain-outcome vs duplication conflict; ask a policy decision instead of inventing safe retries. |
| meaningful-spec-not-process | Capture local reusable sources, meaningful interview, concise output and separated review/repair authority; no new plugin/persona quota, installation or invented business outcome. |
| justified-over-target | Produce titled GWT ACs for all six distinct outcomes, Definitions for the codes they use, and Out of Scope for consumer deduplication. Exceed the length target with the reason stated in chat, not in the spec; propose a plain-language summary without "exactly-once"; no live write. |
| dense-status-recovery-contract | Preserve verification, deadline winner, final-state no-republish, true absence vs error, and build-failure vs returned-send-error distinctions. Use distinct test oracles and accessible supporting references when necessary to meet limits; never truncate, invent guarantees or create tickets automatically. |
| happy-path-only-brief | Cover success and state the unchanged rejection/timeout mapping once without inventing retries or new codes; ask zero questions. |
| surprising-default-disclosed | Reuse the shared formatter without asking; either ask one question about users without a last login, or draft an AC for them and name it beside the draft as a default; never leave it silent. |

Across all cases, verify that the local upstream files are actually read. A sentence should
contribute an observable outcome, necessary constraint, test scenario or scope decision. Flag
filler, unsupported numbers, copied templates without meaning, repeated questions and invented
answers. Treat 1,200 characters and fewer than 150 words as a target: over-target drafts must
state a strong reason beside the draft. Do not reward a short incomplete spec: verify all
obligations inline or through named accessible references.

For the review dialogue, separately trial an authorized fix and a read-only review. The latter
must remain non-mutating even when the challenger finds a real defect. A responder explanation is
not a verdict; supported fixes require current independent challenger verification.
