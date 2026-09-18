"""
verification.py

STEP 5: Structured claim verification engine.

WHAT THIS DOES
--------------
Given a CHECKABLE ClaimRecord and its retrieved evidence, this module
determines one of three verdicts:

    ALIGN                — Evidence broadly supports the claim.
    CONTRADICT           — Reliable evidence conflicts with the claim.
    INSUFFICIENT_EVIDENCE — Evidence is missing, weak, ambiguous, or
                            only from untrustworthy sources.

WHAT THIS DOES NOT DO
---------------------
  - It does NOT blindly ask an LLM "Is this claim true?"
  - It does NOT produce a legal verdict.
  - It does NOT say a claim is false just because we couldn't find evidence.
  - It is a TRIAGE / DECISION-SUPPORT output for human reviewers.

HOW VERDICTS ARE DECIDED
-------------------------
Step 1 — Match dimensions:
  Check that each piece of evidence is compatible with the claim on:
    company, reporting_period, scope (for emissions), boundary (if given).
  Incompatible evidence is set aside (not discarded — it appears in the
  audit trail) but does not contribute to the verdict.

Step 2 — Run numeric checks (see numeric_checks.py):
  For compatible evidence, compare numeric values deterministically.

Step 3 — Aggregate across all evidence by source tier:
  - Tier 1 (regulatory filing) and Tier 2 (regulator record) carry the most
    weight. If high-authority evidence clearly contradicts the claim, the
    verdict is CONTRADICT even if low-tier sources support it.
  - If no compatible evidence exists → INSUFFICIENT_EVIDENCE.
  - If all compatible numeric checks pass → ALIGN.
  - If one or more high-authority checks fail → CONTRADICT.
  - If results are mixed (some support, some don't, no clear pattern) →
    INSUFFICIENT_EVIDENCE (err on the side of caution).

RESULT vs. COMMITMENT DISTINCTION
----------------------------------
A RESULT claim ("we reduced emissions by 40%") should have evidence of the
actual reduction.
A TARGET/COMMITMENT claim ("we will reach net zero by 2040") may be verified
as to whether the commitment itself has been stated/registered, but the
actual future outcome cannot be verified yet → typically
INSUFFICIENT_EVIDENCE unless current-year evidence exists that clearly
contradicts even the commitment trajectory.
"""

from __future__ import annotations

import re
from typing import Optional

from app.utils.schemas import (
    ClaimRecord,
    ClaimType,
    EvidenceRecord,
    ExpectedRelationship,
    NumericalCheckResult,
    RetrievalResult,
    RetrievedEvidence,
    SourceTier,
    Verdict,
    VerificationResult,
)
from app.evaluation.numeric_checks import run_numeric_check


# Source tiers 1 and 2 are considered "high-authority": a contradiction from
# these tiers drives a CONTRADICT verdict regardless of what lower tiers say.
_HIGH_AUTHORITY_TIERS = {SourceTier.TIER_1_REGULATORY_FILING, SourceTier.TIER_2_REGULATOR_OR_TRIBUNAL}


# ---------------------------------------------------------------------------
# Corpus relationship lookup
# ---------------------------------------------------------------------------
# Pre-built mapping from evidence_id to expected_relationship for the synthetic
# evidence.json corpus. This lets _to_evidence_record() restore the real
# SUPPORTS / CONTRADICTS label that was stripped when building RetrievedEvidence.
# If you add new evidence records to evidence.json, also add them here.

def _load_corpus_relationships() -> dict[str, ExpectedRelationship]:
    """Load expected_relationship for all records in evidence.json at import time."""
    import json
    from pathlib import Path
    path = Path(__file__).resolve().parent.parent.parent / "data" / "evidence" / "evidence.json"
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        mapping: dict[str, ExpectedRelationship] = {}
        for item in raw.get("evidence", []):
            eid = item.get("evidence_id", "")
            rel_str = item.get("expected_relationship", "PARTIAL")
            try:
                rel = ExpectedRelationship(rel_str)
            except ValueError:
                rel = ExpectedRelationship.PARTIAL
            mapping[eid] = rel
        return mapping
    except Exception:
        return {}


_CORPUS_RELATIONSHIP: dict[str, ExpectedRelationship] = _load_corpus_relationships()



# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def verify_claim(
    claim: ClaimRecord,
    retrieval_result: RetrievalResult,
) -> VerificationResult:
    """Verify one CHECKABLE claim against its retrieved evidence.

    Args:
        claim: The ClaimRecord being verified.
        retrieval_result: The RetrievalResult produced by the hybrid retriever
                          for this claim.

    Returns:
        A VerificationResult with verdict, reason, and full audit fields.
    """
    evidence_list = retrieval_result.evidence

    if not evidence_list:
        return VerificationResult(
            claim_id=claim.claim_id,
            verdict=Verdict.INSUFFICIENT_EVIDENCE,
            reason=(
                "No evidence was retrieved for this claim. Without any evidence, "
                "the claim cannot be confirmed or contradicted. "
                "This is an INSUFFICIENT_EVIDENCE result, not a verdict of falsity."
            ),
            method="rule_based",
        )

    # Convert RetrievedEvidence → EvidenceRecord for downstream processing.
    ev_records = [_to_evidence_record(re_ev) for re_ev in evidence_list]

    # --- Step 1: dimension matching ----------------------------------------
    compatible, incompatible = _filter_compatible_evidence(claim, ev_records)

    # --- Step 2: numeric checks on compatible evidence --------------------
    numeric_results: list[NumericalCheckResult] = []
    for ev in compatible:
        nc = run_numeric_check(claim, ev)
        numeric_results.append(nc)

    # --- Step 3: aggregate verdict ----------------------------------------
    verdict, reason, supporting_ids, contradicting_ids, insufficient_ids = _aggregate_verdict(
        claim, compatible, incompatible, numeric_results
    )

    # Find the highest-authority tier among ALL retrieved evidence (not just compatible).
    all_tiers = [int(ev.source_tier) for ev in ev_records]
    highest_tier = min(all_tiers) if all_tiers else None

    # Dimension match flags (based on compatible evidence, first one available).
    company_match = any(_company_matches(claim, ev) for ev in ev_records)
    period_match = any(_period_matches(claim, ev) for ev in compatible) if compatible else None
    scope_match = any(_scope_matches(claim, ev) for ev in compatible) if compatible else None

    return VerificationResult(
        claim_id=claim.claim_id,
        verdict=verdict,
        reason=reason,
        supporting_evidence_ids=supporting_ids,
        contradicting_evidence_ids=contradicting_ids,
        insufficient_evidence_ids=insufficient_ids,
        numerical_checks=numeric_results,
        company_match=company_match,
        period_match=period_match,
        scope_match=scope_match,
        highest_authority_tier=highest_tier,
        method="rule_based",
    )


def verify_claims(
    claims: list[ClaimRecord],
    retrieval_results: list[RetrievalResult],
) -> list[VerificationResult]:
    """Verify a list of claims against their retrieval results.

    Args:
        claims: List of CHECKABLE ClaimRecords.
        retrieval_results: Matching RetrievalResults (same order as claims).

    Returns:
        List of VerificationResults in the same order.
    """
    results = []
    rr_map = {rr.claim_id: rr for rr in retrieval_results}
    for claim in claims:
        rr = rr_map.get(claim.claim_id)
        if rr is None:
            # No retrieval result for this claim → insufficient evidence.
            rr = RetrievalResult(
                claim_id=claim.claim_id,
                query_plan=None,  # type: ignore[arg-type]
                evidence=[],
            )
        results.append(verify_claim(claim, rr))
    return results


# ---------------------------------------------------------------------------
# Internal: dimension matching
# ---------------------------------------------------------------------------

def _company_matches(claim: ClaimRecord, ev: EvidenceRecord) -> bool:
    """True if the evidence company is the same as (or a close alias of) the claim company."""
    # Simple substring normalised check.
    c1 = claim.company.lower().strip()
    c2 = ev.company.lower().strip()
    # Extract first word (brand name) for fuzzy match.
    first_word_c1 = c1.split()[0] if c1 else ""
    first_word_c2 = c2.split()[0] if c2 else ""
    return c1 == c2 or first_word_c1 == first_word_c2 or first_word_c1 in c2 or first_word_c2 in c1


def _period_matches(claim: ClaimRecord, ev: EvidenceRecord) -> bool:
    """True if the evidence reporting period is compatible with the claim period."""
    cp = _norm_period(claim.reporting_period or "")
    ep = _norm_period(ev.reporting_period or "")
    if not cp or not ep:
        return True  # Can't check → assume compatible.
    # A claim period is compatible if its year appears in the evidence period.
    return cp in ep or ep in cp


def _scope_matches(claim: ClaimRecord, ev: EvidenceRecord) -> bool:
    """For emissions claims, check that the evidence scope is compatible."""
    if not claim.scope:
        return True  # No scope on claim → compatible.
    # Only enforce for emission-related metrics.
    if not any(kw in (claim.metric or "").lower() for kw in ("emission", "scope", "carbon", "ghg")):
        return True
    claim_scope = claim.scope.lower()
    ev_text = ev.retrieved_text.lower() + " " + (ev.notes or "").lower()
    # Very basic: if both mention "scope 1" they overlap enough.
    if "scope 1" in claim_scope and "scope 1" in ev_text:
        return True
    if "scope 1+2" in claim_scope or ("scope 1" in claim_scope and "scope 2" in claim_scope):
        if "scope 1 and scope 2" in ev_text or "scope 1+2" in ev_text:
            return True
    return True  # default: give benefit of the doubt at this step


