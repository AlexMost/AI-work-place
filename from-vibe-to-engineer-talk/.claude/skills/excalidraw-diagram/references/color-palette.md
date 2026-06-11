# Color Palette & Brand Style

**This is the single source of truth for all colors and brand-specific styles.** To customize diagrams for your own brand, edit this file — everything else in the skill is universal.

> **Style: hand-drawn Excalidraw on a DARK deck.** This talk's reveal.js theme is a deep
> violet (`evo AI DAY`): background `#1c0a33`, white text, lavender muted text.
> Diagrams are exported as transparent SVG and placed straight on that dark background,
> so **never use black or dark gray for text, arrows, or structural lines — they vanish.**
> Shapes keep the classic pastel fills (they pop on dark); everything free-floating must be light.
>
> **Hand-drawn settings (apply to EVERY element):**
> - `roughness: 1` (sketchy, hand-drawn lines — this is the classic look; do NOT use 0)
> - `fontFamily: 1` (Virgil / Excalifont — the hand-drawn font)
> - `fillStyle: "solid"` (clean pastel fills; `"hachure"` for the extra-sketchy variant)
> - `strokeWidth: 2`

---

## Deck Brand Reference (from `src/theme.css`)

| Token | Value | Meaning |
|-------|-------|---------|
| `--bg-deep` | `#1c0a33` | deck background (deep violet) |
| `--fg` | `#ffffff` | main text |
| `--muted` | `#cdbcf2` | light lavender, secondary text |
| `--accent` | `#b388ff` | light violet accent |
| `--accent-hot` | `#ff66c4` | pink, dosed emphasis |

---

## Shape Colors (Semantic)

Bright stroke + pastel fill: the light fill carries readability on the dark deck,
text inside shapes is always dark. Strokes are one notch brighter than the classic
Excalidraw swatches so they don't sink into the violet background.

| Semantic Purpose | Fill | Stroke |
|------------------|------|--------|
| Primary/Neutral | `#ffffff` | `#cdbcf2` (lavender) |
| Secondary | `#a5d8ff` | `#4dabf7` (bright blue) |
| Tertiary | `#d0bfff` | `#b197fc` (bright violet) |
| Start/Trigger | `#ffec99` | `#ffa94d` (bright orange) |
| End/Success | `#b2f2bb` | `#51cf66` (bright green) |
| Warning/Reset | `#ffc9c9` | `#ff922b` (bright deep orange) |
| Decision | `#ffec99` | `#ffa94d` (bright orange) |
| AI/LLM | `#d0bfff` | `#b197fc` (bright violet) |
| Inactive/Disabled | `#3b2a5e` | `#6f5b96` (use dashed stroke) |
| Error | `#ffc9c9` | `#ff8787` (bright red) |
| Hot emphasis (sparingly) | `#1c0a33` | `#ff66c4` (brand pink) |

**Rule**: bright stroke + its pastel fill. Keep `fillStyle: "solid"` and `roughness: 1`.

---

## Text Colors (Hierarchy)

Use color on free-floating text to create visual hierarchy without containers.
**Never `#1e1e1e`/`#495057`/gray for free-floating text — invisible on the dark deck.**

| Level | Color | Use For |
|-------|-------|---------|
| Title | `#ffffff` | Section headings, major labels |
| Subtitle | `#b388ff` | Subheadings, secondary labels (brand accent) |
| Body/Detail | `#cdbcf2` | Descriptions, annotations, metadata (brand muted) |
| On pastel fills | `#1e1e1e` | Text inside the pastel shapes above (always dark) |
| On dark fills | `#ffffff` | Text inside dark shapes (Inactive, Hot emphasis) |
| Arrow labels | match the arrow's stroke | keeps label ↔ arrow pairing obvious |

---

## Evidence Artifact Colors

Used for code snippets, data examples, and other concrete evidence inside technical diagrams.
On the dark deck these read as "glass cards": slightly lighter dark fill + light text.

| Artifact | Background | Stroke | Text Color |
|----------|-----------|--------|------------|
| Code snippet | `#2a1745` | `#6f5b96` | `#b388ff` (or syntax-appropriate light tone) |
| JSON/data example | `#2a1745` | `#6f5b96` | `#69db7c` (light green) |

Keep evidence artifacts hand-drawn too (`roughness: 1`), so they read as part of the sketch.

---

## Default Stroke & Line Colors

| Element | Color |
|---------|-------|
| Arrows (main flow) | White `#ffffff`, or the source element's stroke for emphasis |
| Accent arrows | `#b197fc` (violet), `#4dabf7` (blue), `#ff66c4` (pink — sparingly) |
| Structural lines (dividers, trees, timelines) | `#6f5b96` (dim violet) or `#cdbcf2` (lavender) |
| Marker dots (fill + stroke) | `#ffffff` |

---

## Typography

| Property | Value |
|----------|-------|
| `fontFamily` | `1` (Virgil / Excalifont — the hand-drawn font) |

---

## Background

| Property | Value |
|----------|-------|
| Canvas background (`appState.viewBackgroundColor`) | `#1c0a33` (deck violet — so PNG render previews contrast truthfully) |

Export **transparent SVG** for slides (`export_svg.py` does this by default) so the shapes
sit straight on the deck's dark violet background with no visible rectangle. Keep
`viewBackgroundColor` set to the deck color anyway: the PNG validation render uses it,
and checking contrast against white tells you nothing about the real slide.
