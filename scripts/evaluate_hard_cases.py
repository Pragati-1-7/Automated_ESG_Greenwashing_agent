#!/usr/bin/env python3
"""
evaluate_hard_cases.py

Benchmark evaluation of the full pipeline against data/test/hard_cases.json.

WHY THIS EXISTS
---------------
The hard-case dataset (10 deliberately tricky claims: vague statements,
false-but-precise numbers, shifted baselines, scope confusion, absolute vs.
intensity, boundary mismatches, unit mismatches, unsupported targets, and
capacity mismatches) has existed since Step 1, but nothing has ever actually
run these cases through the pipeline and checked the output against the
expected_verdict label. scripts/validate_dataset.py only checks that the
file parses -- it never evaluates accuracy. This script closes that gap.

HOW IT WORKS
------------
Each HardCaseRecord is converted into a ClaimRecord (same fields, a claim_id
prefixed "CLM-HC-" so it is recognisably a benchmark case), then run through
the exact same build_audit_records() pipeline used by the API and the
Streamlit/React/plain-HTML frontends -- no special-cased logic for this
script. The predicted checkability and verdict are compared against the
hand-labelled expected_verdict for each case, and a confusion-style summary
table plus overall accuracy is printed.

USAGE
-----
    python scripts/evaluate_hard_cases.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.utils.schemas import ClaimRecord, ClaimType, HardCaseRecord, HardCaseType, Verdict
from app.api.pipeline import build_audit_records

HARD_CASES_PATH = PROJECT_ROOT / "data" / "test" / "hard_cases.json"

# UNSUPPORTED_TARGET cases describe a future commitment; TRUE_BUT_VAGUE cases
# are vague values statements. Every other hard-case type describes a
# claimed past/present result. This mapping only affects which verification
# branch applies (future-claim handling vs. result handling); it does not
# affect the deterministic checkability rules, which look at the structured
# fields regardless of claim_type.
_CLAIM_TYPE_BY_HARD_CASE_TYPE = {
    HardCaseType.TRUE_BUT_VAGUE: ClaimType.COMMITMENT,
    HardCaseType.UNSUPPORTED_TARGET: ClaimType.TARGET,
}


def load_hard_cases() -> list[HardCaseRecord]:
    raw = json.loads(HARD_CASES_PATH.read_text(encoding="utf-8"))
    return [HardCaseRecord(**item) for item in raw["hard_cases"]]


def to_claim_record(case: HardCaseRecord) -> ClaimRecord:
    claim_type = _CLAIM_TYPE_BY_HARD_CASE_TYPE.get(case.hard_case_type, ClaimType.RESULT)
    return ClaimRecord(
        claim_id=f"CLM-{case.case_id}",
        company=case.company,
        original_text=case.original_text,
        metric=case.metric,
        value=case.value,
        unit=case.unit,
        scope=case.scope,
        boundary=case.boundary,
        baseline_year=case.baseline_year,
        reporting_period=case.reporting_period,
        claim_type=claim_type,
        checkability=case.checkability,
        expected_verdict=case.expected_verdict,
        source_document="hard_cases.json (synthetic benchmark)",
    )


def run_benchmark(top_k: int = 5, use_semantic: bool = False) -> None:
    cases = load_hard_cases()
    claims = [to_claim_record(c) for c in cases]
    cases_by_id = {f"CLM-{c.case_id}": c for c in cases}

    records = build_audit_records(claims, top_k=top_k, use_semantic=use_semantic)
    records_by_id = {r.claim_id: r for r in records}

    rows = []
    correct = 0
    for claim_id, case in cases_by_id.items():
        record = records_by_id[claim_id]
        cr = record.checkability_result
        vr = record.verification_result

        predicted_checkability = cr.checkability.value if cr else "UNKNOWN"
        if vr is None:
            predicted_verdict = Verdict.NOT_APPLICABLE.value
        else:
            predicted_verdict = vr.verdict.value

        is_match = predicted_verdict == case.expected_verdict.value
        if is_match:
            correct += 1

        rows.append(
            {
                "case_id": case.case_id,
                "type": case.hard_case_type.value,
                "expected_checkability": case.checkability.value,
                "predicted_checkability": predicted_checkability,
                "expected_verdict": case.expected_verdict.value,
                "predicted_verdict": predicted_verdict,
                "match": is_match,
            }
        )

    total = len(rows)
    accuracy = (correct / total * 100) if total else 0.0

    print("=" * 100)
    print("  HARD-CASE BENCHMARK (data/test/hard_cases.json)")
    print("=" * 100)
    header = f"  {'Case':<8} {'Type':<22} {'Expected verdict':<24} {'Predicted verdict':<24} {'Match'}"
    print(header)
    print("  " + "-" * 96)
    for row in rows:
        match_label = "YES" if row["match"] else "NO"
        print(
            f"  {row['case_id']:<8} {row['type']:<22} {row['expected_verdict']:<24} "
            f"{row['predicted_verdict']:<24} {match_label}"
        )

    checkability_mismatches = [
        r for r in rows if r["expected_checkability"] != r["predicted_checkability"]
    ]

    print("\n  " + "-" * 96)
    print(f"  Verdict accuracy: {correct}/{total} ({accuracy:.0f}%)")
    print(f"  Checkability agreement: {total - len(checkability_mismatches)}/{total}")
    if checkability_mismatches:
        print("\n  Checkability mismatches:")
        for r in checkability_mismatches:
            print(
                f"    {r['case_id']}: expected {r['expected_checkability']}, "
                f"got {r['predicted_checkability']}"
            )

    print(
        "\n  [NOTE] This is a triage accuracy benchmark over 10 deliberately adversarial\n"
        "  synthetic cases, not a statistically powered evaluation. A result below 100%\n"
        "  identifies exactly which trick case the current rule set does not yet handle."
    )
    print("=" * 100)


if __name__ == "__main__":
    run_benchmark()
