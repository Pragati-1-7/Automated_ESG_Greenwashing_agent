"""
test_numeric_checks.py

STEP 5 tests: deterministic numeric checks.

All tests are OFFLINE. No LLM, no network, no ChromaDB.
Covers: percentage reduction, percentage increase, absolute values,
        unit mismatch, period mismatch, scope mismatch, baseline mismatch,
        capacity mismatch, count/zero checks.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.utils.schemas import (
    Checkability,
    ClaimRecord,
    ClaimType,
    EvidenceRecord,
    ExpectedRelationship,
    SourceTier,
)
from app.evaluation.numeric_checks import (
    check_capacity_plausibility,
    run_numeric_check,
    run_numeric_checks_for_claim,
)


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _make_claim(**kwargs) -> ClaimRecord:
    defaults = dict(
        claim_id="CLM-TEST",
        company="TestCo",
        original_text="TestCo made a claim.",
        metric="carbon_emissions_scope1",
        value=40.0,
        unit="percent_reduction",
        scope="Scope 1",
        boundary="company-wide",
        baseline_year="FY2023",
        reporting_period="FY2024",
        claim_type=ClaimType.RESULT,
        checkability=Checkability.CHECKABLE,
        source_document="test.pdf",
    )
    defaults.update(kwargs)
    return ClaimRecord(**defaults)


def _make_evidence(retrieved_text: str, **kwargs) -> EvidenceRecord:
    defaults = dict(
        evidence_id="EVD-TEST",
        claim_id="CLM-TEST",
        company="TestCo",
        source="Test Source",
        source_tier=SourceTier.TIER_1_REGULATORY_FILING,
        source_type="regulatory_filing",
        publication_date="2024-06-01",
        reporting_period="FY2024",
        retrieved_text=retrieved_text,
        expected_relationship=ExpectedRelationship.SUPPORTS,
    )
    defaults.update(kwargs)
    return EvidenceRecord(**defaults)


# ---------------------------------------------------------------------------
# 7. Percentage reduction
# ---------------------------------------------------------------------------

class TestPercentReduction:

    def test_matching_percent_reduction_passes(self):
        claim = _make_claim(value=40, unit="percent_reduction")
        ev = _make_evidence("emissions declined by approximately 40%")
        result = run_numeric_check(claim, ev)
        assert result.passed is True
        assert result.check_type == "percent_reduction"

    def test_close_percent_reduction_within_tolerance_passes(self):
        """17.5% vs claimed 18% should be within 5% tolerance."""
        claim = _make_claim(value=18, unit="percent_reduction", metric="water_withdrawal_intensity")
        ev = _make_evidence("reduction of approximately 17.5%")
        result = run_numeric_check(claim, ev)
        assert result.passed is True

    def test_far_off_percent_reduction_fails(self):
        """25% reduction claimed but evidence shows an increase of 5%."""
        claim = _make_claim(value=25, unit="percent_reduction")
        ev = _make_evidence("emissions increased by approximately 5%")
        result = run_numeric_check(claim, ev)
        # 25 vs 5 → far apart → should fail
        assert result.passed is False

    def test_no_percent_in_evidence_skips(self):
        claim = _make_claim(value=40, unit="percent_reduction")
        ev = _make_evidence("The facility submitted its annual environmental return.")
        result = run_numeric_check(claim, ev)
        assert result.skipped is True

    def test_claim_and_evidence_values_recorded(self):
        claim = _make_claim(value=40, unit="percent_reduction")
        ev = _make_evidence("declined by 40%")
        result = run_numeric_check(claim, ev)
        assert result.claim_value == 40.0
        assert result.evidence_value == 40.0


# ---------------------------------------------------------------------------
# 8. Percentage increase
# ---------------------------------------------------------------------------

class TestPercentIncrease:

    def test_matching_percent_increase_passes(self):
        claim = _make_claim(value=25, unit="percent_increase", metric="women_in_senior_management_share")
        ev = _make_evidence("rose by 25 percent compared to the prior year")
        result = run_numeric_check(claim, ev)
        assert result.passed is True

    def test_mismatched_percent_increase_fails(self):
        claim = _make_claim(value=50, unit="percent_increase", metric="renewable_electricity_share")
        ev = _make_evidence("grew by 10%")
        result = run_numeric_check(claim, ev)
        assert result.passed is False


# ---------------------------------------------------------------------------
# 9. Unit mismatch
# ---------------------------------------------------------------------------

class TestUnitMismatch:

    def test_mw_vs_mwh_in_evidence_triggers_unit_mismatch(self):
        """HC-008: claim in MW (capacity) but evidence uses MWh (energy)."""
        claim = _make_claim(
            value=500,
            unit="MW",
            metric="renewable_energy_generation",
            scope="energy generation",
        )
        ev = _make_evidence(
            "Suryodaya generated 900 MWh of clean energy in FY2024.",
            claim_id="CLM-TEST",
        )
        result = run_numeric_check(claim, ev)
        assert result.skipped is True
        assert result.check_type == "unit_mismatch"

    def test_compatible_units_not_flagged_as_mismatch(self):
        claim = _make_claim(value=40, unit="percent_reduction")
        ev = _make_evidence("emissions fell by 40%")
        result = run_numeric_check(claim, ev)
        assert result.check_type != "unit_mismatch"


# ---------------------------------------------------------------------------
# 10. Period mismatch
# ---------------------------------------------------------------------------

class TestPeriodMismatch:

    def test_different_periods_trigger_skip(self):
        """HC-003: evidence covers FY2023 but claim is for FY2024."""
        claim = _make_claim(value=40, unit="percent_reduction", reporting_period="FY2024")
        ev = _make_evidence(
            "emissions fell by 40% in FY2023",
            reporting_period="FY2023",
        )
        result = run_numeric_check(claim, ev)
        assert result.skipped is True
        assert result.check_type == "period_mismatch"

    def test_matching_periods_not_flagged(self):
        claim = _make_claim(value=40, unit="percent_reduction", reporting_period="FY2024")
        ev = _make_evidence("declined by 40%", reporting_period="FY2024")
        result = run_numeric_check(claim, ev)
        assert result.check_type != "period_mismatch"


# ---------------------------------------------------------------------------
# 11. Scope mismatch
# ---------------------------------------------------------------------------

class TestScopeMismatch:

    def test_scope1_claim_vs_scope1_plus_2_evidence_flagged(self):
        """Claim states Scope 1 only; evidence clearly discusses Scope 1+2."""
        claim = _make_claim(
            value=40, unit="percent_reduction",
            metric="carbon_emissions_scope1",
            scope="Scope 1",
        )
        ev = _make_evidence(
            "Combined Scope 1 and Scope 2 emissions fell by 40% in FY2024."
        )
        result = run_numeric_check(claim, ev)
        # Scope mismatch detected → should be skipped or flagged
        assert result.skipped is True
        assert "scope" in result.check_type.lower()


# ---------------------------------------------------------------------------
# 12. Baseline mismatch (handled at verification level — numeric level skips
#     when period doesn't match)
# ---------------------------------------------------------------------------

class TestBaselineMismatch:

    def test_mismatched_baseline_period_skips_numeric(self):
        """HC-004: company restated baseline from FY2020 to FY2023.
        The numeric check sees a period mismatch and skips, which is correct:
        the baseline shift is a verification-stage concern, not a pure number check."""
        claim = _make_claim(
            value=30, unit="percent_reduction",
            baseline_year="FY2023", reporting_period="FY2024",
        )
        ev = _make_evidence(
            "emissions rose by 10% compared to FY2020 baseline.",
            reporting_period="FY2020",
        )
        result = run_numeric_check(claim, ev)
        # Either skipped (period mismatch) or failed (values inconsistent).
        assert result.skipped or not result.passed


# ---------------------------------------------------------------------------
# 13. Capacity mismatch
# ---------------------------------------------------------------------------

class TestCapacityMismatch:

    def test_claim_exceeds_capacity_fails(self):
        """HC-010: claimed 120,000 tonnes but capacity is 40,000 tonnes."""
        result = check_capacity_plausibility(
            claimed_value=120000,
            claimed_unit="tonnes",
            capacity_value=40000,
            capacity_unit="tonnes per year",
            capacity_description="Registered e-waste handling facility capacity.",
        )
        assert result.passed is False
        assert result.check_type == "capacity_mismatch"

    def test_claim_exceeds_capacity_50k_case(self):
        """HC-008 analog: EcoCycle claims 100,000 tonnes, capacity is 50,000."""
        result = check_capacity_plausibility(
            claimed_value=100000,
            claimed_unit="tonnes",
            capacity_value=50000,
            capacity_unit="tonnes per year",
        )
        assert result.passed is False

    def test_claim_within_capacity_passes(self):
        result = check_capacity_plausibility(
            claimed_value=30000,
            claimed_unit="tonnes",
            capacity_value=50000,
            capacity_unit="tonnes per year",
        )
        assert result.passed is True

    def test_capacity_check_stores_claim_and_evidence_values(self):
        result = check_capacity_plausibility(120000, "tonnes", 40000, "tonnes/year")
        assert result.claim_value == 120000.0
        assert result.evidence_value == 40000.0


# ---------------------------------------------------------------------------
# Boolean / count claims
# ---------------------------------------------------------------------------

class TestCountAndBoolean:

    def test_boolean_claim_skips_numeric(self):
        claim = _make_claim(value=None, unit="boolean", metric="brsr_disclosure_compliance")
        ev = _make_evidence("BRSR report filed on 31 May 2024.")
        result = run_numeric_check(claim, ev)
        assert result.skipped is True
        assert result.check_type == "boolean_status"

    def test_zero_count_contradicted_by_positive_number(self):
        """CLM-009: claims zero fatal accidents; evidence mentions two."""
        claim = _make_claim(
            value=0, unit="count",
            metric="fatal_workplace_accidents",
            scope="worker safety",
        )
        ev = _make_evidence(
            "The factory inspectorate recorded two fatal workplace accidents at Bharat Steelworks."
        )
        result = run_numeric_check(claim, ev)
        assert result.passed is False

    def test_zero_count_passes_when_evidence_mentions_no_incident(self):
        claim = _make_claim(value=0, unit="count", metric="fatal_workplace_accidents")
        ev = _make_evidence("No fatalities were reported at any facility during FY2024.")
        result = run_numeric_check(claim, ev)
        # No positive number found → claim of zero not contradicted.
        assert result.passed is True


# ---------------------------------------------------------------------------
# Batch checks
# ---------------------------------------------------------------------------

class TestBatchChecks:

    def test_batch_returns_one_result_per_evidence(self):
        claim = _make_claim(value=40, unit="percent_reduction")
        ev_list = [
            _make_evidence("fell by 40%", evidence_id="EVD-A"),
            _make_evidence("rose by 5%", evidence_id="EVD-B"),
        ]
        results = run_numeric_checks_for_claim(claim, ev_list)
        assert len(results) == 2
