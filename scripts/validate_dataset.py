"""
validate_dataset.py

Validates the Step 1 dataset foundation:
  - data/claims/claims.json
  - data/evidence/evidence.json
  - data/test/hard_cases.json

WHAT IT CHECKS
--------------
1. Every record matches its Pydantic schema (app/utils/schemas.py) -- this
   automatically enforces "required fields are not empty" and "fields have
   valid types/values" (e.g. verdict must be one of the allowed strings).
2. claim_id values are unique across claims.json.
3. evidence_id values are unique across evidence.json.
4. Every evidence.claim_id actually refers to a claim_id that exists in
   claims.json (referential integrity).
5. case_id values are unique across hard_cases.json.
6. Every NOT_CHECKABLE claim has expected_verdict == NOT_APPLICABLE (and
   vice versa is checked loosely -- CHECKABLE claims should NOT be
   NOT_APPLICABLE).

HOW TO RUN
----------
    python scripts/validate_dataset.py

The script prints a clear PASS/FAIL report and exits with code 0 on
success or 1 on failure (so it can be used in CI later).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from pydantic import ValidationError

# Allow running this script directly (python scripts/validate_dataset.py)
# by adding the project root to sys.path.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.utils.schemas import ClaimRecord, EvidenceRecord, HardCaseRecord  # noqa: E402

CLAIMS_PATH = PROJECT_ROOT / "data" / "claims" / "claims.json"
EVIDENCE_PATH = PROJECT_ROOT / "data" / "evidence" / "evidence.json"
HARD_CASES_PATH = PROJECT_ROOT / "data" / "test" / "hard_cases.json"


class ValidationReport:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.passed_checks: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def ok(self, msg: str) -> None:
        self.passed_checks.append(msg)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


def load_json(path: Path, report: ValidationReport) -> dict[str, Any] | None:
    if not path.exists():
        report.error(f"Missing required file: {path.relative_to(PROJECT_ROOT)}")
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        report.error(f"{path.relative_to(PROJECT_ROOT)} is not valid JSON: {e}")
        return None


def validate_claims(data: dict[str, Any], report: ValidationReport) -> list[ClaimRecord]:
    records: list[ClaimRecord] = []
    raw_claims = data.get("claims", [])
    if not raw_claims:
        report.error("claims.json contains no 'claims' array or it is empty.")
        return records

    seen_ids: set[str] = set()
    for i, raw in enumerate(raw_claims):
        try:
            claim = ClaimRecord(**raw)
        except ValidationError as e:
            report.error(f"claims.json[{i}] failed schema validation: {e}")
            continue

        if claim.claim_id in seen_ids:
            report.error(f"Duplicate claim_id found: {claim.claim_id}")
        seen_ids.add(claim.claim_id)

        # Cross-field sanity check: NOT_CHECKABLE claims must resolve to NOT_APPLICABLE.
        if claim.checkability.value == "NOT_CHECKABLE" and claim.expected_verdict.value != "NOT_APPLICABLE":
            report.error(
                f"{claim.claim_id} is NOT_CHECKABLE but expected_verdict is "
                f"'{claim.expected_verdict.value}' (should be NOT_APPLICABLE)."
            )
        if claim.checkability.value == "CHECKABLE" and claim.expected_verdict.value == "NOT_APPLICABLE":
            report.error(
                f"{claim.claim_id} is CHECKABLE but expected_verdict is NOT_APPLICABLE "
                f"(a checkable claim should resolve to ALIGN/CONTRADICT/INSUFFICIENT_EVIDENCE)."
            )

        records.append(claim)

    report.ok(f"Validated {len(records)} claim record(s) against ClaimRecord schema.")
    report.ok(f"Checked claim_id uniqueness across {len(records)} claims.")
    return records


def validate_evidence(
    data: dict[str, Any], report: ValidationReport, valid_claim_ids: set[str]
) -> list[EvidenceRecord]:
    records: list[EvidenceRecord] = []
    raw_evidence = data.get("evidence", [])
    if not raw_evidence:
        report.error("evidence.json contains no 'evidence' array or it is empty.")
        return records

    seen_ids: set[str] = set()
    for i, raw in enumerate(raw_evidence):
        try:
            ev = EvidenceRecord(**raw)
        except ValidationError as e:
            report.error(f"evidence.json[{i}] failed schema validation: {e}")
            continue

        if ev.evidence_id in seen_ids:
            report.error(f"Duplicate evidence_id found: {ev.evidence_id}")
        seen_ids.add(ev.evidence_id)

        if ev.claim_id not in valid_claim_ids:
            report.error(
                f"{ev.evidence_id} references claim_id '{ev.claim_id}' which does not exist in claims.json."
            )

        records.append(ev)

    report.ok(f"Validated {len(records)} evidence record(s) against EvidenceRecord schema.")
    report.ok(f"Checked evidence_id uniqueness across {len(records)} evidence records.")
    report.ok("Checked that every evidence.claim_id refers to an existing claim.")
    return records


def validate_hard_cases(data: dict[str, Any], report: ValidationReport) -> list[HardCaseRecord]:
    records: list[HardCaseRecord] = []
    raw_cases = data.get("hard_cases", [])
    if not raw_cases:
        report.error("hard_cases.json contains no 'hard_cases' array or it is empty.")
        return records

    seen_ids: set[str] = set()
    for i, raw in enumerate(raw_cases):
        try:
            case = HardCaseRecord(**raw)
        except ValidationError as e:
            report.error(f"hard_cases.json[{i}] failed schema validation: {e}")
            continue

        if case.case_id in seen_ids:
            report.error(f"Duplicate case_id found: {case.case_id}")
        seen_ids.add(case.case_id)

        if not case.notes or not case.notes.strip():
            report.error(f"{case.case_id} is missing a non-empty 'notes' explanation.")

        records.append(case)

    report.ok(f"Validated {len(records)} hard case record(s) against HardCaseRecord schema.")
    report.ok(f"Checked case_id uniqueness across {len(records)} hard cases.")
    return records


def print_summary(
    claims: list[ClaimRecord],
    evidence: list[EvidenceRecord],
    hard_cases: list[HardCaseRecord],
) -> None:
    print("\n--- Dataset Summary ---")
    print(f"Claims:      {len(claims)}")
    verdict_counts: dict[str, int] = {}
    for c in claims:
        verdict_counts[c.expected_verdict.value] = verdict_counts.get(c.expected_verdict.value, 0) + 1
    for verdict, count in sorted(verdict_counts.items()):
        print(f"  - {verdict}: {count}")

    print(f"Evidence:    {len(evidence)}")
    tier_counts: dict[int, int] = {}
    for e in evidence:
        tier_counts[e.source_tier.value] = tier_counts.get(e.source_tier.value, 0) + 1
    for tier in sorted(tier_counts):
        print(f"  - Tier {tier}: {tier_counts[tier]}")

    print(f"Hard cases:  {len(hard_cases)}")
    type_counts: dict[str, int] = {}
    for h in hard_cases:
        type_counts[h.hard_case_type.value] = type_counts.get(h.hard_case_type.value, 0) + 1
    for t, count in sorted(type_counts.items()):
        print(f"  - {t}: {count}")


def main() -> int:
    report = ValidationReport()

    print("Running dataset validation for the ESG Greenwashing Detection & Verification Agent...\n")

    claims_data = load_json(CLAIMS_PATH, report)
    evidence_data = load_json(EVIDENCE_PATH, report)
    hard_cases_data = load_json(HARD_CASES_PATH, report)

    claims: list[ClaimRecord] = []
    evidence: list[EvidenceRecord] = []
    hard_cases: list[HardCaseRecord] = []

    if claims_data is not None:
        claims = validate_claims(claims_data, report)

    valid_claim_ids = {c.claim_id for c in claims}

    if evidence_data is not None:
        evidence = validate_evidence(evidence_data, report, valid_claim_ids)

    if hard_cases_data is not None:
        hard_cases = validate_hard_cases(hard_cases_data, report)

    print("--- Checks Passed ---")
    for ok_msg in report.passed_checks:
        print(f"  [PASS] {ok_msg}")

    if report.warnings:
        print("\n--- Warnings ---")
        for w in report.warnings:
            print(f"  [WARN] {w}")

    if report.errors:
        print("\n--- Errors ---")
        for e in report.errors:
            print(f"  [FAIL] {e}")

    if claims or evidence or hard_cases:
        print_summary(claims, evidence, hard_cases)

    print()
    if report.success:
        print("RESULT: PASS - dataset is structurally valid and ready for use.")
        return 0
    else:
        print(f"RESULT: FAIL - {len(report.errors)} error(s) found. Fix the issues above and re-run.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
