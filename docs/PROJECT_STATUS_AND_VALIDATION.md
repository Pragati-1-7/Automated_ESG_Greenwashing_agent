# Project Status & Validation Report

**Project:** Automated ESG Greenwashing Detection & Verification Agent
**Status as of:** 2026-09-27
**Phase:** Steps 1–6 complete (dataset → extraction → checkability → retrieval →
verification/risk scoring → FastAPI + Streamlit application)
**Test suite:** 168/168 automated tests passing · dataset validation passing

This file is the single source of truth for "what does this project actually do,
what has been checked, and what is still open." It is written to be read on its
own - no need to re-read prior chat history to trust these numbers; every number
in this file was re-run and confirmed while writing it.

---

## 1. One-paragraph summary

The system takes a company's ESG/sustainability report (PDF), extracts individual
factual claims, decides which ones are specific enough to check, searches a
synthetic evidence corpus using hybrid (keyword + semantic) retrieval, compares
each claim against the evidence it finds using deterministic Python logic (never
an LLM doing arithmetic), and produces an explainable 0–100 "Greenwashing Risk
Score" per claim plus a full audit trail. It is a **human-review triage tool**,
not a legal verdict - every output surface says so explicitly.

---

## 2. Inputs and outputs (I/O contract)

### Inputs

| Input                   | Where it enters                                  | Constraints enforced                                                                                                |
|-------------------------|--------------------------------------------------|---------------------------------------------------------------------------------------------------------------------|
| ESG report PDF          | Streamlit upload, or `POST /analyze` (multipart) | Must be a real `.pdf`, non-empty, opens successfully in `pdfplumber`                                                |
| "Use demo" flag         | Streamlit checkbox / `use_demo=true` form field  | Bypasses upload, uses bundled `data/sample_pdfs/synthetic_esg_report.pdf`                                           |
| Company name (optional) | Text field                                       | Free text; used only as a hint for the extraction prompt                                                            |
| Extraction mode         | Sidebar dropdown / `mode` field                  | `mock` (default, offline) / `groq` / `ollama` (require env credentials on the backend, never sent from the browser) |
| `top_k`                 | Sidebar slider / form field                      | Integer; how many evidence items to retrieve per claim (tested at 0, 1, 5, 10)                                      |
| `use_semantic`          | Sidebar checkbox / form field                    | Enables ChromaDB semantic retrieval in addition to BM25                                                             |

### Outputs

Every successful `/analyze` or `/demo/dataset` call returns one JSON object containing:

- `status` - `"ok"` or `"no_claims"` (never a silent empty success)
- `summary` - total / checkable / not-checkable claim counts, verdict counts, average risk score
- `audit_records[]` - one per extracted claim, each containing:
  - `checkability_result` (always present)
  - `retrieval_result`, `verification_result`, `risk_score_result` (present only if the claim was CHECKABLE)
- `synthetic_evidence_notice` and `disclaimer` - carried on **every** response, not just the UI

The Streamlit dashboard renders this JSON as: an executive summary, a sortable claims
table, and per-claim tabs (Checkability / Evidence / Verification / Numerical Checks /
Risk Score / step-by-step Audit Trail). Nothing is computed client-side - the frontend
is a pure renderer of backend output.

---

## 3. Integrations made

```
Streamlit (streamlit_app/app.py)
      | HTTP, via `requests`
FastAPI (app/api/main.py)  ---- /health  /analyze  /demo/dataset  /claims/{id}
      |
Orchestration (app/api/pipeline.py)
      |
      ├── pdfplumber              (PDF -> page-aware text)
      ├── LLM provider adapter    (Mock offline / Groq HTTP API / Ollama local HTTP API)
      ├── Rule-based checkability engine (pure Python, no external calls)
      ├── rank_bm25                (keyword retrieval)
      ├── ChromaDB + sentence-transformers (all-MiniLM-L6-v2)  - optional, opt-in
      ├── Deterministic numeric-check engine (pure Python arithmetic)
      ├── Rule-based verification + risk-scoring engines (pure Python)
      └── Pydantic schemas          (validate every object at every boundary)
```

No other external services are integrated. Specifically **not** integrated (by design,
per project scope): live web search, real regulatory/news APIs, authentication providers,
payment systems, or any cloud database. Groq/Ollama are the only two external network
calls the system can make, and both are opt-in and off by default (`mode=mock`).

---

## 4. Data used - is it synthetic? Yes, entirely.

