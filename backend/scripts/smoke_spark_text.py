"""Probe 1a — Muse Spark, text only.

Asks for the kind of output the pipeline needs (a natural Arabic translation plus a
style judgement), then reports latency, token usage, and the estimated cost.
"""

from __future__ import annotations

import json

from _probe import SPARK_MODEL, post_json, receipt, response_text, spark_cost, summarize, usage_of

PROMPT = """You are the text engine of an Arabic localization tool for comics.

Source line (English, spoken by a young character in a slice-of-life comic):
"See you tomorrow, I'll bring the sketches."

Return strict JSON only, with this shape:
{"translation_ar": "...", "register": "one of: casual-egyptian, modern-standard, formal", "style_note": "one short sentence on how a letterer should set this", "riyadh_fit": "short"}

Rules:
- The Arabic must sound like a native speaker, not a translation.
- No Latin characters in translation_ar.
- No explanation outside the JSON.
"""


def main() -> None:
    payload = {
        "model": SPARK_MODEL,
        "input": [
            {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": PROMPT}],
            }
        ],
        "reasoning": {"effort": "minimal"},
        "max_output_tokens": 900,
    }
    result = post_json("/responses", payload)
    text = response_text(result.body)
    parsed: dict[str, object] | None = None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        pass

    path = receipt(
        "spark-text",
        {
            "request": payload,
            "http_status": result.status,
            "latency_ms": result.latency_ms,
            "body": result.body,
            "output_text": text,
        },
    )
    usage = usage_of(result.body)
    summarize(
        "spark_text",
        model=SPARK_MODEL,
        result=result,
        extra={
            "output_text": text,
            "json_parsed": parsed is not None,
            "json": parsed,
            "cost_usd_estimate": spark_cost(usage),
            "receipt": str(path),
        },
    )


if __name__ == "__main__":
    main()
