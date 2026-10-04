"""Builds docs/review/PS_coverage_review.pdf: the EY problem-statement screenshots
(ss1, ss2) marked up like meeting notes, showing what v2 covers."""
import base64, math, random
from pathlib import Path

HERE = Path(__file__).parent
random.seed(7)
GREEN, AMBER, INK = "#1a8f3c", "#d97706", "#1f3a8a"


def b64(p):
    return base64.b64encode((HERE / p).read_bytes()).decode()


def scribble_ellipse(x0, y0, x1, y1, color, w=2.6):
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rx, ry = (x1 - x0) / 2 + 10, (y1 - y0) / 2 + (5 if y1 - y0 < 20 else 8)
    paths = []
    for k in range(2):
        pts = []
        start = random.uniform(0, 0.6)
        n = 70
        for i in range(n + 8):
            t = start + 2 * math.pi * i / n
            j = 1 + random.uniform(-0.025, 0.025)
            pts.append((cx + rx * j * math.cos(t) + k * 2, cy + ry * j * math.sin(t) + k * 1.5))
        d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        paths.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w - k}" '
                     f'stroke-linecap="round" opacity="{0.85 - 0.25 * k}"/>')
    return "".join(paths)


def badge(x, y, n, color):
    return (f'<circle cx="{x}" cy="{y}" r="12" fill="{color}"/>'
            f'<text x="{x}" y="{y + 6}" text-anchor="middle" font-family="Caveat" font-weight="700" '
            f'font-size="21" fill="#fff">{n}</text>')


def tick(x, y, color):
    return (f'<path d="M{x},{y} l7,8 l15,-20" fill="none" stroke="{color}" stroke-width="3.5" '
            f'stroke-linecap="round" stroke-linejoin="round"/>')


def page(img, w, h, marks, title, subtitle, scale):
    svg = []
    for m in marks:
        col = GREEN if m["status"] == "done" else AMBER
        x0, y0, x1, y1 = m["box"]
        svg.append(scribble_ellipse(x0, y0, x1, y1, col))
        by = (y0 + y1) / 2
        svg.append(badge(22, by + m.get("dy", 0), m["n"], col))
        svg.append(tick(min(w - 26, x1 + 14), (y0 + y1) / 2 + 2, col) if m["status"] == "done" else
                   f'<text x="{min(w - 22, x1 + 14)}" y="{(y0 + y1) / 2 + 9}" font-family="Caveat" '
                   f'font-weight="700" font-size="30" fill="{col}">~</text>')
    notes = []
    for m in marks:
        col = GREEN if m["status"] == "done" else AMBER
        tag = "DONE" if m["status"] == "done" else "PARTLY"
        notes.append(f'''<div class="note"><div class="num" style="background:{col}">{m["n"]}</div>
<div><div class="nt"><span class="tag" style="color:{col};border-color:{col}">{tag}</span> {m["title"]}</div>
<div class="nb">{m["body"]}</div></div></div>''')
    return f'''<section class="page"><div class="hdr"><div class="h1">{title}</div><div class="h2">{subtitle}</div></div>
<div class="row"><div class="shot" style="width:{w * scale}px;height:{h * scale}px">
<img src="data:image/png;base64,{b64(img)}" style="width:{w * scale}px;height:{h * scale}px"/>
<svg viewBox="0 0 {w} {h}" style="width:{w * scale}px;height:{h * scale}px">{"".join(svg)}</svg></div>
<div class="notes">{"".join(notes)}</div></div></section>'''


