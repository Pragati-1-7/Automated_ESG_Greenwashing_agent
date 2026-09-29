# Automated ESG Greenwashing Detection & Verification Agent

## 1. Problem Statement

Companies publish ESG (Environmental, Social, Governance) reports containing
sustainability claims — emission reductions, renewable energy usage, worker
safety records, and more. Some of these claims are accurate; others are
vague, exaggerated, or contradicted by independent evidence ("greenwashing").
Manually checking every claim in every report against regulatory filings,
audits, and news is slow and inconsistent.

This project is based on the EY (Ernst & Young) problem statement:
**"Automated ESG Greenwashing Detection & Verification Agent."**

## 2. Project Objective

Build an agentic AI system that:

1. Extracts falsifiable ESG claims from a company's sustainability report.
2. Determines whether each claim is actually checkable.
3. Plans and runs targeted searches for external evidence.
4. Retrieves evidence using hybrid (keyword + semantic) search, prioritizing
   more reliable source types.
5. Compares each claim against the evidence it finds.
6. Performs numerical checks (unit-aware) in Python rather than trusting an
   LLM to do arithmetic.
7. Classifies each claim as **ALIGN**, **CONTRADICT**, or
   **INSUFFICIENT EVIDENCE**.
8. Aggregates results into a transparent, rule-based **Greenwashing Risk
   Score (0–100)**.
9. Produces a full, explainable audit trail for every claim.
10. Presents everything through a Streamlit interface.

> **Important limitation:** This is a **decision-support / triage system**
> for human reviewers. It is **not** a legal verdict on whether a company is
> greenwashing.

## 3. Planned Architecture

```
Company ESG PDF
        ↓
PDF Parser
        ↓
Claim Extraction Engine
        ↓
Structured ESG Claims
        ↓
Checkability Scorer
        ↓
Query Planning / Search Agent
        ↓
Hybrid Evidence Retrieval (BM25 + ChromaDB)
        ↓
Evidence Relevance Validation
        ↓
Contradiction / Entailment Analysis
        ↓
Numeric Verification (Python, unit-aware)
        ↓
Additional Non-AI Checks (capacity check, year-on-year check)
        ↓
Greenwashing Risk Scoring (rule-based)
        ↓
Explainable Audit Report
        ↓
FastAPI Backend + Streamlit UI
```

## 4. Current Project Status: **Steps 1–6 Complete**

Step 1 built the repository structure and dataset foundation.  
Step 2 added the **PDF parsing + ESG claim extraction pipeline**.  
Step 3 added the **rule-based claim checkability engine**.  
Steps 4 & 5 add the **hybrid evidence retrieval, deterministic verification engine, and Greenwashing Risk Scoring system**.
Step 6 adds the **FastAPI backend and Streamlit dashboard**, turning the pipeline into an
end-to-end, PDF-upload-to-risk-score application. See `docs/FINAL_PROJECT_DOCUMENTATION.md`
and `docs/DEMO_FLOW.md`.

**IMPLEMENTED (Steps 1 & 2):**
- Modular repository structure and Pydantic schemas.
- Curated synthetic datasets: 12 claims, 20 evidence records, 10 hard cases.
- Page-aware PDF parser (`app/extraction/pdf_parser.py`).
- LLM claim extraction engine (`app/extraction/claim_extractor.py`) with Groq, Ollama, and deterministic Mock providers.
- Extraction evaluation and automated test suites.

**IMPLEMENTED (Step 3):**
- Rule-based checkability assessment (`app/evaluation/checkability.py`) evaluating structural falsifiability without LLM reliance.