| File                                        | Contents                                                                                       | Real or synthetic                                                              |
|---------------------------------------------|------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------|
| `data/claims/claims.json`                   | 12 ESG claims across 6 fictional companies                                                     | 100% synthetic, hand-authored                                                  |
| `data/evidence/evidence.json`               | 20 evidence records, all 5 source tiers                                                        | 100% synthetic, hand-authored to deliberately align/contradict specific claims |
| `data/test/hard_cases.json`                 | 10 deliberately tricky cases (vague, false-but-precise, baseline shift, scope confusion, etc.) | 100% synthetic                                                                 |
| `data/sample_pdfs/synthetic_esg_report.pdf` | 4-page fictional GreenLeaf Industries Ltd. report                                              | 100% synthetic, generated by `scripts/generate_sample_pdf.py`                  |
| `data/sample_pdfs/edge_cases/*.pdf`         | 5 fixtures for error-path testing                                                              | 100% synthetic, generated by `scripts/generate_edge_case_pdfs.py`              |

No real company names, real filings, or real regulatory records are used anywhere in
this repository. This is stated in the dashboard, in every API response
(`synthetic_evidence_notice`), and in the README/final documentation. **This is an
academic prototype, not a production greenwashing detector** - treat every verdict it
produces as a demonstration of the method, not a real finding about a real company.

---

## 5. Validated use cases

### 5a. General end-user flow (validated live + automated)

1. Open dashboard → check "Use Demo ESG Report" → "Analyze Report".
2. Result (re-run just now, offline, mock provider): 10 claims extracted from the
   sample PDF, 7 checkable, all 7 came back `CONTRADICT` (avg risk 72/100) -
   correct, because the fictional "GreenLeaf" report was authored with inflated
   figures against the same-named claims in the evidence corpus. This is the
   intended "obvious greenwashing" demo path.
3. Open a claim's Evidence / Verification / Risk Score / Audit Trail tabs - confirmed
   to render exactly the backend JSON, with the audit trail as a readable 10-step
   trace (not raw JSON) plus a raw-JSON expander for drill-down.

### 5b. Corporate / professional reviewer use case (validated via `/demo/dataset`)

An ESG analyst or auditor needs to see the full spread of outcomes, not just one
report's slant. Re-run just now against the curated 12-claim dataset (BM25-only):

| Claim   | Company                       | Verdict               | Risk Score | Band     |
|---------|-------------------------------|-----------------------|------------|----------|
| CLM-001 | GreenLeaf Renewables Ltd      | INSUFFICIENT_EVIDENCE | 50         | Moderate |
| CLM-002 | Bharat Steelworks Pvt Ltd     | CONTRADICT            | 70         | High     |
| CLM-003 | Suryodaya Solar Energy Ltd    | ALIGN                 | 0          | Low      |
| CLM-004 | GreenLeaf Renewables Ltd      | INSUFFICIENT_EVIDENCE | 15         | Low      |
| CLM-005 | EcoCycle Waste Management Ltd | ALIGN                 | 0          | Low      |
| CLM-006 | AquaPure Industries Ltd       | ALIGN                 | 0          | Low      |
| CLM-007 | Vasundhara Textiles Ltd       | INSUFFICIENT_EVIDENCE | 15         | Low      |
| CLM-008 | NovaChem Industries Ltd       | ALIGN                 | 0          | Low      |
| CLM-009 | Bharat Steelworks Pvt Ltd     | CONTRADICT            | 75         | High     |
| CLM-010 | Suryodaya Solar Energy Ltd    | ALIGN                 | 0          | Low      |

All three verdict types (ALIGN, CONTRADICT, INSUFFICIENT_EVIDENCE) are reachable and
demonstrated - this is what `docs/DEMO_FLOW.md` walks a professor through. This is
also asserted by an automated test
(`test_edge_cases.py::test_dataset_demo_produces_all_three_verdict_types`).

### 5c. Edge cases (all automated, all passing)

