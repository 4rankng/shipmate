# Design direction (BUILD)

BUILD is opinionated: pick a direction, state it, then implement inside it. This file owns the brief, the archetypes, the palette and pairing defaults, and the anti-slop defaults. Rendering rules live in the domain files.

## Pass 1 — compact brief

Before any code, write the direction down:

- Concrete subject, audience, and the one job this screen does.
- 4–6 named color tokens with roles (page bg, surface, text, muted text, accent, accent-contrast) — never a palette dump.
- A display role and a body role for type, with the faces named.
- One or two layout concepts as prose or ASCII.
- The signature element — the one thing a user would remember.
- One intentional motion role, or an explicit decision to stay still.
- Copy voice.

## Pass 2 — critique before code

Ask: "would any part of this appear unchanged for a different client in the same category?" Revise until the answer is no — until the design belongs to this subject — then implement. State the chosen direction up front, before writing code.

## Six visual archetypes

The primary generation method. Pick the closest, then adapt through the OKLCH formulas in [colors.md](colors.md). The catalog lookup below supplies candidates; these are the defaults.

1. **Dense data dashboard.** Neutral OKLCH base L 0.95–0.30, one accent, 4/8px grid, 13–14px UI text, numerals set for column comparison. Anti-pattern: decorative illustration or rounded friendliness that costs density.
2. **Monochrome tech.** Near-single-hue neutral ramp, one saturated signal color, generous dark surfaces. Anti-pattern: a second accent hue competing with the signal color.
3. **Warm editorial.** Serif display over sans body, cream-neutral ramp, measure 60–75ch. Anti-pattern: dashboard density — dense tables and data grids.
4. **Commerce trust.** Cool neutral ramp, green reserved for confirmation only, product imagery primary. Anti-pattern: playful accents on checkout or payment surfaces.
5. **Dev tool.** Dark base, mono-flavored numerals, low-chroma accents, dense rows. Anti-pattern: a large marketing hero on an app surface.
6. **Friendly productivity.** Mid-lightness neutrals, soft radius 8–12px, one warm accent. Anti-pattern: neon saturation or brutalist hairlines.

## Anti-slop bans (BUILD defaults)

- Inter, Roboto or Arial as the identity face.
- AI purple/blue gradient on white.
- 3-column equal card rows.
- A centered hero at high variance.
- `h-screen` — use `100dvh`.
- Dummy content: "John Doe", "Acme Corp", round numbers.
- Clichés: "Elevate", "Seamless", "Unleash".
- Emoji as structural icons — one SVG icon family instead.
- Default unstyled shadcn.
- Neon or outer glows.
- Custom cursors.
- Gradient header text unless asked.
- Current generic-AI looks to avoid without cause: warm cream + serif + terracotta, near-black + acid accent, hairline editorial.

In AUDIT these are notes, not findings, unless they cause a concrete defect.

## Palette and pairing defaults

| Archetype | Pairing |
| --- | --- |
| Warm editorial | Fraunces + Source Sans 3 |
| Geometric tool | Space Grotesk + IBM Plex Sans |
| Humanist product | Bitter + Inter |
| Mono-accented dev | JetBrains Mono accents + Inter body |
| Warm commerce | Lora + Nunito Sans |

For broader candidates run:

```
python3 skills/uiux/scripts/lookup.py "<product type> <mood keywords>" --domain palette|pairing|style [-n 5]
```

Take the top row and adapt it through the OKLCH formulas in [colors.md](colors.md). Database rows are candidates, not authority — the rules still govern, and every adopted palette passes the contrast table in [accessibility.md](accessibility.md) before use.

## Restraint check

After the first pass, remove one decorative element that does not support the brief. Spend boldness in one place; the supporting UI stays disciplined. The hero is a thesis: open with the most characteristic thing in the subject's world, not a stat block.

Copy voice hands off to [ui-polish-and-writing.md](ui-polish-and-writing.md).
