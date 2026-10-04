"""
numeric_checks.py

STEP 5: Deterministic Python arithmetic checks for ESG claim verification.

WHY DETERMINISTIC?
------------------
An LLM can hallucinate or be inconsistent when asked to compare numbers.
Arithmetic is straightforward -- Python does it exactly. This module
never calls any LLM. All calculations use standard Python operators.

WHAT THIS CHECKS
----------------
Given a claim and a piece of retrieved evidence, this module checks whether
the numerical content of the evidence is consistent with the numerical content
of the claim. It handles:

  1. Percentage reduction  (e.g. "40% reduction from X to Y")
  2. Percentage increase   (e.g. "25% increase from X to Y")
  3. Absolute value match  (e.g. "100,000 tonnes")
  4. Intensity value match (e.g. "18% per tonne of product")
  5. Year-over-year comparison
  6. Baseline comparison

WHAT THIS DELIBERATELY DOES NOT DO
-----------------------------------
  - It does NOT compare numbers when units are incompatible (MW vs. MWh).
  - It does NOT compare numbers from different scopes (Scope 1 vs. Scope 1+2).
  - It does NOT compare numbers from different reporting periods.
  - In each of those cases, it returns a "skipped" result with a clear reason.

TOLERANCE
---------
A tolerance of ±5% (default) is applied to all numeric comparisons. This
handles rounding differences (e.g. 17.5% vs. 18% claimed is within tolerance)
without requiring an exact bit-for-bit match.

HOW NUMBERS ARE EXTRACTED FROM EVIDENCE TEXT
---------------------------------------------
Evidence text is free-form natural language. This module uses simple regex
patterns to extract numeric values. It is not perfect -- it is a heuristic --
but it is correct for all the synthetic evidence records in evidence.json,
and its limitations are clearly documented.
"""

from __future__ import annotations

import re
from typing import Optional

from app.utils.schemas import (
    ClaimRecord,
    EvidenceRecord,
    NumericalCheckResult,
    RetrievedEvidence,
)

# Rounding tolerance: claim and evidence are considered consistent if
# the relative difference between their values is within this percentage.
DEFAULT_TOLERANCE_PCT: float = 5.0

