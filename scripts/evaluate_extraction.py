"""
evaluate_extraction.py

STEP 2 / Part 12: extraction evaluation.

WHAT THIS MEASURES
-------------------
Runs the extraction pipeline (mock mode, so this is reproducible offline)
on the bundled synthetic sample PDF and compares the result against
data/sample_pdfs/expected_claims.json, computing:

1. CLAIM IDENTIFICATION PRECISION / RECALL
   A predicted claim is matched to an expected claim if they are on the
   same page and their normalized `original_text` is identical (Step 2
   only uses mock mode, which is deterministic, so we require exact text
   match rather than fuzzy matching -- see LIMITATIONS below).

     precision = matched_claims / predicted_claims
     recall    = matched_claims / expected_claims

2. IMPORTANT FIELD EXTRACTION CORRECTNESS
   For every matched claim pair, we check field-by-field equality on:
   metric, value, unit, scope, reporting_period, baseline_year.

     field_accuracy = correct_field_values / total_fields_checked

HOW TO RUN
----------
    python scripts/evaluate_extraction.py

LIMITATIONS (documented, not hidden)
--------------------------------------
- This evaluates MOCK mode against itself, which will score ~100% by
  construction -- it exists to (a) prove the evaluation *mechanism* works
  end-to-end and (b) act as a regression check if mock_data.py or the
  sample PDF ever drift out of sync. It is NOT a measure of real LLM
  extraction quality.
- To evaluate real LLM quality, re-run with --provider groq/ollama once
  credentials are available and compare against a hand-labelled answer key
  for a real PDF; that is future work, not Step 2.
- The dataset here is a single PDF / 10 claims. This is an initial sanity
  check, not a statistically meaningful benchmark.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.extraction.claim_extractor import extract_claims_from_pages  # noqa: E402
from app.extraction.pdf_parser import parse_pdf  # noqa: E402
from app.utils.schemas import ClaimRecord  # noqa: E402

SAMPLE_PDF = PROJECT_ROOT / "data" / "sample_pdfs" / "synthetic_esg_report.pdf"
EXPECTED_CLAIMS_PATH = PROJECT_ROOT / "data" / "sample_pdfs" / "expected_claims.json"

FIELDS_TO_CHECK = ["metric", "value", "unit", "scope", "reporting_period", "baseline_year"]


def _normalize(text: str) -> str:
    return " ".join(text.split()).strip().lower()


def load_expected_claims() -> list[dict]:
    with EXPECTED_CLAIMS_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    return data["claims"]


def match_claims(predicted: list[ClaimRecord], expected: list[dict]) -> list[tuple[ClaimRecord, dict]]:
    """Greedy match: same page_number + identical normalized original_text."""
    matches: list[tuple[ClaimRecord, dict]] = []
    used_expected_idx: set[int] = set()

    for p in predicted:
        for i, e in enumerate(expected):
            if i in used_expected_idx:
                continue
            if p.page_number == e["page_number"] and _normalize(p.original_text) == _normalize(e["original_text"]):
                matches.append((p, e))
                used_expected_idx.add(i)
                break

    return matches


def compute_field_accuracy(matches: list[tuple[ClaimRecord, dict]]) -> dict[str, float]:
    per_field_correct: dict[str, int] = {f: 0 for f in FIELDS_TO_CHECK}
    per_field_total: dict[str, int] = {f: 0 for f in FIELDS_TO_CHECK}

    for predicted, expected in matches:
        pred_dict = predicted.model_dump(mode="json")
        for f in FIELDS_TO_CHECK:
            per_field_total[f] += 1
            if pred_dict.get(f) == expected.get(f):
                per_field_correct[f] += 1

    return {
        f: (per_field_correct[f] / per_field_total[f] if per_field_total[f] else float("nan"))
        for f in FIELDS_TO_CHECK
    }


def main() -> int:
    print("Evaluating Step 2 extraction against the bundled synthetic ESG PDF (MOCK mode).\n")

    pages = parse_pdf(SAMPLE_PDF)
    results = extract_claims_from_pages(pages, company_hint="GreenLeaf Industries Ltd.")
    predicted = [c for r in results for c in r.claims]
    expected = load_expected_claims()

    matches = match_claims(predicted, expected)

    n_predicted = len(predicted)
    n_expected = len(expected)
    n_matched = len(matches)

    precision = n_matched / n_predicted if n_predicted else float("nan")
    recall = n_matched / n_expected if n_expected else float("nan")
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) and precision == precision and recall == recall
        else float("nan")
    )

    print("--- Claim Identification ---")
    print(f"Predicted claims: {n_predicted}")
    print(f"Expected claims:  {n_expected}")
    print(f"Matched claims:   {n_matched}")
    print(f"Precision:        {precision:.2%}")
    print(f"Recall:           {recall:.2%}")
    print(f"F1:               {f1:.2%}")

    field_accuracy = compute_field_accuracy(matches)
    print("\n--- Field Extraction Correctness (on matched claims) ---")
    for f, acc in field_accuracy.items():
        print(f"  {f:20s}: {acc:.2%}")

    unmatched_predicted = [p for p in predicted if p not in [m[0] for m in matches]]
    unmatched_expected = [
        e for i, e in enumerate(expected) if e not in [m[1] for m in matches]
    ]
    if unmatched_predicted:
        print(f"\nUnmatched predicted claims ({len(unmatched_predicted)}):")
        for p in unmatched_predicted:
            print(f"  page {p.page_number}: {p.original_text[:80]!r}")
    if unmatched_expected:
        print(f"\nUnmatched expected claims ({len(unmatched_expected)}):")
        for e in unmatched_expected:
            print(f"  page {e['page_number']}: {e['original_text'][:80]!r}")

    print(
        "\nNOTE: this run evaluates MOCK mode against itself and is expected to "
        "score ~100% by construction (see module docstring for why). It is a "
        "sanity check on the evaluation mechanism and a regression guard, not a "
        "measure of real LLM extraction quality."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