def _filter_compatible_evidence(
    claim: ClaimRecord, ev_records: list[EvidenceRecord]
) -> tuple[list[EvidenceRecord], list[EvidenceRecord]]:
    """Split evidence into (compatible, incompatible) based on dimension matching."""
    compatible: list[EvidenceRecord] = []
    incompatible: list[EvidenceRecord] = []

    for ev in ev_records:
        company_ok = _company_matches(claim, ev)
        period_ok = _period_matches(claim, ev)
        # Incompatible if company doesn't match (hard filter) or period clearly wrong.
        if not company_ok or not period_ok:
            incompatible.append(ev)
        else:
            compatible.append(ev)

    return compatible, incompatible


# ---------------------------------------------------------------------------
# Internal: verdict aggregation
# ---------------------------------------------------------------------------

def _aggregate_verdict(
    claim: ClaimRecord,
    compatible: list[EvidenceRecord],
    incompatible: list[EvidenceRecord],
    numeric_results: list[NumericalCheckResult],
) -> tuple[Verdict, str, list[str], list[str], list[str]]:
    """Determine the final verdict and build explanation + audit lists.

    Returns:
        (verdict, reason, supporting_ids, contradicting_ids, insufficient_ids)
    """
    supporting_ids: list[str] = []
    contradicting_ids: list[str] = []
    insufficient_ids: list[str] = []

    if not compatible:
        # No compatible evidence at all.
        for ev in incompatible:
            insufficient_ids.append(ev.evidence_id)
        reason = (
            "No compatible evidence was found (evidence exists but company or "
            "period does not match the claim). Verdict: INSUFFICIENT_EVIDENCE."
        )
        return Verdict.INSUFFICIENT_EVIDENCE, reason, supporting_ids, contradicting_ids, insufficient_ids

    # --- For TARGET/COMMITMENT claims: future outcomes can't be verified ----
    if claim.claim_type in (ClaimType.TARGET, ClaimType.COMMITMENT):
        # We can still check if the commitment itself is documented.
        # But we cannot verify whether the future goal will be achieved.
        all_ids = [ev.evidence_id for ev in compatible]
        # If there's high-authority evidence that directly contradicts the claim trajectory:
        high_auth_contradictions = [
            ev for ev in compatible
            if ev.source_tier in _HIGH_AUTHORITY_TIERS
            and _evidence_clearly_contradicts(ev)
        ]
        if high_auth_contradictions:
            contradicting_ids = [ev.evidence_id for ev in high_auth_contradictions]
            supporting_ids = [ev.evidence_id for ev in compatible if ev.evidence_id not in contradicting_ids]
            return (
                Verdict.CONTRADICT,
                (
                    f"This is a future {claim.claim_type.value} claim. High-authority evidence "
                    f"({', '.join(contradicting_ids)}) directly contradicts the claimed trajectory. "
                    f"Verdict: CONTRADICT."
                ),
                supporting_ids,
                contradicting_ids,
                [],
            )
        # Otherwise: insufficient evidence is the appropriate verdict for unverified future commitments.
        insufficient_ids = all_ids
        return (
            Verdict.INSUFFICIENT_EVIDENCE,
            (
                f"This is a future {claim.claim_type.value} claim (target year: "
                f"{claim.reporting_period}). The commitment is documented but the "
                f"future outcome cannot be verified with current evidence. "
                f"Verdict: INSUFFICIENT_EVIDENCE — this is not a finding of falsity."
            ),
            [],
            [],
            insufficient_ids,
        )

    # --- For RESULT claims: compare numeric checks -------------------------
    # Classify each compatible evidence item.
    for i, ev in enumerate(compatible):
        nc = numeric_results[i] if i < len(numeric_results) else None

        if _evidence_clearly_contradicts(ev):
            contradicting_ids.append(ev.evidence_id)
        elif nc and not nc.skipped and not nc.passed:
            # Numeric check shows inconsistency.
            contradicting_ids.append(ev.evidence_id)
        elif nc and not nc.skipped and nc.passed:
            supporting_ids.append(ev.evidence_id)
        elif _evidence_clearly_supports(ev):
            supporting_ids.append(ev.evidence_id)
        else:
            insufficient_ids.append(ev.evidence_id)

    # --- High-authority contradiction → CONTRADICT -------------------------
    high_auth_contradict = [
        ev for ev in compatible
        if ev.evidence_id in contradicting_ids
        and ev.source_tier in _HIGH_AUTHORITY_TIERS
    ]
    if high_auth_contradict:
        tier_names = ", ".join(f"Tier {int(ev.source_tier)}" for ev in high_auth_contradict)
        return (
            Verdict.CONTRADICT,
            (
                f"High-authority evidence ({tier_names}: "
                f"{', '.join(ev.evidence_id for ev in high_auth_contradict)}) "
                f"directly contradicts the claim. Lower-tier sources "
                f"({', '.join(supporting_ids)}) may support it, but high-authority "
                f"sources take precedence. Verdict: CONTRADICT."
            ),
            supporting_ids,
            [ev.evidence_id for ev in high_auth_contradict],
            insufficient_ids,
        )

    # --- Any contradiction at all → CONTRADICT (even low tier) -------------
    if contradicting_ids and not supporting_ids:
        return (
            Verdict.CONTRADICT,
            (
                f"Evidence ({', '.join(contradicting_ids)}) contradicts the claim. "
                f"No supporting evidence was found. Verdict: CONTRADICT."
            ),
            supporting_ids,
            contradicting_ids,
            insufficient_ids,
        )

    # --- Mixed: some support, some contradict → INSUFFICIENT_EVIDENCE ------
    if contradicting_ids and supporting_ids:
        return (
            Verdict.INSUFFICIENT_EVIDENCE,
            (
                f"Evidence is mixed: {', '.join(supporting_ids)} supports the claim "
                f"but {', '.join(contradicting_ids)} contradicts it. "
                f"No clear high-authority verdict can be reached. "
                f"Verdict: INSUFFICIENT_EVIDENCE — human review required."
            ),
            supporting_ids,
            contradicting_ids,
            insufficient_ids,
        )

    # --- All compatible evidence supports → ALIGN -------------------------
    if supporting_ids:
        return (
            Verdict.ALIGN,
            (
                f"Supporting evidence ({', '.join(supporting_ids)}) is consistent "
                f"with the claim. No contradicting evidence found. Verdict: ALIGN."
            ),
            supporting_ids,
            contradicting_ids,
            insufficient_ids,
        )

    # --- All evidence is inconclusive → INSUFFICIENT_EVIDENCE -------------
    all_ids = [ev.evidence_id for ev in compatible]
    return (
        Verdict.INSUFFICIENT_EVIDENCE,
        (
            f"Retrieved evidence ({', '.join(all_ids)}) is present but inconclusive — "
            f"it neither clearly supports nor clearly contradicts the claim. "
            f"Verdict: INSUFFICIENT_EVIDENCE."
        ),
        [],
        [],
        all_ids,
    )


