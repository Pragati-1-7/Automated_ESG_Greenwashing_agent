"""
hybrid_retriever.py

STEP 4: Hybrid BM25 + semantic evidence retriever.

WHY HYBRID?
-----------
Neither BM25 nor semantic search alone is optimal for ESG evidence retrieval:

  BM25 strengths:
    - Exact matching of company names, year tokens ("FY2024"), scope labels
      ("Scope 1"), metric names ("tCO2e"), and specific numeric values.
    - Fully deterministic and fast.
    - No model download needed.

  Semantic search strengths:
    - Captures meaning similarity even when exact terms differ
      (e.g. "carbon emissions" ≈ "GHG discharge").
    - Useful for finding evidence that paraphrases the claim differently.

  Hybrid combination:
    - Takes the best of both worlds.
    - Keeps both individual scores visible so a human reviewer can see why
      each piece of evidence was ranked where it was.

COMBINATION FORMULA
-------------------
  combined_score = (BM25_WEIGHT × bm25_score) + (SEMANTIC_WEIGHT × semantic_score)

Default weights (documented and tunable):
  BM25_WEIGHT     = 0.6   (exact-term matching matters more for ESG specifics)
  SEMANTIC_WEIGHT = 0.4   (semantic similarity is useful but secondary)

Scores from both retrievers are normalised to [0, 1] before combination,
so neither scale dominates. Normalisation details are in bm25_retriever.py
and chroma_retriever.py respectively.

When use_semantic=False (offline/test mode), semantic scores are all 0.0
and the combined score equals the BM25 score. The formula still applies
transparently -- it just uses a semantic contribution of zero.

DEDUPLICATION
-------------
The same evidence_id may appear in both BM25 and semantic results. The
hybrid merger keeps only the single best combined_score for each evidence_id,
then re-ranks. This prevents double-counting.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.utils.schemas import ClaimRecord, EvidenceRecord, QueryPlan, RetrievalResult, RetrievedEvidence
from app.retrieval.bm25_retriever import BM25Retriever
from app.retrieval.chroma_retriever import ChromaRetriever
from app.retrieval.query_planner import generate_query_plan

# Documented, tunable combination weights.
BM25_WEIGHT: float = 0.6
SEMANTIC_WEIGHT: float = 0.4


class HybridRetriever:
    """Combines BM25 and semantic results into one ranked, deduplicated list.

    Usage (fully offline -- BM25 only):
        retriever = HybridRetriever(use_semantic=False)
        result = retriever.retrieve_for_claim(claim, top_k=5)

    Usage (full hybrid with ChromaDB):
        retriever = HybridRetriever(use_semantic=True)
        result = retriever.retrieve_for_claim(claim, top_k=5)
    """

    def __init__(
        self,
        evidence_path: Optional[Path] = None,
        records: Optional[list[EvidenceRecord]] = None,
        use_semantic: bool = False,   # default offline; set True for full pipeline
        chroma_dir: Optional[Path] = None,
        bm25_weight: float = BM25_WEIGHT,
        semantic_weight: float = SEMANTIC_WEIGHT,
    ) -> None:
        self._bm25 = BM25Retriever(evidence_path=evidence_path, records=records)
        self._chroma = ChromaRetriever(
            evidence_path=evidence_path,
            records=records,
            use_semantic=use_semantic,
            chroma_dir=chroma_dir,
        )
        self._bm25_weight = bm25_weight
        self._semantic_weight = semantic_weight
        self._use_semantic = use_semantic

    def retrieve_for_claim(
        self, claim: ClaimRecord, top_k: int = 5
    ) -> RetrievalResult:
        """Run the full retrieval pipeline for one CHECKABLE claim.

        Steps:
          1. Generate a query plan (deterministic, rule-based).
          2. Run BM25 across all queries.
          3. Run semantic retrieval across all queries (if use_semantic=True).
          4. Merge, deduplicate, compute combined scores, re-rank.
          5. Return a RetrievalResult with the query plan + top-k evidence.

        Args:
            claim: A CHECKABLE ClaimRecord.
            top_k: Maximum evidence items to return.

        Returns:
            RetrievalResult containing the query plan and ranked evidence.
        """
        plan = generate_query_plan(claim)
        ranked = self.retrieve_with_plan(plan, top_k=top_k)
        return RetrievalResult(
            claim_id=claim.claim_id,
            query_plan=plan,
            evidence=ranked,
            top_k=top_k,
        )

    def retrieve_with_plan(
        self, plan: QueryPlan, top_k: int = 5
    ) -> list[RetrievedEvidence]:
        """Execute a pre-built QueryPlan and return merged, ranked evidence.

        Useful when you already have a query plan (e.g. from tests) and want
        to run retrieval without needing a full ClaimRecord.

        Args:
            plan: A QueryPlan with one or more query strings.
            top_k: Maximum results to return.

        Returns:
            Merged, deduplicated, re-ranked list of RetrievedEvidence.
        """
        bm25_results = self._bm25.retrieve_multi_query(plan.queries, top_k=top_k * 2)
        semantic_results = self._chroma.retrieve_multi_query(plan.queries, top_k=top_k * 2)

        merged = _merge_results(
            bm25_results,
            semantic_results,
            bm25_weight=self._bm25_weight,
            semantic_weight=self._semantic_weight,
        )

        # Sort by combined score descending, take top_k, re-assign ranks.
        ranked = sorted(merged, key=lambda r: r.combined_score, reverse=True)[:top_k]
        for i, ev in enumerate(ranked, start=1):
            ev.rank = i
        return ranked


# ---------------------------------------------------------------------------
# Internal merge logic
# ---------------------------------------------------------------------------

def _merge_results(
    bm25_results: list[RetrievedEvidence],
    semantic_results: list[RetrievedEvidence],
    bm25_weight: float = BM25_WEIGHT,
    semantic_weight: float = SEMANTIC_WEIGHT,
) -> list[RetrievedEvidence]:
    """Merge BM25 and semantic results into one deduplicated list.

    For each evidence_id:
      - Take the BM25 score from bm25_results (0.0 if not found there).
      - Take the semantic score from semantic_results (0.0 if not found there).
      - Compute combined_score = bm25_weight × bm25 + semantic_weight × semantic.
      - Keep a single merged RetrievedEvidence object.

    This is fully transparent: the caller can inspect bm25_score and
    semantic_score on each result to understand how the ranking was formed.
    """
    # Index both result sets by evidence_id.
    bm25_map: dict[str, RetrievedEvidence] = {r.evidence_id: r for r in bm25_results}
    sem_map: dict[str, RetrievedEvidence] = {r.evidence_id: r for r in semantic_results}

    all_ids = set(bm25_map) | set(sem_map)
    merged: list[RetrievedEvidence] = []

    for eid in all_ids:
        bm25_item = bm25_map.get(eid)
        sem_item = sem_map.get(eid)

        bm25_score = bm25_item.bm25_score if bm25_item else 0.0
        semantic_score = sem_item.semantic_score if sem_item else 0.0
        combined = bm25_weight * bm25_score + semantic_weight * semantic_score

        # Base the merged record on whichever source has it (prefer BM25 for
        # metadata stability since it always runs).
        base = bm25_item if bm25_item else sem_item
        assert base is not None  # at least one must be present

        merged.append(
            RetrievedEvidence(
                evidence_id=base.evidence_id,
                claim_id=base.claim_id,
                company=base.company,
                source=base.source,
                source_tier=base.source_tier,
                source_type=base.source_type,
                publication_date=base.publication_date,
                reporting_period=base.reporting_period,
                retrieved_text=base.retrieved_text,
                url_or_path=base.url_or_path,
                notes=base.notes,
                rank=1,  # temporary; caller re-assigns after sorting
                bm25_score=round(bm25_score, 4),
                semantic_score=round(semantic_score, 4),
                combined_score=round(combined, 4),
            )
        )

    return merged
