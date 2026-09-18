#!/usr/bin/env python3
"""
run_verification.py

STEP 4 + 5 CLI demonstration.

Runs the complete backend pipeline:
  1. Load claims from data/claims/claims.json
  2. Filter CHECKABLE claims (Step 3 rule engine)
  3. Generate search queries for each CHECKABLE claim
  4. Retrieve evidence using BM25 (offline, deterministic)
  5. Verify each claim against its evidence
  6. Calculate the Greenwashing Risk Score
  7. Print a readable, audit-trail result

USAGE:
    python scripts/run_verification.py
    python scripts/run_verification.py --claim CLM-001
    python scripts/run_verification.py --top-k 3

NOTE:
  This uses BM25-only retrieval (offline mode).
  To use ChromaDB semantic retrieval, set use_semantic=True in the script
  (requires the sentence-transformers model to be downloaded first).

IMPORTANT:
  Results are TRIAGE INDICATORS for human review.
  They are NOT legal verdicts and do NOT prove or disprove greenwashing.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running from the project root without installing the package.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.utils.schemas import ClaimRecord, AuditRecord
from app.evaluation.checkability import assess_checkability, filter_checkable
from app.retrieval.hybrid_retriever import HybridRetriever
from app.evaluation.verification import verify_claim
from app.scoring.risk_score import calculate_risk_score


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

_DIVIDER = "-" * 70
_THICK   = "=" * 70

def _header(text: str) -> str:
    return f"\n{_THICK}\n  {text}\n{_THICK}"

def _section(text: str) -> str:
    return f"\n  {_DIVIDER}\n  {text}\n  {_DIVIDER}"

def _risk_color(band: str) -> str:
    """Return ANSI-coloured risk band label (degrades gracefully on Windows)."""
    colors = {"Low": "\033[32m", "Moderate": "\033[33m", "High": "\033[91m", "Very High": "\033[31m"}
    reset = "\033[0m"
    return f"{colors.get(band, '')}{band}{reset}"



def print_audit_record(record: AuditRecord, verbose: bool = True) -> None:
    """Pretty-print the full audit trail for one claim."""
    cr = record.checkability_result
    rr = record.retrieval_result
    vr = record.verification_result
    rs = record.risk_score_result

    print(_header(f"Claim: {record.claim_id}"))
    print(f"\n  Company : {record.company}")
    print(f"  Text    : {record.claim_text[:100]}{'...' if len(record.claim_text) > 100 else ''}")

    # ---- Checkability ----
    if cr:
        print(_section("Checkability"))
        print(f"    Result      : {cr.checkability.value}")
        print(f"    Completeness: {cr.checkability_completeness:.0f}/100")
        print(f"    Reason      : {cr.reason[:140]}")

    # ---- Queries ----
    if rr and rr.query_plan:
        print(_section("Search Queries Generated"))
        for i, q in enumerate(rr.query_plan.queries, 1):
            print(f"    {i}. {q}")

    # ---- Evidence Retrieved ----
    if rr and rr.evidence:
        print(_section(f"Evidence Retrieved (top {len(rr.evidence)})"))
        for ev in rr.evidence:
            print(f"\n    [{ev.rank}] {ev.evidence_id}  |  Tier {int(ev.source_tier)} ({ev.source_type})")
            print(f"        Source  : {ev.source}")
            print(f"        Period  : {ev.reporting_period or 'N/A'}")
            print(f"        Scores  : BM25={ev.bm25_score:.3f}  Semantic={ev.semantic_score:.3f}  Combined={ev.combined_score:.3f}")
            print(f"        Text    : {ev.retrieved_text[:120]}{'...' if len(ev.retrieved_text) > 120 else ''}")
    elif rr:
        print(_section("Evidence Retrieved"))
        print("    No evidence retrieved.")

    # ---- Verification ----
    if vr:
        print(_section("Verification Result"))
        print(f"    Verdict         : {vr.verdict.value}")
        print(f"    Reason          : {vr.reason[:200]}")
        print(f"    Supporting IDs  : {', '.join(vr.supporting_evidence_ids) or 'none'}")
        print(f"    Contradicting   : {', '.join(vr.contradicting_evidence_ids) or 'none'}")
        if vr.highest_authority_tier:
            print(f"    Highest-Auth Tier: {vr.highest_authority_tier}")
        if verbose and vr.numerical_checks:
            print(f"\n    Numerical checks ({len(vr.numerical_checks)}):")
            for nc in vr.numerical_checks:
                status = "PASS" if nc.passed else ("SKIP" if nc.skipped else "FAIL")
                print(f"      [{status}] {nc.check_type}: {nc.detail[:100]}")

    # ---- Risk Score ----
    if rs:
        print(_section("Greenwashing Risk Score"))
        print(f"    Score  : {rs.risk_score:.0f} / 100  ->  {_risk_color(rs.risk_band)} RISK")
        print(f"    Summary: {rs.summary[:200]}")
        if verbose and rs.factors:
            print(f"\n    Score breakdown ({len(rs.factors)} factors):")
            for f in sorted(rs.factors, key=lambda x: x.points, reverse=True):
                print(f"      +{f.points:.0f} pts  [{f.factor}]  {f.reason[:80]}")
        print(f"\n    [NOTE] {rs.disclaimer}")

    print()


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def load_claims() -> list[ClaimRecord]:
    path = PROJECT_ROOT / "data" / "claims" / "claims.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [ClaimRecord(**c) for c in raw["claims"]]


def run_pipeline(
    claim_ids: list[str] | None = None,
    top_k: int = 5,
    use_semantic: bool = False,
    verbose: bool = True,
) -> list[AuditRecord]:
    """Run the full Step 4 + 5 pipeline.

    Args:
        claim_ids: Optional list of specific claim IDs to process.
                   If None, all CHECKABLE claims are processed.
        top_k: Maximum evidence items retrieved per claim.
        use_semantic: Whether to use ChromaDB semantic retrieval in addition
                      to BM25. Requires sentence-transformers model download.
        verbose: Whether to print detailed output.

    Returns:
        List of AuditRecord objects (one per CHECKABLE claim processed).
    """
    print(f"\n{'='*70}")
    print("  ESG GREENWASHING DETECTION & VERIFICATION AGENT")
    print("  Steps 4 + 5: Evidence Retrieval + Verification + Risk Scoring")
    print(f"{'='*70}")
    print(f"\n  Mode     : {'Hybrid BM25 + Semantic' if use_semantic else 'BM25-only (offline)'}")
    print(f"  Top-K    : {top_k} evidence items per claim")

    # Step 1: Load claims
    all_claims = load_claims()
    print(f"\n  Loaded {len(all_claims)} claims from claims.json")

    # Step 2: Filter CHECKABLE claims
    checkable, not_checkable = filter_checkable(all_claims)
    print(f"  CHECKABLE: {len(checkable)} | NOT_CHECKABLE: {len(not_checkable)}")

    # Apply claim_id filter if specified
    if claim_ids:
        checkable = [c for c in checkable if c.claim_id in claim_ids]
        print(f"  Filtered to: {len(checkable)} claim(s) matching {claim_ids}")

    if not checkable:
        print("\n  No CHECKABLE claims to process.")
        return []

    # Step 3: Initialise retriever (offline BM25 by default)
    retriever = HybridRetriever(use_semantic=use_semantic)

    audit_records: list[AuditRecord] = []

    for claim in checkable:
        # Step 4: Generate queries + retrieve evidence
        retrieval_result = retriever.retrieve_for_claim(claim, top_k=top_k)

        # Step 5: Assess checkability (for the audit record)
        checkability_result = assess_checkability(claim)

        # Step 6: Verify
        verification_result = verify_claim(claim, retrieval_result)

        # Step 7: Risk score
        risk_score_result = calculate_risk_score(verification_result)

        # Build audit record
        record = AuditRecord(
            claim_id=claim.claim_id,
            claim_text=claim.original_text,
            company=claim.company,
            checkability_result=checkability_result,
            retrieval_result=retrieval_result,
            verification_result=verification_result,
            risk_score_result=risk_score_result,
        )
        audit_records.append(record)

        if verbose:
            print_audit_record(record, verbose=verbose)

    # Summary table
    print(_header("PIPELINE SUMMARY"))
    print(f"\n  {'Claim ID':<12} {'Company':<30} {'Verdict':<22} {'Risk Score':<12} {'Band'}")
    print(f"  {'-'*12} {'-'*30} {'-'*22} {'-'*12} {'-'*10}")
    for rec in audit_records:
        vr = rec.verification_result
        rs = rec.risk_score_result
        if vr and rs:
            print(
                f"  {rec.claim_id:<12} "
                f"{rec.company[:29]:<30} "
                f"{vr.verdict.value:<22} "
                f"{rs.risk_score:>6.0f}/100     "
                f"{rs.risk_band}"
            )

    print(f"\n\n  [!] DISCLAIMER: All scores are TRIAGE INDICATORS for human review.")
    print("      They are NOT legal verdicts and do NOT prove or disprove greenwashing.")
    print(f"\n{'='*70}\n")

    return audit_records


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the ESG Greenwashing Verification pipeline (Steps 4 + 5)."
    )
    parser.add_argument(
        "--claim",
        nargs="+",
        metavar="CLAIM_ID",
        help="Process only these specific claim IDs (e.g. --claim CLM-001 CLM-002)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Maximum evidence items to retrieve per claim (default: 5)",
    )
    parser.add_argument(
        "--semantic",
        action="store_true",
        help="Use ChromaDB semantic retrieval in addition to BM25 (requires model download)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Print only the summary table, not the full per-claim audit trail",
    )
    args = parser.parse_args()

    run_pipeline(
        claim_ids=args.claim,
        top_k=args.top_k,
        use_semantic=args.semantic,
        verbose=not args.quiet,
    )


if __name__ == "__main__":
    main()
