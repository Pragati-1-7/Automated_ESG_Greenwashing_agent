# Data sources and APIs we built, and how they work

## How it fits together

```
React UI  --HTTP/SSE-->  FastAPI (app/api)  -->  LangGraph agents  --HTTP tools-->  mock_sources (FastAPI)  -->  data/world/world.db (SQLite)
                                                      |                                     \--> BM25 index over news + assurance text
                                                      \--HTTPS-->  TypeSafe Jev API (live decision engine)
```

- **mock_sources** is a separate FastAPI app (`mock_sources/app.py`). It is shaped like the real data providers an ESG analyst would use. Agents can ONLY reach evidence through it.
- By default the main API mounts it in-process (`MOCK_SOURCES_URL=inproc`), so you don't need a second server. Set `MOCK_SOURCES_URL=http://127.0.0.1:8100` and run `scripts/run_mock_sources.ps1` to run it as a real separate service.
- The same tools are exposed as an **MCP server** (`python -m mock_sources.mcp_server`).
- Every response carries `source`, `tier` and `endpoint`, so each fact in a verdict can be traced back to an exact request.

## Tables (all synthetic; every row is in `db_export/*.csv`)

| Table | Rows | Tier | Mimics | Key columns |
|---|---|---|---|---|
| companies | 150 | - | MCA company master | company_id, CIN, name, aliases, sector, HQ, listing |
| facilities | 422 | - | plant registry + SPCB consents | facility_id, company, type, district, state, **lat, lon**, capacity, consent_no, forest_adjacent |
| brsr_filings | 900 | 1 | SEBI BRSR Core (9 attributes) | scope1/2 tCO2e, ghg_intensity, energy_gj, re_pct, water withdrawal/discharge, waste generated/recovered, LTIFR, fatalities, women_wage_pct, MSME %, assurance type/provider, filed_on |
| facility_ghg | 2,532 | 1 | EPA GHGRP / PAT facility reporting | CO2, CH4, N2O, total; sums to the BRSR Scope 1 within 0.5% |
| ocems_exceedances | 2,000 | 2 | CPCB online continuous emission monitoring | facility, date, parameter (PM/SO2/NOx/BOD/COD/TSS), limit, reading, duration |
| regulatory_actions | 400 | 2 | NGT orders, CPCB/SPCB directions, SEBI | authority, case_no, order_type, date, penalty_inr, status, summary |
| land_alerts | 1,500 | 3 | Global Forest Watch integrated alerts | lat, lon, date, area_ha, confidence, source (GLAD/RADD), nearest facility + km |
| re_certificates | 932 | 3 | I-REC / REC Registry India | company, MWh, vintage, status (retired/active), retired_on |
| audited_reports | 409 | 3 | ISAE 3000 assurance statements | auditor, assurance_type, opinion, scope, statement text |
| news_articles | 500 | 4-5 | news wire + company press releases | outlet, tier (4 = PR, 5 = news), date, headline, 250-600 word body, topics |

There are 9,745 rows in total (`db_export/row_counts.json`). The whole world is generated from one spec (`data_gen/spec.py`). That keeps the PDFs, the tables and the ground truth consistent with each other. Rebuild it with `python -m data_gen.build_world` (deterministic), and validate it with `python -m data_gen.validate_world`.

## The "news API" in detail

`GET /news/search?q=...&company_id=...&k=...&date_from=...&date_to=...`

- **Index:** a BM25 ranking over 500 articles + 409 assurance statements (title + body), built in memory on first call (`mock_sources/db.py`).
- **Query:** the agent writes it from the company short name, the metric label and the claim's key words. For example, `Vajra Steel Renewable share of electricity ... renewable sources`.
- **Filters:** the company filter and the claim-period date window are applied after ranking.
- **Results:** each hit carries outlet, tier, date, headline and a normalised score. The agent keeps only hits with score >= 0.25 and quotes the 2 sentences that best match the claim.
- **Content:** news and PR are deliberately mixed. For example, the Vajra press release says "50% renewable" (tier 4), while an analyst article and the BRSR filing say 18% and that most certificates are unretired. The verdict agent is told that tier 1-2 outweighs tier 4.

## Endpoints (proof: `proof/api_samples/`, one real request/response per file)

| Endpoint | What it returns |
|---|---|
| `GET /companies/resolve?name=` | ranked candidates. The score weights distinctive name tokens, so "Aurelia Renewables" doesn't match "Bundela Renewable Power" |
| `GET /companies/{id}/facilities` | sites with coordinates |
| `GET /sebi/brsr?company_id=&fy=` | BRSR filing rows |
| `GET /ghg/facility?company_id=&fy=` | facility GHG rows |
| `GET /cpcb/ocems/exceedances?company_id=&fy=` | exceedance events in the fiscal-year window |
| `GET /regulatory/actions?company_id=&fy=` | orders and penalties |
| `GET /gfw/alerts/near?lat=&lon=&radius_km=&fy=` | haversine search around a point, with total hectares |
| `GET /gfw/alerts/company?company_id=&radius_km=&fy=` | the same, around every facility of a company |
| `GET /registry/rec?company_id=&vintage=` | certificates, with totals by status |
| `GET /assurance/statements?company_id=&fy=` | assurance statements |
| `GET /news/search?...` | BM25 news/PR search |
| `GET /tables`, `GET /tables/{name}` | catalogue and raw browser (used by the UI's Data sources page) |

## Live external API

**TypeSafe Jev** (`POST https://api.typesafe.ai/v1/systemone`, model `jev-1.13.0`) is the decision engine.

- Every answer is written to `data/cassettes/jev/jev_cassette.jsonl`, keyed by a hash of the exact question.
- `JEV_MODE=replay` reruns everything offline from that file. This is how the 253 tests run without a key.
- Proof that it is live: `proof/` holds the robustness run, where part D asks the API the same questions 3 times without the cassette.
- Cost: one 28-page report cold took 450 calls, about 377K input tokens, roughly $0.02, in 33 s (`benchmark/robustness_latest.json`, part E).

**Groq** (optional, `LLM_PROVIDER=groq`) only rewrites explanation text. It is off by default.
