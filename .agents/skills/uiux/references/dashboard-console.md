# Dashboard console (BUILD)

A dark-first operator console for data products: a near-black tinted canvas, hairline panels, one luminous signal colour, mono labels, tabular figures and a very high data-per-screen ratio. Use it when the screen is an instrument — monitoring, comparing, scanning — not when the page is trying to persuade.

The signature is the **glowing cell grid**: every block is a hairline panel with a subtle signal glow, a mono kicker and a dense body, laid on a faint measurement grid. The screen should look like something an operator watches, not a marketing page with charts on it.

This file is a direction, not a component library. Adapt the roles to the subject; never ship a recoloured clone of the reference product.

## When it fits

- Dashboards, monitoring, KPI surfaces, tables, leagues/leaderboards, archives, analytics.
- Dense numeric products where comparison and scanning beat reading.

Not for: marketing pages, long-form editorial, warm consumer apps, forms with one question per screen. If the surface is mostly reading or persuasion, another archetype in [design-direction.md](../../../../skills/uiux/references/design-direction.md) wins.

## Direction statement

> Dark console, teal signal, mono instrumentation. Near-black canvas with a faint 48px measurement grid and two ambient signal glows. Hairline panels at 8px radius, a 12px body, a 9px mono kicker, tabular figures. One signal colour does interaction; a second data hue and a cold→hot ramp carry data. Density first: no decorative card, no unused cell.

Write that down before coding, then apply the token table.

### Relationship to the skill defaults

[design-direction.md](../../../../skills/uiux/references/design-direction.md) bans neon and outer glows by default. This direction spends its single exception on **panel surfaces and the ambient backdrop wash** — never on text, controls or animated glow. The near-black base is not the "near-black + acid accent" generated default: the signal is mint-teal, the surfaces are navy, the density is instrument-grade, and every block carries data. Keep it that way; one electric accent on flat black with decorative glow is the clone to avoid.

## Tokens

Roles, not palette dumps. Define both appearances up front; dark is the primary appearance and light is the day console. The values below are the reference implementation in the toto.sg console; replace the hues only with an OKLCH ramp built per [colors.md](../../../../skills/uiux/references/colors.md), and confirm every rendered pair against [accessibility.md](../../../../skills/uiux/references/accessibility.md).

| Role | Dark | Light |
| --- | --- | --- |
| canvas | `#041018` | `#EEF6F8` |
| surface | `#07202C` | `#FFFFFF` |
| surface-2 (raised / header strip) | `#0A2A39` | `#E4F0F4` |
| surface-3 (track / inert) | `#0F3547` | `#D5E6EC` |
| line | `#124155` | `#D3E4EA` |
| line-strong | `#1C566E` | `#B9D2DB` |
| ink | `#E8F7FB` | `#06212C` |
| ink-muted | `#9CC4D2` | `#45606C` |
| ink-subtle (mono labels) | `#6C96A8` | `#5F7D89` |
| ink-faint (decoration only) | `#4D7486` | `#8299A4` |
| signal (primary) | `#2EE6C5` | `#0F9E86` |
| signal-strong | `#7CF5DE` | `#0B7A67` |
| signal-soft / signal-line | `#072F33` / `#12605C` | `#E3F7F3` / `#B9E8E0` |
| data (secondary hue) | `#35D6FF` | `#0E7490` |
| heat cold / hot | `#35D6FF` / `#FF5C8A` | `#0284C7` / `#DB2777` |
| gold (jackpot / top rank only) | `#FFD166` | `#D4A500` |

Rules:

- One signal colour does interaction. Cyan is the second data hue, gold is reserved for the jackpot or rank 1. Status hues are the only other colours.
- Text uses the ink ramp; a data colour never sets body text. `ink-faint` is decoration only.
- Sequential heat ramps are their own token family (six steps from canvas-ish to signal), not `color-mix` at render time.
- Declare `color-scheme` on the root and a `theme-color` matching the canvas.

## Backdrop

The canvas is not flat. Two ambient signal glows at the top and a fine measurement grid give the console its surface; both are fixed, neither is a text effect.

```css
body {
    background-color: var(--color-canvas);
    background-image:
        radial-gradient(1000px 560px at 14% -10%, color-mix(in oklab, var(--color-signal) 16%, transparent), transparent 70%),
        radial-gradient(820px 460px at 88% -8%, color-mix(in oklab, var(--color-data) 9%, transparent), transparent 72%),
        linear-gradient(to right, color-mix(in oklab, var(--color-ink) 4%, transparent) 1px, transparent 1px),
        linear-gradient(to bottom, color-mix(in oklab, var(--color-ink) 4%, transparent) 1px, transparent 1px);
    background-size: auto, auto, 48px 48px, 48px 48px;
    background-attachment: fixed;
}
```

