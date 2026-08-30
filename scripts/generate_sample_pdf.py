"""
generate_sample_pdf.py

STEP 2 / Part 3: Generates the reproducible SYNTHETIC ESG test PDF used by
the extraction pipeline's tests and evaluation script.

WHY A GENERATED PDF INSTEAD OF A REAL COMPANY REPORT
-------------------------------------------------------
We need a PDF with KNOWN, exact claim text so we can evaluate extraction
quality against a ground-truth answer key (see data/sample_pdfs/expected_claims.json).
Using a real company's report would mean we don't actually know the "right"
answer, and could also raise attribution/usage concerns. So this script
builds a clearly-labelled FICTIONAL company report instead: "GreenLeaf
Industries Ltd." does not exist.

HOW TO RUN
----------
    python scripts/generate_sample_pdf.py

This overwrites data/sample_pdfs/synthetic_esg_report.pdf. The generated
PDF is also committed to the repo so the test suite does not require
regenerating it, but this script keeps it reproducible if it ever needs
to change.
"""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = PROJECT_ROOT / "data" / "sample_pdfs" / "synthetic_esg_report.pdf"

# Each page's paragraphs, in reading order. Blank strings become spacing.
# NOTE: these sentences are duplicated in app/extraction/mock_data.py so the
# mock extraction provider can return the exact expected original_text for
# each claim -- if you change wording here, update mock_data.py and
# data/sample_pdfs/expected_claims.json to match.
PAGES: list[list[str]] = [
    # Page 1 - Cover / Leadership message
    [
        "GREENLEAF INDUSTRIES LTD.",
        "SUSTAINABILITY REPORT - FY2024",
        "",
        "*** THIS IS A SYNTHETIC / FICTIONAL REPORT CREATED FOR SOFTWARE TESTING PURPOSES ONLY. ***",
        "*** GreenLeaf Industries Ltd. is not a real company. All figures, targets, and statements",
        "    in this document are fabricated and must not be treated as real ESG disclosures. ***",
        "",
        "Message from Leadership",
        "",
        "Sustainability remains at the heart of everything we do, and we continue to strive for "
        "a greener tomorrow. This report summarizes our environmental, social, and governance "
        "performance for the financial year 2024.",
    ],
    # Page 2 - Environmental
    [
        "Environmental Performance",
        "",
        "In FY2024, GreenLeaf Industries Ltd. reduced its Scope 1 greenhouse gas emissions by 18% "
        "compared to a 2019 baseline, from 42,000 tCO2e to 34,440 tCO2e at the company-wide level.",
        "",
        "During FY2024, 32% of the electricity consumed at our manufacturing facilities was "
        "sourced from renewable energy.",
        "",
        "We recycled 8,500 tonnes of industrial waste in FY2024, up from 6,200 tonnes in FY2023.",
        "",
        "We engaged with 65% of our key suppliers, by procurement spend, to assess Scope 3 "
        "emissions across our value chain in FY2024.",
    ],
    # Page 3 - Social
    [
        "Social Performance",
        "",
        "As of March 2024, women comprised 27% of our total workforce, up from 19% in 2019.",
        "",
        "Employee lost-time injury frequency rate improved by 12% during FY2024.",
    ],
    # Page 4 - Governance & Outlook
    [
        "Governance & Outlook",
        "",
        "GreenLeaf Industries Ltd. maintained zero regulatory non-compliance notices from the "
        "Ministry of Environment, Forest and Climate Change during FY2024.",
        "",
        "We are committed to achieving net-zero Scope 1 and Scope 2 emissions by 2040.",
        "",
        "Our governance framework is built on the principles of transparency, accountability, "
        "and stakeholder trust.",
    ],
]


def generate() -> Path:
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)

    for page_paragraphs in PAGES:
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        for para in page_paragraphs:
            if para == "":
                pdf.ln(4)
                continue
            pdf.multi_cell(0, 7, para)
            pdf.ln(2)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUTPUT_PATH))
    return OUTPUT_PATH


if __name__ == "__main__":
    out = generate()
    print(f"Generated synthetic ESG report: {out}")