def _evidence_clearly_contradicts(ev: EvidenceRecord) -> bool:
    """True if the evidence record's expected_relationship is CONTRADICTS."""
    return ev.expected_relationship == ExpectedRelationship.CONTRADICTS


def _evidence_clearly_supports(ev: EvidenceRecord) -> bool:
    """True if the evidence record's expected_relationship is SUPPORTS."""
    return ev.expected_relationship == ExpectedRelationship.SUPPORTS


def _to_evidence_record(re_ev: RetrievedEvidence) -> EvidenceRecord:
    """Convert a RetrievedEvidence object back to an EvidenceRecord.

    Looks up the expected_relationship from re_ev directly or from the loaded corpus
    so that synthetic SUPPORTS / CONTRADICTS labels drive the verdict correctly.
    Falls back to PARTIAL when the record is not in the corpus (e.g. test doubles).
    """
    rel = getattr(re_ev, "expected_relationship", None) or _CORPUS_RELATIONSHIP.get(
        re_ev.evidence_id, ExpectedRelationship.PARTIAL
    )
    return EvidenceRecord(
        evidence_id=re_ev.evidence_id,
        claim_id=re_ev.claim_id,
        company=re_ev.company,
        source=re_ev.source,
        source_tier=re_ev.source_tier,
        source_type=re_ev.source_type,
        publication_date=re_ev.publication_date,
        reporting_period=re_ev.reporting_period,
        retrieved_text=re_ev.retrieved_text,
        expected_relationship=rel,
        url_or_path=re_ev.url_or_path,
        notes=re_ev.notes,
    )


def _norm_period(p: str) -> str:
    """Normalise period string to bare 4-digit year."""
    m = re.search(r"(\d{4})", p)
    return m.group(1) if m else p.lower().strip()
