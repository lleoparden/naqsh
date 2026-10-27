# Meta Model API — findings

Every row is one of: **confirmed by a probe in `backend/scripts/`**, **confirmed
from the official docs** (linked), or explicitly **UNCONFIRMED**. No guesses are
presented as fact.

- Docs: <https://dev.meta.ai/docs> (read 2026-10-27)
- Base URL: `https://api.meta.ai/v1`, Bearer auth, keys start with `LLM_`
- Reachability from Cairo, Egypt: **works**. Unauthenticated calls return `401`
  over HTTPS; no timeout, no geo-block at the network layer.
- Probe receipts: `backend/.cache/probes/*.json` (gitignored). Images:
  `assets/generated/`.
- Spend for this whole phase, one page of three text regions: **≈ $0.040**.

## Headline answers

| Question | Answer |
| --- | --- |
| Is the API reachable from Egypt? | **Yes.** HTTPS + auth work; 401 without a key, 200 with it. |
| Does Muse Image support inpainting or editing? | **Editing, yes; mask inpainting, no.** `mask` is rejected as `unsupported_parameter`. Instruction edits erase lettering extremely well on flat art, but re-render the page with a small global offset (≈16 px vertical on 1280×1920). |
| What does SAM return? | Streamed **special-token text**: one line per frame, `<0f>` then `id<|box;…|><|mask;…|>`. Boxes in source pixels; masks are compressed base85 payloads the size of **the object's box**, not the frame. Use `meta-sam-parser` to decode. |
| How good is the Arabic? | **Good on the first try.** `muse-spark-1.3` returned `أشوفك بكرة وهجيب معايا الرسومات` for "See you tomorrow, I'll bring the sketches" — natural Egyptian colloquial, no Latin characters, valid JSON. Native-speaker judgement is still the owner's job. |

---

## Shared facts

| Item | Value | Source |
| --- | --- | --- |
| Protocols | Responses, Chat Completions, Messages | docs |
| Error envelope | `{"error": {"message", "type", "code", "param"}}` | docs/error-handling |
| 404 nuance | Unknown paths return an empty body (no JSON) | docs/error-handling |
| Rate-limit headers | observed live: `x-ratelimit-limit-requests`, `-remaining-requests`, `-limit-tokens`, `-remaining-tokens` | probe |
| Limits scope | per team, not per key | docs |
| 401 body | `authentication_error` / `invalid_api_key` | probe (unauthenticated call) |

---

## 1. Muse Spark (text + vision)

Models: `muse-spark-1.3` (used), `1.2`, `1.1`; Contributor variants. Price
$1.25/M input, $4.25/M output.

### Probe A — text (`smoke_spark_text.py`)

| Field | Measured |
| --- | --- |
| HTTP | 200 |
| Latency | **2,018 ms** |
| Usage | 137 in / 268 out, of which **204 reasoning tokens** |
| Cost | **$0.00131** |
| JSON | valid on the first try, no prose wrapper |
| Output | `{"translation_ar": "أشوفك بكرة وهجيب معايا الرسومات", "register": "casual-egyptian", …}` |

**Gotcha, and it cost two calls:** with `max_output_tokens: 400` the response
came back `status: incomplete`, `incomplete_details.reason: max_output_tokens`,
`output_tokens: 400` and **398 of them were reasoning** — an empty answer that
looked like a parsing bug. Muse Spark is a reasoning model and reasoning tokens
count against the output budget. Fix: `reasoning: {"effort": "minimal"}` plus a
realistic `max_output_tokens` (900+ here). Even at `minimal`, a short JSON answer
burned 204 reasoning tokens; budget for it.

### Probe B — vision (`smoke_spark_image.py`)

| Field | Measured |
| --- | --- |
| Image | 1280×1920 generated panel, sent as a base64 `data:` URL |
| HTTP / latency | 200 / **6,768 ms** |
| Usage | 3,367 in / 435 out (217 reasoning) |
| Cost | **$0.00606** |
| Accuracy | **3/3** text regions read exactly (`CHAPTER ONE`, `FRESH BREAD?`, `EVERY MORNING`) |
| Bbox quality | speech-bubble boxes cover the bubble, not the glyphs — good for fitting, not for pixel masks |
| Output | strict JSON, 3 regions, each with `bbox_norm`, `source_text`, `translation_ar`, `style`, `font_style` |

