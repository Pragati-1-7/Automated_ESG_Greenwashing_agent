"""
risk_score.py

STEP 5: Explainable 0-100 Greenwashing Risk Score.

PURPOSE
-------
This module translates the structured outputs of the verification engine
into a single, easy-to-understand risk score that helps human reviewers
quickly prioritise which claims need the most attention.

IMPORTANT DISCLAIMER
---------------------
The Greenwashing Risk Score is a TRIAGE INDICATOR. It is:
  - Produced by a deterministic, rule-based algorithm (no LLM, no randomness).
  - Intended to SUPPORT human review, not replace it.
  - NOT a legal verdict, regulatory finding, or professional opinion.
  - NOT proof of greenwashing.

SCORE INTERPRETATION (advisory only)
--------------------------------------
    0 – 29   Low risk      Evidence broadly supports the claim.
   30 – 59   Moderate risk Some concerns; human review recommended.
   60 – 79   High risk     Significant concerns identified.
   80 – 100  Very high risk Strong contradictions or data quality issues.

HOW THE SCORE IS COMPUTED
--------------------------
The score is a simple weighted sum of risk factors, clamped to [0, 100].

    score = Σ(factor_points)  where each factor contributes [0, max_points].

Factor table (total possible = 100 points):
─────────────────────────────────────────────────────────────────────────────
 Factor                     Max pts  Trigger condition
─────────────────────────────────────────────────────────────────────────────
 verdict_contradict           40     Verdict is CONTRADICT
 verdict_insufficient         15     Verdict is INSUFFICIENT_EVIDENCE
 verdict_align                 0     Verdict is ALIGN (no risk from verdict)
 high_auth_contradiction       20     High-authority (Tier 1/2) source CONTRADICTS
 numeric_inconsistency         15     One or more numeric checks failed
 unit_mismatch                 10     Unit mismatch flagged in numeric checks
 period_mismatch               10     Period mismatch flagged
 scope_mismatch                10     Scope mismatch flagged
 no_high_authority_support      8     ALIGN verdict but only from low-tier sources
 all_evidence_low_tier          5     All evidence is Tier 4 or 5 (PR/news)
─────────────────────────────────────────────────────────────────────────────
NOTE: Not all factors apply simultaneously; the total is clamped to 100.

WHY THIS DESIGN?
-----------------
- Simple enough that a faculty member or EY reviewer can re-derive the score
  manually given the audit trail.
- Deterministic: same inputs → same score, always.
- Explainable: every point is traced to a named factor with a reason.
- Calibrated: a CONTRADICT from a Tier 1 source should produce a noticeably
  higher score than a minor numeric inconsistency from a Tier 5 source.
"""

from __future__ import annotations

from app.utils.schemas import (
    RiskScoreFactor,
    RiskScoreResult,
    SourceTier,
    Verdict,
    VerificationResult,
)

# Factor max-point weights (all documented in the module docstring above).
_FACTOR_WEIGHTS: dict[str, float] = {
    "verdict_contradict":         40.0,
    "verdict_insufficient":       15.0,
    "high_auth_contradiction":    20.0,
    "numeric_inconsistency":      15.0,
    "unit_mismatch":              10.0,
    "period_mismatch":            10.0,
    "scope_mismatch":             10.0,
    "no_high_authority_support":   8.0,
    "all_evidence_low_tier":       5.0,
}

_HIGH_AUTHORITY_TIERS = {
    SourceTier.TIER_1_REGULATORY_FILING,
    SourceTier.TIER_2_REGULATOR_OR_TRIBUNAL,
}

