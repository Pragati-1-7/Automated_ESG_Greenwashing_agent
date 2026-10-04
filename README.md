# ESG Greenwashing Agent
> agentic system that reads ESG reports and checks every claim against real-world evidence

companies publish 30-page sustainability reports full of claims like "40% less emissions" or "zero deforestation". nobody can check all of them by hand. this system does: it reads the PDF, pulls out every claim, goes and fetches evidence from filings, regulator records, satellite alerts and news, and decides **ALIGN / CONTRADICT / INSUFFICIENT_EVIDENCE** for each one. you get a **0-100 Greenwashing Risk Score** plus a full audit trail.

not a chatbot reading a PDF. claims get broken into atomic checks, evidence comes from tools, maths runs in a calculator, and every decision is a typed question with a probability behind it.

built for the EY problem statement *Automated ESG Greenwashing Detection & Verification Agent*. all companies and data are synthetic. it's a triage tool for a human analyst, not a legal finding.

---

## how it works

```
                ┌──────────────────────────────────────────────┐
                │                  ANY REPORT                  │
                │     sustainability report PDF · claim text   │
                └──────────────────────┬───────────────────────┘
                                       │
                                       ▼
                ┌──────────────────────────────────────────────┐
                │             LAYER 1 · INGEST                 │
                │  layout-aware PDF parse → sentences with     │
                │  page + section · columns re-joined          │
                └──────────────────────┬───────────────────────┘
                                       │
                                       ▼
                ┌──────────────────────────────────────────────┐
                │          LAYER 2 · UNDERSTAND                │
                │  resolve company → extract claims → triage   │
                │  (done / future plan / vague talk)           │
                └──────────────────────┬───────────────────────┘
                                       │
                                       ▼
                ┌──────────────────────────────────────────────┐
                │          LAYER 3 · INVESTIGATE               │
                │  decompose → route → fetch evidence          │
                │  one sub-graph per claim, all in parallel    │
                │                                              │
                │  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
                │  │  source  │  │calculator│  │   claim    │  │
                │  │  tools   │  │   tool   │  │   parser   │  │
                │  │ 8 APIs   │  │ all maths│  │ lakh·crore │  │
                │  └──────────┘  └──────────┘  └────────────┘  │
                └──────────────────────┬───────────────────────┘
                                       │
                                       ▼
                ┌──────────────────────────────────────────────┐
                │            LAYER 4 · DECIDE                  │
                │  relevance gate → stance → verdict           │
                │  ALIGN / CONTRADICT / INSUFFICIENT           │
                │  grounding guard · citation validator        │
                └──────────────────────┬───────────────────────┘
                                       │
                                       ▼
                ┌──────────────────────────────────────────────┐
                │            LAYER 5 · REPORT                  │
                │  risk score 0-100 · per-claim reasoning      │
                │  audit trail streamed live to the UI         │
                │                                              │
                │  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
                │  │ React UI │  │ REST+SSE │  │ MCP server │  │
                │  │live trace│  │ FastAPI  │  │ data tools │  │
                │  └──────────┘  └──────────┘  └────────────┘  │
                └──────────────────────────────────────────────┘
```

---

## system architecture

```
  ┌──────────┐  REST + SSE   ┌──────────┐        ┌──────────────────────┐
  │ React UI │ ◄───────────► │ FastAPI  │ ─────► │  LangGraph pipeline  │
  └──────────┘               │ jobs +   │        │  one node = one agent│
                             │ events   │        └──────────┬───────────┘
                             └──────────┘                   │
              ┌──────────────────────┬──────────────────────┼───────────────────┐
              ▼                      ▼                      ▼                   ▼
     ┌────────────────┐    ┌──────────────────┐   ┌────────────────┐  ┌────────────────┐
     │  TypeSafe Jev  │    │   mock_sources   │   │   calculator   │  │    LLM slot    │
     │ decision engine│    │  FastAPI + MCP   │   │  % change ·    │  │ mock (default) │
     │ typed questions│    │  SEBI · CPCB ·   │   │  share · units │  │ / Groq         │
     │ + probabilities│    │  NGT · GFW · REC │   │  · gaps        │  │ writes text,   │
     └───────┬────────┘    │  · news (BM25)   │   └────────────────┘  │ never decides  │
             │             └────────┬─────────┘                       └────────────────┘
             ▼                      ▼
     ┌────────────────┐    ┌──────────────────┐
     │   cassette     │    │    world.db      │
     │ every answer   │    │ 150 companies    │
     │ recorded,      │    │ ~9.7K rows       │
     │ offline replay │    │ (SQLite)         │
     └────────────────┘    └──────────────────┘
```

