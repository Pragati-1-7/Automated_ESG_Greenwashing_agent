# Automated ESG Greenwashing Detection & Verification Agent (v2)

An agentic system that reads a company's sustainability report, extracts every ESG claim, breaks complex claims into atomic checks, fetches external evidence at runtime, and decides **ALIGN / CONTRADICT / INSUFFICIENT_EVIDENCE / NOT_CHECKABLE**. It also produces an explainable 0-100 Greenwashing Risk Score and a full audit trail, streamed live to a React UI.

Based on the EY problem statement *"Automated ESG Greenwashing Detection & Verification Agent"*. **All companies and data are synthetic.** This is a triage tool for human reviewers, not a legal determination.

- **Orchestration:** LangGraph (supervisor graph + per-claim sub-graph fanned out with `Send`)
- **Decision engine:** TypeSafe **Jev**. Every judgement is a typed question with calibrated probabilities
- **Evidence:** fetched over HTTP from `mock_sources/`, a stand-in for SEBI BRSR, CPCB OCEMS, NGT/SPCB orders, GFW forest alerts, REC registry, assurance statements and news (REST + MCP)
- **Text generation:** deterministic mock by default (writes only from facts); Groq optional

## Quick start (Windows PowerShell)

```powershell
python -m venv venv; .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env        # put your Jev key in TYPESAFE_API_KEY
.\scripts\run_backend.ps1      # API on http://127.0.0.1:8000  (docs at /docs)
.\scripts\run_frontend.ps1     # UI  on http://localhost:5173  (second terminal)
```

In the UI, open **Analyze (v2)**, pick a demo report and click **Run analysis**. You will watch the agents work live. Without a key, set `JEV_MODE=replay`: the four demo reports and the benchmark run offline from recorded decision-engine answers.

## Results (details in `docs/TECHNICAL_SUMMARY.md`)

| Evaluation | Result |
|---|---|
| 4 demo PDFs (23-28 pages), 46 planted claims | extraction 46/46, verdicts 46/46 |
| Company risk score | greenwasher 56 > mixed 45 > honest 34 > unknown company 24 |
| 200-case benchmark | 0.98 accuracy overall (1.00 on the 60-case test split, see caveats) |
| Held-out benchmark (fresh seed, 172 cases) / hand-written stress set | 0.977 / 23 of 24 |
| Ablations | no retrieval 0.35, news-only RAG 0.45, full agent 1.00 |
| Tests | `pytest`: 253 passing offline (Jev answers replayed from cassettes) |

## Repository map

```
app/
  agents/        one file per agent: resolver, extractor, triage, decomposer, router, investigator,
                 evidence (source builders), judge (+verdict), risk, reporter, prompts (versioned questions)
  decision/jev.py   Jev adapter: typed questions, retries, record/replay cassette
  graph/         pipeline.py (LangGraph wiring), runner.py, claims.py (single-claim verification)
  ingest/pdf.py  layout-aware PDF parsing (PyMuPDF)
  tools/         sources.py (HTTP tools), calculator.py, claim_parser.py
  llm/providers.py  generative slot: MockLLM (default) / GroqLLM
  api/           main.py (v1 + v2), v2.py (jobs, SSE, reports, sources, benchmark)
mock_sources/    separate FastAPI service + MCP server over data/world/world.db
data_gen/        spec.py (single source of truth), world + benchmark generators, validator
report_gen/      builds the demo report PDFs (HTML -> Chromium PDF)
eval/            run_benchmark.py, run_reports.py, fit_risk.py
data/            world/world.db, reports/*.pdf, benchmark/, cassettes/jev/, models/risk_weights.json
web/             React UI (Vite + TS)
docs/            TECHNICAL_SUMMARY.md, ARCHITECTURE_V2.md, DEMO_FLOW_V2.md, API_V2_CONTRACT.md, BENCHMARK_NOTES.md
```

## Useful commands

```bash
python -m pytest -q                       # full suite, offline
python -m eval.run_benchmark              # 200 cases + ablations -> data/benchmark/results_latest.json
python -m eval.run_reports                # end-to-end on the demo PDFs
python -m eval.fit_risk                   # refit risk weights on the train split
python -m data_gen.build_world            # rebuild the synthetic world DB
python -m data_gen.build_benchmark        # rebuild the benchmark
python -m report_gen.build_reports        # rebuild the demo PDFs
python -m mock_sources.mcp_server         # data sources as an MCP server (stdio)
```

The legacy v1 (rule-based) README is kept at `docs/README_v1.md`; v1 routes and the Streamlit app still work.