| #  | Scenario                                        | File / test                                                    | Expected behavior                                                  | Confirmed |
|----|-------------------------------------------------|----------------------------------------------------------------|--------------------------------------------------------------------|-----------|
| 1  | Blank / scanned PDF (no extractable text)       | `blank_scanned_report.pdf`                                     | 'no extractable text' message, not a crash                         | Yes       |
| 2  | Real PDF, zero ESG content                      | `unrelated_content.pdf`                                        | 'no claims extracted' message                                      | Yes       |
| 3  | Corrupted / fake .pdf (invalid bytes)           | `corrupted_not_a_real_pdf.pdf`                                 | Clean 422 with a message, not a 500 or crash                       | Yes       |
| 4  | Sample PDF's content under a different filename | `renamed_sample_report.pdf`                                    | Zero claims - mock mode never guesses a match by content           | Yes       |
| 5  | Long multi-page report (12 pages)               | `large_multi_page_report.pdf`                                  | All 12 pages parsed correctly, page count reported                 | Yes       |
| 6  | No file and use_demo=false                      | `test_analyze_requires_file_or_demo`                           | 400                                                                | Yes       |
| 7  | Non-PDF file uploaded                           | `test_analyze_rejects_non_pdf_upload`                          | 400                                                                | Yes       |
| 8  | Empty (0-byte) file uploaded                    | `test_analyze_rejects_empty_pdf_upload`                        | 400                                                                | Yes       |
| 9  | top_k=0                                         | `test_analyze_pdf_file_with_top_k_zero_returns_no_evidence`    | Zero evidence returned, no error                                   | Yes       |
| 10 | top_k = 1 / 5 / 10                              | `test_demo_dataset_various_top_k`                              | Evidence list never exceeds top_k                                  | Yes       |
| 11 | Unknown claim_id in dataset filter              | `test_analyze_dataset_rejects_unknown_and_mixed_claim_ids`     | Raises a clean PipelineError, not a KeyError                       | Yes       |
| 12 | Mixed known + unknown claim_ids                 | same test                                                      | Silently keeps only the known one                                  | Yes       |
| 13 | Malformed / whitespace claim ID via API         | `test_get_claim_with_malformed_id_returns_404_not_500`         | 404, never 500                                                     | Yes       |
| 14 | NOT_CHECKABLE claims                            | `test_not_checkable_claims_have_no_verification_or_risk_score` | Has a checkability result but no verification/risk score/retrieval | Yes       |

---

## 6. Automated test coverage (168 tests)

| Test file                 | Tests | Covers                                                       |
|---------------------------|-------|--------------------------------------------------------------|
| `test_pdf_parser.py`      | 8     | PDF parsing, page traceability, malformed PDFs               |
| `test_claim_extractor.py` | 9     | LLM extraction, mock provider, validation, retries           |
| `test_retrieval.py`       | 34    | Query planning, BM25, ChromaDB, hybrid fusion/dedup          |
| `test_numeric_checks.py`  | 21    | Percentage/count/capacity/unit arithmetic, tolerances        |
| `test_verification.py`    | 19    | ALIGN/CONTRADICT/INSUFFICIENT_EVIDENCE logic, tier weighting |
| `test_risk_score.py`      | 32    | Factor scoring, banding, disclaimers                         |
| `test_pipeline.py`        | 9     | Step 6 orchestration layer (`app/api/pipeline.py`)           |
| `test_api.py`             | 13    | FastAPI endpoints, including run persistence round-trips     |
| `test_edge_cases.py`      | 15    | Everything in Section 5c above, plus upload filename echo    |
| `test_storage.py`         | 8     | SQLite persistence layer (`app/storage.py`), isolated DB     |
| Total                     | 168   | All tests above combined                                     |

Run it yourself: `python -m pytest -q` and `python scripts/validate_dataset.py`
(both re-confirmed passing while writing this report).

---

## 7. What is explicitly NOT validated / NOT built (be honest about this)

Closed since the last pass:

- **Hard-case benchmark is now automated** (`scripts/evaluate_hard_cases.py`). Result:
  **8/10 (80%) verdict accuracy** on the 10 deliberately adversarial cases, 10/10
  checkability agreement. The two misses are real, documented findings, not bugs
  hidden from this report: HC-006 (absolute vs. intensity) is predicted CONTRADICT
  instead of the expected ALIGN, and HC-007 (boundary mismatch) is predicted ALIGN
  instead of the expected CONTRADICT. Both point at the same root cause: the
  deterministic verification rules do not yet separate "intensity claim" and
  "boundary-scoped claim" semantics from plain result claims.
- **Four-way retrieval comparison is now automated** (`scripts/evaluate_retrieval_methods.py`),
  exactly as described in the original project plan: no-retrieval baseline vs.
  keyword-only (BM25) vs. vector-only (semantic) vs. the full hybrid agent, over the
  curated 12-claim dataset's checkable claims. Result: no-retrieval 2/10 (20%),
  keyword-only 8/10 (80%), vector-only 8/10 (80%), hybrid 8/10 (80%). Retrieval
  clearly matters (20% to 80%); BM25 alone already matches the hybrid result on this
  small synthetic corpus, which is expected since the corpus's terminology overlaps
  the claims almost exactly - a less controlled real corpus would likely separate
  the three retrieval methods more.
