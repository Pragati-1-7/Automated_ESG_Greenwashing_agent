"""
test_retrieval.py

STEP 4 tests: query planning, BM25 retrieval, ChromaDB stub, hybrid ranking,
and source-tier metadata preservation.

All tests are OFFLINE and DETERMINISTIC:
  - No real network access.
  - ChromaDB semantic retrieval is always bypassed (use_semantic=False).
  - BM25 uses the real evidence.json corpus.
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
    QueryPlan,
    RetrievalResult,
    RetrievedEvidence,
    SourceTier,
)
from app.evaluation.checkability import filter_checkable
from app.retrieval.query_planner import generate_query_plan, generate_query_plans
from app.retrieval.bm25_retriever import BM25Retriever
from app.retrieval.chroma_retriever import ChromaRetriever
from app.retrieval.hybrid_retriever import HybridRetriever


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def clm001() -> ClaimRecord:
    """CLM-001: GreenLeaf Scope 1 40% reduction FY2024."""
    return ClaimRecord(
        claim_id="CLM-001",
        company="GreenLeaf Renewables Ltd",
        original_text="GreenLeaf Renewables reduced its Scope 1 carbon emissions by 40% in FY2024 compared to the FY2023 baseline.",
        metric="carbon_emissions_scope1",
        value=40,
        unit="percent_reduction",
        scope="Scope 1",
        boundary="company-wide",
        baseline_year="FY2023",
        reporting_period="FY2024",
        claim_type=ClaimType.RESULT,
        checkability=Checkability.CHECKABLE,
        source_document="greenleaf_sustainability_report_2024.pdf",
        page_number=12,
    )


@pytest.fixture()
def clm002() -> ClaimRecord:
    """CLM-002: Bharat Steelworks 25% reduction Scope 1+2 FY2024 vs FY2022."""
    return ClaimRecord(
        claim_id="CLM-002",
        company="Bharat Steelworks Pvt Ltd",
        original_text="Bharat Steelworks achieved a 25% reduction in Scope 1 and Scope 2 emissions.",
        metric="carbon_emissions_scope1_2",
        value=25,
        unit="percent_reduction",
        scope="Scope 1+2",
        boundary="company-wide",
        baseline_year="FY2022",
        reporting_period="FY2024",
        claim_type=ClaimType.RESULT,
        checkability=Checkability.CHECKABLE,
        source_document="bharat_steelworks_esg_report_2024.pdf",
        page_number=8,
    )


@pytest.fixture()
def bm25() -> BM25Retriever:
    return BM25Retriever()


@pytest.fixture()
def hybrid_offline() -> HybridRetriever:
    return HybridRetriever(use_semantic=False)


# ---------------------------------------------------------------------------
# 1. Query generation tests
# ---------------------------------------------------------------------------

class TestQueryPlanner:

    def test_query_plan_has_claim_id(self, clm001):
        plan = generate_query_plan(clm001)
        assert plan.claim_id == "CLM-001"

    def test_query_plan_has_company(self, clm001):
        plan = generate_query_plan(clm001)
        assert plan.company == "GreenLeaf Renewables Ltd"

    def test_generates_at_least_two_queries(self, clm001):
        plan = generate_query_plan(clm001)
        assert len(plan.queries) >= 2

    def test_generates_at_most_four_queries(self, clm001):
        plan = generate_query_plan(clm001)
        assert len(plan.queries) <= 4

    def test_queries_are_non_empty_strings(self, clm001):
        plan = generate_query_plan(clm001)
        for q in plan.queries:
            assert isinstance(q, str)
            assert len(q.strip()) > 0

    def test_first_query_contains_company_and_period(self, clm001):
        plan = generate_query_plan(clm001)
        q1 = plan.queries[0].lower()
        assert "greenleaf" in q1
        assert "fy2024" in q1

    def test_baseline_query_generated_for_reduction_claim(self, clm001):
        """A percent_reduction claim with a baseline_year should generate a query mentioning it."""
        plan = generate_query_plan(clm001)
        combined = " ".join(plan.queries).lower()
        assert "fy2023" in combined  # baseline_year

    def test_generation_method_is_deterministic(self, clm001):
        plan = generate_query_plan(clm001)
        assert plan.generation_method == "deterministic"

    def test_batch_query_generation(self, clm001, clm002):
        plans = generate_query_plans([clm001, clm002])
        assert len(plans) == 2
        assert plans[0].claim_id == "CLM-001"
        assert plans[1].claim_id == "CLM-002"

    def test_queries_are_unique_within_plan(self, clm001):
        plan = generate_query_plan(clm001)
        assert len(plan.queries) == len(set(plan.queries))


# ---------------------------------------------------------------------------
# 2. Checkable claim filtering (reuses Step 3 filter_checkable)
# ---------------------------------------------------------------------------

class TestCheckableFiltering:

    def test_filter_returns_only_checkable(self, clm001, clm002):
        checkable, not_checkable = filter_checkable([clm001, clm002])
        assert len(checkable) == 2
        assert len(not_checkable) == 0

    def test_not_checkable_excluded_from_retrieval(self):
        vague = ClaimRecord(
            claim_id="CLM-011",
            company="EcoCycle Waste Management Ltd",
            original_text="We are committed to a greener future.",
            metric=None, value=None, unit=None, scope=None,
            boundary=None, baseline_year=None, reporting_period=None,
            claim_type=ClaimType.COMMITMENT,
            checkability=Checkability.NOT_CHECKABLE,
            source_document="test.pdf",
        )
        checkable, not_checkable = filter_checkable([vague])
        assert len(checkable) == 0
        assert len(not_checkable) == 1


# ---------------------------------------------------------------------------
# 3. BM25 retrieval tests
# ---------------------------------------------------------------------------

class TestBM25Retriever:

    def test_retriever_loads_corpus(self, bm25):
        assert len(bm25.records) > 0

    def test_returns_results_for_relevant_query(self, bm25):
        results = bm25.retrieve("GreenLeaf Scope 1 emissions FY2024", top_k=3)
        assert len(results) > 0

    def test_results_are_ranked_highest_first(self, bm25):
        results = bm25.retrieve("GreenLeaf emissions reduction FY2024", top_k=5)
        scores = [r.bm25_score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_top_result_for_clm001_query_is_relevant(self, bm25):
        results = bm25.retrieve("GreenLeaf Renewables Scope 1 carbon emissions FY2024", top_k=3)
        assert len(results) > 0
        top = results[0]
        assert "greenleaf" in top.retrieved_text.lower() or "greenleaf" in top.company.lower()

    def test_bm25_score_normalised_to_0_1(self, bm25):
        results = bm25.retrieve("emissions", top_k=10)
        for r in results:
            assert 0.0 <= r.bm25_score <= 1.0

    def test_empty_query_returns_empty(self, bm25):
        results = bm25.retrieve("", top_k=5)
        assert results == []

    def test_top_k_respected(self, bm25):
        results = bm25.retrieve("sustainability", top_k=3)
        assert len(results) <= 3

    def test_results_have_rank_starting_at_1(self, bm25):
        results = bm25.retrieve("emissions", top_k=5)
        ranks = [r.rank for r in results]
        assert ranks[0] == 1

    def test_source_tier_metadata_preserved(self, bm25):
        """Source tier must survive the retrieval pipeline intact."""
        results = bm25.retrieve("regulatory filing BRSR", top_k=10)
        for r in results:
            assert isinstance(r.source_tier, SourceTier)
            assert 1 <= int(r.source_tier) <= 5

    def test_multi_query_deduplicates(self, bm25):
        queries = [
            "GreenLeaf Scope 1 FY2024",
            "GreenLeaf carbon emissions FY2024",
            "GreenLeaf BRSR filing",
        ]
        results = bm25.retrieve_multi_query(queries, top_k=5)
        ids = [r.evidence_id for r in results]
        assert len(ids) == len(set(ids)), "Duplicate evidence_ids found in multi-query results"

    def test_evidence_id_format_preserved(self, bm25):
        results = bm25.retrieve("emissions", top_k=10)
        for r in results:
            assert r.evidence_id.startswith("EVD-")


# ---------------------------------------------------------------------------
# 4. ChromaDB retriever (stub/offline mode)
# ---------------------------------------------------------------------------

class TestChromaRetrieverStub:

    def test_stub_mode_returns_empty_list(self):
        retriever = ChromaRetriever(use_semantic=False)
        results = retriever.retrieve("any query at all", top_k=5)
        assert results == []

    def test_stub_multi_query_returns_empty(self):
        retriever = ChromaRetriever(use_semantic=False)
        results = retriever.retrieve_multi_query(["q1", "q2"], top_k=5)
        assert results == []

    def test_stub_instantiation_is_fast(self):
        """Stub mode should not download any model or initialise ChromaDB."""
        import time
        start = time.time()
        _ = ChromaRetriever(use_semantic=False)
        elapsed = time.time() - start
        # Should complete in well under 2 seconds.
        assert elapsed < 2.0


# ---------------------------------------------------------------------------
# 5. Hybrid retrieval (offline = BM25 only)
# ---------------------------------------------------------------------------

class TestHybridRetriever:

    def test_hybrid_returns_retrieval_result(self, hybrid_offline, clm001):
        rr = hybrid_offline.retrieve_for_claim(clm001, top_k=5)
        assert isinstance(rr, RetrievalResult)
        assert rr.claim_id == "CLM-001"

    def test_hybrid_evidence_ranked_correctly(self, hybrid_offline, clm001):
        rr = hybrid_offline.retrieve_for_claim(clm001, top_k=5)
        scores = [e.combined_score for e in rr.evidence]
        assert scores == sorted(scores, reverse=True)

    def test_hybrid_ranks_start_at_1(self, hybrid_offline, clm001):
        rr = hybrid_offline.retrieve_for_claim(clm001, top_k=5)
        if rr.evidence:
            assert rr.evidence[0].rank == 1

    def test_hybrid_top_k_respected(self, hybrid_offline, clm001):
        rr = hybrid_offline.retrieve_for_claim(clm001, top_k=3)
        assert len(rr.evidence) <= 3

    def test_hybrid_combined_score_uses_bm25_when_no_semantic(self, hybrid_offline, clm001):
        """In offline mode, combined_score = 0.6 × bm25 + 0.4 × 0.0 = 0.6 × bm25."""
        rr = hybrid_offline.retrieve_for_claim(clm001, top_k=5)
        for ev in rr.evidence:
            assert ev.semantic_score == 0.0
            expected_combined = round(0.6 * ev.bm25_score, 4)
            assert abs(ev.combined_score - expected_combined) < 0.001

    def test_hybrid_query_plan_stored_in_result(self, hybrid_offline, clm001):
        rr = hybrid_offline.retrieve_for_claim(clm001, top_k=5)
        assert rr.query_plan is not None
        assert rr.query_plan.claim_id == "CLM-001"

    def test_source_tier_present_in_hybrid_result(self, hybrid_offline, clm001):
        rr = hybrid_offline.retrieve_for_claim(clm001, top_k=5)
        for ev in rr.evidence:
            assert isinstance(ev.source_tier, SourceTier)

    def test_tier1_evidence_retrievable(self, hybrid_offline, clm001):
        """Tier 1 (regulatory filing) evidence should appear in results for a well-formed claim."""
        rr = hybrid_offline.retrieve_for_claim(clm001, top_k=10)
        tiers = [int(ev.source_tier) for ev in rr.evidence]
        assert 1 in tiers, "Expected at least one Tier 1 (regulatory filing) result"
