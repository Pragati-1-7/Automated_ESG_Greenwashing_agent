"""
pipeline.py

STEP 6: End-to-end orchestration layer connecting the existing Steps 1-5
backend intelligence to the FastAPI/Streamlit application.

This module does NOT re-implement any backend logic. It only calls, in
order, the functions and classes that already exist:

    pdf_parser.parse_pdf
    claim_extractor.extract_claims_from_pages
    checkability.assess_checkability / filter_checkable
    retrieval.hybrid_retriever.HybridRetriever
    evaluation.verification.verify_claim
    scoring.risk_score.calculate_risk_score

IMPORTANT: results are TRIAGE INDICATORS for human review, never a legal
determination of greenwashing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.utils.schemas import AuditRecord, ClaimRecord, Verdict, Checkability
from app.extraction.pdf_parser import parse_pdf, PDFParsingError
from app.extraction.claim_extractor import extract_claims_from_pages
from app.extraction.llm_providers import get_provider, LLMConfigurationError
from app.evaluation.checkability import assess_checkability, filter_checkable
from app.retrieval.hybrid_retriever import HybridRetriever
from app.evaluation.verification import verify_claim
from app.scoring.risk_score import calculate_risk_score

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SAMPLE_PDF_PATH = PROJECT_ROOT / "data" / "sample_pdfs" / "synthetic_esg_report.pdf"
SAMPLE_PDF_FILENAME = SAMPLE_PDF_PATH.name
CLAIMS_DATASET_PATH = PROJECT_ROOT / "data" / "claims" / "claims.json"

DEMO_COMPANY_NAME = "GreenLeaf Industries Ltd. (synthetic demo company)"

SYNTHETIC_EVIDENCE_NOTICE = (
    "Current demonstration uses a synthetic evidence corpus. Real deployment "
    "would connect the retrieval layer to verified external ESG/regulatory sources."
)
TRIAGE_DISCLAIMER = (
    "This tool provides evidence-based triage and decision support. It does not "
    "constitute a legal determination of greenwashing."
)


class PipelineError(Exception):
    """Raised for pipeline-level failures that should surface as a clean API error."""


# ---------------------------------------------------------------------------
# Core orchestration: ClaimRecord list -> list[AuditRecord]
# ---------------------------------------------------------------------------


def build_audit_records(
    claims: list[ClaimRecord],
    top_k: int = 5,
    use_semantic: bool = False,
) -> list[AuditRecord]:
    """Run every existing Step 3-5 stage over a list of claims and return one
    AuditRecord per claim (including NOT_CHECKABLE claims, so the dashboard
    can show why a claim was excluded from evidence retrieval).
    """
    checkable, not_checkable = filter_checkable(claims)
    records: list[AuditRecord] = []

    for claim in not_checkable:
        cr = assess_checkability(claim)
        records.append(
            AuditRecord(
                claim_id=claim.claim_id,
                claim_text=claim.original_text,
                company=claim.company,
                checkability_result=cr,
            )
        )

    if checkable:
        retriever = HybridRetriever(use_semantic=use_semantic)
        for claim in checkable:
            cr = assess_checkability(claim)
            rr = retriever.retrieve_for_claim(claim, top_k=top_k)
            vr = verify_claim(claim, rr)
            rs = calculate_risk_score(vr)
            records.append(
                AuditRecord(
                    claim_id=claim.claim_id,
                    claim_text=claim.original_text,
                    company=claim.company,
                    checkability_result=cr,
                    retrieval_result=rr,
                    verification_result=vr,
                    risk_score_result=rs,
                )
            )

    # Preserve original claim order for a stable, readable table.
    order = {c.claim_id: i for i, c in enumerate(claims)}
    records.sort(key=lambda r: order.get(r.claim_id, 0))
    return records


def summarize(records: list[AuditRecord]) -> dict:
    """Aggregate report-level statistics used by the Executive Summary."""
    total = len(records)
    checkable = sum(
        1
        for r in records
        if r.checkability_result and r.checkability_result.checkability == Checkability.CHECKABLE
    )
    not_checkable = total - checkable

    verdict_counts = {v.value: 0 for v in Verdict if v != Verdict.NOT_APPLICABLE}
    scores = []
    for r in records:
        if r.verification_result:
            verdict_counts[r.verification_result.verdict.value] = (
                verdict_counts.get(r.verification_result.verdict.value, 0) + 1
            )
        if r.risk_score_result:
            scores.append(r.risk_score_result.risk_score)

    average_risk_score = round(sum(scores) / len(scores), 1) if scores else None

    return {
        "total_claims": total,
        "checkable_claims": checkable,
        "not_checkable_claims": not_checkable,
        "align_count": verdict_counts.get("ALIGN", 0),
        "contradict_count": verdict_counts.get("CONTRADICT", 0),
        "insufficient_evidence_count": verdict_counts.get("INSUFFICIENT_EVIDENCE", 0),
        "average_risk_score": average_risk_score,
        "claims_scored": len(scores),
    }


# ---------------------------------------------------------------------------
# PDF entry point
# ---------------------------------------------------------------------------


def analyze_pdf_file(
    pdf_path: Path,
    company_hint: Optional[str] = None,
    mode: str = "mock",
    top_k: int = 5,
    use_semantic: bool = False,
    is_bundled_sample: bool = False,
) -> dict:
    """Run the complete Step 6 pipeline (PDF -> risk score) for one PDF file.

    Returns a plain dict (JSON-serialisable) rather than raising for expected,
    human-facing conditions (empty PDF, no claims extracted, no checkable
    claims) -- see Part 7 of the Step 6 spec. Only unexpected/internal errors
    raise PipelineError.
    """
    try:
        pages = parse_pdf(pdf_path)
    except PDFParsingError as e:
        raise PipelineError(f"Could not read this PDF: {e}") from e

    non_empty_pages = [p for p in pages if p.text.strip()]
    if not non_empty_pages:
        return _empty_result(
            source_document=pdf_path.name,
            company=company_hint or "Unknown",
            page_count=len(pages),
            message=(
                "The PDF was parsed successfully but no extractable text was found "
                "(it may be a scanned/image-only document). No claims could be extracted."
            ),
        )

    # Choose the provider. Only the bundled sample PDF gets deterministic
    # canned mock claims (extract_claims_from_pages' own default); any other
    # PDF in mock mode correctly yields zero fabricated claims rather than
    # mismatched canned text stamped onto the wrong document.
    if mode == "mock":
        provider = None if is_bundled_sample else get_provider("mock")
    else:
        try:
            provider = get_provider(mode)
        except LLMConfigurationError as e:
            raise PipelineError(str(e)) from e

    company = company_hint or (DEMO_COMPANY_NAME if is_bundled_sample else "Unknown")

    extraction_results = extract_claims_from_pages(pages, provider=provider, company_hint=company)
    claims: list[ClaimRecord] = [c for r in extraction_results for c in r.claims]
    extraction_errors = [e for r in extraction_results for e in r.errors]

    if not claims:
        return _empty_result(
            source_document=pdf_path.name,
            company=company,
            page_count=len(pages),
            message=(
                "No ESG claims could be extracted from this document in the current mode. "
                "Try 'Use Demo ESG Report', or configure a real LLM provider (Groq/Ollama) "
                "for non-sample PDFs."
            ),
            extraction_errors=extraction_errors,
        )

    records = build_audit_records(claims, top_k=top_k, use_semantic=use_semantic)
    return {
        "status": "ok",
        "source_document": pdf_path.name,
        "company": company,
        "page_count": len(pages),
        "extraction_errors": extraction_errors,
        "summary": summarize(records),
        "audit_records": [r.model_dump(mode="json") for r in records],
        "synthetic_evidence_notice": SYNTHETIC_EVIDENCE_NOTICE,
        "disclaimer": TRIAGE_DISCLAIMER,
    }


def _empty_result(
    source_document: str,
    company: str,
    page_count: int,
    message: str,
    extraction_errors: Optional[list[str]] = None,
) -> dict:
    return {
        "status": "no_claims",
        "source_document": source_document,
        "company": company,
        "page_count": page_count,
        "message": message,
        "extraction_errors": extraction_errors or [],
        "summary": summarize([]),
        "audit_records": [],
        "synthetic_evidence_notice": SYNTHETIC_EVIDENCE_NOTICE,
        "disclaimer": TRIAGE_DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Curated-dataset entry point (data/claims/claims.json) — used by the
# "full dataset" demo, which reliably shows ALIGN / CONTRADICT /
# INSUFFICIENT_EVIDENCE examples because its evidence corpus was authored
# to match it.
# ---------------------------------------------------------------------------


def load_dataset_claims() -> list[ClaimRecord]:
    import json

    raw = json.loads(CLAIMS_DATASET_PATH.read_text(encoding="utf-8"))
    return [ClaimRecord(**c) for c in raw["claims"]]


def analyze_dataset(
    claim_ids: Optional[list[str]] = None,
    top_k: int = 5,
    use_semantic: bool = False,
) -> dict:
    all_claims = load_dataset_claims()
    if claim_ids:
        all_claims = [c for c in all_claims if c.claim_id in claim_ids]
        if not all_claims:
            raise PipelineError(f"No claims found matching {claim_ids}")

    records = build_audit_records(all_claims, top_k=top_k, use_semantic=use_semantic)
    return {
        "status": "ok",
        "source_document": "data/claims/claims.json (curated synthetic dataset)",
        "company": "Multiple synthetic companies",
        "page_count": None,
        "extraction_errors": [],
        "summary": summarize(records),
        "audit_records": [r.model_dump(mode="json") for r in records],
        "synthetic_evidence_notice": SYNTHETIC_EVIDENCE_NOTICE,
        "disclaimer": TRIAGE_DISCLAIMER,
    }