---

## langgraph workflow

```
  START
    │
    ▼
  ┌───────────┐   ┌───────────┐   ┌───────────┐   ┌───────────┐
  │  ingest   │──►│  resolve  │──►│  extract  │──►│  triage   │
  │ PDF→text  │   │ which co? │   │ is claim? │   │done/plan/ │
  └───────────┘   └───────────┘   │ metric?   │   │  vague    │
                                  └───────────┘   └─────┬─────┘
                    ┌───────────────────────────────────┴──────────────────┐
                    │ Send() one per checkable claim                       │
                    ▼                                                      │   not checkable
  ┌────────────── per-claim sub-graph (runs in parallel) ──────────────┐   │
  │                                                                    │   │
  │  decompose ──► route ──► investigate ──► judge ──► verdict         │   │
  │  atomic        8 yes/no   fetch +         relevant?  ALIGN /       │   │
  │  sub-claims    per source calculate,      supports?  CONTRADICT /  │   │
  │                           round 2 if thin            INSUFFICIENT  │   │
  │                                                                    │   │
  └─────────────────────────────────┬──────────────────────────────────┘   │
                                    │ claim_results (reducer merge)        │
                                    ▼                                      │
                             ┌─────────────┐                               │
                             │  aggregate  │◄──────────────────────────────┘
                             │ risk 0-100  │
                             └──────┬──────┘
                                    ▼
                             ┌─────────────┐
                             │   report    │──► END
                             │ + audit log │
                             └─────────────┘
```

every node emits an event → streamed live to the UI → saved as the audit trail.

---

## how a claim gets decided

```
  "50% of our electricity came from renewable sources"   (Vajra Steel, FY2025)
        │
        ▼
  ┌──────────────┐
  │   route      │  Jev, per source: BRSR 0.86 · assurance 0.84 · news 0.82 · REC 0.76
  └──────┬───────┘
         ▼
  ┌──────────────┐  /sebi/brsr          → re_pct FY2025 = 18.0      (tier 1 filing)
  │ investigate  │  /registry/rec       → 2.1M MWh active, 0.31M retired
  │              │  /news/search        → press release says 50%   (tier 4 PR)
  │              │  calculator          → claimed 50 vs filed 18 = 32 pts gap
  │              │  Jev: evidence sufficient? p = 0.83 → no round 2
  └──────┬───────┘
         ▼
  ┌──────────────┐
  │    judge     │  relevance gate drops off-topic hits · stance contradict (0.99)
  └──────┬───────┘
         ▼
  ┌──────────────┐
  │   verdict    │  CONTRADICT (p = 1.00) · filing outweighs PR
  └──────────────┘  every cited evidence id checked against what was fetched
```

---

## problem statement coverage

| PS asks for | where it is |
|---|---|
| parse sustainability PDFs | `app/ingest/pdf.py` |
| extract falsifiable claims, prompt engineering | `extractor.py`, `triage.py`, versioned prompts in `app/agents/prompts.py` |
| break complex claims into searchable queries | `decomposer.py` + `router.py` |
| search mock DBs, news API, env datasets | `investigator.py` → `mock_sources/` (8 sources) |
| align / contradict / lack sufficient evidence | `judge.py` |
| hallucination control | relevance gate · grounding guard · citation validator · maths in a tool |
| Greenwashing Risk Score 0-100 | `risk.py`, logistic model fitted on the benchmark |
| report with claim + evidence + reasoning | `reporter.py` + live audit trail |
| modular agent-based code | one agent per file, LangGraph wiring in `app/graph/` |
| synthetic dataset of claims + news | `data_gen/`, 200-case benchmark, 4 report PDFs (23-28 pages) |
| UI: upload, live extraction, reasoning, score | React (`web/`) with a live agent trace |
| 2-3 page technical summary | `docs/TECHNICAL_SUMMARY.md` |