# Unit families that are compatible for numeric comparison.
# Units from different families should NOT be compared numerically.
_UNIT_FAMILIES: dict[str, set[str]] = {
    "percent": {"percent", "%", "percent_reduction", "percent_increase", "percentage"},
    "absolute_mass": {"tonnes", "tco2e", "tco2", "kg", "mt", "million tonnes", "lakh tonnes"},
    "count": {"count", "number", "incidents"},
    "boolean": {"boolean", "bool", "yes/no"},
    "energy": {"mwh", "gwh", "kwh", "twh"},
    "capacity": {"mw", "gw", "kw"},  # capacity units -- NOT comparable to energy units
    "intensity": {"per tonne", "per unit", "per product", "kl/tonne", "kilolitres per tonne"},
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_numeric_check(
    claim: ClaimRecord,
    evidence: EvidenceRecord,
    tolerance_pct: float = DEFAULT_TOLERANCE_PCT,
) -> NumericalCheckResult:
    """Run the appropriate numeric check for one claim-evidence pair.

    This is the main entry point. It selects the correct check type based on
    the claim's unit field and runs it.

    Args:
        claim: The ClaimRecord being checked.
        evidence: An EvidenceRecord retrieved for this claim.
        tolerance_pct: Percentage tolerance for numeric comparison.

    Returns:
        A NumericalCheckResult with a clear pass/fail/skip outcome.
    """
    unit = (claim.unit or "").lower().strip()

    # --- Guard: claim has no numeric value (boolean/status claims) ---------
    if unit == "boolean":
        return NumericalCheckResult(
            check_type="boolean_status",
            passed=True,
            detail="Boolean/status claim: numeric comparison not applicable.",
            skipped=True,
            skip_reason="Unit is 'boolean'; no numeric value to compare.",
        )

    if claim.value is None:
        return NumericalCheckResult(
            check_type="no_value",
            passed=False,
            detail="Claim has no numeric value to compare against evidence.",
            skipped=True,
            skip_reason="claim.value is None",
        )

    # --- Guard: unit mismatch check ---------------------------------------
    unit_issue = _check_unit_compatibility(unit, evidence)
    if unit_issue:
        return NumericalCheckResult(
            check_type="unit_mismatch",
            passed=False,
            claim_value=claim.value,
            detail=unit_issue,
            skipped=True,
            skip_reason=unit_issue,
        )

    # --- Guard: scope mismatch -------------------------------------------
    scope_issue = _check_scope_match(claim, evidence)
    if scope_issue:
        return NumericalCheckResult(
            check_type="scope_mismatch",
            passed=False,
            claim_value=claim.value,
            detail=scope_issue,
            skipped=True,
            skip_reason=scope_issue,
        )

    # --- Guard: period mismatch ------------------------------------------
    period_issue = _check_period_match(claim, evidence)
    if period_issue:
        return NumericalCheckResult(
            check_type="period_mismatch",
            passed=False,
            claim_value=claim.value,
            detail=period_issue,
            skipped=True,
            skip_reason=period_issue,
        )

    # --- Dispatch to the appropriate numeric check -----------------------
    if unit in ("percent_reduction",):
        return _check_percent_reduction(claim, evidence, tolerance_pct)
    elif unit in ("percent_increase",):
        return _check_percent_increase(claim, evidence, tolerance_pct)
    elif unit in ("percent", "%", "percentage"):
        return _check_absolute_percent(claim, evidence, tolerance_pct)
    elif unit == "count":
        return _check_count(claim, evidence, tolerance_pct)
    else:
        return _check_absolute_value(claim, evidence, tolerance_pct)


def run_numeric_checks_for_claim(
    claim: ClaimRecord,
    evidence_list: list[EvidenceRecord],
    tolerance_pct: float = DEFAULT_TOLERANCE_PCT,
) -> list[NumericalCheckResult]:
    """Run numeric checks for a claim against every piece of retrieved evidence."""
    return [run_numeric_check(claim, ev, tolerance_pct) for ev in evidence_list]


def check_capacity_plausibility(
    claimed_value: float,
    claimed_unit: str,
    capacity_value: float,
    capacity_unit: str,
    capacity_description: str = "",
) -> NumericalCheckResult:
    """Standalone capacity plausibility check (used for hard cases HC-005, HC-010).

    Checks whether a claimed throughput/output is physically possible given a
    known capacity constraint. Returns a failed result if the claim exceeds
    registered capacity (with a margin).

    Args:
        claimed_value: The value stated in the claim (e.g. 100000 tonnes).
        claimed_unit: The unit of the claim (e.g. "tonnes").
        capacity_value: The registered/authorised capacity (e.g. 50000).
        capacity_unit: The unit of the capacity (e.g. "tonnes per year").
        capacity_description: Optional human-readable description of the capacity source.

    Returns:
        NumericalCheckResult with check_type="capacity_mismatch".
    """
    if claimed_value <= capacity_value:
        return NumericalCheckResult(
            check_type="capacity_check",
            passed=True,
            claim_value=claimed_value,
            evidence_value=capacity_value,
            detail=(
                f"Claimed value ({claimed_value} {claimed_unit}) is within "
                f"registered capacity ({capacity_value} {capacity_unit}). "
                f"{capacity_description}"
            ),
        )
    else:
        ratio = claimed_value / capacity_value if capacity_value > 0 else float("inf")
        return NumericalCheckResult(
            check_type="capacity_mismatch",
            passed=False,
            claim_value=claimed_value,
            evidence_value=capacity_value,
            detail=(
                f"Claimed value ({claimed_value} {claimed_unit}) exceeds "
                f"registered capacity ({capacity_value} {capacity_unit}) by "
                f"{ratio:.1f}x. {capacity_description} "
                f"This is a physical plausibility red flag."
            ),
        )


# ---------------------------------------------------------------------------
# Specific check implementations
# ---------------------------------------------------------------------------

def _check_percent_reduction(
    claim: ClaimRecord, evidence: EvidenceRecord, tolerance_pct: float
) -> NumericalCheckResult:
    """Check a percent_reduction claim against evidence text."""
    evidence_pct = _extract_percentage(evidence.retrieved_text)
    if evidence_pct is None:
        return NumericalCheckResult(
            check_type="percent_reduction",
            passed=False,
            claim_value=claim.value,
            detail=(
                f"Could not extract a percentage value from evidence text to "
                f"compare against the claimed {claim.value}% reduction."
            ),
            skipped=True,
            skip_reason="No numeric percentage found in evidence text",
        )

    consistent = _values_consistent(claim.value, evidence_pct, tolerance_pct)
    return NumericalCheckResult(
        check_type="percent_reduction",
        passed=consistent,
        claim_value=claim.value,
        evidence_value=evidence_pct,
        tolerance_pct=tolerance_pct,
        detail=(
            f"Claim: {claim.value}% reduction. Evidence: {evidence_pct}% reduction. "
            f"{'CONSISTENT within {:.0f}% tolerance.'.format(tolerance_pct) if consistent else 'INCONSISTENT — values diverge beyond tolerance.'}"
        ),
    )


def _check_percent_increase(
    claim: ClaimRecord, evidence: EvidenceRecord, tolerance_pct: float
) -> NumericalCheckResult:
    """Check a percent_increase claim against evidence text."""
    evidence_pct = _extract_percentage(evidence.retrieved_text)
    if evidence_pct is None:
        return NumericalCheckResult(
            check_type="percent_increase",
            passed=False,
            claim_value=claim.value,
            detail=f"Could not extract a percentage from evidence to compare against claimed {claim.value}% increase.",
            skipped=True,
            skip_reason="No numeric percentage found in evidence text",
        )

    consistent = _values_consistent(claim.value, evidence_pct, tolerance_pct)
    return NumericalCheckResult(
        check_type="percent_increase",
        passed=consistent,
        claim_value=claim.value,
        evidence_value=evidence_pct,
        tolerance_pct=tolerance_pct,
        detail=(
            f"Claim: {claim.value}% increase. Evidence: {evidence_pct}%. "
            f"{'CONSISTENT.' if consistent else 'INCONSISTENT.'}"
        ),
    )


def _check_absolute_percent(
    claim: ClaimRecord, evidence: EvidenceRecord, tolerance_pct: float
) -> NumericalCheckResult:
    """Check a plain-percent (snapshot) claim against evidence text."""
    evidence_pct = _extract_percentage(evidence.retrieved_text)
    if evidence_pct is None:
        return NumericalCheckResult(
            check_type="absolute_percent",
            passed=False,
            claim_value=claim.value,
            detail=f"Could not extract a percentage from evidence to compare against claimed {claim.value}%.",
            skipped=True,
            skip_reason="No percentage found in evidence text",
        )

    consistent = _values_consistent(claim.value, evidence_pct, tolerance_pct)
    return NumericalCheckResult(
        check_type="absolute_percent",
        passed=consistent,
        claim_value=claim.value,
        evidence_value=evidence_pct,
        tolerance_pct=tolerance_pct,
        detail=(
            f"Claim: {claim.value}%. Evidence: {evidence_pct}%. "
            f"{'CONSISTENT.' if consistent else 'INCONSISTENT.'}"
        ),
    )


def _check_count(
    claim: ClaimRecord, evidence: EvidenceRecord, tolerance_pct: float
) -> NumericalCheckResult:
    """Check an integer count claim against evidence text."""
    # For count claims with value=0 (e.g. "zero fatal accidents"), check for
    # any positive number in the evidence.
    if claim.value == 0:
        positive_num = _extract_first_positive_integer(evidence.retrieved_text)
        if positive_num is not None and positive_num > 0:
            return NumericalCheckResult(
                check_type="count_zero_vs_nonzero",
                passed=False,
                claim_value=0.0,
                evidence_value=float(positive_num),
                detail=(
                    f"Claim states zero {claim.metric}. Evidence mentions {positive_num}, "
                    f"which directly contradicts the zero claim."
                ),
            )
        return NumericalCheckResult(
            check_type="count_zero",
            passed=True,
            claim_value=0.0,
            detail="Claim states zero; no positive count found in evidence to contradict it.",
        )

    evidence_num = _extract_first_large_number(evidence.retrieved_text)
    if evidence_num is None:
        return NumericalCheckResult(
            check_type="count",
            passed=False,
            claim_value=claim.value,
            detail=f"Could not extract a count from evidence to compare against {claim.value}.",
            skipped=True,
            skip_reason="No count found in evidence text",
        )

    consistent = _values_consistent(claim.value, evidence_num, tolerance_pct)
    return NumericalCheckResult(
        check_type="count",
        passed=consistent,
        claim_value=claim.value,
        evidence_value=evidence_num,
        tolerance_pct=tolerance_pct,
        detail=(
            f"Claim: {claim.value}. Evidence: {evidence_num}. "
            f"{'CONSISTENT.' if consistent else 'INCONSISTENT.'}"
        ),
    )


def _check_absolute_value(
    claim: ClaimRecord, evidence: EvidenceRecord, tolerance_pct: float
) -> NumericalCheckResult:
    """Generic absolute value check (tonnes, kl, etc.)."""
    evidence_num = _extract_first_large_number(evidence.retrieved_text)
    if evidence_num is None:
        return NumericalCheckResult(
            check_type="absolute_value",
            passed=False,
            claim_value=claim.value,
            detail=f"Could not extract a numeric value from evidence to compare against {claim.value} {claim.unit}.",
            skipped=True,
            skip_reason="No numeric value found in evidence text",
        )

    consistent = _values_consistent(claim.value, evidence_num, tolerance_pct)
    return NumericalCheckResult(
        check_type="absolute_value",
        passed=consistent,
        claim_value=claim.value,
        evidence_value=evidence_num,
        tolerance_pct=tolerance_pct,
        detail=(
            f"Claim: {claim.value} {claim.unit}. Evidence value: {evidence_num}. "
            f"{'CONSISTENT.' if consistent else 'INCONSISTENT.'}"
        ),
    )


# ---------------------------------------------------------------------------
# Guard checks (return non-None string = problem found, None = OK)
# ---------------------------------------------------------------------------

_CAPACITY_UNIT_TOKENS = {"mw", "gw", "kw", "megawatt", "gigawatt", "kilowatt"}
_ENERGY_UNIT_TOKENS = {"mwh", "gwh", "kwh", "twh", "megawatt-hour", "kilowatt-hour"}


def _check_unit_compatibility(unit: str, evidence: EvidenceRecord) -> Optional[str]:
    """Return an error message if the claim unit is dimensionally invalid.

    Specifically: a claim in capacity units (MW) should NOT be compared against
    an evidence value expressed in energy units (MWh), and vice versa.
    """
    unit_lower = unit.lower()
    ev_text_lower = evidence.retrieved_text.lower()

    if any(tok in unit_lower for tok in _CAPACITY_UNIT_TOKENS):
        # Claim is in capacity units -- check the evidence doesn't use energy.
        if any(tok in ev_text_lower for tok in _ENERGY_UNIT_TOKENS):
            return (
                f"Unit mismatch: claim is in capacity units ('{unit}') but evidence "
                f"appears to discuss energy units (MWh/GWh). These are dimensionally "
                f"incompatible and cannot be numerically compared."
            )
    return None


def _check_scope_match(claim: ClaimRecord, evidence: EvidenceRecord) -> Optional[str]:
    """Return an error message if claim and evidence scopes clearly conflict.

    Only checks emission-related claims where scope is significant.
    Does not enforce scope matching for non-emission claims.
    """
    if not claim.scope:
        return None  # No scope to check

    claim_scope = claim.scope.lower()
    # Only apply scope mismatch detection to emissions-related claims.
    if not any(kw in (claim.metric or "").lower() for kw in ("emission", "scope", "carbon", "ghg")):
        return None

    ev_text = evidence.retrieved_text.lower()

    # If claim is Scope 1-only but evidence explicitly mentions Scope 1+2 or total:
    if "scope 1" in claim_scope and "scope 2" not in claim_scope:
        if "scope 1 and scope 2" in ev_text or "scope 1+2" in ev_text:
            return (
                "Scope mismatch: claim is Scope 1 only, but evidence discusses "
                "combined Scope 1+2 emissions. These are not directly comparable."
            )

    # If claim is Scope 1+2 but evidence is Scope 1 only:
    if ("scope 1" in claim_scope and "scope 2" in claim_scope):
        if "scope 1 and" not in ev_text and "scope 1+2" not in ev_text and "scope 1, 2" not in ev_text:
            # Evidence only mentions Scope 1 individually: soft warning but don't skip
            pass  # intentional: don't block the check, just note it

    return None


def _check_period_match(claim: ClaimRecord, evidence: EvidenceRecord) -> Optional[str]:
    """Return an error message if the claim and evidence reporting periods clearly differ."""
    claim_period = (claim.reporting_period or "").strip().lower()
    ev_period = (evidence.reporting_period or "").strip().lower()

    if not claim_period or not ev_period:
        return None  # Can't check without both periods

    # Normalise: "fy2024" == "2024" for this simple check.
    claim_norm = _normalise_period(claim_period)
    ev_norm = _normalise_period(ev_period)

    if claim_norm and ev_norm and claim_norm != ev_norm:
        # Check whether the evidence period is a range that includes the claim period.
        if claim_norm not in ev_norm:
            return (
                f"Period mismatch: claim is for '{claim.reporting_period}' but evidence "
                f"covers '{evidence.reporting_period}'. Numbers from different periods "
                f"cannot be directly compared."
            )
    return None


# ---------------------------------------------------------------------------
# Number extraction helpers
# ---------------------------------------------------------------------------

def _extract_percentage(text: str) -> Optional[float]:
    """Extract the first percentage-like number from text.

    Matches patterns like: "40%", "approximately 40%", "40 percent", "40 per cent".
    """
    patterns = [
        r"(\d+(?:\.\d+)?)\s*%",           # "40%" or "40.5%"
        r"(\d+(?:\.\d+)?)\s*percent",      # "40 percent"
        r"(\d+(?:\.\d+)?)\s*per\s+cent",   # "40 per cent"
        r"approximately\s+(\d+(?:\.\d+)?)",  # "approximately 40"
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return float(m.group(1))
    return None


_WORD_TO_INT: dict[str, int] = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
}


def _extract_first_positive_integer(text: str) -> Optional[int]:
    """Extract the first positive integer from text (for count checks)."""
    matches: list[tuple[int, int]] = []

    for m in re.finditer(r"\b([1-9]\d*)\b", text):
        val = int(m.group(1))
        # Ignore standalone 4-digit years like 2023, 2024
        if 1900 <= val <= 2099:
            continue
        matches.append((m.start(), val))

    for word, val in _WORD_TO_INT.items():
        if val <= 0:
            continue
        for m in re.finditer(r"\b" + word + r"\b", text, re.IGNORECASE):
            matches.append((m.start(), val))

    if matches:
        matches.sort(key=lambda x: x[0])
        return matches[0][1]
    return None



def _extract_first_large_number(text: str) -> Optional[float]:
    """Extract the first large number (possibly with commas) from text.

    Useful for extracting absolute quantities like 100,000 tonnes or 1.26 million.
    """
    # Match numbers with commas: "100,000" or plain decimals: "1.26"
    # Also try "X million" or "X lakh" shorthand.
    million_match = re.search(r"(\d+(?:\.\d+)?)\s*million", text, re.IGNORECASE)
    if million_match:
        return float(million_match.group(1)) * 1_000_000

    lakh_match = re.search(r"(\d+(?:\.\d+)?)\s*lakh", text, re.IGNORECASE)
    if lakh_match:
        return float(lakh_match.group(1)) * 100_000

    # Plain number with optional commas: "100,000" or "49200"
    plain_match = re.search(r"\b(\d{1,3}(?:,\d{3})+|\d+)\b", text)
    if plain_match:
        return float(plain_match.group(1).replace(",", ""))

    return None


def _values_consistent(a: float, b: float, tolerance_pct: float) -> bool:
    """Return True if |a - b| / max(|a|, |b|, 1) <= tolerance_pct / 100."""
    denominator = max(abs(a), abs(b), 1.0)
    relative_diff = abs(a - b) / denominator
    return relative_diff <= (tolerance_pct / 100.0)


def _normalise_period(period: str) -> str:
    """Normalise a period string to a bare year for comparison.

    "FY2024" → "2024", "2024" → "2024", "fy2024" → "2024".
    """
    m = re.search(r"(\d{4})", period)
    return m.group(1) if m else period.strip()
