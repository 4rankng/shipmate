# Layout

Grouping, alignment, spacing, reading order and responsive structure — then stress-tested by resizing (320px width, 200% zoom), translating and mirroring for RTL.

The numbers below apply only where the project has no spacing scale or density system; otherwise use its tokens. A finding needs a failure you can show — a clip, an overlap, a broken mirror, a misread group. A value that differs from these starting points is not one.

Hit areas and focus behavior live in [accessibility.md](accessibility.md). Radius, shadows and motion live in [ui-polish-and-writing.md](ui-polish-and-writing.md). Measure, text spacing and truncation mechanics live in [typography.md](typography.md).

## Rules

- Group with space, not lines: background shapes second, separator lines last and only where space alone cannot carry the structure. The between-group gap is at least 2× the within-group gap — `8px` inside a group means `16px` or more between groups.
- Controls distinct from content: every interactive element gets a background shape, a border, an underline or a consistent placement zone. A control styled like the static text beside it does not read as a control.
- Align to shared edges: a small set of alignment edges, one spacing step per nesting level, `16px` a useful default.
- Logical properties for anything that mirrors: `margin-inline-start`, `padding-inline-end`, `inset-inline-start`, `text-align: start`. Physical `left`/`right` only for physical geometry such as safe-area insets.
- Order by importance: most important near the top and the leading edge; identifying content leads, metadata and actions trail. Visual order = DOM order — never move content out of source sequence with `order`, `row-reverse` or grid placement.
- One primary action per view; more than 3 secondary actions go behind a menu. Prefer a short view that links deeper over one long view showing everything at top level.
- Every off-screen or collapsed piece of content shows a visible cue: the project's established cue, the next item peeking 16–32px past the scroll edge, or a disclosure control.
- A truncated value the user needs has a way to the full text — an expand control, a detail view, or a keyboard-reachable tooltip. The clamp mechanics are [typography.md](typography.md)'s.
- Borderless controls need 24px between visible glyphs, counting each button's own padding; 12px between adjacent bordered or filled controls where no density system exists. Compact layouts may go tighter only while hit areas never overlap and controls stay distinct.
- Full-width buttons stay inside the layout margins — start near 16px inline on mobile. Edge-to-edge works only for established platform chrome that accounts for safe areas.
- Content bleeds, controls float: backgrounds and media reach the viewport edges; controls and text stay inside margins and safe areas. `env(safe-area-inset-*)` resolves to 0 without `viewport-fit=cover` in the viewport meta.
- Sticky chrome sets `scroll-padding-block-start` to its height, so anchored targets and focused elements never land beneath it.
- Breakpoints come from the content, not device presets: hold the expanded layout until it stops fitting, then collapse. Prefer container queries for component-level adaptation. Test the smallest and largest supported sizes first.
- Translated strings grow, short ones proportionally more — a one-word button label is the riskiest string on screen. Size text containers with `max-width`/`min-height`, never fixed dimensions; let rows wrap. Test with pseudo-localization and one long-string locale such as German.
- Never park a critical action where resizing, zoom or scrolling clips it — keep it in the normal flow or stable chrome.

## Detection table

| Pattern | Fix |
| --- | --- |
| `1fr` track or flex child holding long text, overflowing its track | `minmax(0, 1fr)` on the track, `min-width: 0` on the flex child |
| `100vw` | `100%` — `100vw` includes the scrollbar and scrolls horizontally |
| `100vh` on a full-height mobile pane | `100dvh`, so browser toolbar and keyboard never cover the bottom |
| Fixed `height` on a box holding text | `min-height`, or `max-height` with `overflow-y: auto` |
| `@media (max-width: …)` inside a reusable component | `@container` on the component's parent |
| `container-type: inline-size` on a width-less box | Give it a definite width; size containment collapses shrink-to-fit to zero |
| `env(safe-area-inset-*)` without `viewport-fit=cover` | Add it, or the insets resolve to 0 |
| Inline logical props mixed with physical safe-area insets | Physical `left`/`right` with the matching inset, plus a `[dir="rtl"]` override |
| `float: left` on mirrored UI | `float: inline-start` |
| `translateX` or `background-position: left` on mirrored UI | A `[dir="rtl"]` override — neither has a logical form |
| Sticky header without `scroll-padding-block-start` | Set it to the header height |
