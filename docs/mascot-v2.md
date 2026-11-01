# Mascot v2 — presenter / face-cam kit

Character: **dotb-vectr-rose** (rose `#e07c7b`, brick `#a94a4a`, ink `#1b1b1f`). She is a
presenter in the video, not an assistant: she never speaks in the product, has no text or
logo in the art, and is used as a small corner overlay in the edit.

Source: `assets/mascot/naqsh-v2.svg` (**11,188 bytes**, under 60 KB). Preview:
`assets/mascot/preview-v2.html` (serve the folder over HTTP).

## States (16)

All at 24 fps and re-rendered at 12 fps. Loops are 1.5 s (36 frames at 24 fps, 18 at 12);
one-shots are 1 s (24 frames at 24 fps, 12 at 12). Frame minimums: 36/24 at 24 fps.

| State | Kind | 24 fps | 12 fps |
|---|---|---|---|
| idle | loop | 36 | 18 |
| blink | one-shot | 24 | 12 |
| talking | loop | 36 | 18 |
| thinking | loop | 36 | 18 |
| curious | one-shot | 24 | 12 |
| surprised | one-shot | 24 | 12 |
| confused | one-shot | 24 | 12 |
| happy | one-shot | 24 | 12 |
| excited | one-shot | 24 | 12 |
| laughing | loop | 36 | 18 |
| proud | one-shot | 24 | 12 |
| sad | one-shot | 24 | 12 |
| sleepy | loop | 36 | 18 |
| wave-hello | one-shot | 24 | 12 |
| wave-goodbye | one-shot | 24 | 12 |
| working | loop | 36 | 18 |

Animation craft is in CSS keyframes with easing, squash/stretch, anticipation and
secondary top-pebble motion; talking cycles five mouth shapes. No visual judgement is
claimed here.

## Transitions

30 state blends plus **26 reaction blends**, 10 frames each at 24 fps (8–12 allowed).
State blends cover idle→talking, talking→idle, and idle→/←each state. Reaction blends
cover **idle→each of the 13 reaction clips and back to idle** (nod, shake, shrug,
point-left, point-right, thumbs-up, thinking, loading, success, error, wave-hello,
wave-goodbye, surprise). They are **crossfades**, not pose interpolation; use them to
avoid a hard cut, then cut to the reaction clip.

## Exports

All outside the repo at `L:\naqsh-review\mascot-assets\v2\video\`.

- **ProRes 4444** `.mov`, `yuva444p10le`, alpha — 768 for every 24 fps state, 1080 hero
  for idle/talking/happy/excited.
- **WebM VP9** `yuva420p` + `alpha_mode=1` — every state at 24 and 12 fps, 30 transitions,
  1080 heroes.
- **MP4 H.264** on chroma green `#00FF00` — every state at 24 fps, 1080 heroes; no alpha.
- 106 encodes total; 86 alpha files decode with **alpha min 0**; MP4s are marked -1
  (no alpha). Frame counts decoded and stored in `video/verification.json`.

Recordly import (not verified in Recordly): use ProRes 4444 `.mov` first; if unsupported,
PNG sequence or WebM alpha; last resort MP4 + chroma key `#00FF00`. I could not verify
Recordly's codec support.

## Voice-driven presenter

`backend/scripts/mascot_presenter.py` — **no network, no cost**, 30 fps alpha ProRes.

```bash
python backend/scripts/mascot_presenter.py --audio voice.wav --out presenter.mov
python backend/scripts/mascot_presenter.py --audio voice.wav --markers markers.json --out presenter.mov
```

`markers.json`: `[{"t": 3.2, "state": "surprised"}]`. Mouth shapes follow the smoothed
WAV RMS (silence = closed); blinks are seeded/random; breathing and sway are applied.
This is **amplitude-driven, not true lip sync**. Test:
`pytest -q tests/test_mascot_presenter.py`. Sample:
`L:\naqsh-review\mascot-assets\v2\presenter\sample-10s-presenter.mov` (300 frames,
10 s, alpha min 0).

## Reaction pack

13 longer clips — **2 s** each, **3 s** for thinking-loop and loading-loop — 768,
24 fps, alpha WebM + ProRes in `L:\naqsh-review\mascot-assets\v2\reaction-clips-long\`;
frames in `reactions-long\`. Each has a 10-frame idle→reaction and reaction→idle blend in
`L:\naqsh-review\mascot-assets\v2\reaction-transition-clips\`.

| Clip | Use when |
|---|---|
| nod | yes / agreement / acknowledgement |
| shake | no / disagreement |
| shrug | uncertainty / “I don’t know” |
| point-left | direct attention left (lean equivalent — no arms) |
| point-right | direct attention right (lean equivalent — no arms) |
| thumbs-up | approval (proud pose equivalent — no arms) |
| thinking-loop | processing / thinking |
| loading-loop | waiting / working |
| success-pop | export or task succeeded |
| error-shake | something failed |
| wave-hello | intro / greeting |
| wave-goodbye | outro / goodbye |
| surprise | unexpected result |

## Preview and GIFs

- `assets/mascot/preview-v2.html`: every state, play/pause, frame counter, 12/24 toggle.
- `L:\naqsh-review\mascot-assets\v2\previews\contact-sheet-24fps.jpg` and
  `contact-sheet-12fps.jpg` (labeled key frames).
- `previews\gif\<state>.gif` (16 GIFs, 384 px, 12 fps).

## Optional Muse Image experiment

**Not run.** It was optional and only after items 1–7; the code-drawn set is the primary
asset. No API spend, so the $20 cap is untouched. Do not mix AI frames with the
code-drawn set.

## Known limits

- Not true lip sync; amplitude only.
- Transitions are crossfades.
- I have not verified Recordly or any editor playback.
- The 32 px legibility, aesthetic quality and animation feel are for the owner to judge.
