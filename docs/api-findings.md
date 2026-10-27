# Meta Model API — findings

Everything here is either (a) confirmed from the official docs at
<https://dev.meta.ai/docs> on 2026-10-27, (b) confirmed by a probe in
`backend/scripts/`, or (c) explicitly marked **UNCONFIRMED**. No guessing is
presented as fact.

**Reachability from Cairo, Egypt:** confirmed. Unauthenticated `GET /v1/models`
and `POST /v1/chat/completions` return `401` through HTTPS (DNS + TLS + routing
work); there is no geo-block at the network layer for these endpoints.

**Probe status:** blocked until `L:\naqsh\.env` exists with `MODEL_API_KEY`
(owner is adding it). Nothing in this file claims a latency or a response shape
that a probe has not produced; those rows say *pending*.

---

## Shared facts

| Item | Value | Source |
| --- | --- | --- |
| Base URL | `https://api.meta.ai/v1` | docs/overview, docs/quickstart |
| Auth | `Authorization: Bearer $MODEL_API_KEY`; keys start with `LLM_` | docs/authentication |
| Protocols | Responses API, Chat Completions, Messages; OpenAI/Anthropic SDKs work when pointed at the base URL | docs/protocols |
| Error envelope | `{"error": {"message", "type", "code", "param"}}`; `type` is `invalid_request_error` / `authentication_error` / `rate_limit_error` / `server_error` | docs/error-handling |
| 404 nuance | Unknown paths return an empty body, no JSON envelope | docs/error-handling |
| Rate-limit headers | `x-ratelimit-limit-tokens`, `-remaining-tokens`, `-limit-requests`, `-remaining-requests`; 429 carries `Retry-After` | docs/pricing-rate-limits |
| Limits scope | Per team, not per key | docs/pricing-rate-limits |

---

## 1. Muse Spark (text + vision)

**Model IDs:** `muse-spark-1.3`, `muse-spark-1.2`, `muse-spark-1.1`; Contributor
variants `muse-spark-1.3-contributor`, `muse-spark-1.2-contributor`. Muse Wonder
is `muse-wonder-1.0`.

**What works (docs):** text, image, video, audio, and PDF input; text out. Images
go in as `input_image` with `image_url` (public URL or base64 `data:` URL) or
`file_id`. Up to 50 images per request. Chat Completions wraps the image in an
`image_url` object instead of a plain string.

**Probes**

| Probe | Question | Result |
| --- | --- | --- |
| `smoke_spark_text.py` | Does a plain text call return strict JSON in the requested Arabic-translation shape? | **pending** |
| `smoke_spark_image.py` | Can it read lettering in place and return per-region JSON (bbox, source text, Arabic, style)? | **pending** |

**Latency:** pending. **Cost** (published): $1.25/M input, $4.25/M output
(standard); $0.10/M input, $0.20/M output (Contributor). A vision read of a
1024×1536 page is *estimated* at a few thousand input tokens — the probe records
the real number.

**Rate limits (published):** 3,000 RPM, 4,000,000 TPM (standard); 150 RPM,
3,000,000 TPM (Contributor).

**Risks / open questions**

- UNCONFIRMED: whether Arabic output is Egyptian-colloquial-capable by prompting
  alone, or whether register must be steered with examples.
- UNCONFIRMED: JSON compliance rate at temperature defaults; the probe records
  whether the reply parsed cleanly, and the fallback is the structured-output
  `text.format` schema.
- Arabic quality is judged by a native speaker (the owner), not by the model.

---

## 2. SAM 3.1 (segmentation)

**Model ID:** `sam-3.1`. Endpoint: **Responses API only**, and segmentation
output is **streamed**.

**Request shape (confirmed from docs):**

```json
{
  "model": "sam-3.1",
  "input": [{
    "type": "message",
    "role": "user",
    "content": [
      {"type": "input_text", "text": "speech bubble"},
      {"type": "input_image", "image_url": "data:image/png;base64,..."}
    ]
  }],
  "metadata": {"mask_encoding": "one_bit", "include_confidence": "true"}
}
```

- One concept per request; several concepts = several requests.
- Box/point prompts exist (`<|box;x1=..;y1=..;x2=..;y2=..;w=..;h=..|>`,
  `<|point;x=..;y=..;w=..;h=..|>`) and take priority for precision; they always
  return `one_bit` masks regardless of `mask_encoding`.
- To segment a region the user picked, box/point prompts are the precision path.

**Response format (confirmed from docs) — this is the surprising part:**

Output is **special-token text**, not JSON images:

```
<0f>0<|box;x1=211;y1=228;x2=270;y2=254;w=320;h=334|><|mask;x=0;y=0;data=27,60,~!!!!M!0c[0o...|>,1<|box;...|><|mask;...|>
```

- One line per frame; a still is frame `<0f>`; each line is one
  `response.output_text.delta` event; terminated by `response.completed`.
- `id` is a stable per-object id across frames, **not dense and not 0-based**.
- Boxes are **source pixels**; `w`,`h` repeat the source dimensions.
- Masks have their own raster size (`data=H,W,<enc><payload>`), smaller than the
  frame, height-first, **base85** (not base64) with an encoding marker `~`
  (lossless, default) or `!` (one_bit). The payload may itself contain `~`/`!`.
- Zero matches is a valid outcome: empty `output_text`, no delta events, and the
  stream still completes. Branch on empty — do not treat as an error.