SS1 = [
    {"n": 1, "status": "done", "box": (310, 225, 535, 238), "title": "Exaggerated / misleading claims",
     "body": "We plant 15 greenwashing types: inflated %, baseline shift, scope swap, unretired RECs, hidden penalty, fake zero-deforestation..."},
    {"n": 2, "status": "done", "box": (61, 255, 585, 327), "title": "Reports + PR vs real-world data, at scale",
     "body": "Reads 25-30 pg PDFs. Checks vs BRSR filings, NGT/SPCB orders, CPCB OCEMS, satellite forest alerts, REC registry, news. Company PR = tier 4, filings outweigh it."},
    {"n": 3, "status": "done", "box": (61, 381, 589, 439), "title": "Ingest, extract, search, score, audit trail",
     "body": "Upload PDF, 46/46 planted claims found, agents query 8 sources live, Risk Score 0-100, every tool call + decision logged with time."},
    {"n": 4, "status": "done", "box": (188, 492, 371, 505), "title": "Modular, agent-based",
     "body": "LangGraph: 11 agents, 1 file each. Each claim runs its own sub-graph in parallel (Send API)."},
    {"n": 5, "status": "partial", "box": (79, 567, 589, 610), "title": "LLM (Llama-3/Mistral) parses PDF + prompt eng.",
     "body": "PyMuPDF parses, Jev (typed decision model) picks claims, prompts versioned. Groq/Llama slot wired but OFF tonight (mock), so not Llama doing it."},
    {"n": 6, "status": "done", "box": (79, 672, 589, 712), "title": "LangChain + build queries + mock DBs/news/env data",
     "body": "LangGraph (LangChain family). Decomposer splits claim, router picks sources, investigator hits mock_sources API (REST + MCP). Never hardcoded."},
    {"n": 7, "status": "done", "box": (79, 716, 589, 745), "title": "Align / Contradict / Insufficient",
     "body": "Jev reads claim + evidence + calculator output, gives verdict with probabilities. Decision model, not a chat LLM: no maths in the model."},
    {"n": 8, "status": "done", "box": (79, 792, 585, 820), "title": "Algorithmic 0-100 risk score",
     "body": "Logistic model on Jev outputs, weights fitted on 140 train cases (AUC 0.99). Vajra 56 High, Sahyadri 45, Kaveri 34, unknown co 24."},
]
SS2 = [
    {"n": 9, "status": "done", "box": (88, 83, 598, 111), "title": "Transparent report",
     "body": "Per claim: text + page, evidence cards (tier + API endpoint), calc steps, reasoning. Report tab + full audit trail."},
    {"n": 10, "status": "done", "box": (88, 164, 594, 207), "title": "Repo + curated synthetic dataset",
     "body": "app/graph = orchestration. 150 cos, ~9.75K rows / 10 tables, 500 news articles, 200 labelled claims, 4 report PDFs."},
    {"n": 11, "status": "partial", "box": (88, 212, 598, 233), "title": "UI (Streamlit or Gradio)",
     "body": "Built in React instead: live agent trace (SSE), drill-down, verify-a-claim. Old Streamlit still runs, if jury insists."},
    {"n": 12, "status": "done", "box": (88, 239, 598, 267), "title": "2-3 pg technical summary",
     "body": "docs/TECHNICAL_SUMMARY (md + docx): agent design, prompt method, results, honest limitations."},
    {"n": 13, "dy": -7, "status": "done", "box": (251, 320, 447, 334), "title": "Agentic logic",
     "body": "Claim breaks into sub-claims, each typed + routed. Shown live in the trace."},
    {"n": 14, "dy": 8, "status": "done", "box": (217, 335, 447, 348), "title": "Accuracy + hallucination control",
     "body": "200 cases: 98%. No retrieval 35%, news-only RAG 45%. Relevance gate, citation check, abstains when no proof."},
    {"n": 15, "status": "done", "box": (217, 365, 535, 378), "title": "Code modularity",
     "body": "agents / tools / graph / ingest / decision split. 247 tests pass offline."},
    {"n": 16, "status": "done", "box": (211, 394, 379, 407), "title": "Business-ready output",
     "body": "Company score, top red flags with page refs, PDF report. Honest co not flagged."},
]

