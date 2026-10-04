#!/usr/bin/env python3
"""
evaluate_retrieval_methods.py

Four-way retrieval comparison: no retrieval, keyword-only (BM25), vector-only
(semantic), and the full hybrid agent. Produces a results table instead of a
claim, directly answering the original project plan's call for this exact
comparison.

HOW EACH CONFIGURATION WORKS
-----------------------------
no_retrieval   : retrieval is skipped entirely; verify_claim() is called with
                 zero evidence, which always yields INSUFFICIENT_EVIDENCE.
                 This is the baseline every other method must beat.
keyword_only   : HybridRetriever with bm25_weight=1.0, semantic_weight=0.0,
                 use_semantic=False (no embedding model loaded at all).
vector_only    : HybridRetriever with bm25_weight=0.0, semantic_weight=1.0,
                 use_semantic=True (ChromaDB + sentence-transformers).
hybrid         : HybridRetriever at its documented default weights
                 (0.6 BM25 / 0.4 semantic), use_semantic=True.

Accuracy is measured against the curated dataset's ClaimRecord.expected_verdict
field (hand-labelled since Step 1), over CHECKABLE claims only -- checkability
does not depend on retrieval, so including NOT_CHECKABLE claims would pad
every method's score identically and hide the real signal.

USAGE
-----
    python scripts/evaluate_retrieval_methods.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.utils.schemas import RetrievalResult, Verdict
from app.evaluation.checkability import assess_checkability, filter_checkable
from app.evaluation.verification import verify_claim
from app.retrieval.hybrid_retriever import HybridRetriever
from app.retrieval.query_planner import generate_query_plan
from app.api.pipeline import load_dataset_claims

TOP_K = 5


def evaluate_no_retrieval(claims) -> dict[str, Verdict]:
    results = {}
    for claim in claims:
        plan = generate_query_plan(claim)
        empty = RetrievalResult(claim_id=claim.claim_id, query_plan=plan, evidence=[])
        vr = verify_claim(claim, empty)
        results[claim.claim_id] = vr.verdict
    return results


def evaluate_with_retriever(claims, retriever: HybridRetriever) -> dict[str, Verdict]:
    results = {}
    for claim in claims:
        rr = retriever.retrieve_for_claim(claim, top_k=TOP_K)
        vr = verify_claim(claim, rr)
        results[claim.claim_id] = vr.verdict
    return results


def run_comparison() -> None:
    all_claims = load_dataset_claims()
    checkable, _ = filter_checkable(all_claims)
    expected = {c.claim_id: c.expected_verdict for c in checkable}

    configs = {
        "no_retrieval": None,
        "keyword_only": HybridRetriever(bm25_weight=1.0, semantic_weight=0.0, use_semantic=False),
        "vector_only": HybridRetriever(bm25_weight=0.0, semantic_weight=1.0, use_semantic=True),
        "hybrid": HybridRetriever(use_semantic=True),
    }

    all_results: dict[str, dict[str, Verdict]] = {}
    for name, retriever in configs.items():
        if retriever is None:
            all_results[name] = evaluate_no_retrieval(checkable)
        else:
            all_results[name] = evaluate_with_retriever(checkable, retriever)

    print("=" * 100)
    print("  FOUR-WAY RETRIEVAL COMPARISON (legacy/v1_data/claims/claims.json, checkable claims only)")
    print("=" * 100)
    col_width = 24
    header = f"  {'Claim':<10} {'Expected':<{col_width}}"
    for name in configs:
        header += f" {name:<{col_width}}"
    print(header)
    print("  " + "-" * (10 + col_width * (len(configs) + 1) + len(configs) + 1))

    correct_counts = {name: 0 for name in configs}
    for claim in checkable:
        cid = claim.claim_id
        exp = expected[cid].value
        row = f"  {cid:<10} {exp:<{col_width}}"
        for name in configs:
            predicted = all_results[name][cid].value
            match = predicted == exp
            if match:
                correct_counts[name] += 1
            row += f" {predicted:<{col_width}}"
        print(row)

    total = len(checkable)
    print("\n  " + "-" * 96)
    print("  ACCURACY SUMMARY")
    for name in configs:
        acc = correct_counts[name] / total * 100 if total else 0.0
        print(f"    {name:<16}: {correct_counts[name]}/{total} ({acc:.0f}%)")

    print(
        "\n  [NOTE] This compares verdict accuracy by retrieval strategy over the curated\n"
        "  12-claim synthetic dataset. It is a methodology demonstration, not a\n"
        "  statistically powered benchmark -- the dataset is intentionally small and\n"
        "  hand-authored so every expected_verdict is known with certainty."
    )
    print("=" * 100)


if __name__ == "__main__":
    run_comparison()
