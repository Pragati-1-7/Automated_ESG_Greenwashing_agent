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

## 4. Current Project Status: **Step 2 Complete**

Step 1 built the repository structure and dataset foundation.
Step 2 adds the **PDF parsing + ESG claim extraction pipeline**.

**IMPLEMENTED (Step 1):**
- Modular repository structure (see below).
- Pydantic schemas for Claim, Evidence, and Hard Case records.
- A curated synthetic dataset: 12 claims, 20 evidence records, 10 hard cases.
- An automated dataset validation script.
- Environment configuration templates (`.env.example`).

**IMPLEMENTED (Step 2):**
- Page-aware PDF parser (`app/extraction/pdf_parser.py`, pdfplumber-based),
  with graceful handling of empty/malformed PDFs.
- LLM-based claim extraction engine (`app/extraction/claim_extractor.py`)
  that turns page text into `ClaimRecord`-validated structured claims.
- Provider-agnostic LLM architecture (`app/extraction/llm_providers.py`):
  **Groq**, **Ollama**, and a deterministic **Mock** provider for offline
  testing. Selected via `EXTRACTION_MODE` in `.env` or a CLI flag.
- The full extraction prompt as an editable file, not buried in code:
  `prompts/claim_extraction_prompt.md`.
- A minimal, justified extension to `ClaimRecord` (`char_start`, `char_end`,
  `extraction_method`, and `expected_verdict` made optional) — see
  `docs/PROJECT_PROGRESS_STEP_2.md` for the full rationale. All Step 1 data
  still validates unchanged.
- A clearly-labelled **synthetic** test PDF (`data/sample_pdfs/synthetic_esg_report.pdf`,
  reproducible via `scripts/generate_sample_pdf.py`) with 10 known claims
  covering numeric/vague/target/scope/baseline variations.
- An extraction evaluation script (`scripts/evaluate_extraction.py`):
  precision/recall on claim identification + field-level accuracy.
- 17 automated tests (`tests/`) covering the parser and the extractor,
  including malformed-JSON and invalid-enum handling.

**NOT implemented yet (future phases):**
- The query-planning search agent.
- Hybrid BM25 + ChromaDB retrieval.
- LLM-based entailment/contradiction analysis against external evidence.
- Numeric verification logic.
- Capacity check and year-on-year check logic.
- Greenwashing Risk Score calculation.
- FastAPI backend.
- Streamlit frontend.

## 5. Technology Stack

| Layer | Technology | Phase |
|---|---|---|
| Data models | Pydantic | Step 1 (done) |
| Config | python-dotenv | Step 1 (done) |
| PDF parsing | pdfplumber | Step 2 (done) |
| LLM inference | LLaMA 3 / Mistral via Groq and/or Ollama | Step 2 (done, architecture) |
| Agent orchestration | LangChain (only where genuinely useful) | Phase 3+ |
| Vector search | ChromaDB + sentence-transformers | Phase 3 |
| Keyword search | rank_bm25 | Phase 3 |
| Storage | SQLite | Phase 3+ |
| Backend API | FastAPI | Phase 4 |
| Frontend | Streamlit | Phase 5 |
| Version control | Git / GitHub | Throughout |

## 6. Repository Structure

```
esg-greenwashing-agent/
├── app/
│   ├── extraction/      # [ACTIVE - Step 2] pdf_parser.py, claim_extractor.py,
│   │                    #   llm_providers.py, mock_data.py
│   ├── retrieval/       # Query planning + hybrid evidence retrieval (Phase 3)
│   ├── evaluation/      # Entailment/contradiction + numeric verification (Phase 3-4)
│   ├── scoring/         # Greenwashing Risk Score logic (Phase 4)
│   ├── api/             # FastAPI backend (Phase 4)
│   └── utils/           # Pydantic schemas (schemas.py) + shared helpers [ACTIVE]
├── data/
│   ├── claims/          # claims.json — synthetic ESG claims dataset [ACTIVE]
│   ├── evidence/        # evidence.json — synthetic evidence dataset [ACTIVE]
│   ├── test/            # hard_cases.json — tricky edge-case dataset [ACTIVE]
│   └── sample_pdfs/     # [ACTIVE - Step 2] synthetic_esg_report.pdf + expected_claims.json
├── prompts/
│   └── claim_extraction_prompt.md   # [ACTIVE - Step 2] extraction prompt
├── tests/
│   ├── test_pdf_parser.py       # [ACTIVE - Step 2]
│   └── test_claim_extractor.py  # [ACTIVE - Step 2]
├── scripts/
│   ├── validate_dataset.py      # Dataset validation script [ACTIVE]
│   ├── generate_sample_pdf.py   # [ACTIVE - Step 2] builds the synthetic test PDF
│   ├── run_extraction.py        # [ACTIVE - Step 2] CLI: PDF -> claims
│   └── evaluate_extraction.py   # [ACTIVE - Step 2] precision/recall/field accuracy
├── streamlit_app/        # Streamlit UI (Phase 5)
├── docs/
│   ├── PROJECT_PROGRESS_STEP_1.md
│   └── PROJECT_PROGRESS_STEP_2.md   # Faculty-facing progress documentation
├── requirements.txt       # Step 1 + Step 2 dependencies (future phases commented)
├── .env.example            # Environment variable template (no real keys)
├── .gitignore
└── main.py                 # Placeholder entry point, runs the validator
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

Must still print `RESULT: PASS` — Step 2 must never break Step 1's dataset.

## 12. Future Development Phases

- **Phase 3:** Query planning agent + hybrid (BM25 + ChromaDB) evidence retrieval.
- **Phase 4:** Numeric verification, capacity/year-on-year checks, risk scoring, FastAPI backend.
- **Phase 5:** Streamlit UI.
- **Phase 6:** End-to-end evaluation against the held-out hard-case dataset.

## 13. Important Limitation

This system is a **triage / decision-support tool** intended to help a
human ESG reviewer prioritize which claims deserve closer scrutiny. It does
**not** produce a legal or definitive determination that a company is
greenwashing, and every verdict is meant to be reviewed by a human before
any conclusion is acted on.