- Confirmed by docs: `decodeMaskToRaster` returns a row-major `Uint8Array` of
  `H*W` 0/1 values. Official parsers exist: `meta-sam-parser` (Python, ≥0.0.6)
  and `@meta-sam/parser` (JS, ≥0.0.13).

**Probes**

| Probe | Question | Result |
| --- | --- | --- |
| `smoke_sam.py` | Exact line for our test panel; does a mask decode to H×W bits; how long does the stream take? | **pending** |

**Cost (published):** $2.50 per 1,000 images ($0.0025/image); video $0.20/1,000
frames, billed with a 50-frame minimum. **Rate limit:** 3,000 RPM, no TPM.

**Risks / open questions**

- UNCONFIRMED: whether the concept prompt `"text"` reliably finds lettering, or
  whether it needs `"speech bubble"` / `"word balloon"` and a second pass for
  text inside them. This decides the region strategy in Phase 4.
- UNCONFIRMED: mask decode for `lossless` vs `one_bit` without the official
  parser. The probe tries Ascii85/RFC1924 + bit unpack + zlib and reports what
  matches. If nothing matches cleanly, we add `meta-sam-parser` rather than
  reverse-engineering further.
- The mask raster is smaller than the frame; upscaling with nearest-neighbour
  will cost edge precision on thin lettering. That is acceptable for a *layer
  boundary* but must be checked against thin strokes.

---

## 3. Muse Image (generation + edit)

**Model ID:** `muse-image-1.0`. Two interfaces: conversational Responses API
(multi-turn refine) and OpenAI-compatible `POST /v1/images/generations` /
`POST /v1/images/edits`.

**Confirmed parameters:** `n` (1–10), `size` (`"WxH"`, sets aspect ratio, not
exact pixels), `response_format` (`b64_json` default, or `url`), `output_format`
(`webp` default, `png`, `jpeg`). Edits take `images: [{image_url | file_id}]`
(JSON) or multipart `image` (SDK). Only the `image_generation` tool is accepted;
a `web_search` tool returns 400. Built-in grounding is included in the price.

**Inpainting — the important finding:**

- **There is no mask parameter.** Multipart `mask`, `input_fidelity`, and
  `partial_images` all return `400 unsupported_parameter`. So we cannot ask for
  "repaint only these pixels".
- Edits are **instruction-based**: "changes only what you ask for while keeping
  the rest intact" is the model's claim, not a guarantee. Nothing in the docs
  bounds drift.
- **Plan A for the clean plate:** send the page with an instruction to erase the
  lettering, receive an edited page, then **composite the edited pixels back
  through SAM's masks only** — outside the text regions the original artwork is
  kept byte-for-byte. This turns an unbounded edit into a bounded one.
- **Plan B:** classical inpainting (OpenCV Telea/NS) seeded from the SAM mask and
  the bubble's sampled fill colour, used when the edit drifts or returns
  non-matching geometry.
- **Plan C (always available):** draw the bubble interior as an opaque vector
  shape above the original art, so ghost lettering is hidden even if repair is
  imperfect. This is what a human letterer does when a cover-up is cheaper than a
  repaint.

**Probes**

| Probe | Question | Result |
| --- | --- | --- |
| `smoke_image_generate.py` | Does generation work end to end, what comes back, how long, what does $0.01 buy? | **pending** |
| `smoke_image_edit.py` | Does instruction-based text removal preserve the rest of the panel, and at what latency? | **pending** |

**Cost (published):** $0.01 per returned image, flat, regardless of prompt or
search use; failures and safety-filtered images are not billed.
**Rate limit:** 150 RPM, no TPM.

**Risks / open questions**

- UNCONFIRMED: output resolution for a `1024x1536` request — the docs say `size`
  sets aspect ratio and the returned pixels differ. If the returned page is
  smaller than the source, upscaling will blur line art; Phase 5 must decide
  whether to request a larger size or re-composite at source resolution.
- UNCONFIRMED: whether the edit preserves *exact* geometry (same character
  positions, same line weights). If it drifts, only the masked composite saves
  us, and thin-stroke areas may still show seams.
- UNCONFIRMED: safety filtering on comic lettering (text inside images may trip
  content filters); the probe records the refusal shape if it happens.

---

## Cost model for one page (estimate, to be replaced by measured numbers)

| Call | Price | Per page |
| --- | --- | --- |
| SAM, 2 concepts (bubbles, text) | $0.0025 each | $0.0050 |
| Muse Spark vision read | ~2–6k in, ~0.5–1k out | $0.005–0.012 |
| Muse Spark translation batch | ~1–2k in, ~0.5k out | $0.003–0.005 |
| Muse Image clean plate | $0.01 | $0.0100 |
| **Total** | | **≈ $0.023–0.032 / page** |

At ~$0.03/page, the $150 credit covers ~5,000 pages — far beyond what the demo
needs. The real constraint is wall-clock time per page, not money. Measured
numbers land in `docs/submission-notes.md`.

---

## Errors seen so far

| Where | Status | Body | Notes |
| --- | --- | --- | --- |
| `GET /v1/models`, unauthenticated | 401 | (not printed) | Expected; proves reachability. |
| `POST /v1/chat/completions`, unauthenticated | 401 | (not printed) | Same. |

Friction log with timestamps lives in `docs/submission-notes.md`; this table is
the technical summary.
