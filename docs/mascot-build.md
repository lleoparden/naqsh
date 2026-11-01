# Mascot build — dotb-vectr-rose

Source: `assets/mascot/naqsh.svg` (**5.8 KB**, under the 30 KB cap), no external
dependencies. Preview: `assets/mascot/preview.html` (serve the folder over HTTP).

## Design

Two stacked pebbles: rose `#e07c7b` body, brick `#a94a4a` top, charcoal `#1b1b1f`
outline, tiny dot eyes and a small mouth. No text, no logo, no arms/legs, no chat shape.
Palette matches the Vectr UI retheme; the task's stale `#5B6CFF` note is superseded by
the owner's palette change and the selected rose variant. Colors are CSS variables, so a
blue variant is a one-line change.

## States

| State | Length | Loop | CSS |
|---|---|---|---|
| idle | 2 s | infinite | blink at 12 fps steps, tiny bob |
| thinking | 2 s | infinite | gaze up, three dots step in |
| wave | 1.5 s | once | top pebble rocks (hover) |
| happy | 1.5 s | once | closed eyes, small bounce |
| sad | 1.5 s | once | gaze down, tilt, dim |

All animations use `steps(1, end)` at 12 fps. `prefers-reduced-motion: reduce` disables
animations; each state still has a distinct static pose.

## Static poses

`L:\naqsh-review\mascot-assets\static\`: `naqsh-idle|thinking|wave|happy|sad-512.png`
(RGBA, alpha min 0) and `naqsh-idle-1024.png` (RGBA). Rendered with
`frontend/e2e/mascot-static.mjs`.

## Verification

- SVG file size 5,789 bytes.
- PNGs are 512×512 / 1024×1024 RGBA with transparent corners.
- 32 px legibility is **not** claimed; the favicon is the first real 32 px test.
