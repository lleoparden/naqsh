# Naqsh UI design brief

Contract for the editor overhaul. Anything that conflicts with the owner's brief is
overruled by the owner; this file records the direction, tokens and rules the code must
follow. Written before any redesign code.

## Direction

A clean, neutral, modern **design-tool** UI — the register of Figma, Photopea and
Linear, not a marketing page. Dark neutral-gray workspace, one cool accent, no
decoration that is not information. The canvas is the product; chrome stays quiet.

Explicitly banned: beige/cream backgrounds, orange or brand-red as accents, serif
typefaces anywhere. Red is reserved for destructive actions and errors only.

## Tokens

Colour (dark, WCAG AA checked against the text colours below):

| Token | Value | Use |
|---|---|---|
| `--bg` | `#0E0F12` | app background |
| `--panel` | `#16181D` | top bar, side panels |
| `--raised` | `#1D2026` | inputs, menus, popovers |
| `--border` | `#2A2E36` | hairlines, dividers |
| `--text` | `#E6E8EE` | primary text (13.2:1 on `--bg`) |
| `--muted` | `#9AA1AD` | secondary text (6.1:1 on `--bg`) |
| `--accent` | `#5B6CFF` | selection, active tool, focus ring (proposed; owner can veto) |
| `--accent-strong` | `#4353E8` | pressed/primary button |
| `--danger` | `#E5484D` | destructive + error only |
| `--success` | `#3FB950` | success toast only |

Type: **Inter** for Latin UI chrome, **IBM Plex Sans Arabic** for Arabic UI copy and
samples. Both OFL and bundled locally (no CDN). Scale: 12 / 13 / 14 / 16 / 20 px; UI
body 13 px; panel headers 12 px with normal case (no letter-spaced all-caps eyebrows).

Space: 4/8 px scale only (4, 8, 12, 16, 24, 32). Radius 6 px. One-pixel borders.

Icons: **Lucide** only, 16 px in controls, 18 px in the toolbar; every icon button has
a tooltip with its shortcut.

## Layout (desktop only, min width 1280)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ logo  job · page            undo redo   zoom   [Original]        [Export ▾]  │
├────┬──────────────────────────────────────────────┬──────────────────────────┤
│ ⬚  │                                              │ Properties               │
│ T  │                 canvas (plate +              │  region name / type      │
│ ▧  │                 text + covers)               │  Arabic text (RTL)       │
│ ◉  │                                              │  font · size · colour    │
│    │                                              │  Re-translate · Reset    │
│    │                                              ├──────────────────────────┤
│    │                                              │ Layers                   │
│    │                                              │  original (locked)       │
│    │                                              │  clean plate             │
│    │                                              │  covers, text regions    │
└────┴──────────────────────────────────────────────┴──────────────────────────┘
```

- Left toolbar, top to bottom: Select/Move (`V`), Text (`T`), Cover patch (`C`),
  Eyedropper (`I`).
- Top bar right: Export menu with Layered SVG, Outlined SVG, PNG, Bundle (ZIP) — one
  description line each.
- Translation settings (Arabic style, Digits) live in one labelled popover with helper
  text, not in the top bar.
- Layers: original reference (locked, hidden), clean plate, covers, text regions; drag
  to reorder, inline rename, eye, lock.

## Interaction rules

- Every control has hover, active, focus-visible (2 px accent ring, 2 px offset),
  disabled and loading states; panels have empty and error states.
- Shortcuts: `Ctrl/Cmd+Z` undo, `Shift+Ctrl/Cmd+Z` / `Ctrl+Y` redo, `Delete` skip
  region, `Esc` deselect, `V/T/C/I` tools, `Space`+drag pan.
- Tooltips carry the shortcut for every icon button.
- Canvas text selection outline uses `--accent`; destructive actions use `--danger`.

## Copy rules

Plain verbs, sentence case, no filler. An action keeps its name through the flow.
Errors say what happened and how to fix it, never apologise. Empty states invite the
next action. No "eyebrow" labels and no middle-dot meta strings.

## Non-goals

Mobile/responsive layout, light theme, custom illustration, animations beyond
action feedback (toast, menu, drag), a marketing landing page.


## Palette update (2026-11-01, owner)

The owner directed the project to use the Vectr UI colour template. Tokens:
background `#1b1b1f`, panel `#202024`, raised `#242428`, border `#3a3335`,
text `#f3eee8`, muted `#c6bfb7`, accent `#a94a4a`, accent-deep `#8b3a3a`,
accent-light `#e07c7b`, danger `#e2665c`. This supersedes the earlier
`#5B6CFF` accent decision. A muted sage `#7f9a6d` is used for success because
Vectr has no success token.
