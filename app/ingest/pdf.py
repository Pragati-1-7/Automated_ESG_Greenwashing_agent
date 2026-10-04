"""
app/ingest/pdf.py

PDF -> page-aware, section-aware sentences. No LLM. PyMuPDF layout blocks are
used so multi-column pages, sidebars, running headers and footers are handled.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pymupdf

from app.core.models import Sentence


class IngestError(Exception):
    pass


@dataclass
class Document:
    filename: str
    page_count: int
    sentences: list[Sentence]
    front_text: str          # first pages, used for company resolution


_ABBREV = r"(?<!\bRs\.)(?<!\bNo\.)(?<!\bLtd\.)(?<!\bPvt\.)(?<!\bCo\.)(?<!\be\.g\.)(?<!\bi\.e\.)(?<!\bvs\.)(?<!\bDr\.)(?<!\bMr\.)(?<!\bMs\.)(?<!\bSt\.)"
_SENT_SPLIT = re.compile(_ABBREV + r"(?<=[.!?])\s+(?=[A-Z0-9\"'(“])")


def _fix_spacing(text: str) -> str:
    """Display fonts sometimes extract as 'O ur   bi o di v e rs i ty'. If most
    tokens are 1-2 letters, treat runs of 2+ spaces as word breaks."""
    toks = text.split()
    if len(toks) >= 4 and sum(len(t) <= 2 for t in toks) / len(toks) > 0.5:
        words = re.split(r"\s{2,}", text.strip())
        return " ".join(w.replace(" ", "") for w in words)
    return text


def _clean(text: str) -> str:
    text = text.replace("­", "").replace("ﬁ", "fi").replace("ﬂ", "fl")
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    return re.sub(r"\s+", " ", text).strip()


def _looks_like_heading(text: str) -> bool:
    words = re.findall(r"[A-Za-z]{3,}", text)
    return len(words) >= 2 and not re.match(r"^(rs|inr|over|up to|\d)", text, re.I)


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT_SPLIT.split(text) if len(s.strip()) > 1]


def parse_pdf(path: str | Path) -> Document:
    path = Path(path)
    try:
        doc = pymupdf.open(path)
    except Exception as exc:  # noqa: BLE001 - surface any parser failure cleanly
        raise IngestError(f"Could not open PDF: {exc}") from exc
    if doc.page_count == 0:
        raise IngestError("PDF has no pages")

    sentences: list[Sentence] = []
    front: list[str] = []
    section: str | None = None
    pending: list | None = None   # [text, page, section, blocks_waited]
    dropcap: str | None = None
    n = 0
    for pno, page in enumerate(doc, start=1):
        h = page.rect.height
        blocks = page.get_text("dict")["blocks"]   # content-stream order = reading order for HTML-rendered PDFs
        body_size = 10.5
        dropcap = None
        for b in blocks:
            if b.get("type") != 0:
                continue
            spans = [s for line in b["lines"] for s in line["spans"] if s["text"].strip()]
            if not spans:
                continue
            raw = "\n".join(" ".join(s["text"] for s in line["spans"]) for line in b["lines"])
            text = _clean(_fix_spacing(raw.replace("\n", "  ")) if "  " in raw else raw)
            text = _clean(text)
            if not text:
                continue
            if pno <= 3:
                front.append(text)
            if re.fullmatch(r"[A-Z]", text):        # decorative drop cap
                dropcap = text
                continue
            if dropcap and text[:1].islower():
                text = dropcap + text
                dropcap = None
            y0, y1 = b["bbox"][1], b["bbox"][3]
            if y1 < 55 or y0 > h - 50:         # running header / footer
                continue
            size = max(s["size"] for s in spans)
            if len(text) < 90 and not text.endswith((".", ":")):
                if size >= body_size + 3 and _looks_like_heading(text):
                    section = re.sub(r"^(s\s*e\s*c\s*t\s*i\s*o\s*n|chapter)\s*\d+\s*", "", text, flags=re.I).strip() or section
                if len(text) < 70:
                    continue
            # Re-join a sentence that a column or page break cut in two.
            page_of_first = pno
            if pending and text[:1].islower():
                text = pending[0] + " " + text
                page_of_first = pending[1]
                pending = None
            elif pending:
                pending[3] += 1
                if pending[3] > 4:
                    sentences.append(Sentence(sid=f"S{(n := n + 1):04d}", text=pending[0], page=pending[1],
                                              section=pending[2]))
                    pending = None
            parts = split_sentences(text)
            if parts and not re.search(r"[.!?:;\"\u201d)]$", parts[-1]):
                if pending:
                    sentences.append(Sentence(sid=f"S{(n := n + 1):04d}", text=pending[0], page=pending[1],
                                              section=pending[2]))
                pending = [parts.pop(), page_of_first if not parts else pno, section, 0]
            for i, s in enumerate(parts):
                if len(s) < 25:
                    continue
                n += 1
                sentences.append(Sentence(sid=f"S{n:04d}", text=s, page=page_of_first if i == 0 else pno,
                                          section=section))
    if pending and len(pending[0]) >= 25:
        sentences.append(Sentence(sid=f"S{n + 1:04d}", text=pending[0], page=pending[1], section=pending[2]))
    if not sentences:
        raise IngestError("No extractable text found (the PDF may be scanned images).")
    return Document(filename=path.name, page_count=doc.page_count, sentences=sentences,
                    front_text=" ".join(front)[:6000])
