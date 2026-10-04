"""Verify the generated PDFs and write data/reports/manifest.json.

For each company: every spec claim sentence must be found VERBATIM (whitespace-normalised only) exactly
once by BOTH pdfplumber and PyMuPDF, on the same page. Also sanity-checks page counts, the Vajra
hidden-number rules, the absence of em dashes and the fictional-company footer line.
"""
from __future__ import annotations
import json
import re
import sys
import unicodedata
import warnings

warnings.filterwarnings("ignore")
import logging
import fitz
import pdfplumber
logging.getLogger('pdfminer').setLevel(logging.ERROR)

from . import data
from .build_reports import FILES, OUT

TITLES = {k: data.company(k)["report_title"] for k in FILES}
PAGE_RANGE = {"vajra": (24, 30), "sahyadri": (24, 30), "kaveri": (24, 30), "aurelia": (20, 24)}
FOOTER_LINE = "Fictional company. Generated for an academic ESG verification demo."

# Vajra: true values for metrics whose claims are NOT aligned must not be printed anywhere.
VAJRA_FORBIDDEN = [r"10,856", r"10\.86", r"10\.856", r"10856", r"72,08", r"72\.08", r"7[12],?080", r"(?<![\d.])0\.41(?!\d)", r"(?<![\d.])18\.0\s*%",
                   r"(?<![\d.])18\s*(%|per cent)", r"1,380,000", r"1\.38 ?Mt", r"310,000", r"2\.1 million", r"126\.4", r"4\.2 crore",
                   r"11,?800,?000", r"11\.8 ?Mt", r"68\.0 ?million", r"Independent Assurer", r"limited assurance"]


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", s)).strip()


def page_texts(path):
    with pdfplumber.open(str(path)) as pdf:
        plumb = [norm(pg.extract_text() or "") for pg in pdf.pages]
    d = fitz.open(str(path))
    mu = [norm(pg.get_text()) for pg in d]
    return plumb, mu


def locate(pages, claim):
    """Return (count_in_document, first_page_1based or None). Page-boundary safe."""
    joined = " ".join(pages)
    count = joined.count(claim)
    first = None
    for i, t in enumerate(pages, 1):
        if claim in t:
            first = i
            break
    if first is None and count:
        pos = joined.index(claim)
        acc = 0
        for i, t in enumerate(pages, 1):
            acc += len(t) + 1
            if pos < acc:
                first = i
                break
    return count, first


def verify_all(write_manifest: bool = True, quiet: bool = False) -> bool:
    ok = True
    manifest = []
    for key, fname in FILES.items():
        path = OUT / fname
        co = data.company(key)
        if not path.exists():
            print(f"[{key}] MISSING {path}")
            ok = False
            continue
        plumb, mu = page_texts(path)
        n = len(mu)
        lo, hi = PAGE_RANGE[key]
        problems = []
        if not (lo <= n <= hi):
            problems.append(f"page count {n} outside {lo}-{hi}")
        entries = []
        for c in co["claims"]:
            cl = norm(unicodedata.normalize("NFKC", c["text"]))
            cp, pp = locate(plumb, cl)
            cm, pm = locate(mu, cl)
            if cp != 1 or cm != 1:
                problems.append(f"{c['id']}: occurrences pdfplumber={cp} pymupdf={cm} (need exactly 1 each)")
            elif pp != pm:
                problems.append(f"{c['id']}: page mismatch pdfplumber={pp} pymupdf={pm}")
            entries.append({"id": c["id"], "page": pm})
            if not quiet:
                print(f"  {c['id']}: pdfplumber p{pp} x{cp} | pymupdf p{pm} x{cm}")
        d = fitz.open(str(path))
        for i in range(2, n - 1):
            ys = [b[3] for b in d[i].get_text('blocks') if b[3] < 780]
            if ys and max(ys) < 330:
                print(f"   ! sparse page {i + 1} (content ends at y={int(max(ys))}pt)")
        alltext = " ".join(mu)
        if "—" in alltext:
            problems.append("em dash present")
        if FOOTER_LINE not in mu[-1]:
            problems.append("fictional footer line missing on last page")
        if key == "vajra":
            for pat in VAJRA_FORBIDDEN:
                m = re.search(pat, alltext, flags=re.I)
                if m:
                    problems.append(f"forbidden Vajra content matched /{pat}/ near '{alltext[max(0, m.start()-40):m.end()+40]}'")
        if key != "aurelia":
            pass
        status = "PASS" if not problems else "FAIL"
        print(f"[{key}] {fname}: {n} pages, {len(entries)} claims -> {status}")
        for pr in problems:
            print("   -", pr)
        ok &= not problems
        manifest.append({"key": key, "filename": fname, "title": TITLES[key], "company": co["name"], "company_id": co["company_id"],
                         "profile": co["profile"], "pages": n, "claims": entries})
    if write_manifest:
        (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return ok


if __name__ == "__main__":
    sys.exit(0 if verify_all() else 1)
