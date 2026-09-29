"""
main.py

STEP 6: FastAPI backend exposing the existing Steps 1-5 pipeline to the
Streamlit dashboard.

Endpoints
---------
GET  /health                    liveness/status check
POST /analyze                   upload a PDF (or use_demo=true) and run the
                                 full pipeline, returning claims + audit trail
GET  /demo/dataset               run the curated data/claims/claims.json
                                 dataset (guaranteed ALIGN/CONTRADICT/
                                 INSUFFICIENT_EVIDENCE examples for demos)
GET  /claims/{claim_id}          look up one claim's full audit record in the
                                 curated dataset

This module contains NO business logic of its own -- it only validates
input, calls app.api.pipeline, and shapes HTTP responses/errors.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.api.pipeline import (
    analyze_pdf_file,
    analyze_dataset,
    build_audit_records,
    load_dataset_claims,
    PipelineError,
    SAMPLE_PDF_PATH,
    SAMPLE_PDF_FILENAME,
    DEMO_COMPANY_NAME,
    SYNTHETIC_EVIDENCE_NOTICE,
    TRIAGE_DISCLAIMER,
)

app = FastAPI(
    title="ESG Claim Verification & Greenwashing Risk Analyzer API",
    description=(
        "Decision-support / triage API for detecting potentially misleading ESG "
        "claims. This is NOT a legal determination of greenwashing."
    ),
    version="1.0.0",
)

# Local-only academic demo: Streamlit (typically :8501) calls this API (:8000).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "esg-greenwashing-agent-api",
        "disclaimer": TRIAGE_DISCLAIMER,
    }


@app.post("/analyze")
async def analyze(
    file: Optional[UploadFile] = File(default=None),
    company: Optional[str] = Form(default=None),
    use_demo: bool = Form(default=False),
    mode: str = Form(default="mock"),
    top_k: int = Form(default=5),
    use_semantic: bool = Form(default=False),
) -> dict:
    """Accept an uploaded ESG PDF (or use_demo=true) and run the full pipeline."""
    if not use_demo and file is None:
        raise HTTPException(status_code=400, detail="Provide a PDF file or set use_demo=true.")

    if use_demo or file is None:
        if not SAMPLE_PDF_PATH.exists():
            raise HTTPException(
                status_code=500, detail="Bundled demo PDF is missing from the server."
            )
        pdf_path = SAMPLE_PDF_PATH
        is_bundled_sample = True
        tmp_path = None
    else:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp.write(contents)
        tmp.close()
        tmp_path = Path(tmp.name)
        pdf_path = tmp_path
        is_bundled_sample = file.filename == SAMPLE_PDF_FILENAME

    try:
        result = analyze_pdf_file(
            pdf_path=pdf_path,
            company_hint=company,
            mode=mode,
            top_k=top_k,
            use_semantic=use_semantic,
            is_bundled_sample=is_bundled_sample,
        )
        if is_bundled_sample:
            result["source_document"] = SAMPLE_PDF_FILENAME
            result.setdefault("company", DEMO_COMPANY_NAME)
        else:
            # analyze_pdf_file only sees the server-side temp file path; restore
            # the real uploaded filename the user actually sees in the response.
            result["source_document"] = file.filename
        return result
    except PipelineError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {e}") from e
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)


@app.get("/demo/dataset")
def demo_dataset(top_k: int = 5, use_semantic: bool = False) -> dict:
    """Run the curated synthetic dataset (data/claims/claims.json) so a
    professor can reliably see ALIGN, CONTRADICT, and INSUFFICIENT_EVIDENCE
    examples without depending on PDF extraction matching the evidence corpus.
    """
    try:
        return analyze_dataset(top_k=top_k, use_semantic=use_semantic)
    except PipelineError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@app.get("/claims/{claim_id}")
def get_claim(claim_id: str) -> dict:
    """Return the full audit record for one claim_id in the curated dataset."""
    try:
        claims = load_dataset_claims()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Could not load dataset: {e}") from e

    if not any(c.claim_id == claim_id for c in claims):
        raise HTTPException(
            status_code=404, detail=f"Claim '{claim_id}' not found in the curated dataset."
        )

    records = build_audit_records(claims, top_k=5, use_semantic=False)
    match = next((r for r in records if r.claim_id == claim_id), None)
    if match is None:
        raise HTTPException(status_code=404, detail=f"Claim '{claim_id}' not found.")
    return {
        "audit_record": match.model_dump(mode="json"),
        "synthetic_evidence_notice": SYNTHETIC_EVIDENCE_NOTICE,
        "disclaimer": TRIAGE_DISCLAIMER,
    }
