# UI polish and interface writing

One cheat-sheet for visual polish, motion and copy. The values below are exact, not ranges: `0.96` is not `0.95`, `150ms` is not `200ms`, `cubic-bezier(0.2, 0, 0, 1)` is not `cubic-bezier(0.4, 0, 0.2, 1)`. The optical nudges are the exception — starting points judged by eye.

A deliberate, consistent project convention — a motion language, a no-shadows style — is a preference, not a finding. The same detail done two ways within the project is a finding. A polish finding never outranks a broken interaction.

The reduced-motion requirement and focus rings live in [accessibility.md](accessibility.md); contrast measurement in [colors.md](colors.md); text rendering in [typography.md](typography.md).

## Surfaces

- Outer radius = inner radius + padding + border width, where the inset is even. Past `24px` of padding, or where padding is deliberately asymmetric, treat the layers as separate surfaces and keep each radius token.
- Shadows for elevation — layered transparent `box-shadow` values. Borders for structure — dividers, separators, table cells, selected states, and inputs (whose boundary needs the 3:1 rule).
- `border: 1px solid transparent` under a shadow ring, so forced-colors mode still draws an edge.
- Content images get a `1px` outline inset by `1px`: `oklch(0 0 0 / 0.1)` in light mode, `oklch(1 0 0 / 0.1)` in dark. Never a palette near-black, tinted neutral or accent — the tint shows as a colored fringe. Skip transparent artwork such as logos.
- Optical alignment by eye: `2px` less padding on a button's icon side, a play triangle shifted toward its point, asymmetric glyphs fixed in the SVG itself.

## Icons

- One icon family per surface. A stroke tracks the adjacent text weight: `1.5px` at weight 400 → `2.5px` at 700.
- Icons use `currentColor` and take hover, selected and disabled states from CSS color and opacity, never separate assets or hardcoded fills. Outline is the default variant; fill marks the active state.
- Under `dir="rtl"`, mirror only icons whose meaning follows reading direction; never mirror symmetric glyphs.

## Motion

- Press scale `0.96` over `150ms` with `ease-out`; a disabled control never scales. Opt out through the component's variant API or a `static` prop.
- High-frequency interactions — keystrokes, row hovers, tab switches — respond instantly, or with ≤150ms on `opacity`/`background-color` only. Expressive motion is for infrequent moments: first load, success, empty.
- Stagger infrequent entrances `100ms` apart, each entering with opacity + `4px` blur + `12px` translateY over `300ms` with `ease-out`. Never stagger routine interactions.
- Exits are shorter and smaller than enters: opacity + `4px` blur + a fixed `-12px` translateY over `150ms`. Remove instantly where motion adds nothing.
- Icon cross-fade on an infrequent state swap: scale `0.25`→`1`, opacity `0`→`1`, blur `4px`→`0`, with `{ type: "spring", duration: 0.3, bounce: 0 }` — bounce is always `0` — or `300ms` `cubic-bezier(0.2, 0, 0, 1)`.
- Transitions, not keyframes, for interactive state — keyframes run a fixed timeline and cannot reverse.
- Every animated state change leaves a static cue: a color, icon or label. Motion is never the only feedback channel.
- `initial={false}` on a state-swap wrapper so the default state does not animate on mount; never around an intentional entrance.
- Theme switch: disable every transition, force a style flush, restore after the next frame — otherwise every color transition fires at once.
- Name transition properties, never `all`. `will-change` only after observed stutter, naming the animated property, limited to transform/opacity/filter.
- Hover styling behind `@media (hover: hover)` — on touch, `:hover` latches after a tap. `-webkit-tap-highlight-color: transparent` where a control draws its own pressed state.
- `overscroll-behavior: contain` on scrollable dialogs, drawers, menus and side panels, so scrolling past their end never scrolls the page behind.

## Writing

- Inventory the strings first: find the translation layer (`t(`, `i18n.`, `<FormattedMessage`) and its locale files; list the noun per object, the verb per action, the case per element type. New copy uses that vocabulary. A synonym is a finding only where the same thing is named two ways.
- One voice, one vocabulary through a flow. Tone by stakes: success, onboarding and empty states warm; routine actions and settings neutral; errors and destructive confirmations calm and plain; data loss and security serious and explicit.
- "You", not "the user".
- Strings built whole: one message with placeholders and the locale's plural rules via `Intl`. Never `"You have " + n + " messages"`.
- Verb-first button labels: "Export CSV", "Delete project" — never "OK!". Icon-button names name the action, not the glyph. Links describe their destination; no duplicate bare "Learn more".
- One capitalization policy per element type; sentence case is the default.
- Toggles label the ON state: "Send read receipts", never "Don't send read receipts".
- Errors sit beside the field, state what happened and how to fix it — no blame, no "oops", no exclamation marks; positive phrasing: "Use at least 8 characters". An error that names no recovery is a HIGH trigger. A recurring error means redesign the interaction.
- Undo beats confirmation when the action is reversible and common: act, then "Project archived. Undo". Confirm irreversible, other-affecting or bulk actions: the title names action + object ("Delete 'Q3 report'?"), the body states what is lost with counts, buttons are verb + object never Yes/No, and accounts/workspaces/repos ask for the name typed.
- Empty states orient and offer one clear action. Filtered empties name the query and the exit: "No results for 'quarterly'. Clear filters".
- Placeholders show a realistic example in the accepted format — `name@example.com`, `DD/MM/YYYY` — never an instruction.

## Status copy

- Loading — a skeleton or progress indicator for waits over `300ms`.
- Empty — orientation plus one action.
- Error — what failed and the recovery path, near where it broke.
- Success — a brief confirmation: "Changes saved", never "successfully".

## Detection table

| Pattern | Fix |
| --- | --- |
| Same radius inside a padded parent | Add the padding to the outer radius |
| Ring with no transparent border beside it | `border: 1px solid transparent` |
| `transition-all` | Name the changing properties |
| `animation:` on a toggled class | A transition on the same properties |
| `active:scale` below 0.96 | `0.96` |
| `:active` with no `:disabled` exclusion | `enabled:active:` or `:not(:disabled):active` |
| Nonzero `bounce` | `bounce: 0` |
| Ungated transform/scale/filter motion | Gate under `prefers-reduced-motion: no-preference`; cross-fade opacity under reduced motion |
| Hardcoded icon `fill`/`stroke` | `currentColor` |
| Overlay scroll without `overscroll-behavior` | `overscroll-behavior: contain` |
| A changing value without `tabular-nums` | `font-variant-numeric: tabular-nums` — mechanics in typography.md |
| "Click here" or duplicate "Learn more" | Name the destination |
| "Oops"/"Something went wrong"/`!` in errors | What failed + the next step |
| Concatenated fragments or `=== 1 ? "" : "s"` | One message with placeholders + locale plurals |
| "Are you sure" dialogs | Title names action + object |
| Negative toggle labels | Describe the ON state |
| Glyph-named `aria-label`s | Name the action |
| Locale-less `toLocaleDateString()` | `Intl.DateTimeFormat` with the user's locale |