Observations:

- The model answered with the whole page in context — one call returns reading,
  translation, and a lettering-style description, which is exactly the triple the
  pipeline needs.
- `bbox_norm` is usable as a **prompt** for SAM (see below) but is too loose to be
  the layer boundary itself.
- UNCONFIRMED: behaviour on dense pages (a 9-panel comic), on Arabic *source*
  text, and on low-contrast lettering. Phase 5 measures recall on 5 pages.

---

## 2. SAM 3.1 (segmentation)

Model: `sam-3.1`. Responses API only, streamed. $2.50 / 1,000 images.

### Wire format (confirmed)

```
<0f>0<|box;x1=90;y1=479;x2=512;y2=807;w=1280;h=1920;c=0.9609…|><|mask;x=0;y=0;c=0.9609…;data=329,423,!…|>
```

- One `response.output_text.delta` per frame; a still is `<0f>`; `response.completed`
  ends it. 9 SSE events for one image.
- Object ids are stable but **not dense**.
- Boxes are source pixels; `w`,`h` are source dimensions, repeated on every record.
- Mask `data=H,W,<enc><payload>`: `H`,`W` are the mask raster, **not the frame**.
  In both probes the raster matched the object's **box size** (329×423 for a
  422×328 box; 148×657 for a 656×130 box), so the mask is a crop of the box at
  roughly 1:1 scale. Placing it needs the box offset.
- `<enc>` is `!` (one_bit) or `~` (lossless). Box/point prompts always return
  `one_bit`.
- Payload is **compressed** base85, not raw bits: 329×423 = 139,167 pixels but the
  payload is ~294 chars. A hand-rolled Ascii85/RFC1924 + bit-unpack attempt failed
  on every alphabet. **Use `meta-sam-parser` (Python ≥0.0.6; 0.1.0 used here)** —
  `parse_responses_stream(events, image_segmentation_format())` then
  `decode_mask_to_raster(record.mask)` returns `H*W` bytes of 0/1. Feed it the real
  event objects; synthetic events that lack lane fields raise
  `ResponsesStreamLaneError`.

### Probe C — concept prompt (`smoke_sam.py "<prompt>"`)

| Prompt | Result |
| --- | --- |
| `text` | **0 matches**, 3,446 ms, billed 1 image. Empty lane, no error — valid outcome. |
| `speech bubble` | **2 matches**, 3,429 ms, conf 0.961 on both, masks 329×423 and 391×445, foreground 73%/64% of their boxes |

The overlay (`assets/generated/test-panel-speech-bubble-masks.png`) shows both
bubbles tinted exactly, outline included.

**Consequence for the pipeline:** SAM's concept vocabulary is a noun phrase the
model recognizes ("speech bubble", "caption box", "menu item"), not "text".
Lettering is not a reliable concept. Phase 5 therefore uses **Spark's bboxes as
SAM box prompts** for the text itself, and concept prompts only for containers.

### Probe D — box prompt (the precision path)

Prompt text: `<0f>1<|box;x1=301;y1=321;x2=982;y2=451;w=1280;h=1920|>`

| Field | Measured |
| --- | --- |
| Result | 1 object, mask 148×657, foreground 93%, conf 0.949 |
| Box refinement | input (301,321)–(982,451) → returned (315,315)–(971,462): SAM tightened the box to the caption panel |
| Latency | ~3.4 s, $0.0025 |

**Syntax gotcha:** the box prompt without a frame header and object id failed with
`400 invalid prompt: the noun phrase must not contain <|...|> tokens; geometric
prompts go after a <Nf> frame header`. The working form is `<0f><id><|box;…|>`,
ids chosen by the caller, up to 16 objects per request.

---

## 3. Muse Image (generation + edit)

Model: `muse-image-1.0`. $0.01 per returned image, 150 RPM. Two interfaces:
Responses (conversational) and `/v1/images/generations` + `/v1/images/edits`
(OpenAI-compatible).

### Probe E — generate (`smoke_image_generate.py`)

