"""
test_pipeline.py

STEP 6 tests: end-to-end orchestration layer (app/api/pipeline.py).

These tests never call a real LLM or the network -- they use the bundled
mock provider / sample PDF and the curated synthetic dataset, exactly like
the rest of the test suite.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.api.pipeline import (
    analyze_dataset,
    analyze_pdf_file,
    build_audit_records,
    load_dataset_claims,
    summarize,
    SAMPLE_PDF_PATH,
    PipelineError,
)
from app.utils.schemas import AuditRecord


def test_load_dataset_claims_returns_all_claims():
    claims = load_dataset_claims()
    assert len(claims) == 12
    assert all(c.claim_id.startswith("CLM-") for c in claims)


def test_build_audit_records_covers_every_claim():
    claims = load_dataset_claims()
    records = build_audit_records(claims, top_k=5, use_semantic=False)
    assert len(records) == len(claims)
    assert all(isinstance(r, AuditRecord) for r in records)
    # Every record has a checkability result; not-checkable ones lack verification.
    for r in records:
        assert r.checkability_result is not None
        if r.checkability_result.checkability.value == "NOT_CHECKABLE":
            assert r.verification_result is None
            assert r.risk_score_result is None


def test_summarize_counts_match_records():
    claims = load_dataset_claims()
    records = build_audit_records(claims, top_k=5, use_semantic=False)
    summary = summarize(records)
    assert summary["total_claims"] == len(records)
    assert summary["checkable_claims"] + summary["not_checkable_claims"] == len(records)
    verdict_total = (
        summary["align_count"]
        + summary["contradict_count"]
        + summary["insufficient_evidence_count"]
    )
    assert verdict_total == summary["checkable_claims"]


def test_analyze_dataset_end_to_end():
    result = analyze_dataset(top_k=5, use_semantic=False)
    assert result["status"] == "ok"
    assert result["summary"]["total_claims"] == 12
    assert len(result["audit_records"]) == 12
    assert "disclaimer" in result
    assert "synthetic_evidence_notice" in result


def test_analyze_dataset_with_unknown_claim_id_raises():
    with pytest.raises(PipelineError):
        analyze_dataset(claim_ids=["CLM-DOES-NOT-EXIST"])


def test_analyze_dataset_filters_to_requested_claims():
    result = analyze_dataset(claim_ids=["CLM-001"], top_k=5, use_semantic=False)
    assert len(result["audit_records"]) == 1
    assert result["audit_records"][0]["claim_id"] == "CLM-001"


def test_analyze_pdf_file_sample_pdf_extracts_claims():
    assert SAMPLE_PDF_PATH.exists(), "Bundled sample PDF must exist for this test"
    result = analyze_pdf_file(
        pdf_path=SAMPLE_PDF_PATH,
        company_hint="GreenLeaf Industries Ltd.",
        mode="mock",
        top_k=3,
        use_semantic=False,
        is_bundled_sample=True,
    )
    assert result["status"] == "ok"
    assert result["summary"]["total_claims"] > 0


def test_analyze_pdf_file_nonexistent_path_raises():
    with pytest.raises(PipelineError):
        analyze_pdf_file(
            pdf_path=Path("this_file_does_not_exist.pdf"),
            company_hint="Nobody",
            mode="mock",
            is_bundled_sample=False,
        )


def test_analyze_pdf_file_non_sample_mock_mode_reports_no_claims(tmp_path):
    """An arbitrary (non-bundled) PDF in mock mode must never be silently
    stamped with the sample PDF's canned claims -- it should honestly report
    that no claims were extracted."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, "This is an unrelated test document with no ESG claims format.")
    out_path = tmp_path / "unrelated.pdf"
    pdf.output(str(out_path))

    result = analyze_pdf_file(
        pdf_path=out_path,
        company_hint="Some Other Company",
        mode="mock",
        is_bundled_sample=False,
    )
    assert result["status"] == "no_claims"
    assert result["summary"]["total_claims"] == 0