**IMPLEMENTED (Steps 4 & 5):**
- **Query Planner (`app/retrieval/query_planner.py`):** Deterministic search query generation per checkable claim.
- **BM25 Retriever (`app/retrieval/bm25_retriever.py`):** Fast, offline lexical search with min-max score normalisation.
- **ChromaDB Retriever (`app/retrieval/chroma_retriever.py`):** Dense semantic search using `sentence-transformers` (`all-MiniLM-L6-v2`).
- **Hybrid Retriever (`app/retrieval/hybrid_retriever.py`):** Weighted fusion of BM25 and vector scores into a combined ranking.
- **Deterministic Numeric Verification (`app/evaluation/numeric_checks.py`):** Exact Python arithmetic for percentage changes, count checks, capacity checks, and unit/scope validations with tolerance.
- **Verification Engine (`app/evaluation/verification.py`):** Evidence aggregation with source-tier weighting (Tier 1 regulatory filings override lower-tier claims) producing `ALIGN`, `CONTRADICT`, or `INSUFFICIENT_EVIDENCE` verdicts.
- **Greenwashing Risk Scoring (`app/scoring/risk_score.py`):** Explainable 0–100 risk score breakdown with Low, Moderate, High, and Very High risk bands.
- **Verification CLI (`scripts/run_verification.py`):** End-to-end pipeline execution with rich audit trails and disclaimers.
- **Full Test Suite:** 123 automated pytest tests passing across all components.

**IMPLEMENTED (Step 6):**
- **FastAPI backend (`app/api/main.py`, `app/api/pipeline.py`):** `/health`, `/analyze`
  (PDF upload or demo mode), `/demo/dataset` (curated dataset demo), `/claims/{claim_id}`.
- **Streamlit dashboard (`streamlit_app/app.py`):** PDF upload, executive summary, claim
  table, per-claim detail (checkability / evidence / verification / numerical checks /
  risk score / audit trail).

## 5. Technology Stack

| Layer | Technology | Phase |
|---|---|---|
| Data models | Pydantic | Step 1 (done) |
| Config | python-dotenv | Step 1 (done) |
| PDF parsing | pdfplumber | Step 2 (done) |
| LLM inference | LLaMA 3 / Mistral via Groq, Ollama, or Mock | Step 2 (done) |
| Checkability | Rule-based Python engine | Step 3 (done) |
| Keyword search | rank_bm25 | Step 4 (done) |
| Vector search | ChromaDB + sentence-transformers | Step 4 (done) |
| Hybrid retrieval | Score normalisation + weighted fusion | Step 4 (done) |
| Numeric checks | Deterministic Python arithmetic | Step 5 (done) |
| Verification | Tier-weighted rule engine | Step 5 (done) |
| Risk scoring | Explainable 0–100 additive factor model | Step 5 (done) |
| Backend API | FastAPI | Step 6 (done) |
| Frontend | Streamlit | Step 6 (done) |
| Version control | Git / GitHub | Throughout |

## 6. Repository Structure

```
esg-greenwashing-agent/
├── app/
│   ├── extraction/      # [ACTIVE] pdf_parser.py, claim_extractor.py, llm_providers.py, mock_data.py
│   ├── retrieval/       # [ACTIVE - Step 4] query_planner.py, bm25_retriever.py, chroma_retriever.py, hybrid_retriever.py
│   ├── evaluation/      # [ACTIVE - Step 3 & 5] checkability.py, numeric_checks.py, verification.py
│   ├── scoring/         # [ACTIVE - Step 5] risk_score.py (0-100 Greenwashing Risk Score)
│   ├── api/             # FastAPI backend (future phase)
│   └── utils/           # Pydantic schemas (schemas.py) + shared helpers [ACTIVE]
├── data/
│   ├── claims/          # claims.json — synthetic ESG claims dataset [ACTIVE]
│   ├── evidence/        # evidence.json — synthetic evidence dataset [ACTIVE]
│   ├── test/            # hard_cases.json — tricky edge-case dataset [ACTIVE]
│   └── sample_pdfs/     # synthetic_esg_report.pdf + expected_claims.json
├── prompts/
│   └── claim_extraction_prompt.md   # Extraction prompt template
├── tests/
│   ├── test_pdf_parser.py       # PDF parsing unit tests (8 tests)
│   ├── test_claim_extractor.py  # Claim extractor unit tests (9 tests)
│   ├── test_retrieval.py        # BM25, Chroma, Hybrid, and Planner tests (34 tests)
│   ├── test_numeric_checks.py   # Arithmetic and dimensional checks (21 tests)
│   ├── test_verification.py     # Verdict aggregation and tier weighting (19 tests)
│   └── test_risk_score.py       # Risk scoring factors and banding (32 tests)
├── scripts/
│   ├── validate_dataset.py      # Dataset validation script
│   ├── generate_sample_pdf.py   # Builds the synthetic test PDF
│   ├── run_extraction.py        # CLI: PDF -> claims
│   ├── evaluate_extraction.py   # Precision/recall/field accuracy
│   └── run_verification.py      # [ACTIVE - Steps 4+5] CLI for end-to-end verification pipeline
├── streamlit_app/
│   └── app.py            # [ACTIVE - Step 6] Streamlit dashboard (calls the FastAPI backend)
├── docs/
│   ├── PROJECT_PROGRESS_STEP_1.md
│   ├── PROJECT_PROGRESS_STEP_2.md
│   ├── PROJECT_PROGRESS_STEP_4_5.md # Documentation for Steps 4 & 5
│   ├── FINAL_PROJECT_DOCUMENTATION.md # Full Step 1-6 documentation
│   └── DEMO_FLOW.md                 # How to demo the app to the professor
├── requirements.txt       # All active dependencies
├── .env.example            # Environment variable template
└── main.py                 # Project status and dataset validation entry point
```


