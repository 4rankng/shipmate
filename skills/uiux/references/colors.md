# Colors

Builds and audits color systems: ramps, token roles, notation and rendered contrast. Never report a contrast value you did not measure, and never estimate a color you could compute. Perceived lightness means OKLCH `L`, from `0` to `1`.

Which pair must pass (4.5:1 / 3:1) lives in [accessibility.md](accessibility.md). Surfaces, shadows and icon color live in [ui-polish-and-writing.md](ui-polish-and-writing.md).

## Generation method

Tokenized OKLCH ramp formulas — build with a color library or the formulas, never by eye:

- Neutral ramp: one hue, L descending 0.98 → 0.30, light-end steps 0.04–0.05 L apart, chroma ≤0.02 at the text steps.
- Accent ramp: hue held within ±2° end to end, chroma peaking mid-ramp, the light end stepped as finely as the neutral.
- Status hues sit ≥15° OKLCH away from the accent hue.
- Dark mode is its own ramp — lower accent chroma, wider dark end — never inverted light tokens.

## Rules

- A system is ramps, not colors: one neutral ramp, one accent ramp, and only the status ramps the product actually renders. A ramp nothing imports is maintenance for zero pixels.
- Every step has a job — page bg, component hover, border, solid fill, body text. No step without a role; no role without a token.
- Primitives are named by value (`--blue-600`) and never applied in a component. Semantics are named by role (`--color-text-secondary`), point at a primitive, and are the only tier components reference. That seam lets a theme repoint colors without touching components.
- A token is never used outside its role — a separator used as a text color dies when borders get lighter. Missing role → add the token.
- One color, one meaning: treat anything within 15° of OKLCH hue as the same color.
- Exactly one filled primary action per view; peers stay neutral. Color on the background, not the label — a filled button reads primary across the room, accent text on a neutral button reads as a link.
- Measure the rendered pair — the background actually rendered, including alpha and overlays, in both themes — before reporting. Report the pair, the measured value and the missed threshold, then leave the colors alone unless asked.
- `oklch()` is the default for new systems; everywhere else use the project's notation consistently — a consistent hex system beats hex with `oklch()` scattered through it.
- Gradients interpolate `in oklab`; reach for `in oklch` when a two-hue gradient would go gray in the middle.
- Contrast fixes change lightness, not hue — lightness is the channel contrast responds to.
- One dark-switching mechanism: `prefers-color-scheme` XOR a `.dark` class, never both.
- `prefers-contrast: more` gets per-appearance values, not one block overriding both appearances.
- Text on a color with alpha is measured as rendered, or replaced with a solid token.
- Declare the sRGB value before a p3-only chroma, with the vivid value inside `@media (color-gamut: p3)`.

## Detection table

| Pattern | Fix |
| --- | --- |
| A hex/`rgb(`/`oklch(` literal where a token exists | Reuse or add the role token, in the project's notation |
| A primitive referenced in a component (`bg-blue-600`, `var(--blue-600)`) | Point a semantic token at the primitive, use that |
| A semantic name containing a hue or component (`--color-sidebar-gray`) | Rename for the role: `--color-accent-solid`, `--color-bg-surface` |
| Cross-role token borrowing (border token as text color) | Add a token for the missing role |
| An HSL ramp differing only in lightness | Rebuild with a constant perceived hue |
| Uniform step distance at the light end | Tighten to 0.04–0.05 L per step |
| A status hue within 15° of the accent hue | Move it ≥15° away, or give the action a distinct treatment |
| Dark tokens = the light ramp reversed | Own dark ramp: lower accent chroma, wider dark end, remeasure |
| Dual switching mechanisms (`prefers-color-scheme` + `.dark`) | Pick one, use it throughout |
| A contrast fix that changes hue, not lightness | Change lightness |
| An unmeasured alpha text pair (`/50`, `rgba(`, `color-mix(`) | Measure the rendered result or use a solid token |
| `text-white` on a `500` fill | Measure it; most hues need the fill at `600` |