---

## quick start

```powershell
python -m venv venv; .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.api.main:app --port 8000 --reload      # terminal 1 · API on http://127.0.0.1:8000

cd web; npm install; npm run dev                   # terminal 2 · UI on http://localhost:5173
```

open **Analyze (v2)**, pick a demo report, hit **Run analysis**. no Jev key? set `$env:JEV_MODE="replay"` and the 4 demo reports run offline from recorded answers.

---

## API

```
POST   /v2/analyses                 start an analysis (demo report or PDF upload)
GET    /v2/analyses/{id}/events     live agent events (SSE)
GET    /v2/analyses/{id}/report     final report + audit trail
POST   /v2/verify-claim             check a single claim
GET    /v2/demo-reports             the 4 demo PDFs
GET    /v2/sources/overview         data source tables + row counts
GET    /v2/benchmark/latest         latest benchmark results
GET    /health                      engine · llm · sources status
```

data source APIs (`mock_sources/`): `/sebi/brsr` · `/ghg/facility` · `/cpcb/ocems/exceedances` · `/regulatory/actions` · `/gfw/alerts/near` · `/registry/rec` · `/assurance/statements` · `/news/search`

interactive docs at `http://127.0.0.1:8000/docs`

---

## tech stack

| layer | tech |
|---|---|
| orchestration | LangGraph · StateGraph + Send fan-out + reducers |
| decisions | TypeSafe Jev · typed questions (yes/no · choice · score) · record/replay |
| text | MockLLM (writes only from given facts) · Groq optional |
| data | SQLite world.db · BM25 news index · MCP server |
| PDF | PyMuPDF, layout-aware |
| api | FastAPI · Pydantic · SSE |
| ui | React · Vite · TypeScript |

---

## data

| table | rows | acts like |
|---|---|---|
| companies / facilities | 150 / 422 | MCA master + plant registry with lat/lon |
| brsr_filings | 900 | SEBI BRSR Core |
| facility_ghg | 2,532 | facility GHG reporting |
| ocems_exceedances | 2,000 | CPCB emission monitoring |
| regulatory_actions | 400 | NGT / CPCB / SPCB orders |
| land_alerts | 1,500 | Global Forest Watch |
| re_certificates | 932 | REC / I-REC registry |
| audited_reports | 409 | assurance statements |
| news_articles | 500 | news + press releases |

---

## results

| test | result |
|---|---|
| 4 demo PDFs, 46 planted claims | 46/46 extracted · 46/46 correct verdicts |
| company risk | greenwasher 56 > mixed 45 > honest 34 > unknown 24 |
| benchmark (200) / held-out (172 fresh) | 0.98 / 0.977 accuracy |
| stress set (hand-written) | 23/24 |
| ablation | no retrieval 0.35 · news-only RAG 0.45 · full agent 1.00 (test split) |

synthetic, self-generated data, so this proves the method, not real-world accuracy. details in `docs/TECHNICAL_SUMMARY.md` and `verification_pack/`.

---

## .env

```env
TYPESAFE_API_KEY=your_jev_key
JEV_MODE=live                # or replay (offline)
LLM_PROVIDER=mock            # or groq
MOCK_SOURCES_URL=inproc      # or http://127.0.0.1:8100
```

---

## run tests

```bash
python -m pytest -q          # 85 passed, fully offline
```

---

## folders

```
app/                agents/ · graph/ · decision/jev.py · tools/ · ingest/ · llm/ · api/
mock_sources/       data source APIs + MCP server
data_gen/           synthetic world + benchmark generator
report_gen/         builds the demo PDFs
eval/               benchmark · robustness · risk fitting
data/               world.db · reports · benchmark · Jev cassettes
web/                React UI
docs/               technical summary · architecture · API contract
verification_pack/  proof · DB exports · honest evaluation
scrap/              old v1 code, not used
```

---

## status

- [x] v2 agentic pipeline + live UI
- [x] synthetic world, 4 report PDFs, benchmark + held-out eval
- [ ] plug real BRSR / CPCB / news feeds into the same tools
- [ ] read charts and image-only tables
- [ ] human review step on every CONTRADICT