## 7. Dataset Description

All data in this repository is **synthetic** — fictional companies and
figures created for development and testing. It is clearly labeled as such
in each file's `_meta` block and must never be presented as real-world data.

- **`data/claims/claims.json`** — 12 ESG claims covering Environmental
  (emissions, renewable energy, waste, water, deforestation), Social
  (workforce diversity, worker safety), and Governance (regulatory
  disclosure) topics. Includes checkable and non-checkable claims, and
  covers all four verdict outcomes (ALIGN, CONTRADICT,
  INSUFFICIENT_EVIDENCE, NOT_APPLICABLE).
- **`data/evidence/evidence.json`** — 20 evidence records spanning all five
  source-reliability tiers (regulatory filing → regulator record → audited
  report → company PR → news), linked to claims via `claim_id`.
- **`data/test/hard_cases.json`** — 10 deliberately tricky cases: vague
  claims, false-but-precise claims, period mismatches, shifted baselines,
  scope confusion, absolute-vs-intensity confusion, boundary mismatches,
  unit mismatches, unsupported future targets, and capacity mismatches.

## 8. Setup Instructions

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd esg-greenwashing-agent

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate

# 3. Install Step 1 dependencies
pip install -r requirements.txt

# 4. Create your local environment file (optional at this stage)
cp .env.example .env
```

## 9. How to Validate the Dataset

```bash
python scripts/validate_dataset.py
```

This checks: schema compliance (via Pydantic), ID uniqueness, referential
integrity between evidence and claims, and required-field completeness. It
prints a PASS/FAIL report and a summary of the dataset composition.

You can also run:

```bash
python main.py
```

which prints the current project status and runs the same validation.

## 10. Step 2: PDF Parsing & Claim Extraction

### 10.1 What it does

```
ESG PDF -> PDF Parser -> page-aware text -> LLM extraction prompt
    -> structured JSON -> Pydantic validation (ClaimRecord) -> validated claims