- **Persistence is now implemented** (`app/storage.py`, SQLite, matching the
  `SQLITE_DB_PATH` placeholder that had existed unused in `.env.example` since Step
  1). Every `/analyze` and `/demo/dataset` call now saves its full result and
  returns a `run_id`; `GET /runs`, `GET /runs/{id}`, and `DELETE /runs/{id}` let a
  past run be listed, reopened, or removed. Covered by 13 new tests
  (`tests/test_storage.py`, plus persistence tests in `tests/test_api.py`), each
  isolated to a throwaway database file so the test suite never touches the real one.
- **Real LLM extraction is now live-tested**, not just theoretically wired up. A real
  Groq API key was configured, and a genuine bug was caught and fixed in the process:
  the FastAPI server never called `load_dotenv()`, so `.env` was silently ignored by
  the running API even though the CLI script read it correctly. Fixed in
  `app/api/main.py`. Re-verified afterward: a real `openai/gpt-oss-120b` call
  (the available large model on this account; classic Llama-70B models were not
  present) correctly extracted 9 structured claims from the sample PDF with zero
  errors, end to end through `/analyze` with `mode=groq`.

Still open:

- **No real regulatory/news data.** Retrieval only ever searches the 20 synthetic
  evidence records. An uploaded PDF from a company not in that synthetic set will
  almost always return `INSUFFICIENT_EVIDENCE` - this is correct, expected behavior
  for a prototype, not a bug, but it means the system cannot yet demonstrate value on
  an arbitrary real-world PDF.
- **No multi-year / multi-filing year-on-year comparison** (the "same metric restated
  differently across 3 years of filings" check described in the original project plan
  docx). Only single-document, single-snapshot comparison is implemented.
- **No CI pipeline.** Tests are not run automatically on push/PR - someone has to
  remember to run `pytest` locally before pushing.
- **No auth, no rate limiting, no upload size cap.** Fine for a local academic demo;
  not fine if this were ever exposed on the open internet. This now matters slightly
  more than before since a real API key is configured in `.env` - that file is
  gitignored and was never committed, but it is a live credential sitting on this
  machine's disk.

---

## 8. Recommendations - what would make this project stronger / more defensible

Ranked by effort-to-value for an academic submission:

1. **Investigate the two hard-case misses (HC-006, HC-007)** before presenting. An 80%
   score with two named, understood failure modes is far stronger in front of a
   reviewer than silence on the topic - be ready to explain the absolute-vs-intensity
   and boundary-mismatch gaps if asked.
2. **Add a citation-validator test** asserting that every `supporting_evidence_ids`/
   `contradicting_evidence_ids` in a `VerificationResult` is a subset of the IDs that
   were actually retrieved for that claim - proves by test, not just by code
   inspection, that the system never "cites" evidence it didn't pull.
3. **Add GitHub Actions CI** (`.github/workflows/tests.yml`) running
   `pytest` + `validate_dataset.py` on every push - protects against silent
   regressions, especially important once more than one person is committing.
4. **Pin dependency versions** in `requirements.txt` (currently all `>=`). An
   unrelated upstream release (e.g. a ChromaDB or FastAPI major bump) could break the
   demo the night before a presentation with zero code changes on your side.
5. **Add an upload size/page limit** on `/analyze` (e.g. reject >20MB or >200 pages)
   so a mis-click doesn't hang the demo machine.
6. **Add a `Dockerfile` / `docker-compose.yml`** so the whole app (API + dashboard)
   starts with one command on any machine, independent of the presenter's local
   Python setup - removes "works on my machine" risk on presentation day.
7. **Keep committing in small, logical commits** (as done for Step 6) rather than one
   giant commit per step - makes it far easier for a professor or teammate to review
   what changed and why, and gives you a recovery point if something breaks.
8. **Never upload a real, confidential company ESG report** to this prototype without
   that company's consent - the pipeline sends page text to whichever LLM provider is
   configured (Groq/Ollama), and although mock mode is fully offline, real-provider
   mode is not.
9. **Rotate the configured Groq API key before any public sharing of this machine or
   repo.** It lives only in the local, gitignored `.env` file and was never
   committed, but treat it as sensitive since it was shared in plaintext once.

---

## 9. Bottom line

Steps 1–6 are complete, integrated, and passing 168/168 automated tests plus 15
explicit edge-case scenarios and 2 full end-to-end use-case walkthroughs (general
user + corporate reviewer) confirmed live in this report. The system is an honest,
clearly-labeled **triage prototype** built entirely on synthetic data - it does
exactly what it claims to do and does not overstate itself anywhere in the UI, API,
or documentation. The most valuable next step, if more time is available, is
recommendation #1 above: turning the hard-case dataset into an automated accuracy
benchmark.
