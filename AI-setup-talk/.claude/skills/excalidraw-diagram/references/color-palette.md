# Color Palette & Brand Style

**This is the single source of truth for all colors and brand-specific styles.** To customize diagrams for your own brand, edit this file — everything else in the skill is universal.

> **Style: classic Excalidraw (hand-drawn, light).** Matches the light reveal.js deck.
> White/transparent canvas, the default Excalidraw swatches: black or colored strokes
> with pastel solid fills, hand-drawn font, sketchy edges.
>
> **Hand-drawn settings (apply to EVERY element):**
> - `roughness: 1` (sketchy, hand-drawn lines — this is the classic look; do NOT use 0)
> - `fontFamily: 1` (Virgil / Excalifont — the hand-drawn font)
> - `fillStyle: "solid"` (clean pastel fills; `"hachure"` for the extra-sketchy variant)
> - `strokeWidth: 2`

---

## Shape Colors (Semantic)

The default Excalidraw palette: a darker colored (or black) stroke paired with its pastel fill.

| Semantic Purpose | Fill | Stroke |
|------------------|------|--------|
| Primary/Neutral | `#ffffff` | `#1e1e1e` (black) |
| Secondary | `#a5d8ff` | `#1971c2` (blue) |
| Tertiary | `#d0bfff` | `#9c36b5` (violet) |
| Start/Trigger | `#ffec99` | `#f08c00` (orange) |
| End/Success | `#b2f2bb` | `#2f9e44` (green) |
| Warning/Reset | `#ffc9c9` | `#e8590c` (deep orange) |
| Decision | `#ffec99` | `#f08c00` (orange) |
| AI/LLM | `#d0bfff` | `#9c36b5` (violet) |
| Inactive/Disabled | `#e9ecef` | `#868e96` (use dashed stroke) |
| Error | `#ffc9c9` | `#e03131` (red) |

**Rule**: darker/colored stroke + its pastel fill. Keep `fillStyle: "solid"` and `roughness: 1`.

---

## Text Colors (Hierarchy)

Use color on free-floating text to create visual hierarchy without containers.

| Level | Color | Use For |
|-------|-------|---------|
| Title | `#1e1e1e` | Section headings, major labels |
| Subtitle | `#1971c2` | Subheadings, secondary labels (blue) |
| Body/Detail | `#495057` | Descriptions, annotations, metadata |
| On light fills | `#1e1e1e` | Text inside the pastel shapes above (always dark) |
| On dark fills | `#ffffff` | Text inside any rare dark shape |

---

## Evidence Artifact Colors

Used for code snippets, data examples, and other concrete evidence inside technical diagrams.

| Artifact | Background | Text Color |
|----------|-----------|------------|
| Code snippet | `#f1f3f5` | `#1971c2` (or syntax-appropriate), with `#868e96` stroke |
| JSON/data example | `#f1f3f5` | `#2f9e44` (green) |

Keep evidence artifacts hand-drawn too (`roughness: 1`), so they read as part of the sketch.

---

## Default Stroke & Line Colors

| Element | Color |
|---------|-------|
| Arrows | Black `#1e1e1e` (classic), or the source element's stroke for emphasis |
| Structural lines (dividers, trees, timelines) | Black `#1e1e1e` or gray `#868e96` |
| Marker dots (fill + stroke) | Black `#1e1e1e` |

---

## Typography

| Property | Value |
|----------|-------|
| `fontFamily` | `1` (Virgil / Excalifont — the hand-drawn font) |

---

## Background

| Property | Value |
|----------|-------|
| Canvas background (`appState.viewBackgroundColor`) | `#ffffff` |

Export **transparent** for slides (`export_svg.py` does this by default) so the hand-drawn
shapes sit on the deck's light "paper" background with no visible rectangle.
