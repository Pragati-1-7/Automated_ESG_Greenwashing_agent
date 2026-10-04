"""Entry point:  python3 -m report_gen.build_reports [key ...]

Builds the four fictional reports into data/reports/ and then runs the verifier,
which also writes data/reports/manifest.json.
"""
from __future__ import annotations
import importlib
import re
import sys
from pathlib import Path

import fitz
from playwright.sync_api import sync_playwright

from . import layout, data, charts, india_map
from .context import Ctx, BUILD

OUT = data.ROOT / "data" / "reports"
FILES = {
    "vajra": "vajra_steel_sr_fy2025.pdf",
    "sahyadri": "sahyadri_cement_iar_fy2025.pdf",
    "kaveri": "kaveri_threads_brsr_fy2025.pdf",
    "aurelia": "aurelia_renewables_sr_2025.pdf",
}
ART = {"vajra": "steel", "sahyadri": "cement", "kaveri": "thread", "aurelia": "solar"}


def _browser(p):
    try:
        return p.chromium.launch()
    except Exception:
        return p.chromium.launch(executable_path="/opt/pw-browsers/chromium")


def _assemble(ctx, chapters, pages):
    """Return full body HTML. pages: {chapter_number: page} (empty on first pass)."""
    art = ctx.img("cover_art.png")
    parts = [layout.cover(ctx, art)]
    entries = []
    for i, ch in enumerate(chapters, 1):
        entries.append((f"{i:02d}", ch["title"], pages.get(f"{i:02d}", "-")))
    parts.append(layout.toc(entries, groups={g["at"]: g["label"] for g in ctx.toc_groups}))
    for i, ch in enumerate(chapters, 1):
        parts.append(layout.chapter(f"{i:02d}", ch["title"], ch["subtitle"], ch["body"], raw=ch.get("raw", False), cls=ch.get("cls", "")))
    parts.append(layout.back_cover(ctx, ctx.img("back_art.png")))
    return "".join(parts)


def _render(pw_browser, html_path: Path, pdf_path: Path):
    pg = pw_browser.new_page()
    pg.goto(html_path.as_uri())
    pg.wait_for_load_state("load")
    pg.pdf(path=str(pdf_path), prefer_css_page_size=True, print_background=True)
    pg.close()


def _find_pages(pdf_path: Path, n: int) -> dict:
    doc = fitz.open(str(pdf_path))
    out = {}
    for i in range(1, n + 1):
        tag = f"SECTION {i:02d}"
        for pno in range(2, len(doc)):  # skip cover + contents
            if tag in doc[pno].get_text():
                out[f"{i:02d}"] = pno + 1
                break
    return out


def build(key: str, browser) -> Path:
    ctx = Ctx(key)
    mod = importlib.import_module(f"report_gen.content_{key}")
    # visuals
    charts.cover_art(ctx.path("cover_art.png"), ART[key], ctx.pal)
    charts.cover_art(ctx.path("back_art.png"), ART[key], {**ctx.pal, "dark": ctx.pal["dark"]}, size=(8.27, 11.69))
    india_map.facility_map(ctx.path("map.png"), ctx.co["facilities"], ctx.pal)
    mod.make_charts(ctx)
    chapters = mod.chapters(ctx)
    ctx.check_claims_used()
    ctx.toc_groups = getattr(mod, "TOC_GROUPS", [])
    pages: dict = {}
    pdf = OUT / FILES[key]
    html_path = ctx.dir / f"{key}.html"
    for _ in range(3):
        html_path.write_text(layout.document(ctx, _assemble(ctx, chapters, pages)), encoding="utf-8")
        _render(browser, html_path, pdf)
        new = _find_pages(pdf, len(chapters))
        if new == pages:
            break
        pages = new
    n = len(fitz.open(str(pdf)))
    print(f"[{key}] {pdf.name}: {n} pages")
    return pdf


def main(argv=None):
    keys = (argv if argv is not None else sys.argv[1:]) or list(FILES)
    OUT.mkdir(parents=True, exist_ok=True)
    BUILD.mkdir(exist_ok=True)
    with sync_playwright() as p:
        b = _browser(p)
        for k in keys:
            build(k, b)
        b.close()
    from . import verify_reports
    ok = verify_reports.verify_all(write_manifest=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