SCORE = '''<section class="page"><div class="hdr"><div class="h1">Scorecard: where we stand</div>
<div class="h2">14 of 16 marked points fully done, 2 partly. Nothing missing.</div></div>
<div class="score">
<div class="col"><div class="st" style="color:#1a8f3c">Done (14)</div><ul>
<li>Claim extraction from real-looking 23-28 pg PDFs: 46/46</li><li>Agents fetch evidence live over API (8 sources), REST + MCP</li>
<li>Align / Contradict / Insufficient with probabilities</li><li>Fitted 0-100 risk score + top red flags</li>
<li>Audit trail of every step, live on screen</li><li>LangGraph multi-agent, modular code</li>
<li>Synthetic dataset: 150 cos, ~9.75K rows, 200 test claims</li><li>2-3 pg technical summary</li>
<li>Benchmark 98%, ablations prove retrieval matters</li><li>247 tests, offline replay</li></ul></div>
<div class="col"><div class="st" style="color:#d97706">Partly (2)</div><ul>
<li><b>#5 LLM = Llama/Mistral:</b> decisions by Jev, Groq/Llama slot exists but was off. Fix: put Groq key, set LLM_PROVIDER=groq, rerun once.</li>
<li><b>#11 Streamlit/Gradio:</b> we chose React. Streamlit v1 still runs as backup.</li></ul>
<div class="st" style="color:#1f3a8a;margin-top:26px">Say it before they ask</div><ul>
<li>All data synthetic; test score 100% is optimistic (we saw test errors while fixing).</li>
<li>Chart-image claims not read, only text + tables.</li><li>Triage tool, not a legal verdict.</li></ul></div></div>
<div class="legend"><span style="color:#1a8f3c">&#10003; green = done</span> &nbsp;&nbsp; <span style="color:#d97706">~ amber = partly</span></div></section>'''

CSS = '''@page{size:A4 landscape;margin:0}
body{margin:0;font-family:'Kalam',cursive;color:#1f2937}
.page{width:1123px;height:794px;box-sizing:border-box;padding:22px 30px;page-break-after:always;background:#fffdf7;position:relative}
.hdr{display:flex;align-items:baseline;gap:18px;border-bottom:2px dashed #cbd5e1;padding-bottom:6px;margin-bottom:10px}
.h1{font-family:'Caveat';font-weight:700;font-size:38px;color:#1f3a8a}
.h2{font-family:'Caveat';font-size:24px;color:#6b7280}
.row{display:flex;gap:22px;align-items:flex-start}
.shot{position:relative;flex:none;box-shadow:0 2px 10px rgba(0,0,0,.18);transform:rotate(-0.4deg)}
.shot img,.shot svg{position:absolute;left:0;top:0}
.notes{flex:1;display:flex;flex-direction:column;gap:7px}
.note{display:flex;gap:9px;align-items:flex-start}
.num{flex:none;width:26px;height:26px;border-radius:50%;color:#fff;font-family:'Caveat';font-weight:700;font-size:20px;text-align:center;line-height:26px;margin-top:2px}
.nt{font-family:'Caveat';font-weight:700;font-size:23px;line-height:1.05;color:#111827}
.nb{font-size:13px;line-height:1.3;color:#374151}
.tag{font-family:'Kalam';font-size:11px;border:1.5px solid;border-radius:6px;padding:0 5px;vertical-align:3px}
.score{display:flex;gap:40px;padding:10px 20px}
.col{flex:1}.st{font-family:'Caveat';font-weight:700;font-size:34px}
.col ul{font-size:17px;line-height:1.5;padding-left:22px}
.legend{position:absolute;bottom:22px;left:50px;font-family:'Caveat';font-size:26px}'''

html = f'''<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Caveat:wght@400;700&family=Kalam:wght@400;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
{page("ss1.png", 650, 906, SS1, "Problem statement, page 1", "what v2 covers (green = done, amber = partly)", 0.81)}
{page("ss2.png", 692, 452, SS2, "Problem statement, page 2", "deliverables + how we get judged", 0.93)}
{SCORE}</body></html>'''
(HERE / "review.html").write_text(html)

from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1123, "height": 794})
    pg.goto((HERE / "review.html").as_uri())
    pg.wait_for_timeout(2500)
    pg.evaluate("document.fonts.ready")
    pg.pdf(path=str(HERE / "PS_coverage_review.pdf"), width="1123px", height="794px", print_background=True)
    b.close()
print("ok")