_LOW_AUTHORITY_TIERS = {
    SourceTier.TIER_4_COMPANY_PR,
    SourceTier.TIER_5_NEWS,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def calculate_risk_score(verification: VerificationResult) -> RiskScoreResult:
    """Calculate the Greenwashing Risk Score for one verified claim.

    Args:
        verification: The VerificationResult produced by the verification engine.

    Returns:
        A RiskScoreResult with the score, band, factor breakdown, and summary.
    """
    factors: list[RiskScoreFactor] = []

    # --- Factor 1: Verdict ---------------------------------------------------
    if verification.verdict == Verdict.CONTRADICT:
        factors.append(RiskScoreFactor(
            factor="verdict_contradict",
            points=_FACTOR_WEIGHTS["verdict_contradict"],
            max_points=_FACTOR_WEIGHTS["verdict_contradict"],
            reason=(
                f"Verification verdict is CONTRADICT. Evidence directly conflicts "
                f"with the claim. Contradicting evidence IDs: "
                f"{', '.join(verification.contradicting_evidence_ids) or 'none listed'}."
            ),
        ))
    elif verification.verdict == Verdict.INSUFFICIENT_EVIDENCE:
        factors.append(RiskScoreFactor(
            factor="verdict_insufficient",
            points=_FACTOR_WEIGHTS["verdict_insufficient"],
            max_points=_FACTOR_WEIGHTS["verdict_insufficient"],
            reason=(
                "Verification verdict is INSUFFICIENT_EVIDENCE. The claim cannot "
                "be confirmed or contradicted with available evidence."
            ),
        ))
    # ALIGN: no risk points from verdict.

    # --- Factor 2: High-authority contradiction --------------------------------
    if verification.contradicting_evidence_ids and verification.highest_authority_tier is not None:
        if verification.highest_authority_tier <= 2:
            factors.append(RiskScoreFactor(
                factor="high_auth_contradiction",
                points=_FACTOR_WEIGHTS["high_auth_contradiction"],
                max_points=_FACTOR_WEIGHTS["high_auth_contradiction"],
                reason=(
                    f"The most authoritative evidence available (Tier "
                    f"{verification.highest_authority_tier}) contradicts the claim. "
                    f"High-authority sources (regulatory filings, regulator records) "
                    f"are the most reliable and carry extra weight in the risk score."
                ),
            ))

    # --- Factor 3: Numeric inconsistency -------------------------------------
    failed_numeric = [nc for nc in verification.numerical_checks if not nc.passed and not nc.skipped]
    if failed_numeric:
        factors.append(RiskScoreFactor(
            factor="numeric_inconsistency",
            points=_FACTOR_WEIGHTS["numeric_inconsistency"],
            max_points=_FACTOR_WEIGHTS["numeric_inconsistency"],
            reason=(
                f"{len(failed_numeric)} numeric check(s) failed: "
                + "; ".join(nc.detail[:80] for nc in failed_numeric[:2])
                + ("..." if len(failed_numeric) > 2 else "")
            ),
        ))

    # --- Factor 4: Unit mismatch ----------------------------------------------
    unit_mismatch_checks = [nc for nc in verification.numerical_checks if nc.check_type == "unit_mismatch"]
    if unit_mismatch_checks:
        factors.append(RiskScoreFactor(
            factor="unit_mismatch",
            points=_FACTOR_WEIGHTS["unit_mismatch"],
            max_points=_FACTOR_WEIGHTS["unit_mismatch"],
            reason=(
                "A unit mismatch was detected: the claim's unit is dimensionally "
                "incompatible with units found in the evidence. This may indicate "
                "incorrect or misleading reporting (e.g. MW stated instead of MWh)."
            ),
        ))

    # --- Factor 5: Period mismatch --------------------------------------------
    period_mismatch_checks = [nc for nc in verification.numerical_checks if nc.check_type == "period_mismatch"]
    if period_mismatch_checks:
        factors.append(RiskScoreFactor(
            factor="period_mismatch",
            points=_FACTOR_WEIGHTS["period_mismatch"],
            max_points=_FACTOR_WEIGHTS["period_mismatch"],
            reason=(
                "A reporting period mismatch was detected between the claim and "
                "the evidence. Numbers from different periods cannot be directly "
                "compared and may indicate cherry-picking of comparison years."
            ),
        ))

    # --- Factor 6: Scope mismatch ---------------------------------------------
    scope_mismatch_checks = [nc for nc in verification.numerical_checks if nc.check_type == "scope_mismatch"]
    if scope_mismatch_checks:
        factors.append(RiskScoreFactor(
            factor="scope_mismatch",
            points=_FACTOR_WEIGHTS["scope_mismatch"],
            max_points=_FACTOR_WEIGHTS["scope_mismatch"],
            reason=(
                "A scope mismatch was detected (e.g. claim states Scope 1 only "
                "but evidence covers a different scope boundary). Mixing scopes "
                "without disclosure is a common form of selective reporting."
            ),
        ))

    # --- Factor 7: ALIGN but only from low-authority sources ------------------
    if verification.verdict == Verdict.ALIGN:
        if verification.highest_authority_tier is not None and verification.highest_authority_tier >= 4:
            factors.append(RiskScoreFactor(
                factor="no_high_authority_support",
                points=_FACTOR_WEIGHTS["no_high_authority_support"],
                max_points=_FACTOR_WEIGHTS["no_high_authority_support"],
                reason=(
                    f"The claim appears to ALIGN, but the most authoritative supporting "
                    f"evidence is only Tier {verification.highest_authority_tier} "
                    f"(PR/news). No regulatory filing or audited report was found to "
                    f"corroborate the claim. Moderate risk due to lack of independent verification."
                ),
            ))

    # --- Factor 8: All evidence is low-tier -----------------------------------
    if verification.highest_authority_tier is not None and verification.highest_authority_tier >= 4:
        if verification.verdict != Verdict.ALIGN:  # Already covered by factor 7 for ALIGN.
            factors.append(RiskScoreFactor(
                factor="all_evidence_low_tier",
                points=_FACTOR_WEIGHTS["all_evidence_low_tier"],
                max_points=_FACTOR_WEIGHTS["all_evidence_low_tier"],
                reason=(
                    f"All retrieved evidence is low-authority (Tier "
                    f"{verification.highest_authority_tier}: PR/news). "
                    f"No independent, regulatory, or audited source was found."
                ),
            ))

    # --- Compute final score --------------------------------------------------
    raw_score = sum(f.points for f in factors)
    clamped_score = max(0.0, min(100.0, raw_score))
    band = _score_to_band(clamped_score)

    summary = _build_summary(verification, clamped_score, band, factors)

    return RiskScoreResult(
        claim_id=verification.claim_id,
        risk_score=round(clamped_score, 1),
        risk_band=band,
        factors=factors,
        summary=summary,
    )


def calculate_risk_scores(
    verification_results: list[VerificationResult],
) -> list[RiskScoreResult]:
    """Calculate risk scores for a list of verification results."""
    return [calculate_risk_score(vr) for vr in verification_results]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _score_to_band(score: float) -> str:
    if score < 30:
        return "Low"
    elif score < 60:
        return "Moderate"
    elif score < 80:
        return "High"
    else:
        return "Very High"


def _build_summary(
    verification: VerificationResult,
    score: float,
    band: str,
    factors: list[RiskScoreFactor],
) -> str:
    if not factors:
        return (
            f"Greenwashing Risk Score: {score:.0f}/100 ({band}). "
            f"The verification result is {verification.verdict.value} with no significant "
            f"risk factors identified. The claim appears to be well-supported by evidence."
        )

    top_factors = sorted(factors, key=lambda f: f.points, reverse=True)[:3]
    factor_summary = "; ".join(f.factor.replace("_", " ") for f in top_factors)
    return (
        f"Greenwashing Risk Score: {score:.0f}/100 ({band} risk). "
        f"Verdict: {verification.verdict.value}. "
        f"Key contributing factors: {factor_summary}. "
        f"This score is a triage indicator for human review — it is not a legal verdict."
    )