- Keep the grid at 3–5% ink and 48px; denser reads as a texture, not a measurement surface.
- No neon text, no glow on headings, no animated background. If it moves, it is not a backdrop.
- The light appearance keeps the same geometry with a much quieter glow.

## Geometry and surfaces

- Panels: 8px radius, 1px `line`, `surface`, `panel-glow` — `inset 0 1px 0 signal/18%` plus `0 28px 60px -46px signal/65%`. No ordinary drop shadow.
- Controls: 6px radius; chips/marks: 2px. Never a pill unless it is a status.
- Gaps: 8px between cells, 12px panel padding, 8px/12px panel header padding. Density comes from tight padding, not small text.
- One filled signal action per view; everything else is a hairline control.
- No cards inside cards. A panel inside a panel is a table or a list, not another boxed surface.

## Type

Sora for display, DM Sans or Inter for body, a system mono for every label, kicker, table figure and KPI note. `font-variant-numeric: tabular-nums` on the root.

| Role | Size / tracking | Notes |
| --- | --- | --- |
| Page title | 20–24px desktop, 20px mobile, −0.02em | display, 600 |
| Panel title | 13px, −0.01em | display, 600 |
| Kicker / KPI label | 9px mono, 0.16–0.20em, uppercase | one per panel; signal or muted |
| Body / description | 12–13px, 1.4–1.5 | muted ink |
| KPI value | 20–24px display | tabular; compact long values |
| Table | 12–13px, 36px rows | numbers mono, right-aligned |
| Filter controls | 14px select/menu, 16px input on mobile | compact height; never the large control size on phones |

- Uppercase mono labels are the console's voice; do not use them for prose.
- Long KPI values compact (`S$13.1M`) instead of wrapping or clipping; the exact figure lives in a detail panel.
- Body copy stays short; detail prose lives behind a disclosure.

## Shell

- A 52px top bar: mono 10px uppercase nav, one signal underline on the active item, theme toggle at the end.
- **All nav items fit in the bar at every width.** A hamburger only appears above five or six items; below that, shrink the mono size and padding (`9px` / `0.1em` / `px-1.5` at 320) so every item is visible.
- The bar **auto-hides**: hide on scroll down past ~6px after 24px, reveal on any upward scroll and at the top; 200ms translate; `inert` while hidden; never hide while focus is inside it. It is chrome, not a permanent 52px tax.
- Page header under the bar: a 3px signal bar, mono kicker, 20–24px title, one line of meta in mono, optional right-side actions, bottom hairline.

## Page anatomy

1. **Page header** — signal bar + kicker + title + meta + actions.
2. **KPI strip** — 2 columns on phones, 3 on tablets, 4–6 on desktop. Icon chip + mono label + one figure + a one-line hint. This is the top-level answer, not decoration.
3. **Body grid** — 12 columns, 8px gap. Pair heights deliberately: 8/4, 7/5, 6/6, 4/4/4. A tall panel beside a short one leaves a hole; either fill it with another data block or rebalance the pair.
4. **Closing note** — one small muted line for the caveat; no large disclaimer card.

Rules:

- `items-start` on the grid. Do not stretch panels to equal height and then leave the body empty.
- Every cell must earn its place. If a cell repeats data already visible, delete it.
- Full-bleed: content spans the container; panels share edges. No floating page wrapper with unused margins.

## Components

### KPI card

Icon chip 36px (signal/cyan/gold tint at 10% with a 30% ring), mono 9px label, display value 20px, 10px hint. Long values are compacted, not truncated mid-number. The icon is the only decorative element.

### Panel

Mono kicker, 13px title, 11px description, actions at the end. Header strip `surface-2/40` with a bottom hairline. Body 12px padding. Footer for a caption. No shadow beyond the signal glow.

### Data table

- 36px rows, 12–13px text, header 11px mono uppercase; numbers mono right-aligned; hairline rows, no zebra.
- If the columns do not fit, **hide columns at a breakpoint**; do not introduce horizontal page scroll. A dense table that fits beats a complete table that scrolls.
- No vertically sticky header inside an `overflow-x: auto` rail — the sticky offset is measured against the rail and paints the header over the first rows. Either make the table fit, or keep the header static.
- Table actions live in the row; hide low-value columns and expose them in an expanded detail.

### Sequence / leaderboard row

A row whose main output is a set of values (six numbers, a pick, a code) is **two lines**:

1. identity, score, one stat — all on one line;
2. the sequence at 36–44px, on its own line, aligned under the name.

