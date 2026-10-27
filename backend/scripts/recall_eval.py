"""Ground-truth recall/precision for region finding.

The strings used to generate each fixture (or the visible strings of the public-domain
poster) are the truth. Each page is read once with Muse Spark; every expected string is
matched to a found region and the failures are classified as missing, split, merged or
hallucinated.

Usage: python backend/scripts/recall_eval.py [page ...]
"""

from __future__ import annotations

import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image  # noqa: E402

from app.pipeline.regions import read_regions  # noqa: E402
from app.pipeline.spend import record_spend  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "assets" / "generated" / "fixtures"
EVIDENCE = REPO / "docs" / "evidence" / "phase-5"
GROUND_TRUTH = EVIDENCE / "ground-truth.json"
MATCH_THRESHOLD = 0.72
PUNCT = re.compile(r"[^\w\s\u0600-\u06FF]", re.UNICODE)


def normalise(text: str) -> str:
    text = text.casefold().replace("&", " and ")
    text = PUNCT.sub(" ", text)
    return " ".join(text.split())


def score(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    ratio = SequenceMatcher(None, a, b).ratio()
    if a in b or b in a:
        ratio = max(ratio, 0.95)
    return ratio


def evaluate_page(name: str, expected: list[str], found: list[str]) -> dict:
    exp = [normalise(item) for item in expected]
    fnd = [normalise(item) for item in found]
    pairs = []
    for i, e in enumerate(exp):
        for j, f in enumerate(fnd):
            s = score(e, f)
            if s >= MATCH_THRESHOLD:
                pairs.append((s, i, j))
    pairs.sort(reverse=True)
    matched_exp: dict[int, int] = {}
    matched_fnd: set[int] = set()
    for s, i, j in pairs:
        if i in matched_exp or j in matched_fnd:
            continue
        matched_exp[i] = j
        matched_fnd.add(j)

    missing = [expected[i] for i in range(len(exp)) if i not in matched_exp]

    # Prices/numbers found as their own regions are correct behaviour for a localizer,
    # not hallucinations; count them separately.
    def is_numeric(text: str) -> bool:
        return bool(re.fullmatch(r"[\d\s.,/+-]+", text))

    numeric_found = [j for j in range(len(fnd)) if j not in matched_fnd and fnd[j] and is_numeric(fnd[j])]
    text_found = [j for j in range(len(fnd)) if j not in matched_fnd and j not in numeric_found]

    split = 0
    for j in text_found:
        for i in range(len(exp)):
            if fnd[j] and (fnd[j] in exp[i] or exp[i] in fnd[j]):
                split += 1
                break
    hallucinated = [
        found[j]
        for j in text_found
        if not any(fnd[j] and (fnd[j] in exp[i] or exp[i] in fnd[j]) for i in range(len(exp)))
    ]
    merged = 0
    counts: dict[int, int] = {}
    for _s, i, _j in pairs:
        if i in matched_exp:
            counts[i] = counts.get(i, 0) + 1
    merged = sum(1 for value in counts.values() if value > 1)

    text_regions = len(fnd) - len(numeric_found)
    recall = len(matched_exp) / len(exp) if exp else 0.0
    precision = len(matched_fnd) / text_regions if text_regions else 0.0
    return {
        "page": name,
        "expected": len(exp),
        "found": len(fnd),
        "matched": len(matched_exp),
        "recall": round(recall, 3),
        "precision": round(precision, 3),
        "prices": len(numeric_found),
        "missing": missing,
        "hallucinated": hallucinated,
        "split": split,
        "merged": merged,
    }


def main() -> None:
    truth = json.loads(GROUND_TRUTH.read_text(encoding="utf-8"))
    pages = sys.argv[1:] or list(truth)
    results = []
    total_cost = 0.0
    for name in pages:
        path = FIXTURES / f"{name}.png"
        if not path.is_file():
            print(f"{name}: missing file", flush=True)
            continue
        with Image.open(path) as image:
            width, height = image.size
        regions, usage = read_regions(path.read_bytes(), width, height, "egyptian")
        cost = usage.spark_cost()
        total_cost += cost
        record_spend(f"recall eval {name}", cost, kind="read", regions=len(regions))
        found = [region.source_text for region in regions]
        row = evaluate_page(name, truth[name]["expected"], found)
        row["types"] = [{"id": r.id, "type": r.type, "action": r.action} for r in regions]
        results.append(row)
        print(
            f"{name:24s} recall={row['recall']:.2f} precision={row['precision']:.2f} "
            f"found={row['found']:2d}/{row['expected']:2d} missing={len(row['missing'])} "
            f"halluc={len(row['hallucinated'])} cost=${cost:.4f}",
            flush=True,
        )

    (EVIDENCE / "recall-eval.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nTOTAL COST ${total_cost:.4f}")


if __name__ == "__main__":
    main()
