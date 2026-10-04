"""
pdf_parser.py

STEP 2: PDF -> page-aware text.

WHY THIS FILE EXISTS
---------------------
Before we can extract ESG claims, we need to turn a PDF into plain text
while keeping track of WHICH PAGE each piece of text came from. Page
numbers matter later because every ClaimRecord must be traceable back to
its exact location in the source document (Part 10 of the Step 2 spec).

We use pdfplumber (not PyPDF2/pypdf) because it is more reliable at
preserving reading order and plain text layout for report-style PDFs,
which matters for getting clean sentences out of ESG reports.

WHAT THIS FILE DOES NOT DO
---------------------------
This module only reads a PDF and returns text. It does NOT call an LLM
and does NOT know what a "claim" is. That is app/extraction/claim_extractor.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Union

import pdfplumber


class PDFParsingError(Exception):
    """Raised when a PDF cannot be opened or read at all (e.g. corrupted file)."""


@dataclass
class PageText:
    """Page-aware text extracted from one page of a PDF.

    Attributes:
        page_number: 1-indexed page number (matches ClaimRecord.page_number).
        text: The raw extracted text of this page. May be an empty string
            if the page has no extractable text (e.g. a scanned image page).
        source_document: The filename (not full path) of the PDF this page
            came from, so it can be copied straight into ClaimRecord.source_document.
        char_count: Convenience field = len(text). Useful for sanity checks
            and for computing char_start/char_end offsets later.
    """

    page_number: int
    text: str
    source_document: str
    char_count: int


def parse_pdf(pdf_path: Union[str, Path]) -> list[PageText]:
    """Parse a PDF into a list of page-aware text objects.

    Args:
        pdf_path: Path to the PDF file on disk.

    Returns:
        A list of PageText, one entry per page, in page order (1-indexed).
        Pages with no extractable text still get an entry with text="" --
        we do NOT silently drop pages, because that would break page-number
        traceability for later pages (e.g. if page 3 is dropped, page 4's
        content would otherwise look like it came from page 3).

    Raises:
        PDFParsingError: if the file does not exist, is not a valid PDF,
            or pdfplumber fails to open it for any other reason.
    """
    path = Path(pdf_path)

    if not path.exists():
        raise PDFParsingError(f"PDF file not found: {path}")

    if path.suffix.lower() != ".pdf":
        raise PDFParsingError(f"Expected a .pdf file, got: {path.name}")

    source_document = path.name
    pages: list[PageText] = []

    try:
        with pdfplumber.open(path) as pdf:
            if len(pdf.pages) == 0:
                raise PDFParsingError(f"PDF has zero pages: {path.name}")

            for i, page in enumerate(pdf.pages, start=1):
                try:
                    raw_text = page.extract_text() or ""
                except Exception as page_error:  # noqa: BLE001
                    # A single malformed/empty page should not kill the whole
                    # parse -- record it as an empty page and keep going, so
                    # page numbers for the rest of the document stay correct.
                    raw_text = ""

                cleaned = raw_text.strip()
                pages.append(
                    PageText(
                        page_number=i,
                        text=cleaned,
                        source_document=source_document,
                        char_count=len(cleaned),
                    )
                )
    except PDFParsingError:
        raise
    except Exception as e:  # noqa: BLE001
        # Covers pdfplumber/pdfminer failures on corrupted/malformed PDFs.
        raise PDFParsingError(f"Failed to open/parse PDF '{path.name}': {e}") from e

    return pages


def combine_pages_text(pages: list[PageText]) -> str:
    """Utility: join all page texts into one string, with page markers.

    Not used by the extraction engine directly (extraction works page by
    page so page_number stays accurate), but useful for debugging/inspection.
    """
    parts = []
    for p in pages:
        parts.append(f"--- Page {p.page_number} ---\n{p.text}")
    return "\n\n".join(parts)
