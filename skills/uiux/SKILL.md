---
name: uiux
description: Use when building, polishing or reviewing a web interface — design direction, accessibility, layout, typography, color, UI polish, motion and interface writing — ending in a ranked, evidence-based report
---

# UI/UX

Build, polish and review web interfaces in three modes. The domain rules live in the reference files; this file owns the mode triggers, the review procedure and the one shared severity and verdict vocabulary.

## Resolve the mode

- **BUILD** — a new page, feature or surface from a brief. Load [design-direction.md](references/design-direction.md) first and state the chosen direction before writing code. Load each domain file as that domain is implemented: [accessibility.md](references/accessibility.md), [layout.md](references/layout.md), [typography.md](references/typography.md), [colors.md](references/colors.md), [ui-polish-and-writing.md](references/ui-polish-and-writing.md). While choosing palette, type pairing or style, optionally run `scripts/lookup.py` for candidates — BUILD only; an audit measures the rendered pair, never a catalog row.
- **POLISH** — a small change to an existing surface. Load only the touched domain's file and apply its exact values.
- **AUDIT** — review an existing screen, flow, branch or diff. Run the procedure below, walking the domain files sequentially in review order.

Never require every reference file for a routine task.

## Review order

accessibility → layout → writing → typography → colors → UI polish. Foundational failures must not be hidden by polish. A domain not inspected is `Not reviewed`, never `Clear`.

## Evidence, not taste

A trigger is a failure whatever the style guide says. A density, radius or voice you merely dislike is not a finding. A documented project convention settles taste; it never excuses a trigger. In AUDIT, anti-slop and design-direction preferences are notes, not findings, unless they cause a concrete defect such as a failing contrast pair or a 320px breakage. A visually unconventional interface that works and meets its requirements is not a defect.

## Recon before judgment (AUDIT)

Identify the framework, styling system, design tokens, supported viewports and any preview or test command. Read what the project says about its own interface — AGENTS.md, design-system docs, CONTRIBUTING — and name what you found. Write every fix in the project's own idiom, never as an adoption request.

## Escalation triggers — HIGH on sight

When a domain file confirms one of these, it is HIGH on sight, never averaged down because the surface is minor:

1. An interactive control with no accessible name.
2. A keyboard-reachable control with no visible focus indicator.
3. A pointer-only path — reachable by pointer but not by keyboard.
4. Motion or auto-playing content that ignores `prefers-reduced-motion`.
5. Content or a control clipped, overlapped or unreachable at 320px width or 200% zoom.
6. A rendered contrast pair failing its required ratio.
7. Meaning carried by color alone.
8. A destructive action with no confirmation, undo or distinct treatment.
9. Truncated content with no way to the full value.
10. Content or a control reachable only past a scroll edge or behind a disclosure with no visible cue.
11. An error that names no way to recover from it.
12. A semantic color used against its meaning, such as the danger hue on a non-destructive action.
13. A state change carried by motion alone, with no color, icon or label left behind when the animation does not run.

Triggers rank above every other finding. When more fire than the cap allows, list them first and say how many the cap excluded. A cap shortens a report; it never hides a blocker.

## Severity ladder

- HIGH — blocks a task, misleads the user, hides content or controls, risks data loss or repeats systemically.
- MEDIUM — meaningfully harms comprehension, efficiency, adaptability or consistency.
- LOW — isolated polish with limited task impact.

Within a severity, rank by reach. A token or shared-component fix outranks the same symptom in one leaf.

## Fix priority — earliest that works

1. Delete. 2. Use the platform. 3. Reuse what the project has. 4. Correct the value. 5. Add.

A finding whose After adds something Delete would fix is itself a finding.

## Findings discipline

- At most 15 findings per review, trigger findings first, then severity and reach. One row per root cause, with every confirmed location in that row.
- Evidence is `path/to/file:line` plus the current implementation.
- A check you cannot run is `Not verified`, never a finding. Never report an unmeasured contrast value.
- Never pad toward the cap. A short review or no findings is a valid result.

## Verification duty

Inspect the rendered interface when runtime behavior or visual judgment matters, and report the exact command or interaction and its result.

## Verdict

`Block` when any HIGH remains, else `Approve`. Never approve coverage you did not inspect. Read-only by default: edit only when implementation is also requested, then re-run the relevant verification.

The report format lives in [review-report.md](references/review-report.md).

## Reference index

| File | Load when |
| --- | --- |
| [references/design-direction.md](references/design-direction.md) | BUILD: brief, archetypes, palette and pairing defaults, anti-slop bans, restraint |
| [references/accessibility.md](references/accessibility.md) | Semantics, keyboard and focus, forms, announcements, hit areas, zoom, motion gating |
| [references/layout.md](references/layout.md) | Grouping, alignment, reading order, responsive structure, RTL, growth |
| [references/typography.md](references/typography.md) | Rendering: line-height, weights, measure, truncation, punctuation, floors |
| [references/colors.md](references/colors.md) | Ramps, token roles, contrast measurement, dark mode, gamut |
| [references/ui-polish-and-writing.md](references/ui-polish-and-writing.md) | Surfaces, icons, motion values; interface copy, errors, confirmations |
| [references/review-report.md](references/review-report.md) | AUDIT: report structure, coverage table, findings table, verdict line |
| `scripts/lookup.py` | BUILD only: palette/pairing/style candidates from the vendored catalog |

Adapted from [jakubkrehel/skills](https://github.com/jakubkrehel/skills) (MIT), Anthropic frontend-design, and ui-ux-pro-max (MIT; palette, pairing and style data, https://github.com/nextlevelbuilder/ui-ux-pro-max-skill).
