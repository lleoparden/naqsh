"""Run the 40 English translation cases in both registers and write an Arabic review sheet.

Automatable checks only: valid JSON, Arabic-script ratio, digits preserved, Latin left
over, length ratio. Correctness is never asserted; the owner reviews the sheet at
L:\\naqsh-review\\arabic-review\\.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.pipeline import meta
from app.pipeline.spend import record_spend

REPO = Path(__file__).resolve().parents[2]
CASES = REPO / "backend" / "data" / "translation-cases.json"
OUT = REPO / "docs" / "evidence" / "translation-eval.json"
REVIEW = Path(r"L:\naqsh-review\arabic-review")

ARABIC = re.compile(r"[\u0600-\u06ff]")
LATIN = re.compile(r"[A-Za-z]")
DIGITS = re.compile(r"[0-9\u0660-\u0669]+")

PROMPT = """Translate each English line to Arabic for a friendly bakery/cafe/travel comic.
Return strict JSON: {"t01": "Arabic", ..., "t40": "Arabic"}.

Rules:
- Keep personal and place names in consistent Arabic transliteration.
- Keep numbers as digits exactly (do not spell them out); keep times like 08:30.
- Keep brand-like words (Moonbrew) as a consistent Arabic transliteration.
- Translate SFX into natural Arabic sound words.
- No English words left unless the input is a proper brand name.
- Register: {register}.
"""


def normalize_digits(text: str) -> str:
    table = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
    return text.translate(table)


def digits(text: str) -> list[str]:
    return DIGITS.findall(normalize_digits(text))


def check(source: str, arabic: str, allow_latin: bool) -> dict:
    letters = [c for c in arabic if c.isalpha()]
    arabic_letters = sum(1 for c in letters if ARABIC.match(c))
    latin = LATIN.findall(arabic)
    return {
        "arabic_ratio": round(arabic_letters / max(1, len(letters)), 3),
        "digits_source": digits(source),
        "digits_arabic": digits(arabic),
        "digits_preserved": digits(source) == digits(arabic),
        "latin_left": "".join(sorted(set(latin))),
        "latin_ok": (not latin) or allow_latin,
        "length_ratio": round(len(arabic) / max(1, len(source)), 2),
        "empty": not arabic.strip(),
    }


def call(register: str) -> tuple[dict, float]:
    prompt = PROMPT.replace("{register}", "Egyptian colloquial Arabic" if register == "egyptian" else "Modern Standard Arabic")
    payload = {
        "model": meta.settings.spark_model,
        "input": [{"type": "message", "role": "user", "content": [{"type": "input_text", "text": prompt}]}],
        "reasoning": {"effort": "minimal"},
        "max_output_tokens": 4000,
    }
    body = meta._post("/responses", payload)
    if body.get("status") == "incomplete":
        raise RuntimeError(f"incomplete: {body.get('incomplete_details')}")
    usage = meta.Usage.from_response(body)
    data = meta._parse_json_object(meta._response_text(body))
    return data, usage.spark_cost()


def main() -> None:
    payload = json.loads(CASES.read_text(encoding="utf-8"))
    cases = payload["cases"]
    results = {}
    total = 0.0
    ids = "\n".join(f"{case['id']}: {case['text']}" for case in cases)
    for register in ("egyptian", "msa"):
        prompt = PROMPT.replace("{register}", "Egyptian colloquial Arabic" if register == "egyptian" else "Modern Standard Arabic")
        body = meta._post(
            "/responses",
            {
                "model": meta.settings.spark_model,
                "input": [
                    {
                        "type": "message",
                        "role": "user",
                        "content": [{"type": "input_text", "text": prompt + "\n\n" + ids}],
                    }
                ],
                "reasoning": {"effort": "minimal"},
                "max_output_tokens": 4000,
            },
        )
        usage = meta.Usage.from_response(body)
        cost = usage.spark_cost()
        total += cost
        record_spend(f"translation cases {register}", cost, kind="text", cases=len(cases))
        translations = meta._parse_json_object(meta._response_text(body))
        results[register] = translations
        print(register, len(translations), f"${cost:.4f}")

    rows = []
    summary = {"cases": len(cases), "cost_usd": round(total, 6), "checks": {}}
    for case in cases:
        egyptian = str(results["egyptian"].get(case["id"], ""))
        msa = str(results["msa"].get(case["id"], ""))
        checks = {
            "egyptian": check(case["text"], egyptian, case.get("allow_latin", False)),
            "msa": check(case["text"], msa, case.get("allow_latin", False)),
        }
        for register in ("egyptian", "msa"):
            for key, value in checks[register].items():
                summary["checks"].setdefault(f"{register}.{key}", []).append(value)
        rows.append(
            f"| {case['id']} | {case['text']} | {egyptian} | {msa} | "
            f"{checks['egyptian']['arabic_ratio']} / {checks['msa']['arabic_ratio']} | "
            f"{'yes' if checks['egyptian']['digits_preserved'] else 'NO'} / {'yes' if checks['msa']['digits_preserved'] else 'NO'} |"
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"summary": summary, "results": results, "per_case": [
        {"id": case["id"], "text": case["text"], **checks} for case, checks in
        ((case, {"egyptian": check(case["text"], str(results["egyptian"].get(case["id"], "")), case.get("allow_latin", False)),
                 "msa": check(case["text"], str(results["msa"].get(case["id"], "")), case.get("allow_latin", False))})
         for case in cases)
    ]}, indent=2, ensure_ascii=False), encoding="utf-8")

    REVIEW.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Arabic review sheet — English translation cases",
        "",
        "Automatable checks only; correctness is yours to judge. `ratios` = Arabic-script",
        "letter ratio (Egyptian / MSA); `digits` = source digits preserved (Egyptian / MSA).",
        "",
        "| id | English | Egyptian | MSA | ratios | digits |",
        "|---|---|---|---|---|---|",
        *rows,
        "",
        f"Cost: ${total:.4f} for {len(cases)} strings x 2 registers.",
    ]
    (REVIEW / "review.md").write_text("\n".join(lines), encoding="utf-8")
    print("wrote", OUT, "and", REVIEW / "review.md", f"total ${total:.4f}")


if __name__ == "__main__":
    main()
