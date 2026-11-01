# Mascot video and brand exports

All outputs are outside the repo at `L:\naqsh-review\mascot-assets\`.

## Frames

`frames\<state>\frame-000.png` … at 512×512 RGBA, 12 fps. Counts: idle 24,
thinking 24, wave/happy/sad 18. `seam.png` is rendered at exactly one period.

## Video (verification.json)

| State | Frames | WebM alpha | MP4 green | Loop seam |
|---|---|---|---|---|
| idle | 24 | 512 VP9 yuva420p, alpha min 0 | 1024 H.264, 24 | identical (0) |
| thinking | 24 | same | same | identical (0) |
| wave | 18 | same | same | identical (0), one-shot |
| happy | 18 | same | same | **not identical** (one-shot; 62 max channel diff) |
| sad | 18 | same | same | identical (0), one-shot |

Alpha was verified by decoding the WebM with `ffmpeg -c:v libvpx-vp9 -pix_fmt rgba`
(native decoders report it opaque). WebM filenames include state, seconds and frames,
e.g. `naqsh-idle-2s-24f-alpha.webm`.

Loop seam is meaningful only for the looping states (idle, thinking); both are
numerically identical at one period. Happy is a one-shot and is not looped.

## Brand

`brand\`: `favicon.svg` source at `assets/mascot/favicon.svg`; `favicon-32.png` (32×32
RGBA), `readme-header-1500x500.png`, `x-avatar-400.png`, `x-banner-1500x500.png`. Fonts:
OFL Inter and IBM Plex Sans Arabic, embedded from `assets/fonts/`. No text inside the
mascot art; wordmark is outside the SVG.

## Limits

- The brand images are raster exports; no visual approval is claimed.
- MP4 is chroma green by design, not alpha.
- Happy’s seam is not identical; do not loop it.
