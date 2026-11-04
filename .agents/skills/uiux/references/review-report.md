# Review report

The output format for AUDIT mode. A review is not finished until this report is written. The severity ladder, findings cap, evidence rules and verdict rules live in SKILL.md; this file is their shape.

## 1. Scope

State the resolved scope — screen, flow, feature, branch or diff — and what it excluded. Never imply uninspected surfaces were reviewed.

## 2. Coverage

| Domain | Evidence inspected | Result |
| --- | --- | --- |
| Accessibility | Files, components, states or checks run | Findings count or `Clear` |
| Layout | … | … |
| Writing | … | … |
| Typography | … | … |
| Colors | … | … |
| UI polish | … | … |

`Clear` means inspected with no actionable finding. A domain not inspected is `Not reviewed`, with the reason — never `Clear`.

## 3. Findings

One table, ordered by trigger findings first, then severity, then reach:

| Severity | Location | Before | After | Why |
| --- | --- | --- | --- | --- |
| HIGH | `src/Dialog.tsx:42` | `<button><XIcon /></button>` | Add `aria-label="Close"` | The icon-only control has no accessible name |

- `Location` is `path/to/file:line`, or the exact screen and component when the artifact has no source files.
- `Before`/`After` show the current implementation and an actionable replacement, each written in the project's own idiom.
- `Why` names the violated rule or trigger and its user impact.
- One row per root cause, with every confirmed location in that row.
- Findings beyond the 15 cap: triggers are listed first and the exclusions counted in prose — a cap never hides a blocker.
- With no findings, omit the table and state "No actionable interface findings."

## 4. Verification

List each check or interaction with the exact command or steps and the observed result. Separate passed checks from checks marked `Not verified`. Never report an unmeasured contrast value.

## 5. Verdict

One of two:

- `Block` — one or more HIGH findings remain. Do not ship until they are fixed.
- `Approve` — no HIGH remains; MEDIUM and LOW stay in the table as work to do.

`Approve` covers only the domains the coverage table shows as inspected; name every `Not reviewed` domain in the verdict line.
