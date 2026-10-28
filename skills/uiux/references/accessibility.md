# Accessibility

Reviews and fixes semantics, keyboard and focus behavior, accessible names, forms, announcements, motion and zoom. Every finding cites a WCAG 2.2 Level A/AA criterion number, or a concrete task an assistive-technology user cannot complete. AAA criteria and APG conventions are recommendations, never HIGH.

Two walks: keyboard-only, where every flow completes without a mouse; then screen-reader, where every control announces a name, a role and its state. When unsure, take the platform default over a custom rebuild, and remove ARIA rather than add it.

Contrast pairs are measured in [colors.md](colors.md). Text sizing, iOS input zoom and language metadata live in [typography.md](typography.md). Spacing between targets lives in [layout.md](layout.md). Label, error and alt wording lives in [ui-polish-and-writing.md](ui-polish-and-writing.md).

## Contrast requirements

| Criterion | Applies to | Minimum |
| --- | --- | --- |
| 1.4.3 AA | Text | 4.5:1 |
| 1.4.3 AA | Large text, at least `24px` or `18.67px` bold | 3:1 |
| 1.4.11 AA | UI component boundaries, states and meaningful graphics | 3:1 |

Inactive controls and logos are exempt. Measure the rendered pair per [colors.md](colors.md) and report the pair plus the criterion it misses.

## Rules

- Native elements first: `<button>` for actions, `<a href>` for navigation, never `<div onClick>`. A real link supports Cmd/Ctrl/middle-click. The first rule of ARIA is not to use ARIA when a native element exists.
- Disabled means unavailable: native `disabled` when a control is genuinely unavailable. `aria-disabled="true"` only when it must stay focusable — then block pointer, keyboard and form behavior in code, and style the state explicitly.
- Focus rings: style `:focus-visible`, not bare `:focus`; keyboard users get a ring, mouse users usually do not. A custom ring reaches 3:1 against every adjacent color it crosses, `currentColor` included (1.4.11). Never bare `outline: none` without a verified replacement. Preserve system colors in forced-colors mode.
- A focused element never sits fully hidden behind a sticky header, footer or banner (2.4.11); the scroller-padding fix lives in [layout.md](layout.md).
- Keyboard: follow the APG patterns — Escape closes overlays, arrow keys move within composite widgets, Tab moves between widgets, Enter and Space activate buttons. Only `tabindex="0"` joins the natural tab order and `tabindex="-1"` for programmatic focus; positive values break the order. Roving tabindex for composite widgets; `aria-activedescendant` where focus must stay in an input, as in a combobox.
- Overlays: prefer `<dialog>` opened with `showModal()` — the background goes inert and Escape is handled. A custom overlay sets `inert` on the background and `role="dialog"` + `aria-modal="true"` on itself; move focus inside on open and back to the trigger on close.
- Client-side route changes update `document.title` and move focus to the new view's `<h1>` or `<main>`.
- Hit areas: 24×24 CSS px is the AA baseline (2.5.8); aim 44×44 on touch where density permits; extend with a pseudo-element when the visible element stays smaller. Extended areas never overlap, and decorative layers get `pointer-events: none` so a glow never swallows clicks. Every drag interaction has a single-pointer alternative (2.5.7).
- Every input is labeled: `<label for>` or a wrapping `<label>`; a placeholder is never a label; no dead zone between a checkbox and its text. Add a valid `autocomplete` token, a descriptive `name`, and the `type`/`inputmode` that summon the right keyboard. Never block paste.
- Validate on submit, never by disabling submit until the form is valid. Failing fields get `aria-invalid="true"`, `aria-describedby` points at the inline error text, and focus goes to the first invalid field.
- Accessible names everywhere: icon-only buttons get a descriptive `aria-label` naming the action; visible label text appears in the accessible name; decorative elements get `aria-hidden="true"`, never on a focusable element.
- Status carries a redundant cue — an icon, text or underline alongside the color (1.4.1).
- Motion wraps in `@media (prefers-reduced-motion: no-preference)` so it is opt-in. Under reduced motion, slides and scales become opacity cross-fades; parallax and autoplay die entirely.
- Nothing the user needs runs on a timer: anything moving, blinking or auto-updating for more than 5 seconds needs a visible pause control (2.2.2). Toasts carrying an action or an error stay until dismissed.
- Live regions, three mechanisms, three jobs: `aria-describedby` carries field validation; `role="status"` carries non-urgent updates not tied to a control (toasts, result counts), rendered as a stable empty region before its text updates; `role="alert"` carries urgent errors and nothing else.
- Alt by purpose: decorative images get `alt=""`; informative images describe the meaning; functional images describe the action, never the picture.
- Structure is navigation: headings describe their sections; one visible primary `<main>`; a "Skip to content" link as the first focusable when chrome precedes it; `scroll-margin-block-start` on anchored headings.
- Text survives 200% resize (1.4.4); the page reflows at 320px width without horizontal scrolling (1.4.10); text containers take `min-height`, not `height`. Never `maximum-scale=1` or `user-scalable=no` in the viewport meta.

## Detection table

| Pattern | Fix |
| --- | --- |
| A failing contrast pair | Measure per colors.md; report the pair and the missed criterion |
| `outline: none`/`outline-none` with no `focus-visible` replacement | Restore the browser ring or add a verified custom one |
| `<div onClick` or an unlabeled icon-only control | Native element; `aria-label` naming the action |
| Positive `tabindex` | Fix the DOM order, use `0` |
| `disabled={!isValid}` on a submit button | Keep it enabled, validate on submit |
| Live region mounted together with its text | Render the empty region first, then update its text |
| `aria-hidden` on a focusable ancestor | Remove it, or make the subtree inert |
| `maximum-scale=1`/`user-scalable=no` | Remove the zoom lock |
