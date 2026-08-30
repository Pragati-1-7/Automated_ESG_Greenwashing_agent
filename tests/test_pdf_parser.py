"""
test_pdf_parser.py

STEP 2 / Part 13: automated tests for app/extraction/pdf_parser.py.

Covers:
- normal PDF parsing
- multiple-page PDF parsing
- empty PDF handling
- malformed PDF handling
- source/page preservation
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fpdf import FPDF

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.extraction.pdf_parser import PDFParsingError, PageText, parse_pdf  # noqa: E402

SAMPLE_PDF = PROJECT_ROOT / "data" / "sample_pdfs" / "synthetic_esg_report.pdf"


def _make_pdf(tmp_path: Path, pages_text: list[str], filename: str = "test.pdf") -> Path:
    pdf = FPDF()
    for text in pages_text:
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        if text:
            pdf.multi_cell(0, 10, text)
    out = tmp_path / filename
    pdf.output(str(out))
    return out


def test_normal_pdf_parsing(tmp_path: Path):
    path = _make_pdf(tmp_path, ["Hello ESG world."])
    pages = parse_pdf(path)
    assert len(pages) == 1
    assert isinstance(pages[0], PageText)
    assert pages[0].page_number == 1
    assert "Hello ESG world." in pages[0].text
    assert pages[0].source_document == path.name


def test_multiple_page_pdf_parsing(tmp_path: Path):
    path = _make_pdf(tmp_path, ["Page one text.", "Page two text.", "Page three text."])
    pages = parse_pdf(path)
    assert len(pages) == 3
    assert [p.page_number for p in pages] == [1, 2, 3]
    assert "Page one" in pages[0].text
    assert "Page two" in pages[1].text
    assert "Page three" in pages[2].text


def test_empty_page_handling(tmp_path: Path):
    # A page with no text content should still produce a PageText entry
    # with an empty string, not be dropped (so later page numbers stay correct).
    path = _make_pdf(tmp_path, ["Real content on page 1.", "", "Real content on page 3."])
    pages = parse_pdf(path)
    assert len(pages) == 3
    assert pages[1].text == ""
    assert pages[1].char_count == 0
    # Page numbers after the empty page are unaffected.
    assert pages[2].page_number == 3
    assert "page 3" in pages[2].text.lower()


def test_zero_page_pdf_raises(tmp_path: Path):
    pdf = FPDF()
    out = tmp_path / "empty.pdf"
    # FPDF requires at least one page to output bytes; simulate a
    # zero-page PDF scenario via a nonexistent/garbage file instead,
    # since a true zero-page PDF is not producible via fpdf2.
    out.write_bytes(b"%PDF-1.4\n%%EOF")
    with pytest.raises(PDFParsingError):
        parse_pdf(out)


def test_malformed_pdf_raises(tmp_path: Path):
    bad_path = tmp_path / "not_a_real.pdf"
    bad_path.write_bytes(b"this is definitely not a valid PDF file content")
    with pytest.raises(PDFParsingError):
        parse_pdf(bad_path)


def test_missing_file_raises(tmp_path: Path):
    missing = tmp_path / "does_not_exist.pdf"
    with pytest.raises(PDFParsingError):
        parse_pdf(missing)


def test_wrong_extension_raises(tmp_path: Path):
    txt_file = tmp_path / "not_a_pdf.txt"
    txt_file.write_text("hello")
    with pytest.raises(PDFParsingError):
        parse_pdf(txt_file)


def test_source_and_page_preserved_on_sample_pdf():
    assert SAMPLE_PDF.exists(), "Run scripts/generate_sample_pdf.py first."
    pages = parse_pdf(SAMPLE_PDF)
    assert len(pages) == 4
    for p in pages:
        assert p.source_document == "synthetic_esg_report.pdf"
        assert p.page_number >= 1
    assert "Environmental Performance" in pages[1].text
    assert "Social Performance" in pages[2].text
    assert "Governance" in pages[3].text
