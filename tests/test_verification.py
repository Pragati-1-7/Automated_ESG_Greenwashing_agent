"""
test_verification.py

STEP 5 tests: verification engine.

Tests cover:
  - ALIGN verdict
  - CONTRADICT verdict (from high-authority source)
  - INSUFFICIENT_EVIDENCE verdict (no evidence, future target, mixed)
  - Audit trail completeness
  - Result vs. commitment distinction
  - High-authority tier weighting
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
    QueryPlan,
    RetrievalResult,
    RetrievedEvidence,
    SourceTier,
    Verdict,
)
from app.evaluation.verification import verify_claim


# ---------------------------------------------------------------------------
# Helpers
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


def _make_retrieval_result(
    claim: ClaimRecord,
    evidence_records: list[EvidenceRecord],
) -> RetrievalResult:
    """Wrap evidence records in a minimal RetrievalResult for testing."""
    plan = QueryPlan(claim_id=claim.claim_id, company=claim.company, queries=["test query"])
    retrieved = [
        RetrievedEvidence.from_evidence_record(ev, rank=i + 1, bm25_score=0.9 - i * 0.1)
        for i, ev in enumerate(evidence_records)
    ]
    return RetrievalResult(claim_id=claim.claim_id, query_plan=plan, evidence=retrieved)


def _make_evidence(
    retrieved_text: str,
    relationship: ExpectedRelationship,
    source_tier: SourceTier = SourceTier.TIER_1_REGULATORY_FILING,
    reporting_period: str = "FY2024",
    evidence_id: str = "EVD-TEST",
    company: str = "TestCo",
) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=evidence_id,
        claim_id="CLM-TEST",
        company=company,
        source="Test Source",
        source_tier=source_tier,
        source_type="regulatory_filing",
        publication_date="2024-06-01",
        reporting_period=reporting_period,
        retrieved_text=retrieved_text,
        expected_relationship=relationship,
    )


# ---------------------------------------------------------------------------
# 14. ALIGN tests
# ---------------------------------------------------------------------------

class TestAlignVerdict:

    def test_align_when_tier1_supports(self):
        """Tier 1 supporting evidence → ALIGN."""
        claim = _make_claim()
        ev = _make_evidence(
            "Scope 1 emissions declined by approximately 40%.",
            ExpectedRelationship.SUPPORTS,
            source_tier=SourceTier.TIER_1_REGULATORY_FILING,
        )
        rr = _make_retrieval_result(claim, [ev])
        result = verify_claim(claim, rr)
        assert result.verdict == Verdict.ALIGN

    def test_align_stores_supporting_evidence_ids(self):
        claim = _make_claim()
        ev = _make_evidence(
            "emissions fell by 40%",
            ExpectedRelationship.SUPPORTS,
            evidence_id="EVD-001",
        )
        rr = _make_retrieval_result(claim, [ev])
        result = verify_claim(claim, rr)
        assert "EVD-001" in result.supporting_evidence_ids

    def test_align_has_no_contradicting_evidence(self):
        claim = _make_claim()
        ev = _make_evidence("emissions fell by 40%", ExpectedRelationship.SUPPORTS)
        rr = _make_retrieval_result(claim, [ev])
        result = verify_claim(claim, rr)
        assert len(result.contradicting_evidence_ids) == 0

    def test_align_records_method_as_rule_based(self):
        claim = _make_claim()
        ev = _make_evidence("fell by 40%", ExpectedRelationship.SUPPORTS)
        rr = _make_retrieval_result(claim, [ev])
        result = verify_claim(claim, rr)
        assert result.method == "rule_based"


# ---------------------------------------------------------------------------
# 15. CONTRADICT tests
# ---------------------------------------------------------------------------

class TestContradictVerdict:

    def test_contradict_when_tier1_contradicts(self):
        """High-authority (Tier 1) contradicting evidence → CONTRADICT."""
        claim = _make_claim(value=25, unit="percent_reduction")
        ev = _make_evidence(
            "Combined Scope 1 and Scope 2 emissions increased by approximately 5%.",
            ExpectedRelationship.CONTRADICTS,
            source_tier=SourceTier.TIER_1_REGULATORY_FILING,
        )
        rr = _make_retrieval_result(claim, [ev])
        result = verify_claim(claim, rr)
        assert result.verdict == Verdict.CONTRADICT

    def test_contradict_when_tier2_contradicts(self):
        """Tier 2 (regulator record) contradiction → CONTRADICT."""
        claim = _make_claim(value=0, unit="count", metric="fatal_workplace_accidents")
        ev = _make_evidence(
            "The factory inspectorate recorded two fatal accidents.",
            ExpectedRelationship.CONTRADICTS,
            source_tier=SourceTier.TIER_2_REGULATOR_OR_TRIBUNAL,
        )
        rr = _make_retrieval_result(claim, [ev])
        result = verify_claim(claim, rr)
        assert result.verdict == Verdict.CONTRADICT

    def test_contradict_stores_contradicting_ids(self):
        claim = _make_claim()
        ev = _make_evidence(
            "emissions increased by 5%",
            ExpectedRelationship.CONTRADICTS,
            evidence_id="EVD-003",
        )
        rr = _make_retrieval_result(claim, [ev])
        result = verify_claim(claim, rr)
        assert "EVD-003" in result.contradicting_evidence_ids

    def test_high_authority_contradict_beats_low_tier_support(self):
        """Tier 1 contradiction should override Tier 5 support → CONTRADICT."""
        claim = _make_claim(value=25, unit="percent_reduction")
        ev_tier1 = _make_evidence(
            "emissions increased by 5%",
            ExpectedRelationship.CONTRADICTS,
            source_tier=SourceTier.TIER_1_REGULATORY_FILING,
            evidence_id="EVD-HIGH",
        )
        ev_tier5 = _make_evidence(
            "company claims a 25% reduction according to its own press release",
            ExpectedRelationship.SUPPORTS,
            source_tier=SourceTier.TIER_5_NEWS,
            evidence_id="EVD-LOW",
        )
        rr = _make_retrieval_result(claim, [ev_tier1, ev_tier5])
        result = verify_claim(claim, rr)
        assert result.verdict == Verdict.CONTRADICT

    def test_highest_authority_tier_reported(self):
        claim = _make_claim()
        ev = _make_evidence(
            "emissions rose",
            ExpectedRelationship.CONTRADICTS,
            source_tier=SourceTier.TIER_2_REGULATOR_OR_TRIBUNAL,
        )
        rr = _make_retrieval_result(claim, [ev])
        result = verify_claim(claim, rr)
        assert result.highest_authority_tier == 2


# ---------------------------------------------------------------------------
# 16. INSUFFICIENT_EVIDENCE tests
# ---------------------------------------------------------------------------

class TestInsufficientEvidence:

    def test_no_evidence_returns_insufficient(self):
        """Empty evidence list → INSUFFICIENT_EVIDENCE."""
        claim = _make_claim()
        rr = _make_retrieval_result(claim, [])
        result = verify_claim(claim, rr)
        assert result.verdict == Verdict.INSUFFICIENT_EVIDENCE

    def test_future_target_returns_insufficient(self):
        """Future target claim → INSUFFICIENT_EVIDENCE (can't verify future)."""
        claim = _make_claim(
            claim_type=ClaimType.TARGET,
            reporting_period="2030 (future target)",
            value=100,
            unit="percent",
            metric="renewable_electricity_share",
        )
        ev = _make_evidence(
            "Roadmap targets 60% renewable electricity by 2027.",
            ExpectedRelationship.PARTIAL,
            source_tier=SourceTier.TIER_4_COMPANY_PR,
        )
        rr = _make_retrieval_result(claim, [ev])
        result = verify_claim(claim, rr)
        assert result.verdict == Verdict.INSUFFICIENT_EVIDENCE

    def test_partial_evidence_only_returns_insufficient(self):
        """Only PARTIAL evidence → INSUFFICIENT_EVIDENCE."""
        claim = _make_claim()
        ev = _make_evidence(
            "Some deforestation-free sourcing policy exists for Tier 1 suppliers.",
            ExpectedRelationship.PARTIAL,
            source_tier=SourceTier.TIER_4_COMPANY_PR,
        )
        rr = _make_retrieval_result(claim, [ev])
        result = verify_claim(claim, rr)
        assert result.verdict == Verdict.INSUFFICIENT_EVIDENCE


# ---------------------------------------------------------------------------
# 19. Audit trail completeness
# ---------------------------------------------------------------------------

class TestAuditTrail:

    def test_verification_result_has_claim_id(self):
        claim = _make_claim()
        ev = _make_evidence("fell by 40%", ExpectedRelationship.SUPPORTS)
        rr = _make_retrieval_result(claim, [ev])
        result = verify_claim(claim, rr)
        assert result.claim_id == "CLM-TEST"

    def test_verification_result_has_verdict(self):
        claim = _make_claim()
        ev = _make_evidence("fell by 40%", ExpectedRelationship.SUPPORTS)
        rr = _make_retrieval_result(claim, [ev])
        result = verify_claim(claim, rr)
        assert result.verdict in (Verdict.ALIGN, Verdict.CONTRADICT, Verdict.INSUFFICIENT_EVIDENCE)

    def test_verification_result_has_reason(self):
        claim = _make_claim()
        ev = _make_evidence("fell by 40%", ExpectedRelationship.SUPPORTS)
        rr = _make_retrieval_result(claim, [ev])
        result = verify_claim(claim, rr)
        assert isinstance(result.reason, str)
        assert len(result.reason) > 10

    def test_verification_result_has_numerical_checks(self):
        claim = _make_claim()
        ev = _make_evidence("emissions fell by 40%", ExpectedRelationship.SUPPORTS)
        rr = _make_retrieval_result(claim, [ev])
        result = verify_claim(claim, rr)
        # numerical_checks may be empty for non-numeric claims, but should be a list.
        assert isinstance(result.numerical_checks, list)

    def test_audit_trail_shows_all_evidence_ids(self):
        claim = _make_claim()
        ev1 = _make_evidence("fell by 40%", ExpectedRelationship.SUPPORTS, evidence_id="EVD-A")
        ev2 = _make_evidence("also fell", ExpectedRelationship.SUPPORTS, evidence_id="EVD-B")
        rr = _make_retrieval_result(claim, [ev1, ev2])
        result = verify_claim(claim, rr)
        # All evidence IDs should appear in at least one of the audit lists.
        all_ids = (
            result.supporting_evidence_ids
            + result.contradicting_evidence_ids
            + result.insufficient_evidence_ids
        )
        for ev_id in ["EVD-A", "EVD-B"]:
            assert ev_id in all_ids, f"{ev_id} missing from audit trail"

    def test_company_match_flag_present(self):
        claim = _make_claim()
        ev = _make_evidence("fell by 40%", ExpectedRelationship.SUPPORTS)
        rr = _make_retrieval_result(claim, [ev])
        result = verify_claim(claim, rr)
        assert result.company_match is not None

    def test_verdict_is_never_not_applicable(self):
        """NOT_APPLICABLE is reserved for non-checkable claims; verification must never produce it."""
        claim = _make_claim()
        rr = _make_retrieval_result(claim, [])
        result = verify_claim(claim, rr)
        assert result.verdict != Verdict.NOT_APPLICABLE