```

### 10.2 Install Step 2 dependencies

```bash
pip install -r requirements.txt
```

### 10.3 The synthetic sample PDF

A fictional company report, **GreenLeaf Industries Ltd. (not a real
company)**, used for reproducible testing. Regenerate it anytime with:

```bash
python scripts/generate_sample_pdf.py
```

### 10.4 Run extraction — mock mode (no API key needed)

```bash
python scripts/run_extraction.py --mock
```

This runs the deterministic mock provider against the bundled sample PDF
and prints all 10 extracted claims. Mock output always has
`extraction_method="mock"` and a `CLM-MOCK-...` claim ID, so it can never
be confused with a real LLM result.

### 10.5 Run extraction — real LLM mode

1. Copy `.env.example` to `.env` and fill in real values:
   ```bash
   cp .env.example .env
   ```
2. For **Groq**: set `GROQ_API_KEY` and `LLM_MODEL_NAME` (e.g.
   `llama-3.1-70b-versatile`), then:
   ```bash
   python scripts/run_extraction.py --provider groq --pdf path/to/your.pdf --company "Some Company"
   ```
3. For **Ollama** (local): install and run `ollama serve`, set
   `OLLAMA_BASE_URL` and `LLM_MODEL_NAME` (e.g. `llama3`), then:
   ```bash
   python scripts/run_extraction.py --provider ollama --pdf path/to/your.pdf --company "Some Company"
   ```

If credentials are missing or invalid, the script prints a clear
`CONFIGURATION ERROR` — it never silently falls back to mock output.

### 10.6 Run the tests

```bash
python -m pytest tests/ -v
```

### 10.7 Run the extraction evaluation

```bash
python scripts/evaluate_extraction.py
```

Reports precision/recall on claim identification and per-field accuracy
against `data/sample_pdfs/expected_claims.json`. This evaluates mock mode
against itself as a regression/sanity check — see the script's docstring
for why that is not a measure of real LLM quality.

### 10.8 Re-run the Step 1 regression check

```bash
python scripts/validate_dataset.py
```

Must still print `RESULT: PASS` — later steps must never break the underlying dataset.

## 11. Steps 4 & 5: Evidence Retrieval, Verification & Risk Scoring

### 11.1 Run the Full Verification Pipeline

Run the end-to-end pipeline across all checkable claims:

```bash
python scripts/run_verification.py
```

### 11.2 Run for a Specific Claim

Inspect the detailed audit trail for a single claim (e.g. `CLM-002`):

```bash
python scripts/run_verification.py --claim CLM-002
```

### 11.3 Quiet Mode (Summary Table Only)

```bash
python scripts/run_verification.py --quiet
```

### 11.4 Enable Hybrid ChromaDB Semantic Retrieval

```bash
python scripts/run_verification.py --semantic
```

## 12. Step 6: FastAPI Backend + Streamlit Dashboard

### 12.1 Install Step 6 dependencies

```bash
pip install -r requirements.txt
```

### 12.2 Run the FastAPI backend

```bash
uvicorn app.api.main:app --reload
```

API docs: `http://127.0.0.1:8000/docs`. Endpoints: `GET /health`, `POST /analyze`,
`GET /demo/dataset`, `GET /claims/{claim_id}`.

### 12.3 Run the Streamlit dashboard (in a second terminal)

```bash
streamlit run streamlit_app/app.py
```

Open `http://localhost:8501`.

### 12.3b Run the React frontend instead (optional, in a second terminal)

An alternative to the Streamlit dashboard — same backend, same data, different
UI. Both are kept; use whichever you prefer for a given demo.

```bash
cd web
npm install
npm run dev
```

Open `http://localhost:5173`. See `web/README.md` for details.

### 12.4 Run the demo offline (no API key needed)

In the dashboard, check **"Use Demo ESG Report"** and click **"Analyze Report"** — this runs
the bundled synthetic sample PDF through the full pipeline using the deterministic Mock LLM
provider. For a demo that reliably shows all three verdict types (ALIGN / CONTRADICT /
INSUFFICIENT_EVIDENCE), open the **"Full Dataset Demo"** page and click **"Run Dataset Demo"**.
See `docs/DEMO_FLOW.md` for a full presentation script.

### 12.5 Future Development

- Connect the retrieval layer to real, verified external ESG/regulatory data sources.
- Formal benchmark evaluation over the 10 held-out hard cases.
- Persist analysis runs so a report can be revisited without re-uploading the PDF.


## 13. Important Limitation

This system is a **triage / decision-support tool** intended to help a
human ESG reviewer prioritize which claims deserve closer scrutiny. It does
**not** produce a legal or definitive determination that a company is
greenwashing, and every verdict is meant to be reviewed by a human before
any conclusion is acted on.
