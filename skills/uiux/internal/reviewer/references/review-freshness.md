# Review freshness

Specification and plan reviews establish that the current meaning is clear, feasible, and covered.
Their hashes are optional audit metadata, not admission or approval locks. Candidate review must
still establish that reviewers and CI checked the same code and evidence.

| Observed change | Action |
|---|---|
| No previous ticket, approval record, or digest | Read/create Local Markdown requirements, then perform normal clarity review. Do not require a ticket. |
| Only layout, emphasis, wording with identical meaning, AC row order, or source metadata | Continue using the semantic review; update the stored source copy. No reapproval or reviewer replay solely for formatting. |
| Clear material requirement or plan change, including negation, limits, status values, ownership or scope | Refresh affected specification/plan reviews, AC mapping and candidate reviews before progressing, even when code is unchanged. |
| Ambiguity, contradiction or unresolved decision affecting implementation | Ask one precise decision question, then resume the affected work when answered. Do not guess. |
| Candidate commit/tree/patch or target/base/context identity changes | Rebuild affected verification and selected candidate reviews against the new identity; require an independent delta or full readback. |
| Candidate evidence, contract, response or adjudication changes without code changes | Invalidate affected reviews and downstream gate under the candidate envelope; reconstruct affected evidence/reviews. No artificial code commit is necessary. |

Read the current description and one complete comment inventory; do not demand stable
timestamps or identical repeated reads. Pagination failure is incomplete evidence, not an unclear
specification: report it and retry the read, without guessing omitted decisions.
If concurrent edits are observed, compare their meaning using this table. Do not claim an atomic
source snapshot. If meaning cannot be determined safely, request the specific clarification.

Capture complete inputs per invocation and retain exact responses/adjudications for traceability.
Missing audit hashes never reject a clear specification or plan; missing actual evidence,
unresolved findings, unsafe repository changes and candidate identity mismatches still block.