| Field | Measured |
| --- | --- |
| Request | `1024x1536`, `output_format: png`, `response_format: b64_json` |
| Latency | **12,200 ms** |
| Returned | **1280×1920** PNG, 2.19 MB — `size` really is aspect ratio only |
| Cost | $0.01 |
| Result | clean, original comic panel with exactly the three text regions requested |

### Probe F — edit / "inpaint" (`smoke_image_edit.py`)

| Field | Measured |
| --- | --- |
| Request | JSON body, `images: [{image_url: data:…}]`, instruction prompt |
| Latency | **13,643 ms** |
| Cost | $0.01 |
| Lettering | **removed cleanly** from all three regions; bubbles and caption left empty and readable |
| Artwork | character, lamps, bread, city, line weights all preserved to the eye |
| Geometry | **not pixel-identical**: a global offset of ≈ **-16 px vertically** (phase correlation), mean abs diff outside text 19.96 → 12.36 after shifting |

**What this means for the pipeline:**

- Plan A is viable, but the edited image must be **registered** (phase
  correlation / ECC) before it is composited through SAM masks. Without that,
  masked compositing leaves a 16 px seam.
- Alternative that needs no registration: accept the edit as the new base plate
  (the art is faithful) and draw Arabic layers on top. Cheaper and visually
  indistinguishable at page scale, but the demo must not claim "original pixels
  preserved".
- No mask parameter: multipart `mask` → `400 unsupported_parameter`; edits are
  instruction-only. Composite or accept the re-render.
- UNCONFIRMED: behaviour on photographic or gradient-heavy art (flat vector art
  is the easy case), and whether repeated edits accumulate drift.

### Observed variability (7 runs, 2026-10-27)

| Outcome | Runs | Notes |
| --- | --- | --- |
| Clean plate, clean output | 4 | no ghost; text fits |
| Faint ghost in one bubble | 2 | "MORNING" remained at ~60% opacity |
| Smear on the caption panel | 1 | edit re-rendered the panel edge |

The offset also varies: **-16 px**, **-30 px**, and **-40 px** vertical were all
measured on the same input. Registration handles that part; the ghost does not.
A mask-aware cleanliness score is Phase 4 work — the bbox-based `dirty_ratio`
correlates (clean ≈0.05, ghosted ≈0.08–0.13) but overlaps, so it is not a gate.

---

## Cost model (measured, not estimated)

One page, three text regions, this probe set:

| Call | Measured cost |
| --- | --- |
| Spark vision read | $0.00606 |
| Spark text/translation | $0.00131 |
| SAM concept (per concept) | $0.00250 |
| SAM box prompts (1 region) | $0.00250 |
| Muse Image generate | $0.01000 |
| Muse Image edit | $0.01000 |
| **One production page (vision + 1 SAM pass + 1 edit)** | **≈ $0.022** |
| **This phase's total spend** | **≈ $0.040** |

At ~$0.02–0.03/page the $150 credit covers thousands of pages; wall-clock, not
money, is the constraint. A page currently costs **~20–30 s** of model time
(6.8 vision + 3.4 SAM + 13.6 edit), before any local work.

## Errors seen

| Where | Status | Body / note |
| --- | --- | --- |
| Unauthenticated `GET /v1/models` | 401 | `authentication_error`, `invalid_api_key` |
| Spark with `max_output_tokens: 400` | 200 | `status: incomplete`, reason `max_output_tokens` — silent empty answer |
| SAM concept `text` | 200 | zero matches, empty lane — not an error, must be handled |
| SAM box prompt without `<0f>id` | 400 | `invalid prompt: … geometric prompts go after a <Nf> frame header` |
| Muse Image multipart `mask` | 400 | `unsupported_parameter` (from docs; not re-tested) |

## Still UNCONFIRMED

- Arabic quality judgement by a native speaker across registers and short bubbles.
- Recall on dense pages / photographic posters / menus (Phase 5 gate).
- Whether SAM "lossless" (`~`) masks differ in practice from `one_bit` for our use.
- Content-policy behaviour when an image contains text the filter dislikes.
- Behaviour at large page sizes (payload limits, 413).
