# Before (v1) vs after (v2)

v1 = the repo as it was on 3 Oct 2026. v2 = what was built on the night of 3-4 Oct 2026.

## Big picture

| Area | Before (v1) | After (v2) |
|---|---|---|
| Who decides a verdict | Hand-written Python rules (`verification.py`) | TypeSafe **Jev** decision engine: typed questions with probabilities |
| Claim extraction | LLM (Groq/Ollama) or a Mock that returned hardcoded claims for one filename | Jev screens every sentence ("is this a company ESG claim?" + which of 20 metrics) |
| Checkability | Regex/field rules (`checkability.py`) | Triage agent: A3CG labels implemented / planning / indeterminate, vagueness, materiality |
| Complex claims | One-shot, no decomposition | Decomposer splits into atomic sub-claims, each typed (pct_change, share, zero_events, geo...) |
| Search queries | Template strings (`query_planner.py`) | Router agent: Jev gives P(useful) for each of 8 sources; investigator builds tool calls |
| Evidence | 20 hand-written records in `data/evidence/evidence.json`, linked to claims by id | Fetched at runtime over HTTP from `mock_sources` (10 tables, 9,745 rows); nothing linked by id |
| Data sources | 1 JSON file | SEBI BRSR filings, facility GHG, CPCB OCEMS, NGT/SPCB/CPCB/SEBI orders, forest-loss alerts, REC registry, assurance statements, news + PR |
| Arithmetic | Inside the rule engine | Calculator tool, every formula shown in the audit trail |
| Hallucination control | n/a | Relevance gate, grounding guard (abstain), citation validator |
| Orchestration | Plain sequential Python (`pipeline.py`) | LangGraph `StateGraph` + per-claim sub-graph run in parallel (`Send`) |
| Iteration | none | FIRE-style loop: "is the evidence sufficient?", if not, widen sources, 2nd round |
| Risk score | Hand-picked points (+40 contradict, etc.) | Logistic model over Jev outputs, weights fitted on 140 train cases (AUC 0.99) |
| Test input | 4-page GreenLeaf PDF | 4 reports of 23-28 pages (greenwasher, mixed, honest, unknown company) |
| Dataset | 12 claims, 20 evidence, 10 hard cases | 150 companies, 9,745 DB rows, 500 news articles, 200-case labelled benchmark |
| Evaluation | 8/10 hard cases | 196/200 benchmark, 46/46 claims in the demo PDFs, ablations |
| API | `/analyze`, `/demo/dataset`, `/claims`, `/runs` | + `/v2/analyses` (async jobs), SSE live event stream, `/v2/verify-claim`, `/v2/sources/*`, `/v2/benchmark/latest`, report endpoint |
| UI | React results table (+ Streamlit, simple-ui) | React v2: live agent trace, claim drill-down with evidence and relevance, verify-a-claim, data explorer, benchmark page |
| Tests | 168 | 253 (offline; Jev answers recorded once and replayed) |
| Interop | none | `mock_sources` also runs as an MCP server |

## File by file

**Moved (proof that v2 does not need them)**

- `data/claims/`, `data/evidence/`, `data/test/`, `data/sample_pdfs/` moved to `legacy/v1_data/`. v1 code paths were updated to the new location so v1 still runs. See `proof/v2_tests_with_old_json_moved.txt`.
- `README.md` moved to `docs/README_v1.md` (a new README replaces it).
- `docs/TECHNICAL_SUMMARY.docx` moved to `docs/TECHNICAL_SUMMARY_v1.docx` (new .md + .docx replace it).

**Kept untouched (v1 still works):** `app/extraction/*`, `app/evaluation/*`, `app/retrieval/*`, `app/scoring/*`, `app/api/pipeline.py`, `streamlit_app/`, `simple-ui/`, v1 tests (paths only changed).

**Changed**

- `app/api/main.py`: mounts the v2 router; `/health` now reports the decision engine, LLM and sources.
- `web/src/App.tsx`: v2 is the default view, and v1 lives under "Legacy v1".
- `requirements.txt`, `.env.example`, `.gitignore`

**New: v2 backend**

- `app/core/` (config, models, events, ablation)
- `app/decision/jev.py` (decision engine adapter + record/replay)
- `app/agents/` (resolver, extractor, triage, decomposer, router, investigator, evidence, judge, risk, reporter, prompts)
- `app/graph/` (pipeline, runner, claims)
- `app/ingest/pdf.py`
- `app/tools/` (sources, calculator, claim_parser)
- `app/llm/providers.py`
- `app/api/v2.py`

**New: data and services**

- `mock_sources/` (REST service + MCP server)
- `data_gen/` (spec, world builder, benchmark builder, validator)
- `report_gen/` (PDF builder)
- `data/world/world.db`
- `data/reports/*.pdf`
- `data/benchmark/*`
- `data/cassettes/jev/`
- `data/models/risk_weights.json`

**New: eval and tests**

- `eval/` (run_benchmark, run_reports, fit_risk)
- `tests/test_v2_*.py`, `tests/test_world_db.py`, `tests/test_benchmark.py`

**New: UI**

- `web/src/components/v2/*`
- `web/src/lib/v2*.ts`
- `web/src/v2.css`
- `web/src/fixtures/`
- `web/screenshots/`

**New: docs**

- `docs/TECHNICAL_SUMMARY.md/.docx`
- `docs/ARCHITECTURE_V2.md`
- `docs/DEMO_FLOW_V2.md`
- `docs/API_V2_CONTRACT.md`
- `docs/BENCHMARK_NOTES.md`
- `docs/PS_coverage_review.pdf`
- `verification_pack/`

**New: scripts:** `scripts/run_backend.ps1`, `run_frontend.ps1`, `run_mock_sources.ps1`, `push_v2.ps1`.
