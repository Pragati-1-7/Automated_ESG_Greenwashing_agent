"""
test_risk_score.py

STEP 5 tests: Greenwashing Risk Score.

Tests cover:
  - Score range 0-100
  - Score determinism (same input → same output)
  - Factor breakdown present and explainable
  - ALIGN produces lower score than CONTRADICT
  - CONTRADICT from Tier 1 produces high score
  - INSUFFICIENT_EVIDENCE produces moderate score
  - Risk band labels correct
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.utils.schemas import (
    NumericalCheckResult,
    RiskScoreResult,
    SourceTier,
    Verdict,
    VerificationResult,
)
from app.scoring.risk_score import calculate_risk_score, _score_to_band


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_verification(
    verdict: Verdict,
    highest_tier: int = 3,
    contradicting_ids: list[str] | None = None,
    supporting_ids: list[str] | None = None,
    numeric_checks: list[NumericalCheckResult] | None = None,
) -> VerificationResult:
    return VerificationResult(
        claim_id="CLM-TEST",
        verdict=verdict,
        reason="Test reason.",
        supporting_evidence_ids=supporting_ids or [],
        contradicting_evidence_ids=contradicting_ids or [],
        insufficient_evidence_ids=[],
        numerical_checks=numeric_checks or [],
        highest_authority_tier=highest_tier,
    )


# ---------------------------------------------------------------------------
# 17. Risk score range 0-100
# ---------------------------------------------------------------------------

class TestRiskScoreRange:

    def test_align_score_in_range(self):
        vr = _make_verification(Verdict.ALIGN, supporting_ids=["EVD-001"])
        result = calculate_risk_score(vr)
        assert 0 <= result.risk_score <= 100

    def test_contradict_score_in_range(self):
        vr = _make_verification(Verdict.CONTRADICT, contradicting_ids=["EVD-001"])
        result = calculate_risk_score(vr)
        assert 0 <= result.risk_score <= 100

    def test_insufficient_score_in_range(self):
        vr = _make_verification(Verdict.INSUFFICIENT_EVIDENCE)
        result = calculate_risk_score(vr)
        assert 0 <= result.risk_score <= 100

    def test_score_never_below_zero(self):
        """Edge case: ALIGN with high-authority support should be >= 0."""
        vr = _make_verification(Verdict.ALIGN, highest_tier=1, supporting_ids=["EVD-X"])
        result = calculate_risk_score(vr)
        assert result.risk_score >= 0

    def test_score_never_above_100(self):
        """Edge case: worst possible input should be clamped at 100."""
        nc_fail = NumericalCheckResult(
            check_type="unit_mismatch",
            passed=False,
            detail="Unit mismatch.",
            skipped=True,
            skip_reason="Unit mismatch",
        )
        vr = _make_verification(
            Verdict.CONTRADICT,
            highest_tier=1,
            contradicting_ids=["EVD-A", "EVD-B"],
            numeric_checks=[nc_fail],
        )
        result = calculate_risk_score(vr)
        assert result.risk_score <= 100


# ---------------------------------------------------------------------------
# 18. Risk score determinism
# ---------------------------------------------------------------------------

class TestRiskScoreDeterminism:

    def test_same_input_same_score(self):
        vr = _make_verification(Verdict.CONTRADICT, contradicting_ids=["EVD-001"])
        score1 = calculate_risk_score(vr).risk_score
        score2 = calculate_risk_score(vr).risk_score
        assert score1 == score2

    def test_different_verdicts_produce_different_scores(self):
        vr_align = _make_verification(Verdict.ALIGN, supporting_ids=["EVD-X"])
        vr_contradict = _make_verification(Verdict.CONTRADICT, contradicting_ids=["EVD-X"])
        score_align = calculate_risk_score(vr_align).risk_score
        score_contradict = calculate_risk_score(vr_contradict).risk_score
        assert score_contradict > score_align

    def test_tier1_contradiction_higher_score_than_tier5(self):
        vr_tier1 = _make_verification(Verdict.CONTRADICT, highest_tier=1, contradicting_ids=["EVD-A"])
        vr_tier5 = _make_verification(Verdict.CONTRADICT, highest_tier=5, contradicting_ids=["EVD-A"])
        score_tier1 = calculate_risk_score(vr_tier1).risk_score
        score_tier5 = calculate_risk_score(vr_tier5).risk_score
        assert score_tier1 > score_tier5


# ---------------------------------------------------------------------------
# Factor breakdown
# ---------------------------------------------------------------------------

class TestRiskScoreFactors:

    def test_contradict_verdict_factor_present(self):
        vr = _make_verification(Verdict.CONTRADICT, contradicting_ids=["EVD-001"])
        result = calculate_risk_score(vr)
        factor_names = [f.factor for f in result.factors]
        assert "verdict_contradict" in factor_names

    def test_insufficient_evidence_factor_present(self):
        vr = _make_verification(Verdict.INSUFFICIENT_EVIDENCE)
        result = calculate_risk_score(vr)
        factor_names = [f.factor for f in result.factors]
        assert "verdict_insufficient" in factor_names

    def test_high_auth_contradiction_factor_present_for_tier1(self):
        vr = _make_verification(
            Verdict.CONTRADICT, highest_tier=1, contradicting_ids=["EVD-001"]
        )
        result = calculate_risk_score(vr)
        factor_names = [f.factor for f in result.factors]
        assert "high_auth_contradiction" in factor_names

    def test_align_from_low_tier_triggers_factor(self):
        vr = _make_verification(Verdict.ALIGN, highest_tier=4, supporting_ids=["EVD-X"])
        result = calculate_risk_score(vr)
        factor_names = [f.factor for f in result.factors]
        assert "no_high_authority_support" in factor_names

    def test_numeric_inconsistency_factor_present_on_failed_check(self):
        nc = NumericalCheckResult(
            check_type="percent_reduction",
            passed=False,
            claim_value=40,
            evidence_value=5,
            detail="Claim 40% vs evidence 5%.",
        )
        vr = _make_verification(Verdict.CONTRADICT, contradicting_ids=["EVD-A"], numeric_checks=[nc])
        result = calculate_risk_score(vr)
        factor_names = [f.factor for f in result.factors]
        assert "numeric_inconsistency" in factor_names

    def test_each_factor_has_reason(self):
        vr = _make_verification(Verdict.CONTRADICT, contradicting_ids=["EVD-001"])
        result = calculate_risk_score(vr)
        for f in result.factors:
            assert isinstance(f.reason, str) and len(f.reason) > 5

    def test_points_never_exceed_max_points(self):
        vr = _make_verification(Verdict.CONTRADICT, contradicting_ids=["EVD-001"])
        result = calculate_risk_score(vr)
        for f in result.factors:
            assert f.points <= f.max_points

    def test_disclaimer_present(self):
        vr = _make_verification(Verdict.ALIGN, supporting_ids=["EVD-X"])
        result = calculate_risk_score(vr)
        assert "triage indicator" in result.disclaimer.lower()


# ---------------------------------------------------------------------------
# Risk bands
# ---------------------------------------------------------------------------

class TestRiskBands:

    @pytest.mark.parametrize("score,expected_band", [
        (0, "Low"),
        (15, "Low"),
        (29.9, "Low"),
        (30, "Moderate"),
        (45, "Moderate"),
        (59.9, "Moderate"),
        (60, "High"),
        (70, "High"),
        (79.9, "High"),
        (80, "Very High"),
        (100, "Very High"),
    ])
    def test_band_boundaries(self, score, expected_band):
        assert _score_to_band(score) == expected_band

    def test_result_has_risk_band(self):
        vr = _make_verification(Verdict.ALIGN, supporting_ids=["EVD-X"])
        result = calculate_risk_score(vr)
        assert result.risk_band in ("Low", "Moderate", "High", "Very High")

    def test_contradict_from_tier1_is_very_high_risk(self):
        vr = _make_verification(
            Verdict.CONTRADICT, highest_tier=1, contradicting_ids=["EVD-A"]
        )
        result = calculate_risk_score(vr)
        assert result.risk_band in ("High", "Very High")

    def test_align_from_tier1_is_low_risk(self):
        vr = _make_verification(
            Verdict.ALIGN, highest_tier=1, supporting_ids=["EVD-A"]
        )
        result = calculate_risk_score(vr)
        assert result.risk_band == "Low"


# ---------------------------------------------------------------------------
# Summary / output completeness
# ---------------------------------------------------------------------------

class TestRiskScoreOutput:

    def test_summary_is_string(self):
        vr = _make_verification(Verdict.CONTRADICT, contradicting_ids=["EVD-001"])
        result = calculate_risk_score(vr)
        assert isinstance(result.summary, str) and len(result.summary) > 10

    def test_claim_id_preserved(self):
        vr = _make_verification(Verdict.ALIGN, supporting_ids=["EVD-X"])
        result = calculate_risk_score(vr)
        assert result.claim_id == "CLM-TEST"