Never squeeze the sequence into the same line as the name and stats. The sequence is the point of the row.

### Filters

One row, always. Compact controls: the select trigger and menu text at 14px, the search input at 16px on mobile (iOS Safari zooms the page when an input is smaller — see [typography.md](../../../../skills/uiux/references/typography.md)) and 14px from `md` up, a flexible search field and a segmented sort. `flex-nowrap`; allow horizontal scroll inside the filter bar only below the smallest supported width. Never wrap to two or three lines. Never use the large/`lg` control size on phones.

### Donut / gauge

- Donut: 4–6 segments max, 10px ring, centre value + mono label, legend stacked below in a narrow column. Show the percentage, not just the colour.
- Gauge: half-circle, one value, centre reading, mono label; use for rates (`47% of draws`), not for arbitrary scores.
- Both are supporting visuals. If the same number is already a KPI, the chart must add the distribution, not repeat the total.

## Colour semantics

- Signal = interaction and the primary series.
- Data cyan = the second series.
- Cold→hot ramp = heat boards and divisions; blue is below expectation, pink above.
- Gold = jackpot, rank 1, the single best value. Not a general accent.
- Status = success/warning/error only when the status is real. No green chrome.
- One hue per meaning. Two saturated accents competing for attention is the failure mode of this style.

## Motion

- 100–200ms, ease-out; state only. No ambient loops, no parallax, no scroll-linked reveals on app surfaces.
- The auto-hide bar is a 200ms `translateY`; focus inside it prevents hiding.
- `prefers-reduced-motion` removes durations and transforms; nothing is lost because no state is carried by motion alone.

## Responsive contract

- 320, 390, 768, 1024, 1440. Test all five before calling it done.
- 320: nav items all visible (9px mono, tight padding), KPI 2-up, filters one row, no horizontal document scroll.
- 390: same, filters still one row.
- 768: KPI 3-up, tables hide low-value columns rather than scroll.
- 1024+: KPI 4–6, full 12-column pairing.
- `document.documentElement.scrollWidth === clientWidth` at every width. A hidden 1px overflow is still a broken page on a phone.

## Anti-patterns

| Symptom | Fix |
| --- | --- |
| 18px filter controls on phones | 14–16px compact controls, one row |
| Filters wrap to 2–3 rows | `flex-nowrap` + flexible search + `overflow-x-auto` only below 360; inputs stay 16px on mobile |
| Hamburger with four items | Put the items in the bar; shrink mono size/padding |
| KPI value clipped in a 2-col tile | Compact the value (`S$13.1M`), keep the exact figure in a detail panel |
| A progress bar wider than the data it explains | Sequence/values in the foreground; bars ≤120px or moved behind the content |
| Card next to a taller card with empty body | `items-start` and either fill the shorter card or rebalance the pairing |
| Empty lower half of a hero card | Add a real data block or shrink the hero |
| Sticky table header painted over the first row | No vertical sticky inside a horizontal rail |
| Sequence crammed at the end of the name line | Two-line row, sequence on its own line |
| Donut legend crushed in a narrow column | Stack the legend below the ring |
| Glow on text, borders and charts at once | Glow only on panel surfaces; one signal |
| Two saturated accents fighting | One signal + one data hue + status only |
| Dark-first skin with a flat black background and no grid | Add the measurement grid and one ambient glow |
| Auto-hide bar hiding a focused control | Focus guard + `inert` |

## Implementation recipe

1. Define the token block (both appearances) and set `font-variant-numeric: tabular-nums` on the root.
2. Paint the canvas: grid + two radial signal glows.
3. Build the panel primitive: 8px radius, 1px line, surface, `panel-glow`, mono kicker header.
4. Build the KPI card and the page header (signal bar + mono kicker).
5. Lay the 12-column grid; place a KPI strip, then panels by height pairs; `items-start`.
6. Add tables/rows/filters with the responsive contract.
7. Add the two charts only where they add distribution or rate.
8. Add the auto-hide top bar last.
9. Verify at 320/390/768/1024/1440 in both appearances, then check focus, reduced motion and `scrollWidth`.

Colour, contrast and token mechanics stay with [colors.md](../../../../skills/uiux/references/colors.md); type rendering with [typography.md](../../../../skills/uiux/references/typography.md); responsive structure with [layout.md](../../../../skills/uiux/references/layout.md); accessibility with [accessibility.md](../../../../skills/uiux/references/accessibility.md); writing with [ui-polish-and-writing.md](../../../../skills/uiux/references/ui-polish-and-writing.md). This file is the direction those rules are applied inside.
