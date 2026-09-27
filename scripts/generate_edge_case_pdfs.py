"""
generate_edge_case_pdfs.py

STEP 6: Generates a small set of SYNTHETIC edge-case PDFs for manually
testing the "Upload ESG PDF" flow in the Streamlit dashboard and for the
automated edge-case tests in tests/test_edge_cases.py.

None of these are real ESG reports. Each one is built to exercise one
specific error-handling / boundary path described in docs/DEMO_FLOW.md and
Part 7 of the project spec ("Error Handling").

HOW TO RUN
----------
    python scripts/generate_edge_case_pdfs.py

Writes into data/sample_pdfs/edge_cases/. Also committed to the repo so
tests don't need to regenerate them, but kept reproducible here.
"""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "data" / "sample_pdfs" / "edge_cases"


def _write_text_pdf(filename: str, paragraphs: list[str]) -> Path:
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    for para in paragraphs:
        if para == "":
            pdf.ln(4)
            continue
        pdf.multi_cell(0, 7, para)
        pdf.ln(2)
    out_path = OUT_DIR / filename
    pdf.output(str(out_path))
    return out_path


def generate_blank_pdf() -> Path:
    """A PDF with pages but zero extractable text (simulates a scanned/
    image-only report). Expected behavior: pipeline reports
    'no extractable text was found'."""
    pdf = FPDF(format="A4")
    pdf.add_page()
    pdf.add_page()
    out_path = OUT_DIR / "blank_scanned_report.pdf"
    pdf.output(str(out_path))
    return out_path


def generate_unrelated_content_pdf() -> Path:
    """A real, readable PDF that contains no ESG claims at all. Expected
    behavior: pipeline reports 'No ESG claims could be extracted'."""
    return _write_text_pdf(
        "unrelated_content.pdf",
        [
            "COMPANY PICNIC NEWSLETTER",
            "",
            "This document is a synthetic test fixture with no ESG content "
            "whatsoever, used to verify that the pipeline correctly reports "
            "zero extracted claims instead of fabricating any.",
            "",
            "The picnic will be held on the first Saturday of next month. "
            "Please bring a dish to share. There will be games for children "
            "and a raffle with prizes donated by local businesses.",
        ],
    )


def generate_corrupted_pdf() -> Path:
    """A file with a .pdf extension that is NOT a valid PDF (garbage bytes).
    Expected behavior: PDFParsingError -> HTTP 422 with a clear message."""
    out_path = OUT_DIR / "corrupted_not_a_real_pdf.pdf"
    out_path.write_bytes(b"%PDF-1.4\nTHIS IS NOT VALID PDF CONTENT... %%garbage garbage garbage")
    return out_path


def generate_renamed_sample_pdf() -> Path:
    """A byte-for-byte copy of the bundled sample PDF under a DIFFERENT
    filename. Expected behavior in mock mode: zero claims extracted, because
    the mock provider only returns its canned claims for the exact bundled
    filename -- it must never guess that a differently-named file is the
    sample report. This is intentional, documented behavior (see
    app/api/pipeline.py: analyze_pdf_file), not a bug."""
    sample = PROJECT_ROOT / "data" / "sample_pdfs" / "synthetic_esg_report.pdf"
    out_path = OUT_DIR / "renamed_sample_report.pdf"
    out_path.write_bytes(sample.read_bytes())
    return out_path


def generate_large_multi_page_pdf() -> Path:
    """A longer (12-page) synthetic report to sanity-check that page-aware
    parsing and the dashboard's page count display scale beyond a handful
    of pages. Also mock mode -> zero claims (different filename)."""
    paragraphs: list[str] = []
    for i in range(1, 13):
        paragraphs.extend(
            [
                f"SECTION {i}: GENERIC SUSTAINABILITY DISCUSSION",
                "",
                "This is a synthetic filler section used only to test multi-page "
                "PDF parsing performance and page-number traceability. It does "
                "not contain any specific, checkable ESG claim.",
                "",
            ]
        )
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    for i in range(0, len(paragraphs), 4):
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        for para in paragraphs[i : i + 4]:
            if para == "":
                pdf.ln(4)
                continue
            pdf.multi_cell(0, 7, para)
            pdf.ln(2)
    out_path = OUT_DIR / "large_multi_page_report.pdf"
    pdf.output(str(out_path))
    return out_path


def generate() -> list[Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    return [
        generate_blank_pdf(),
        generate_unrelated_content_pdf(),
        generate_corrupted_pdf(),
        generate_renamed_sample_pdf(),
        generate_large_multi_page_pdf(),
    ]


if __name__ == "__main__":
    paths = generate()
    print("Generated edge-case PDFs:")
    for p in paths:
        print(f"  - {p.relative_to(PROJECT_ROOT)}")
