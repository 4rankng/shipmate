# Typography

How text renders: type scale, spacing, font features, wrapping, truncation and punctuation. Font choice lives in [design-direction.md](design-direction.md); the words themselves live in [ui-polish-and-writing.md](ui-polish-and-writing.md); contrast measurement lives in [colors.md](colors.md).

Write every fix in the project's styling system.

## Exact rules — findings when missed

- Unitless `line-height`. A fixed `24px` does not scale with the font size.
- Weight `400` or heavier below `18px`. Weights 100–300 belong at `28px` and up, checked against the background even there.
- Long-form measure capped at 60–75 characters per line. Any unit works, as long as a cap exists and the line lands in range.
- Inputs at `16px` on mobile — iOS Safari zooms the whole page when an input's text is smaller. Two fixes hold `16px`: size the input up on mobile, or keep `font-size: 16px` and render the intended size with `transform: scale()`.
- `tabular-nums` on timers, counters, prices and numeric table columns, so every digit keeps one width. Prose figures stay proportional.
- Body sizes in `rem`, so the reader's browser font size still applies.

## Heuristics — only against the project's own scale

Letter-spacing, scale ratios and pairing contrast are heuristics. Report them only where they break the project's own scale. Never propose a new typeface, paid or free, unless the task asks for a type change.

## Rules

- Rarely more than three fonts. Pair for contrast: a serif display over a sans body reads deliberate; two near-identical sans-serifs read as a mistake.
- Load every face the design uses — browsers synthesize a missing weight or style, distorting the face. Leave `font-optical-sizing` at its default `auto`.
- Properties over raw tags: `font-weight: 650`, not `font-variation-settings: "wght" 650`; `font-variant-numeric: tabular-nums`, not `font-feature-settings: "tnum" 1`. Reserve raw tags for custom axes (`"GRAD" 80`) and features with no property (`"ss01" 1`).
- A semantic type scale: a small set of sizes, each paired with its line-height and weight, so a role is one decision instead of three. Deviate as little as possible.
- Heading sizes descend with level — a subordinate heading never overpowers its parent, and a heading is never smaller than body text unless it is a deliberate overline.
- Line-height by role: display 1.1, headings 1.2–1.3, body 1.5–1.6. Anything that wraps to three or more lines needs at least 1.4, even in a height-constrained row.
- Letter-spacing in `em`: headings at `24px` and up take −0.01em to −0.02em; uppercase labels at `14px` or smaller take 0.05em; body stays at `0`. Kerning is built in and on by default — `font-kerning: none` is never a fix.
- `text-wrap: balance` evens out headings and short text, never paragraphs; `text-wrap: pretty` keeps a lone word off a paragraph's last line. `overflow-wrap: break-word` where a long word, link or ID could escape the container.
- `text-align: start`; `justify` belongs only in specific editorial layouts.
- Truncate with a way back: one line — `overflow: hidden` + `text-overflow: ellipsis` + `white-space: nowrap`; several lines — `display: -webkit-box` + `-webkit-box-orient: vertical` + `-webkit-line-clamp` + `overflow: hidden`. The way-back control is [layout.md](layout.md)'s.
- Natural case stored, `text-transform` for display, so a redesign never rewrites copy.
- Typographic characters in rendered text: curly quotes, en dashes, em dashes, the `…` character. Code keeps straight quotes.
- `text-underline-position: from-font` and `text-decoration-thickness: from-font`.
- Size floors: body starts at 16px; inputs and menus at 14px; captions at 13px; rarely below 12px.
- Font smoothing once on the root — `-webkit-font-smoothing: antialiased` + `-moz-osx-font-smoothing: grayscale` — never per component.
- `lang` set on the document, `dir` wherever direction changes; mixed-direction values (names, numbers, URLs) wrapped in `<bdi>`, digits never reordered by hand.
- Keep text selectable. `user-select: none` belongs only on draggable or gesture-driven surfaces.

## Detection table

| Pattern | Fix |
| --- | --- |
| `line-height` in `px` or `rem` | A unitless value |
| `leading-none`/`leading-tight` on wrappable text | `1.4` or more |
| `font-variation-settings: "wght"` or `"opsz"` | `font-weight`; drop `"opsz"` so `font-optical-sizing: auto` applies |
| `font-feature-settings: "tnum"` | `font-variant-numeric: tabular-nums` |
| Weight under 400 below 18px | `400` or heavier |
| `text-wrap: balance` on a paragraph | `text-wrap: pretty` |
| `-webkit-line-clamp` without the box mechanics | Add `display: -webkit-box` + `-webkit-box-orient: vertical` |
| A changing value without `tabular-nums` | `font-variant-numeric: tabular-nums` |
| `...`/`--` in rendered strings | `…`, an em dash or an en dash |
| A 14px input with no mobile override | One of the 16px fixes above |
| Per-component `antialiased` | Move it to the root |
| `select-none` on a text root | Remove it; keep it only on gesture surfaces |
